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
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file, send_from_directory

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from config import *

app = Flask(__name__)

CLIENT_PICKS_FILE = DATA_DIR / "client_picks.json"
THUMBS_DIR = DATA_DIR / "thumbs"
THUMBS_DIR.mkdir(exist_ok=True)
LOGOS_DIR = PROJECT_DIR / "logos"
DESIGN_BRIEF_FILE = DATA_DIR / "design_brief.json"
USAGE_FILE = DATA_DIR / "usage.json"

# ── Workspace helpers (dynamic — reads disk each call so switching works) ─────
def _read_workspaces():
    if WORKSPACES_FILE.exists():
        try:
            return json.loads(WORKSPACES_FILE.read_text()).get("workspaces", [])
        except Exception:
            pass
    return []

def _write_workspaces(ws_list):
    WORKSPACES_FILE.write_text(json.dumps({"workspaces": ws_list}, indent=2))

def _get_active_workspace():
    ws_list = _read_workspaces()
    if not ws_list:
        return {"id": "default", "name": "Main Shoot", "folder": PHOTOS_FOLDER, "type": WORKSPACE_TYPE}
    active_id = ws_list[0]["id"]
    if ACTIVE_WS_FILE.exists():
        try:
            active_id = json.loads(ACTIVE_WS_FILE.read_text()).get("id", active_id)
        except Exception:
            pass
    for ws in ws_list:
        if ws["id"] == active_id:
            return ws
    return ws_list[0]

def _ws_data_dir():
    ws = _get_active_workspace()
    d = DATA_DIR / ws["id"]
    d.mkdir(parents=True, exist_ok=True)
    return d

def _get_catalog_file():      return _ws_data_dir() / "catalog.json"
def _get_groups_file():       return _ws_data_dir() / "groups.json"
def _get_manual_groups_file(): return _ws_data_dir() / "manual_groups.json"
def _get_semantic_groups_file(): return _ws_data_dir() / "semantic_groups.json"

MONTHLY_BUDGET = float(os.getenv("MONTHLY_BUDGET", "0") or "0")


def log_usage(cost):
    """Append cost to the persistent usage log (data/usage.json)."""
    if not cost:
        return
    try:
        data = json.loads(USAGE_FILE.read_text()) if USAGE_FILE.exists() else {}
        data["total_cost"] = round(data.get("total_cost", 0) + cost, 6)
        USAGE_FILE.write_text(json.dumps(data))
    except Exception:
        pass  # non-critical

