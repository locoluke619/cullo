#!/usr/bin/env python3
"""
STEP 3: REVIEW YOUR PHOTOS
============================
This starts a local web app where you can review the photos
Claude analyzed, approve the ones you like, and then build
your website.

How to run:
    python app.py

Then open your browser to: http://localhost:5000
"""

import json
import subprocess
import sys
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from config import *

app = Flask(__name__)


GROUPS_FILE = DATA_DIR / "groups.json"
CLIENT_PICKS_FILE = DATA_DIR / "client_picks.json"


def load_catalog():
    """Load the photo catalog from disk."""
    if not CATALOG_FILE.exists():
        return []
    with open(CATALOG_FILE) as f:
        return json.load(f)


def save_catalog(catalog):
    """Save the photo catalog to disk."""
    with open(CATALOG_FILE, "w") as f:
        json.dump(catalog, f, indent=2)


def load_groups():
    """Load groups file if it exists."""
    if not GROUPS_FILE.exists():
        return None
    with open(GROUPS_FILE) as f:
        return json.load(f)


@app.route("/")
def index():
    """Main review page."""
    return render_template("review.html")


@app.route("/api/photos")
def get_photos():
    """Return all analyzed photos as JSON."""
    catalog = load_catalog()
    # Only return photos that have Claude analysis
    analyzed = [
        p for p in catalog
        if p.get("claude_analysis") and "error" not in p.get("claude_analysis", {})
    ]
    # Sort by Claude's score (highest first)
    analyzed.sort(
        key=lambda x: x.get("claude_analysis", {}).get("score", 0),
        reverse=True,
    )
    return jsonify(analyzed)


@app.route("/api/photos/<int:photo_id>/approve", methods=["POST"])
def approve_photo(photo_id):
    """Mark a photo as approved for the website."""
    catalog = load_catalog()
    for photo in catalog:
        if photo.get("id") == photo_id:
            photo["approved"] = True
            save_catalog(catalog)
            return jsonify({"status": "approved", "id": photo_id})
    return jsonify({"error": "Photo not found"}), 404


@app.route("/api/photos/<int:photo_id>/reject", methods=["POST"])
def reject_photo(photo_id):
    """Mark a photo as rejected (won't be on website)."""
    catalog = load_catalog()
    for photo in catalog:
        if photo.get("id") == photo_id:
            photo["approved"] = False
            save_catalog(catalog)
            return jsonify({"status": "rejected", "id": photo_id})
    return jsonify({"error": "Photo not found"}), 404


@app.route("/api/photos/<int:photo_id>/reset", methods=["POST"])
def reset_photo(photo_id):
    """Reset a photo's approval status."""
    catalog = load_catalog()
    for photo in catalog:
        if photo.get("id") == photo_id:
            photo["approved"] = None
            save_catalog(catalog)
            return jsonify({"status": "reset", "id": photo_id})
    return jsonify({"error": "Photo not found"}), 404


@app.route("/browse")
def browse_all():
    """Browse every photo with its local scores — rescue ones Claude missed."""
    return render_template("browse.html")


@app.route("/api/browse")
def api_browse():
    """Return all photos with local scores, sorted by score."""
    catalog = load_catalog()
    result = []
    for p in catalog:
        if "error" in p:
            continue
        result.append({
            "id": p.get("id"),
            "filename": p.get("filename"),
            "overall_score": p.get("overall_score", 0),
            "scores": p.get("scores", {}),
            "width": p.get("width"),
            "height": p.get("height"),
            "megapixels": p.get("megapixels"),
            "has_analysis": bool(
                p.get("claude_analysis")
                and "error" not in p.get("claude_analysis", {})
            ),
            "approved": p.get("approved"),
        })
    result.sort(key=lambda x: x["overall_score"], reverse=True)
    return jsonify(result)


