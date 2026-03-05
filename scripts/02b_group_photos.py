#!/usr/bin/env python3
"""
STEP 2B: GROUP SIMILAR PHOTOS AND COMPARE THEM
================================================
This script finds photos of the same scene (burst shots, similar angles)
and groups them together. Then it sends each group to Claude so you can
see the subtle differences and pick the best one.

How to run:
    python scripts/02b_group_photos.py
"""

import anthropic
import base64
import json
import sys
from io import BytesIO
from pathlib import Path
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import *
from utils import open_image


# ==========================================
# PERCEPTUAL HASHING (no extra libraries)
# ==========================================

def compute_dhash(image_path, hash_size=8):
    """
    Difference hash: captures horizontal gradient patterns.
    Near-identical photos score < 8 apart.
    Different scenes score 20+ apart.
    Works with both standard and RAW files.
    """
    try:
        with open_image(image_path, half_size=True) as img:
            # Resize to (hash_size+1) x hash_size grayscale
            img = img.convert("L").resize(
                (hash_size + 1, hash_size), Image.LANCZOS
            )
            pixels = list(img.tobytes())  # tobytes() is the modern way for 'L' mode
            bits = []
            for row in range(hash_size):
                for col in range(hash_size):
                    idx = row * (hash_size + 1) + col
                    bits.append(1 if pixels[idx] > pixels[idx + 1] else 0)
            return bits
    except Exception:
        return None


def hamming_distance(hash1, hash2):
    """Count number of differing bits between two hashes."""
    if hash1 is None or hash2 is None:
        return 999
    return sum(b1 != b2 for b1, b2 in zip(hash1, hash2))


def get_seq_number(filename):
    """Extract the numeric sequence from IMG_3583.JPG -> 3583."""
    import re
    m = re.search(r"(\d+)", filename)
    return int(m.group(1)) if m else -1


def cluster_photos(photos, hash_threshold=10):
    """
    Connected-components clustering based purely on visual similarity.

    Two photos are linked only if their perceptual hash distance <= hash_threshold.
    A threshold of 8 (out of 64 bits) means ~12% of bits differ — catches genuine
    burst shots and near-identical reframes while keeping unrelated scenes separate.

    Sequence-number linking was removed: sequential filenames does NOT mean
    similar content (e.g. IMG_3476 through IMG_3508 can be completely different scenes).

    Connected components: if A≈B and B≈C they all land in one group even if
    A and C aren't directly similar — correctly chains a burst of 10 shots.
    """
    n = len(photos)

    # Build adjacency matrix on visual similarity only
    adj = [[False] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            h_dist = hamming_distance(photos[i].get("_hash"), photos[j].get("_hash"))
            if h_dist <= hash_threshold:
                adj[i][j] = adj[j][i] = True

    # BFS to find connected components
    visited = [False] * n
    groups = []
    for start in range(n):
        if visited[start]:
            continue
        group = []
        queue = [start]
        while queue:
            node = queue.pop(0)
            if visited[node]:
                continue
            visited[node] = True
            group.append(photos[node])
            for nb in range(n):
                if adj[node][nb] and not visited[nb]:
                    queue.append(nb)
        groups.append(group)

    return groups


# ==========================================
# CLAUDE COMPARISON
# ==========================================

def resize_for_api(image_path, max_size=900):
    """Resize and encode image for the API. Supports RAW files."""
    img = open_image(image_path, half_size=False)
    if img.mode != "RGB":
        img = img.convert("RGB")
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=82)
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