# ── Claude model pricing (per million tokens) ────────────────────────────────
_MODEL_PRICING = {
    "claude-opus-4-6":            {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6":          {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5":           {"input":  0.25, "output":  1.25},
    "claude-haiku-4-5-20251001":  {"input":  0.25, "output":  1.25},
    "claude-3-5-sonnet-20241022": {"input":  3.00, "output": 15.00},
    "claude-3-5-haiku-20241022":  {"input":  0.80, "output":  4.00},
}
_DEFAULT_PRICING = {"input": 3.00, "output": 15.00}

def calc_cost(model, input_tokens, output_tokens):
    p = _MODEL_PRICING.get(model, _DEFAULT_PRICING)
    return round((input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000, 6)

# ── In-memory catalog cache ───────────────────────────────────────────────────
_catalog_cache = []
_catalog_mtime = 0.0
_catalog_ws_id = None  # invalidate when workspace switches

def load_catalog():
    global _catalog_cache, _catalog_mtime, _catalog_ws_id
    f = _get_catalog_file()
    ws_id = _get_active_workspace()["id"]
    if not f.exists():
        return []
    mtime = f.stat().st_mtime
    if mtime != _catalog_mtime or ws_id != _catalog_ws_id:
        with open(f) as fh:
            _catalog_cache = json.load(fh)
        _catalog_mtime = mtime
        _catalog_ws_id = ws_id
    return _catalog_cache


def _invalidate_cache():
    global _catalog_mtime
    _catalog_mtime = 0.0


def save_catalog(catalog):
    f = _get_catalog_file()
    with open(f, "w") as fh:
        json.dump(catalog, fh, indent=2)
    _invalidate_cache()


def save_groups_manual(groups):
    f = _get_manual_groups_file()
    with open(f, "w") as fh:
        json.dump(groups, fh, indent=2)


def load_groups():
    """Load groups. Priority: manual_groups.json > semantic_groups.json > groups.json."""
    mf = _get_manual_groups_file()
    sf = _get_semantic_groups_file()
    gf = _get_groups_file()

    if mf.exists():
        with open(mf) as f:
            return json.load(f)
    if sf.exists():
        with open(sf) as f:
            raw = json.load(f)
        return [
            {
                "id": f"scene_{i}",
                "is_group": True,
                "theme": g["name"],
                "photo_ids": g["photo_ids"],
                "best_photo_id": None,
                "recommendation": "",
                "photo_notes": {},
                "has_claude_comparison": False,
                "is_semantic": True,
            }
            for i, g in enumerate(raw)
        ]
    if gf.exists():
        with open(gf) as f:
            return json.load(f)
    return None


@app.route("/")
def home():
    """Home / landing page."""
    return render_template("home.html")


@app.route("/dashboard")
def index():
    """Main review dashboard."""
    return render_template("review.html")


@app.route("/api/photos")
def get_photos():
    """Return all photos from the catalog.
    Frontend filters by tab (Top Photos requires claude_analysis, etc.).
    Returning all photos ensures visual search can surface unanalyzed photos.
    """
    catalog = load_catalog()

    def _sort_key(p):
        return (p.get("claude_analysis") or {}).get("score", 0) or p.get("overall_score", 0) / 10

    result = [p for p in catalog if not p.get("error")]
    result.sort(key=_sort_key, reverse=True)
    return jsonify(result)


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


@app.route("/api/photos/reset-all", methods=["POST"])
def reset_all_photos():
    """Reset every photo's approval status back to pending."""
    catalog = load_catalog()
    count = 0
    for photo in catalog:
        if photo.get("approved") is not None:
            photo["approved"] = None
            count += 1
    save_catalog(catalog)
    return jsonify({"reset": count})


@app.route("/api/photos/<int:photo_id>/exif")
def get_exif(photo_id):
    """Return EXIF data (camera settings) for a photo."""
    catalog = load_catalog()
    photo = next((p for p in catalog if p.get("id") == photo_id), None)
    if not photo:
        return jsonify({"error": "Photo not found"}), 404
    file_path = Path(photo.get("file", ""))
    if not file_path.exists():
        return jsonify({})
    try:
        from PIL import Image as _PILImage, ExifTags as _ExifTags
        img = _PILImage.open(file_path)
        raw_exif = img.getexif() if hasattr(img, 'getexif') else {}
        tag_map = {v: k for k, v in _ExifTags.TAGS.items()}
        def _get(name):
            tag_id = tag_map.get(name)
            return raw_exif.get(tag_id) if tag_id else None
        # Shutter speed as human-readable fraction
        et = _get("ExposureTime")
        if et and hasattr(et, 'numerator'):
            if et.numerator == 1 or et < 0.5:
                shutter = f"1/{round(et.denominator / et.numerator)}s"
            else:
                shutter = f"{float(et):.1f}s"
        elif et:
            shutter = f"1/{round(1/et)}s" if et < 0.5 else f"{et:.1f}s"
        else:
            shutter = None
        fn = _get("FNumber")
        aperture = f"f/{float(fn):.1f}" if fn else None
        iso = _get("ISOSpeedRatings")
        fl = _get("FocalLength")
        focal = f"{round(float(fl))}mm" if fl else None
        make  = _get("Make") or ""
        model = (_get("Model") or "").replace(make, "").strip()
        dt = _get("DateTimeOriginal") or _get("DateTime")
        return jsonify({
            "shutter":   shutter,
            "aperture":  aperture,
            "iso":       iso,
            "focal":     focal,
            "camera":    model or make or None,
            "datetime":  dt,
        })
    except Exception as e:
        return jsonify({})


@app.route("/api/groups/approve-best", methods=["POST"])
def approve_best_from_groups():
    """Approve the highest-scoring photo from each group. Skip the rest."""
    groups = load_groups()
    if not groups:
        return jsonify({"approved": 0, "skipped": 0})
    catalog = load_catalog()
    photo_by_id = {p.get("id"): p for p in catalog}
    approved_ids = []
    skipped_ids  = []
    for group in groups:
        if not group.get("is_group") or len(group.get("photo_ids", [])) < 2:
            continue
        photos = [photo_by_id[pid] for pid in group["photo_ids"] if pid in photo_by_id]
        if not photos:
            continue
        # Pick the photo with the highest Claude score, falling back to local quality score
        best = max(photos, key=lambda p: (
            (p.get("claude_analysis") or {}).get("score", 0) or p.get("overall_score", 0)
        ))
        for p in photos:
            if p["id"] == best["id"]:
                if p.get("approved") is None:
                    p["approved"] = True
                    approved_ids.append(p["id"])
            else:
                if p.get("approved") is None:
                    p["approved"] = False
                    skipped_ids.append(p["id"])
    if approved_ids or skipped_ids:
        save_catalog(catalog)
    return jsonify({"approved": len(approved_ids), "skipped": len(skipped_ids)})


@app.route("/api/auto-reject", methods=["POST"])
def auto_reject_failures():
    """
    Preview or apply auto-rejection of obvious technical failures.
    POST { dry_run: true }  → returns count + sample filenames, does NOT save
    POST { dry_run: false } → applies rejections, returns count

    Uses LOCAL quality scores only (sharpness, exposure, contrast, resolution, etc.)
    on a 0-100 scale — NOT Claude's subjective score. This catches blurry, dark,
    low-resolution, and flat photos regardless of how Claude rated the composition.
    Default threshold 35/100 catches obvious technical failures.
    """
    data = request.json or {}
    threshold = float(data.get("threshold", 35))
    dry_run   = data.get("dry_run", True)
    catalog   = load_catalog()

    def _local_quality(p):
        """Return the local (pixel-based) overall quality score, 0-100."""
        return float(p.get("overall_score", 100))

    candidates = [
        p for p in catalog
        if p.get("approved") is None
        and _local_quality(p) < threshold
    ]
    if dry_run:
        return jsonify({
            "count": len(candidates),
            "samples": [p["filename"] for p in candidates[:8]],
        })
    for p in candidates:
        p["approved"] = False
    if candidates:
        save_catalog(catalog)
    return jsonify({"rejected": len(candidates)})


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
        has_analysis = bool(
            p.get("claude_analysis")
            and "error" not in p.get("claude_analysis", {})
        )
        result.append({
            "id": p.get("id"),
            "filename": p.get("filename"),
            "overall_score": p.get("overall_score", 0),
            "scores": p.get("scores", {}),
            "width": p.get("width"),
            "height": p.get("height"),
            "megapixels": p.get("megapixels"),
            "has_analysis": has_analysis,
            "claude_score": p.get("claude_analysis", {}).get("score") if has_analysis else None,
            "approved": p.get("approved"),
            "client_pick": p.get("client_pick", False),
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
        # Resize image for API — supports both standard and RAW formats
        import sys as _sys
        _sys.path.insert(0, str(PROJECT_DIR / "scripts"))
        from utils import open_image as _open_image
        img = _open_image(photo["file"], half_size=False)
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

        input_tok = message.usage.input_tokens
        output_tok = message.usage.output_tokens
        actual_cost = calc_cost(CLAUDE_MODEL, input_tok, output_tok)
        log_usage(actual_cost)

        return jsonify({
            "status": "ok",
            "analysis": analysis,
            "input_tokens": input_tok,
            "output_tokens": output_tok,
            "actual_cost": actual_cost,
            "model": CLAUDE_MODEL,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/import_client_picks", methods=["POST"])
def import_client_picks():
    """
    Parse a [PICKS:file1.jpg,file2.jpg,...] code pasted from a client's email
    and mark those photos as client_pick=True in the catalog.
    """
    data = request.get_json(force=True)
    raw = data.get("text", "")

    # Extract [PICKS:...] code from anywhere in the pasted text
    import re
    match = re.search(r'\[PICKS:([^\]]+)\]', raw)
    if not match:
        # Also try plain comma-separated filenames if no code wrapper
        filenames = [f.strip() for f in raw.split(",") if f.strip()]
        if not filenames:
            return jsonify({"status": "error", "message": "No picks code found. Make sure to paste the full email including the [PICKS:...] line at the bottom."}), 400
    else:
        filenames = [f.strip() for f in match.group(1).split(",") if f.strip()]

    catalog = load_catalog()

    # Clear old client picks first
    for p in catalog:
        p.pop("client_pick", None)

    # Match by filename (case-insensitive)
    filename_lower = {f.lower() for f in filenames}
    matched = []
    for p in catalog:
        if p.get("filename", "").lower() in filename_lower:
            p["client_pick"] = True
            matched.append(p["filename"])

    save_catalog(catalog)

    return jsonify({
        "status": "success",
        "matched": len(matched),
        "total_in_code": len(filenames),
        "filenames": matched,
    })


@app.route("/api/client_picks")
def get_client_picks():
    """Return all photos marked as client picks."""
    catalog = load_catalog()
    picks = [p for p in catalog if p.get("client_pick")]
    return jsonify({"count": len(picks), "filenames": [p["filename"] for p in picks]})


@app.route("/api/export_client_proof", methods=["POST"])
def export_client_proof():
    """Generate a standalone client_proof.html and return its path."""
    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_DIR / "scripts" / "05_export_client_proof.py")],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_DIR),
        )
        out_path = PROJECT_DIR / "exports" / "client_proof.html"
        if result.returncode == 0 and out_path.exists():
            size_mb = round(out_path.stat().st_size / (1024 * 1024), 1)
            return jsonify({
                "status": "success",
                "path": str(out_path),
                "size_mb": size_mb,
            })
        return jsonify({"status": "error", "message": result.stderr or result.stdout}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/groups/<group_id>/remove/<int:photo_id>", methods=["POST"])
def group_remove_photo(group_id, photo_id):
    """Remove a single photo from a group. If group drops to 1 photo, dissolve it."""
    groups = load_groups()
    if not groups:
        return jsonify({"error": "No groups"}), 404
    group = next((g for g in groups if g["id"] == group_id), None)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    group["photo_ids"] = [pid for pid in group["photo_ids"] if pid != photo_id]
    if len(group["photo_ids"]) <= 1:
        groups = [g for g in groups if g["id"] != group_id]  # dissolve singleton groups
    save_groups_manual(groups)
    return jsonify({"status": "ok", "remaining": len(group.get("photo_ids", []))})


@app.route("/api/groups/create", methods=["POST"])
def group_create():
    """Create a new custom group from a list of photo IDs."""
    data = request.json or {}
    photo_ids = data.get("photo_ids", [])
    theme = data.get("theme", "Custom Group")
    if len(photo_ids) < 2:
        return jsonify({"error": "Need at least 2 photos to form a group"}), 400
    groups = load_groups() or []
    # Remove these photos from any existing groups first
    for g in groups:
        g["photo_ids"] = [pid for pid in g["photo_ids"] if pid not in photo_ids]
    # Keep all non-empty entries (including single-photo placeholders from groups.json)
    # Only truly empty groups get dissolved
    groups = [g for g in groups if len(g["photo_ids"]) >= 1]
    import uuid
    new_group = {
        "id": f"custom_{uuid.uuid4().hex[:8]}",
        "is_group": True,
        "theme": theme,
        "photo_ids": photo_ids,
        "best_photo_id": None,
        "recommendation": "",
        "photo_notes": {},
        "has_claude_comparison": False,
    }
    groups.append(new_group)
    save_groups_manual(groups)
    return jsonify({"status": "ok", "group_id": new_group["id"], "theme": theme})


@app.route("/api/groups/<group_id>/rename", methods=["POST"])
def group_rename(group_id):
    """Rename a group's theme label."""
    data = request.json or {}
    new_theme = data.get("theme", "").strip()
    if not new_theme:
        return jsonify({"error": "Theme required"}), 400
    groups = load_groups()
    if not groups:
        return jsonify({"error": "No groups"}), 404
    group = next((g for g in groups if g["id"] == group_id), None)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    group["theme"] = new_theme
    save_groups_manual(groups)
    return jsonify({"status": "ok"})


@app.route("/api/regroup", methods=["POST"])
def regroup():
    """
    Re-run Step 2B (visual hash grouping) with an optional threshold.
    Streams PROGRESS:pct:message lines so the frontend can show a progress bar,
    then ends with a JSON status line: {"status":"ok"} or {"status":"error",...}
    """
    import os
    from flask import stream_with_context, Response

    data = request.json or {}
    threshold = int(data.get("threshold", 10))
    threshold = max(4, min(20, threshold))
    mf = _get_manual_groups_file()
    if mf.exists():
        mf.rename(mf.with_suffix(".json.bak"))

    full_env = {**os.environ, "HASH_THRESHOLD": str(threshold), "PYTHONUNBUFFERED": "1"}

    def generate():
        try:
            proc = subprocess.Popen(
                [sys.executable, str(PROJECT_DIR / "scripts" / "02b_group_photos.py")],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, cwd=str(PROJECT_DIR), env=full_env,
            )
            for line in proc.stdout:
                yield line          # pass every line through (PROGRESS: lines + normal output)
            proc.wait()
            if proc.returncode == 0:
                yield '{"status":"ok"}\n'
            else:
                yield f'{{"status":"error","message":"Exit code {proc.returncode}"}}\n'
        except Exception as e:
            yield f'{{"status":"error","message":{json.dumps(str(e))}}}\n'

    return Response(stream_with_context(generate()), mimetype="text/plain")


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
    # Optional ?ids= filter (sent when user selects a subset in the overlay)
    ids_param = request.args.get("ids", "")
    if ids_param:
        try:
            allowed = set(int(i) for i in ids_param.split(",") if i.strip())
            photos = [photo_by_id[pid] for pid in group["photo_ids"] if pid in photo_by_id and pid in allowed]
        except ValueError:
            photos = [photo_by_id[pid] for pid in group["photo_ids"] if pid in photo_by_id]
    else:
        photos = [photo_by_id[pid] for pid in group["photo_ids"] if pid in photo_by_id]
    return render_template("compare.html", group=group, photos=photos)


@app.route("/compare-selected")
def compare_selected():
    """Compare an arbitrary set of photos by ID (multi-select from dashboard)."""
    ids_param = request.args.get("ids", "")
    try:
        ids = [int(i) for i in ids_param.split(",") if i.strip()]
    except ValueError:
        return "Invalid photo IDs.", 400
    if len(ids) < 2:
        return "Select at least 2 photos to compare.", 400

    catalog = load_catalog()
    photo_by_id = {p.get("id"): p for p in catalog}
    photos = [photo_by_id[i] for i in ids if i in photo_by_id]
    if not photos:
        return "Photos not found.", 404

    analyzed = [
        p for p in photos
        if isinstance(p.get("claude_analysis"), dict)
        and "error" not in p.get("claude_analysis", {})
    ]
    best = (
        max(analyzed, key=lambda p: p["claude_analysis"].get("score", 0))
        if analyzed else photos[0]
    )
    group = {
        "id": f"custom_{'_'.join(str(i) for i in ids)}",
        "theme": "Selected Photos",
        "photo_ids": ids,
        "best_photo_id": best["id"],
        "recommendation": "",
        "photo_notes": {},
        "is_group": True,
        "has_claude_comparison": False,
    }
    return render_template("compare.html", group=group, photos=photos)


@app.route("/api/compare-photos", methods=["POST"])
def api_compare_photos():
    """
    Send a set of photos to Claude for side-by-side comparison analysis.
    Accepts JSON: { "ids": [1, 2, 3] }
    Returns: { best_photo_id, recommendation, theme, notes: {id: text}, actual_cost, ... }
    """
    import anthropic as _anthropic
    import base64
    from io import BytesIO
    from PIL import Image as _Image

    data = request.get_json(force=True)
    ids  = [int(i) for i in data.get("ids", [])]
    if len(ids) < 2:
        return jsonify({"error": "Need at least 2 photos to compare"}), 400

    catalog = load_catalog()
    photo_by_id = {p.get("id"): p for p in catalog}
    photos = [photo_by_id[i] for i in ids if i in photo_by_id]
    if len(photos) < 2:
        return jsonify({"error": "Photos not found"}), 404

    def resize_img(file_path, max_size=900):
        try:
            from scripts.utils import open_image
            img = open_image(file_path, half_size=False)
        except Exception:
            img = _Image.open(file_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), _Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=82)
        return base64.standard_b64encode(buf.getvalue()).decode("utf-8")

    content = []
    for i, photo in enumerate(photos):
        try:
            b64 = resize_img(photo["file"])
        except Exception as e:
            return jsonify({"error": f"Could not read photo {photo['filename']}: {e}"}), 500
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})
        a = photo.get("claude_analysis") or {}
        score_line = f"  (Claude score: {a['score']}/10)" if a.get("score") else ""
        content.append({"type": "text", "text": f"Photo {i+1}: {photo['filename']}{score_line}"})

    n = len(photos)
    photos_json = "\n".join(f'        "{i+1}": "...'   for i in range(n))
    content.append({"type": "text", "text": f"""You are an expert photography editor comparing {n} similar shots.

Compare these photos carefully and respond in EXACTLY this JSON format (no other text):

{{
    "group_theme": "Brief description of the scene (5-8 words)",
    "best_photo_index": 1,
    "recommendation": "One clear sentence: why Photo X is the best choice.",
    "photos": {{
        "1": "2-3 sentences covering sharpness, exposure, framing, expression/eyes. Be specific about what differs from the others.",
        "2": "Same format for Photo 2.",
        "3": "Same format for Photo 3."
    }}
}}

Focus on DIFFERENCES between photos. For portraits always check and state eye status (open/closed/blinking). Note exposure, sharpness, composition, expression, and decisive moment differences. Be direct and photographer-friendly."""})

    try:
        client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": content}],
        )
        raw = message.content[0].text.strip() if message.content else ""
        if not raw:
            return jsonify({"error": "Claude returned an empty response. Please try again."}), 500
        # Robustly extract the JSON object, even when wrapped in ``` or preceded by text
        import re as _re
        json_match = _re.search(r'\{[\s\S]*\}', raw)
        if not json_match:
            return jsonify({"error": f"Claude didn't return JSON. Response: {raw[:300]}"}), 500
        result = json.loads(json_match.group(0))

        # Resolve best photo
        best_idx = result.get("best_photo_index", 1)
        if isinstance(best_idx, int) and 1 <= best_idx <= len(photos):
            best_photo = photos[best_idx - 1]
        else:
            analyzed = [p for p in photos if p.get("claude_analysis", {}).get("score")]
            best_photo = max(analyzed, key=lambda p: p["claude_analysis"]["score"]) if analyzed else photos[0]

        # Map photo index keys → photo id keys
        notes_by_id = {}
        for k, note in result.get("photos", {}).items():
            try:
                idx = int(k) - 1
                if 0 <= idx < len(photos):
                    notes_by_id[str(photos[idx]["id"])] = note
            except (ValueError, IndexError):
                pass

        input_tok  = message.usage.input_tokens
        output_tok = message.usage.output_tokens
        cost = calc_cost(CLAUDE_MODEL, input_tok, output_tok)
        log_usage(cost)

        return jsonify({
            "best_photo_id":  best_photo["id"],
            "recommendation": result.get("recommendation", ""),
            "theme":          result.get("group_theme", ""),
            "notes":          notes_by_id,
            "input_tokens":   input_tok,
            "output_tokens":  output_tok,
            "actual_cost":    cost,
        })
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Claude returned invalid JSON: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/scene/<group_id>")
def scene_page(group_id):
    """Grid view for a semantic scene group — shows all photos in the scene."""
    groups = load_groups()
    if not groups:
        return "No groups found. Run Step 4c first.", 404
    catalog = load_catalog()
    photo_by_id = {p.get("id"): p for p in catalog}
    group = next((g for g in groups if g["id"] == group_id), None)
    if not group:
        return "Scene not found.", 404
    photos = [photo_by_id[pid] for pid in group["photo_ids"] if pid in photo_by_id]
    return render_template("scene.html", group=group, photos=photos)