@app.route("/api/photos/<int:photo_id>/analyze", methods=["POST"])
def analyze_single(photo_id):
    """Send a single photo to Claude for analysis (rescue from filtered-out pool)."""
    import anthropic as _anthropic
    import base64
    from io import BytesIO
    from PIL import Image as _Image

    catalog = load_catalog()
    photo = next((p for p in catalog if p.get("id") == photo_id), None)
    if not photo:
        return jsonify({"error": "Photo not found"}), 404

    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your-api-key-here":
        return jsonify({"error": "No API key configured"}), 400

    try:
        # Resize image for API
        with _Image.open(photo["file"]) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            if max(img.size) > 1280:
                ratio = 1280 / max(img.size)
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), _Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85)
            img_data = base64.standard_b64encode(buf.getvalue()).decode("utf-8")

        client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = """You are a professional photography educator and critic helping a photographer build a portfolio.

Analyze this photograph and respond in EXACTLY this JSON format (no other text):

{
    "title": "A short, evocative title (2-6 words)",
    "score": 8.5,
    "summary": "One sentence about the single strongest quality of this photo.",
    "score_reasoning": {
        "strengths": "2-3 specific reasons why this photo earned its score.",
        "weaknesses": "2-3 honest specific issues holding it back from a higher score."
    },
    "composition": "2-3 sentences on framing, rule of thirds, leading lines, balance.",
    "technical": "2-3 sentences on sharpness, exposure, noise, color balance, depth of field.",
    "mood": "1-2 sentences on the feeling or emotion this photo evokes.",
    "story": "1-2 sentences on the moment or story captured.",
    "editing_tips": [
        "Specific Lightroom/Photoshop tip with values (e.g. 'Lift shadows +25 to recover face detail')",
        "Second specific adjustment",
        "Crop or third editing note"
    ],
    "expression_notes": "For photos with people: quality of expressions, genuine vs forced, eye contact. Write 'No people' if none.",
    "eyes_check": "Note any closed eyes or blinks explicitly. Write 'All eyes open' or describe. Write 'N/A' if no people.",
    "website_worthy": true,
    "best_use": "hero image / gallery feature / supporting image"
}

Score 1-10. Set website_worthy true if score >= 6. Be specific and honest."""

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=900,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_data}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )

        response_text = message.content[0].text.strip()
        if "```" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            response_text = response_text[start:end]

        import json as _json
        analysis = _json.loads(response_text)
        photo["claude_analysis"] = analysis
        save_catalog(catalog)
        return jsonify({"status": "ok", "analysis": analysis})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/client")
def client_gallery():
    """Client-facing gallery where clients can heart their favourite photos."""
    return render_template("client_gallery.html")


@app.route("/api/client/photos")
def client_photos():
    """Return all approved photos for the client gallery."""
    catalog = load_catalog()
    picks = _load_client_picks()
    result = []
    for p in catalog:
        if not p.get("claude_analysis") or "error" in p.get("claude_analysis", {}):
            continue
        if p.get("approved") is False:
            continue
        a = p.get("claude_analysis", {})
        result.append({
            "id": p["id"],
            "filename": p["filename"],
            "title": a.get("title", p["filename"]),
            "score": a.get("score", 0),
            "summary": a.get("summary", ""),
            "hearted": p["id"] in picks,
        })
    result.sort(key=lambda x: x["score"], reverse=True)
    return jsonify(result)


@app.route("/api/client/heart/<int:photo_id>", methods=["POST"])
def client_heart(photo_id):
    """Toggle a heart/favourite on a photo."""
    picks = _load_client_picks()
    if photo_id in picks:
        picks.discard(photo_id)
        hearted = False
    else:
        picks.add(photo_id)
        hearted = True
    _save_client_picks(picks)
    return jsonify({"id": photo_id, "hearted": hearted, "total": len(picks)})


@app.route("/api/client/picks")
def client_picks_summary():
    """Return the list of hearted photo IDs and count."""
    picks = _load_client_picks()
    return jsonify({"count": len(picks), "ids": sorted(picks)})


def _load_client_picks():
    if not CLIENT_PICKS_FILE.exists():
        return set()
    with open(CLIENT_PICKS_FILE) as f:
        return set(json.load(f))


def _save_client_picks(picks):
    with open(CLIENT_PICKS_FILE, "w") as f:
        json.dump(sorted(picks), f)


@app.route("/compare/<group_id>")
def compare_page(group_id):
    """Dedicated comparison page for a group of similar photos."""
    groups = load_groups()
    if not groups:
        return "No groups found. Run Step 2B first.", 404
    catalog = load_catalog()
    photo_by_id = {p.get("id"): p for p in catalog}
    group = next((g for g in groups if g["id"] == group_id), None)
    if not group:
        return "Group not found.", 404
    photos = [photo_by_id[pid] for pid in group["photo_ids"] if pid in photo_by_id]
    return render_template("compare.html", group=group, photos=photos)