def compare_group(client, group_photos, model):
    """
    Send a group of similar photos to Claude for comparative analysis.
    Returns structured comparison notes.
    """
    n = len(group_photos)

    # Build message content: interleave images and labels
    content = []
    for i, photo in enumerate(group_photos):
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": resize_for_api(photo["file"]),
            },
        })
        content.append({
            "type": "text",
            "text": f"Photo {i + 1}: {photo['filename']}",
        })

    content.append({
        "type": "text",
        "text": f"""These {n} photos are similar shots of the same scene.

Compare them carefully and respond in EXACTLY this JSON format (no other text):

{{
    "group_theme": "Brief description of what's in these photos (5-8 words)",
    "best_photo_index": 1,
    "recommendation": "One sentence explaining why Photo X is the best choice.",
    "photos": {{
        "1": "2-3 sentences on Photo 1: note subtle differences in exposure, sharpness, framing, and moment. IMPORTANT: explicitly flag any closed eyes or blinks.",
        "2": "2-3 sentences on Photo 2...",
        "3": "2-3 sentences on Photo 3..."
    }}
}}

Focus on DIFFERENCES. Always check and explicitly state eye status for portraits/groups (e.g. 'All eyes open', 'Subject on left has eyes closed', 'Mid-blink on right side').
Other good notes: sharpness differences, exposure, composition, expression quality, moment captured.""",
    })

    try:
        message = client.messages.create(
            model=model,
            max_tokens=600,
            messages=[{"role": "user", "content": content}],
        )

        response_text = message.content[0].text.strip()

        # Strip markdown code fences if present
        if "```" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            response_text = response_text[start:end]

        return json.loads(response_text)

    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "group_theme": "Similar shots",
            "best_photo_index": 1,
            "recommendation": "See individual photo analyses for details.",
            "photos": {str(i + 1): "" for i in range(n)},
        }
    except Exception as e:
        return {"error": str(e)}


# ==========================================
# MAIN
# ==========================================