@app.route("/api/groups")
def get_groups():
    """Return photos organized into groups. Falls back to flat list if no groups file."""
    catalog = load_catalog()
    groups = load_groups()

    # Build a lookup dict of ALL photos by id (not just analyzed)
    photo_by_id = {p.get("id"): p for p in catalog}

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
                    "has_claude_comparison": False,
                })
        result.sort(key=lambda g: ((g.get("best_photo") or {}).get("claude_analysis") or {}).get("score", 0), reverse=True)
        return jsonify(result)

    # Build enriched group list — include all photos, not just analyzed
    # Deduplicate: each photo appears in at most one group (first-seen wins)
    seen_photo_ids = set()
    result = []
    for group in groups:
        unique_ids = [pid for pid in group["photo_ids"] if pid not in seen_photo_ids]
        if not unique_ids:
            continue
        seen_photo_ids.update(unique_ids)
        photos = [photo_by_id[pid] for pid in unique_ids if pid in photo_by_id]
        if not photos:
            continue
        # Update photo_ids to deduplicated list
        group = {**group, "photo_ids": unique_ids}
        if group.get("best_photo_id") and group["best_photo_id"] in photo_by_id:
            best_photo = photo_by_id[group["best_photo_id"]]
        else:
            # Semantic group — pick highest-scoring analyzed photo, fall back to local score
            analyzed_in_group = [
                p for p in photos
                if isinstance(p.get("claude_analysis"), dict)
                and "error" not in p.get("claude_analysis", {})
            ]
            if analyzed_in_group:
                best_photo = max(analyzed_in_group, key=lambda p: p["claude_analysis"].get("score", 0))
            else:
                best_photo = max(photos, key=lambda p: p.get("overall_score", 0))

        # Group approval = True if best photo approved, False if best photo rejected
        approved = best_photo.get("approved")
        analyzed_count = sum(
            1 for p in photos
            if isinstance(p.get("claude_analysis"), dict) and "error" not in p.get("claude_analysis", {})
        )

        result.append({
            **group,
            "photos": photos,
            "best_photo": best_photo,
            "approved": approved,
            "analyzed_count": analyzed_count,
        })

    # Sort by best photo's Claude score, highest first
    result.sort(key=lambda g: ((g.get("best_photo") or {}).get("claude_analysis") or {}).get("score", 0), reverse=True)

    return jsonify(result)