@app.route("/api/groups")
def get_groups():
    """Return photos organized into groups. Falls back to flat list if no groups file."""
    catalog = load_catalog()
    groups = load_groups()

    # Build a lookup dict of photos by id
    photo_by_id = {p.get("id"): p for p in catalog if p.get("claude_analysis") and "error" not in p.get("claude_analysis", {})}

    if not groups:
        # No grouping done — return each analyzed photo as its own "group"
        result = []
        for p in catalog:
            if p.get("claude_analysis") and "error" not in p.get("claude_analysis", {}):
                result.append({
                    "id": f"single_{p['id']}",
                    "is_group": False,
                    "theme": p.get("claude_analysis", {}).get("title", p["filename"]),
                    "best_photo_id": p["id"],
                    "photo_ids": [p["id"]],
                    "recommendation": "",
                    "photo_notes": {},
                    "photos": [p],
                    "best_photo": p,
                    "approved": p.get("approved"),
                })
        result.sort(key=lambda g: g["best_photo"].get("claude_analysis", {}).get("score", 0), reverse=True)
        return jsonify(result)

    # Build enriched group list
    result = []
    for group in groups:
        photos = [photo_by_id[pid] for pid in group["photo_ids"] if pid in photo_by_id]
        if not photos:
            continue
        best_photo = photo_by_id.get(group["best_photo_id"], photos[0])

        # Group approval = True if best photo approved, False if best photo rejected
        approved = best_photo.get("approved")

        result.append({
            **group,
            "photos": photos,
            "best_photo": best_photo,
            "approved": approved,
        })

    # Sort by best photo's Claude score, highest first
    result.sort(key=lambda g: g["best_photo"].get("claude_analysis", {}).get("score", 0), reverse=True)

    return jsonify(result)


@app.route("/api/build", methods=["POST"])
def build_website():
    """Trigger the website build script."""
    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_DIR / "scripts" / "03_build_website.py")],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_DIR),
        )
        return jsonify({
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "errors": result.stderr,
        })
    except Exception as e:
        return jsonify({"status": "error", "errors": str(e)}), 500


@app.route("/api/stats")
def get_stats():
    """Get review progress statistics."""
    catalog = load_catalog()
    analyzed = [
        p for p in catalog
        if p.get("claude_analysis") and "error" not in p.get("claude_analysis", {})
    ]
    approved = [p for p in analyzed if p.get("approved") is True]
    rejected = [p for p in analyzed if p.get("approved") is False]
    pending = [p for p in analyzed if p.get("approved") is None]

    return jsonify({
        "total_photos": len(catalog),
        "analyzed": len(analyzed),
        "approved": len(approved),
        "rejected": len(rejected),
        "pending": len(pending),
    })


@app.route("/photo/<int:photo_id>")
def serve_photo(photo_id):
    """Serve a photo file by its catalog ID."""
    catalog = load_catalog()
    for photo in catalog:
        if photo.get("id") == photo_id:
            file_path = Path(photo["file"])
            if file_path.exists():
                return send_file(file_path)
            return "Photo file not found", 404
    return "Photo not found in catalog", 404


if __name__ == "__main__":
    print()
    print("=" * 55)
    print("  STEP 3: Photo Review App")
    print("=" * 55)
    print()

    if not CATALOG_FILE.exists():
        print("  ERROR: No catalog found!")
        print("  Run Steps 1 and 2 first:")
        print("    python scripts/01_scan_and_score.py")
        print("    python scripts/02_analyze_with_claude.py")
        print()
        sys.exit(1)

    catalog = load_catalog()
    analyzed = [
        p for p in catalog
        if p.get("claude_analysis") and "error" not in p.get("claude_analysis", {})
    ]

    print(f"  Loaded {len(analyzed)} analyzed photos")
    print()
    print("  Opening review app...")
    print("  Go to: http://localhost:5000")
    print()
    print("  (Press Ctrl+C to stop the app)")
    print()

    app.run(debug=False, port=5000)