def main():
    print()
    print("=" * 55)
    print("  STEP 2B: Grouping and Comparing Similar Photos")
    print("=" * 55)
    print()

    # Check API key
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your-api-key-here":
        print("  ERROR: No API key found in .env file.")
        sys.exit(1)

    # Load catalog
    if not CATALOG_FILE.exists():
        print("  ERROR: Run Steps 1 and 2 first.")
        sys.exit(1)

    with open(CATALOG_FILE) as f:
        catalog = json.load(f)

    # Get analyzed photos only
    # Cluster ALL photos — not just analyzed ones.
    # Unanalyzed photos show up in groups with a "not yet analyzed" indicator.
    all_photos = [p for p in catalog if "error" not in p]

    print(f"  Clustering all {len(all_photos)} photos for similarity...")
    print()

    analyzed_ids = {
        p["id"] for p in catalog
        if isinstance(p.get("claude_analysis"), dict)
        and "error" not in p.get("claude_analysis", {})
    }

    # Clear any previous grouping data first
    for photo in catalog:
        photo.pop("group_id", None)
        photo.pop("_hash", None)

    # Compute hashes — emit PROGRESS lines for dashboard streaming
    total = len(all_photos)
    print(f"PROGRESS:5:Hashing {total} photos…", flush=True)
    for i, photo in enumerate(all_photos):
        photo["_hash"] = compute_dhash(Path(photo["file"]))
        if total > 0 and (i % max(1, total // 20) == 0 or i == total - 1):
            pct = 5 + int((i / total) * 70)  # 5 → 75
            print(f"PROGRESS:{pct}:Hashing photo {i+1}/{total}…", flush=True)

    # Cluster into groups — threshold can be overridden via env var (from dashboard re-run)
    import os as _os
    _thresh = int(_os.environ.get("HASH_THRESHOLD", 10))
    print(f"PROGRESS:80:Clustering with threshold {_thresh}…", flush=True)
    groups = cluster_photos(all_photos, hash_threshold=_thresh)

    multi_groups = [g for g in groups if len(g) > 1]
    single_groups = [g for g in groups if len(g) == 1]

    print(f"PROGRESS:88:Found {len(multi_groups)} groups, {len(single_groups)} unique…", flush=True)
    print()
    print(f"  Found {len(multi_groups)} groups of similar shots")
    print(f"  Found {len(single_groups)} unique photos")
    print()

    # Only offer Claude comparison for groups where at least one photo is analyzed
    comparable = [g for g in multi_groups if any(p["id"] in analyzed_ids for p in g)]
    unanalyzed_groups = [g for g in multi_groups if not any(p["id"] in analyzed_ids for p in g)]

    groups_data = []

    # When invoked from the dashboard (HASH_THRESHOLD env var is set), skip the
    # interactive prompt — just save groups without running Claude comparisons.
    dashboard_mode = "HASH_THRESHOLD" in _os.environ

    if comparable and not dashboard_mode:
        est_cost = len(comparable) * 0.05
        print(f"  {len(comparable)} groups have Claude-analyzed photos — can compare side by side.")
        print(f"  {len(unanalyzed_groups)} groups are unanalyzed (will still appear on the groups page).")
        print(f"  Estimated cost for comparisons: ~${est_cost:.2f}")
        print()
        response = input("  Type 'yes' to run Claude comparisons (or Enter to just save groups): ").strip().lower()
        run_comparisons = response in ("yes", "y")
    else:
        if comparable:
            print(f"  {len(comparable)} groups ready — skipping Claude comparisons (dashboard mode).")
        else:
            print("  No analyzed photos found in any group — saving groups without Claude comparison.")
        run_comparisons = False

    print()

    if run_comparisons:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    gi = 0
    for group in tqdm(multi_groups, desc="  Processing groups"):
        has_analysis = any(p["id"] in analyzed_ids for p in group)

        if run_comparisons and has_analysis:
            # Only send analyzed photos to Claude for comparison
            analyzed_in_group = [p for p in group if p["id"] in analyzed_ids]
            comparison = compare_group(client, analyzed_in_group, CLAUDE_MODEL)

            best_idx = comparison.get("best_photo_index", 1)
            if isinstance(best_idx, int) and 1 <= best_idx <= len(analyzed_in_group):
                best_photo = analyzed_in_group[best_idx - 1]
            else:
                best_photo = max(analyzed_in_group,
                                 key=lambda p: (p.get("claude_analysis") or {}).get("score", 0))

            photo_notes = {}
            for k, note in comparison.get("photos", {}).items():
                try:
                    idx = int(k) - 1
                    if 0 <= idx < len(analyzed_in_group):
                        photo_notes[str(analyzed_in_group[idx]["id"])] = note
                except (ValueError, IndexError):
                    pass

            theme = comparison.get("group_theme", "Similar shots")
            recommendation = comparison.get("recommendation", "")
        else:
            # No comparison — pick best by local score or first analyzed photo
            analyzed_in_group = [p for p in group if p["id"] in analyzed_ids]
            if analyzed_in_group:
                best_photo = max(analyzed_in_group,
                                 key=lambda p: (p.get("claude_analysis") or {}).get("score", 0))
                theme = (best_photo.get("claude_analysis") or {}).get("title", "Similar shots")
            else:
                best_photo = max(group, key=lambda p: p.get("overall_score", 0))
                theme = "Similar shots"
            photo_notes = {}
            recommendation = ""

        groups_data.append({
            "id": f"group_{gi}",
            "photo_ids": [p["id"] for p in group],
            "best_photo_id": best_photo["id"],
            "theme": theme,
            "recommendation": recommendation,
            "photo_notes": photo_notes,
            "is_group": True,
            "has_claude_comparison": run_comparisons and has_analysis,
        })
        gi += 1

    # Add singles
    for photo_list in single_groups:
        photo = photo_list[0]
        groups_data.append({
            "id": f"single_{photo['id']}",
            "photo_ids": [photo["id"]],
            "best_photo_id": photo["id"],
            "theme": (photo.get("claude_analysis") or {}).get("title", photo.get("filename", "")),
            "recommendation": "",
            "photo_notes": {},
            "is_group": False,
            "has_claude_comparison": False,
        })

    # Save groups
    print("PROGRESS:95:Saving groups…", flush=True)
    GROUPS_FILE = DATA_DIR / "groups.json"
    with open(GROUPS_FILE, "w") as f:
        json.dump(groups_data, f, indent=2)

    # Update catalog with group_id
    photo_to_group = {}
    for group in groups_data:
        for pid in group["photo_ids"]:
            photo_to_group[pid] = group["id"]

    for photo in catalog:
        if photo.get("id") in photo_to_group:
            photo["group_id"] = photo_to_group[photo["id"]]

    # Remove temp hash data from catalog
    for photo in catalog:
        photo.pop("_hash", None)

    with open(CATALOG_FILE, "w") as f:
        json.dump(catalog, f, indent=2)

    # Summary
    print()
    print("=" * 55)
    print("  GROUPING COMPLETE")
    print("=" * 55)
    print()
    for g in groups_data:
        if g["is_group"]:
            n = len(g["photo_ids"])
            print(f"  GROUP ({n} shots): {g['theme']}")
            print(f"    Best pick: photo #{g['best_photo_id']}")
            print(f"    {g['recommendation']}")
            print()

    total = len(multi_groups) + len(single_groups)
    print(f"  {total} total groups saved to data/groups.json")
    print("PROGRESS:100:Done!", flush=True)
    print()
    print("  NEXT STEP:")
    print("    Run: python app.py")
    print("    Then open http://localhost:5000 in your browser")
    print()


if __name__ == "__main__":
    main()