@app.route("/api/export_raws", methods=["POST"])
def export_raws():
    """
    Find the RAW file counterpart for every approved photo and copy them
    into exports/ready_to_edit/ — drag that folder into Lightroom/Capture One.
    """
    catalog = load_catalog()
    approved = [p for p in catalog if p.get("approved") is True]

    if not approved:
        return jsonify({"status": "error", "message": "No approved photos yet. Approve some photos first."}), 400

    export_dir = PROJECT_DIR / "exports" / "ready_to_edit"
    export_dir.mkdir(parents=True, exist_ok=True)

    # Clear previous export
    for old in export_dir.iterdir():
        old.unlink()

    copied = []
    missing = []

    for photo in approved:
        jpg_path = Path(photo["file"])
        stem = jpg_path.stem
        parent = jpg_path.parent

        # Look for a matching RAW file alongside the JPG
        found_raw = None
        for ext in RAW_FORMATS:
            for candidate in [stem + ext, stem + ext.upper()]:
                raw_path = parent / candidate
                if raw_path.exists():
                    found_raw = raw_path
                    break
            if found_raw:
                break

        if found_raw:
            dest = export_dir / found_raw.name
            shutil.copy2(found_raw, dest)
            copied.append(found_raw.name)
        else:
            missing.append(jpg_path.name)

    # Also open the folder in Finder on Mac
    try:
        subprocess.run(["open", str(export_dir)], check=False)
    except Exception:
        pass

    return jsonify({
        "status": "success",
        "copied": len(copied),
        "missing": len(missing),
        "export_path": str(export_dir),
        "files": copied,
        "no_raw_found": missing,
    })


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


@app.route("/api/workspaces")
def get_workspaces():
    ws_list = _read_workspaces()
    active = _get_active_workspace()
    return jsonify({"workspaces": ws_list, "active_id": active["id"]})


@app.route("/api/workspaces", methods=["POST"])
def create_workspace():
    import re, time as _time
    data = request.get_json(force=True)
    name   = data.get("name", "").strip()
    folder = data.get("folder", "").strip()
    ws_type = data.get("type", "shoot")

    if not name or not folder:
        return jsonify({"error": "name and folder are required"}), 400

    folder = folder.strip("'\"")
    path = Path(folder) if Path(folder).is_absolute() else PROJECT_DIR / folder
    if not path.exists():
        return jsonify({"error": f"Folder not found: {folder}"}), 400

    ws_id = re.sub(r"[^a-z0-9]", "_", name.lower())[:20].strip("_") + f"_{int(_time.time()) % 100000}"
    ws_list = _read_workspaces()
    ws_list.append({"id": ws_id, "name": name, "folder": str(path), "type": ws_type})
    _write_workspaces(ws_list)
    (DATA_DIR / ws_id).mkdir(parents=True, exist_ok=True)
    return jsonify({"id": ws_id, "name": name, "folder": str(path), "type": ws_type})


@app.route("/api/workspaces/<ws_id>/activate", methods=["POST"])
def activate_workspace(ws_id):
    ws_list = _read_workspaces()
    if not any(w["id"] == ws_id for w in ws_list):
        return jsonify({"error": "Workspace not found"}), 404
    ACTIVE_WS_FILE.write_text(json.dumps({"id": ws_id}))
    _invalidate_cache()
    ws = next(w for w in ws_list if w["id"] == ws_id)
    return jsonify({"active_id": ws_id, "workspace": ws})


@app.route("/api/workspaces/<ws_id>", methods=["DELETE"])
def delete_workspace(ws_id):
    ws_list = _read_workspaces()
    if len(ws_list) <= 1:
        return jsonify({"error": "Cannot delete the only workspace"}), 400
    ws_list = [w for w in ws_list if w["id"] != ws_id]
    _write_workspaces(ws_list)
    active = _get_active_workspace()
    if active["id"] == ws_id:
        ACTIVE_WS_FILE.write_text(json.dumps({"id": ws_list[0]["id"]}))
        _invalidate_cache()
    return jsonify({"ok": True})


@app.route("/api/stats")
def get_stats():
    """Get review progress statistics."""
    catalog = load_catalog()
    analyzed = [
        p for p in catalog
        if p.get("claude_analysis") and "error" not in (p.get("claude_analysis") or {})
    ]
    # Count across ALL photos, not just analyzed ones
    approved = [p for p in catalog if p.get("approved") is True]
    rejected = [p for p in catalog if p.get("approved") is False]
    pending  = [p for p in catalog if p.get("approved") is None]

    return jsonify({
        "total_photos": len(catalog),
        "analyzed": len(analyzed),
        "approved": len(approved),
        "rejected": len(rejected),
        "pending": len(pending),
    })


@app.route("/api/usage")
def get_usage():
    """Return persistent cumulative API cost + optional monthly budget."""
    data = json.loads(USAGE_FILE.read_text()) if USAGE_FILE.exists() else {}
    return jsonify({
        "total_cost": data.get("total_cost", 0),
        "budget":     MONTHLY_BUDGET,
    })


@app.route("/api/usage/reset", methods=["POST"])
def reset_usage():
    """Reset the persistent usage counter to zero."""
    USAGE_FILE.write_text(json.dumps({"total_cost": 0}))
    return jsonify({"status": "reset"})


def _photo_path(photo_id):
    """Look up a photo's file path from the catalog. Returns Path or None."""
    for photo in load_catalog():
        if photo.get("id") == photo_id:
            return Path(photo["file"])
    return None


def _make_jpeg(file_path, max_size=None):
    """
    Open any supported photo (including RAW) and return a JPEG BytesIO.
    Optionally resize so the longest edge <= max_size.
    """
    from io import BytesIO
    from PIL import Image as _Image
    suffix = file_path.suffix.lower()
    if suffix in RAW_FORMATS:
        import rawpy
        with rawpy.imread(str(file_path)) as raw:
            rgb = raw.postprocess(use_camera_wb=True, half_size=True,
                                  no_auto_bright=False, output_bps=8)
        img = _Image.fromarray(rgb)
    else:
        img = _Image.open(file_path)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

    if max_size and max(img.size) > max_size:
        ratio = max_size / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)),
                         _Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=82)
    buf.seek(0)
    return buf


@app.route("/thumb/<int:photo_id>")
def serve_thumb(photo_id):
    """
    Serve a 400px thumbnail. Generated once and cached to data/thumbs/.
    Grid views use this instead of full-res — much faster page loads.
    """
    thumb_path = THUMBS_DIR / f"{photo_id}.jpg"
    if thumb_path.exists():
        resp = send_file(thumb_path, mimetype="image/jpeg")
        resp.headers["Cache-Control"] = "public, max-age=604800"
        return resp

    file_path = _photo_path(photo_id)
    if not file_path or not file_path.exists():
        return "Photo not found", 404

    try:
        buf = _make_jpeg(file_path, max_size=400)
        thumb_path.write_bytes(buf.getvalue())
        buf.seek(0)
        resp = send_file(buf, mimetype="image/jpeg")
        resp.headers["Cache-Control"] = "public, max-age=604800"
        return resp
    except Exception as e:
        return f"Could not generate thumbnail: {e}", 500


@app.route("/photo/<int:photo_id>")
def serve_photo(photo_id):
    """Serve a full-resolution photo. Used for modals and compare view."""
    file_path = _photo_path(photo_id)
    if not file_path:
        return "Photo not found in catalog", 404
    if not file_path.exists():
        return "Photo file not found", 404

    suffix = file_path.suffix.lower()
    if suffix in RAW_FORMATS:
        try:
            buf = _make_jpeg(file_path)
            resp = send_file(buf, mimetype="image/jpeg")
            resp.headers["Cache-Control"] = "public, max-age=86400"
            return resp
        except Exception as e:
            return f"Could not convert RAW file: {e}", 500

    resp = send_file(file_path)
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@app.route("/logos/<path:filename>")
def serve_logo(filename):
    """Serve logo assets from the logos/ directory."""
    return send_from_directory(LOGOS_DIR, filename)


@app.route("/website-design")
def website_design():
    """AI Website Design Consultant page."""
    return render_template("design_chat.html")


@app.route("/api/design-chat", methods=["POST"])
def design_chat():
    """
    Chat endpoint for the AI Website Design Consultant.
    Accepts conversation history, returns Claude's response + token costs.
    """
    import anthropic as _anthropic

    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your-api-key-here":
        return jsonify({"error": "No API key configured"}), 400

    data = request.get_json(force=True)
    messages = data.get("messages", [])
    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    # Estimate input tokens (rough: 4 chars ≈ 1 token)
    estimated_input = sum(len(m.get("content", "")) for m in messages) // 4 + 200
    estimated_cost = calc_cost(CLAUDE_MODEL, estimated_input, 600)

    system_prompt = """You are Cullo's AI Website Design Consultant — a friendly, expert creative director helping a photographer design their portfolio website.

Your job is to ask targeted questions to understand their vision, then synthesize the answers into a detailed design brief.

Ask questions one or two at a time, in a natural conversational flow. Cover these areas:
1. Overall style/vibe (editorial, moody, clean/minimal, bold/dramatic, warm/lifestyle)
2. Primary color preference (warm tones, cool tones, black & white, earthy, or custom)
3. Typography feel (modern sans-serif, classic serif, mixed)
4. Layout preference (full-screen hero, grid gallery, magazine-style)
5. Sections needed (about, services, contact, testimonials, blog)
6. What emotions should visitors feel when they land on the site
7. 2-3 websites they admire (for reference)
8. Any specific shots they want featured prominently

When you have enough information (typically 6-8 exchanges), output a complete design brief in this EXACT format:

---BRIEF_START---
{
  "style": "...",
  "primary_color": "...",
  "accent_color": "...",
  "typography": "...",
  "layout": "...",
  "sections": [...],
  "hero_mood": "...",
  "color_palette_description": "...",
  "inspiration_notes": "...",
  "featured_photo_strategy": "..."
}
---BRIEF_END---

Keep responses concise and warm. You're a collaborator, not a questionnaire."""

    try:
        client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system=system_prompt,
            messages=messages,
        )

        reply = response.content[0].text
        input_tok = response.usage.input_tokens
        output_tok = response.usage.output_tokens
        actual_cost = calc_cost(CLAUDE_MODEL, input_tok, output_tok)

        # Check if a brief was generated
        brief = None
        if "---BRIEF_START---" in reply and "---BRIEF_END---" in reply:
            import re
            match = re.search(r'---BRIEF_START---\s*(\{.*?\})\s*---BRIEF_END---', reply, re.DOTALL)
            if match:
                try:
                    brief = json.loads(match.group(1))
                    with open(DESIGN_BRIEF_FILE, "w") as f:
                        json.dump(brief, f, indent=2)
                    # Clean reply text (remove the raw JSON block)
                    reply = reply.replace(match.group(0), "\n\nI've saved your design brief! You can now click **Build Website** to generate your portfolio with these settings.").strip()
                except Exception:
                    pass

        return jsonify({
            "reply": reply,
            "input_tokens": input_tok,
            "output_tokens": output_tok,
            "actual_cost": actual_cost,
            "estimated_cost": estimated_cost,
            "model": CLAUDE_MODEL,
            "brief_saved": brief is not None,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/design-brief")
def get_design_brief():
    """Return the current saved design brief, if any."""
    if DESIGN_BRIEF_FILE.exists():
        with open(DESIGN_BRIEF_FILE) as f:
            return jsonify(json.load(f))
    return jsonify(None)


@app.route("/api/visual-search", methods=["POST"])
def api_visual_search():
    """
    Visual search: scan all photos with Claude Haiku Vision to find images matching a query.
    Accepts: { query: "girl with red jacket" }
    Returns: { matches: [photo_id, ...], total_scanned: N, actual_cost: X }

    Uses cached thumbnails (data/thumbs/) for speed. Sends batches of 20 to Claude Haiku.
    """
    import anthropic as _anthropic
    import base64 as _base64
    import re as _re
    import json as _json

    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your-api-key-here":
        return jsonify({"error": "No API key configured"}), 400

    data = request.get_json(force=True)
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "No query provided"}), 400

    catalog = load_catalog()
    searchable = [p for p in catalog if not p.get("error") and p.get("file") and p.get("id") is not None]

    BATCH_SIZE = 20
    THUMB_PX   = 200  # small enough to be cheap, large enough to see content

    def get_thumb_b64(photo):
        """Return base64 JPEG of the photo thumbnail (use cached if available)."""
        thumb_path = THUMBS_DIR / f"{photo['id']}.jpg"
        if thumb_path.exists():
            return _base64.standard_b64encode(thumb_path.read_bytes()).decode("utf-8")
        # Generate on the fly
        try:
            buf = _make_jpeg(Path(photo["file"]), max_size=THUMB_PX)
            thumb_path.write_bytes(buf.getvalue())
            buf.seek(0)
            return _base64.standard_b64encode(buf.read()).decode("utf-8")
        except Exception:
            return None

    client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    haiku_model = "claude-haiku-4-5-20251001"

    all_matches = []
    total_input = 0
    total_output = 0

    for batch_start in range(0, len(searchable), BATCH_SIZE):
        batch = searchable[batch_start:batch_start + BATCH_SIZE]

        content = []
        valid_in_batch = []
        for photo in batch:
            b64 = get_thumb_b64(photo)
            if b64 is None:
                continue
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
            })
            content.append({
                "type": "text",
                "text": f"[Photo {len(valid_in_batch) + 1}: {photo.get('filename','')}]",
            })
            valid_in_batch.append(photo)

        if not valid_in_batch:
            continue

        n = len(valid_in_batch)
        content.append({
            "type": "text",
            "text": (
                f'Look at these {n} photos. Which ones match this description: "{query}"?\n'
                f"Respond with ONLY a JSON array of the photo numbers (1-indexed) that match.\n"
                f"Example: [1, 3, 7]\n"
                f"If none match, respond with: []\n"
                f"No explanation needed."
            ),
        })

        try:
            resp = client.messages.create(
                model=haiku_model,
                max_tokens=120,
                messages=[{"role": "user", "content": content}],
            )
            total_input  += resp.usage.input_tokens
            total_output += resp.usage.output_tokens

            text = resp.content[0].text.strip()
            m = _re.search(r'\[[\d,\s]*\]', text)
            if m:
                indices = _json.loads(m.group())
                for idx in indices:
                    if isinstance(idx, int) and 1 <= idx <= len(valid_in_batch):
                        all_matches.append(valid_in_batch[idx - 1]["id"])
        except Exception:
            continue  # skip failed batches, don't abort entire search

    cost = calc_cost(haiku_model, total_input, total_output)
    log_usage(cost)

    return jsonify({
        "matches":       all_matches,
        "total_scanned": len(searchable),
        "actual_cost":   cost,
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Dashboard chatbot — Claude knows your catalog and can trigger actions.
    Accepts: { messages: [{role, content}], stats: {total, approved, pending, rejected} }
    Returns: { reply, action?, chips?, actual_cost }
    """
    import anthropic as _anthropic
    import re as _re

    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your-api-key-here":
        return jsonify({"error": "No API key configured"}), 400

    data = request.get_json(force=True)
    messages = data.get("messages", [])
    stats = data.get("stats", {})

    # Build catalog context
    catalog = load_catalog()
    analyzed = [p for p in catalog if p.get("claude_analysis") and "error" not in p.get("claude_analysis", {})]
    top = sorted(analyzed, key=lambda p: p.get("claude_analysis", {}).get("score", 0), reverse=True)[:8]
    top_lines = "\n".join(
        f"  #{i+1}: id={p['id']} {p['filename']} — {p.get('claude_analysis',{}).get('score','?')}/10 — {p.get('claude_analysis',{}).get('title','')} — {p.get('claude_analysis',{}).get('summary','')[:80]}"
        for i, p in enumerate(top)
    )
    # All analyzed photos for keyword grouping (id + filename + analysis summary)
    all_analyzed_lines = "\n".join(
        f"id={p['id']} {p['filename']}: {p.get('claude_analysis',{}).get('title','')} | {p.get('claude_analysis',{}).get('summary','')[:100]}"
        for p in analyzed
    )

    approved_n  = stats.get("approved", 0)
    pending_n   = stats.get("pending",  0)
    rejected_n  = stats.get("rejected", 0)
    total_n     = stats.get("total",    len(catalog))

    system = f"""You are Cullo's AI photo assistant — concise, helpful, photographer-friendly.

CURRENT SHOOT:
- Total scanned: {total_n}  |  Analyzed: {len(analyzed)}
- Approved: {approved_n}  |  Pending review: {pending_n}  |  Skipped: {rejected_n}

TOP PHOTOS BY SCORE:
{top_lines}

ALL ANALYZED PHOTOS (for grouping requests):
{all_analyzed_lines}

TRIGGERABLE ACTIONS — include ONE tag at the very end of your reply if appropriate:
[ACTION:approve_all_pending] — approve every pending photo
[ACTION:skip_all_pending]    — skip every pending photo
[ACTION:run_quick_cull]      — open Quick Cull keyboard mode
[ACTION:create_group:THEME:id1,id2,id3] — create a group from specific photo IDs (use real IDs from the list above)
[ACTION:visual_search:the search query] — visually scan all photos for something specific (use when the user says "find", "show me", "search for", "where is", or describes visual content like people/places/objects/colors)

RULES:
- Be direct and brief (1-3 sentences max)
- Use actual filenames and scores when relevant
- Only suggest an action if the user clearly wants it done
- For grouping requests: identify matching photos by keyword in their title/summary, list their IDs, and use [ACTION:create_group:THEME:id1,id2,...]
- For visual searches: use [ACTION:visual_search:description] — Claude will scan actual photo pixels
- If asked a stats question, answer it numerically
"""

    try:
        client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=350,
            system=system,
            messages=messages,
        )
        raw = response.content[0].text
        input_tok  = response.usage.input_tokens
        output_tok = response.usage.output_tokens
        cost = calc_cost(CLAUDE_MODEL, input_tok, output_tok)

        # Extract action tag — supports simple [ACTION:name] and [ACTION:create_group:THEME:ids]
        action = None
        action_data = None
        action_match = _re.search(r'\[ACTION:([^\]]+)\]', raw)
        if action_match:
            action_str = action_match.group(1)
            raw = raw[:action_match.start()].strip()
            if action_str.startswith("create_group:"):
                parts = action_str.split(":", 2)  # create_group, THEME, ids
                if len(parts) == 3:
                    action = "create_group"
                    action_data = {
                        "theme": parts[1],
                        "ids": [int(x) for x in parts[2].split(",") if x.strip().isdigit()],
                    }
            elif action_str.startswith("visual_search:"):
                action = "visual_search"
                action_data = {"query": action_str[len("visual_search:"):].strip()}
            else:
                action = action_str

        # Contextual quick-reply chips
        chips = []
        if pending_n > 0:
            chips.append(f"Approve all {pending_n} pending")
        chips.append("Show top 5 photos")
        chips.append("Start Quick Cull")
        chips = chips[:3]

        log_usage(cost)
        return jsonify({
            "reply":         raw,
            "action":        action,
            "action_data":   action_data,
            "chips":         chips if not action else [],
            "input_tokens":  input_tok,
            "output_tokens": output_tok,
            "actual_cost":   cost,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print()
    print("=" * 55)
    print("  STEP 3: Photo Review App")
    print("=" * 55)
    print()

    if not _get_catalog_file().exists():
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
    print("  Opening Cullo in your browser…")
    print("  (If it doesn't open, go to: http://localhost:5000)")
    print()
    print("  Press Ctrl+C to stop.")
    print()

    def _open_browser():
        time.sleep(1.5)
        webbrowser.open("http://localhost:8765")

    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host="0.0.0.0", port=8765, debug=False)
