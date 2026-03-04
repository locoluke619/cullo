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


# ==========================================
# PERCEPTUAL HASHING (no extra libraries)
# ==========================================

def compute_dhash(image_path, hash_size=8):
    """
    Difference hash: captures horizontal gradient patterns.
    Near-identical photos score < 8 apart.
    Different scenes score 20+ apart.
    """
    try:
        with Image.open(image_path) as img:
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


def cluster_photos(photos, hash_threshold=15, seq_threshold=12):
    """
    Connected-components clustering.

    Two photos are linked if:
      - Their perceptual hash distance <= hash_threshold, OR
      - Their filename sequence numbers are within seq_threshold AND
        their hash distance <= 22 (clearly same session, slightly different scene)

    Connected components means: if A≈B and B≈C they all end up in one group
    even if A and C aren't directly similar — fixes the "split group" problem.
    """
    n = len(photos)
    seqs = [get_seq_number(p["filename"]) for p in photos]

    # Build adjacency matrix
    adj = [[False] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            h_dist = hamming_distance(photos[i].get("_hash"), photos[j].get("_hash"))
            s_diff = (
                abs(seqs[i] - seqs[j])
                if seqs[i] >= 0 and seqs[j] >= 0
                else 999
            )
            if h_dist <= hash_threshold or s_diff <= seq_threshold:
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
    """Resize and encode image for the API."""
    with Image.open(image_path) as img:
        if img.mode != "RGB":
            img = img.convert("RGB")
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            img = img.resize(
                (int(img.width * ratio), int(img.height * ratio)),
                Image.LANCZOS,
            )
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
    analyzed = [
        p for p in catalog
        if p.get("claude_analysis")
        and "error" not in p.get("claude_analysis", {})
    ]

    if not analyzed:
        print("  ERROR: No analyzed photos found. Run Step 2 first.")
        sys.exit(1)

    print(f"  Analyzing {len(analyzed)} photos for similarity...")
    print()

    # Clear any previous grouping data first
    for photo in catalog:
        photo.pop("group_id", None)
        photo.pop("_hash", None)

    # Compute hashes
    for photo in tqdm(analyzed, desc="  Hashing", unit="photo"):
        photo["_hash"] = compute_dhash(Path(photo["file"]))

    # Cluster into groups
    groups = cluster_photos(analyzed)

    multi_groups = [g for g in groups if len(g) > 1]
    single_groups = [g for g in groups if len(g) == 1]

    print()
    print(f"  Found {len(multi_groups)} groups of similar shots")
    print(f"  Found {len(single_groups)} unique photos")
    print()

    if not multi_groups:
        print("  No similar photo groups found. All photos are unique.")
        print("  You can still use the review app normally.")
        # Save empty groups file
        groups_data = []
        for photo in analyzed:
            groups_data.append({
                "id": f"single_{photo['id']}",
                "photo_ids": [photo["id"]],
                "best_photo_id": photo["id"],
                "theme": photo.get("claude_analysis", {}).get("title", ""),
                "recommendation": "",
                "photo_notes": {},
                "is_group": False,
            })
        GROUPS_FILE = DATA_DIR / "groups.json"
        with open(GROUPS_FILE, "w") as f:
            json.dump(groups_data, f, indent=2)
        return

    # Confirm cost
    est_cost = len(multi_groups) * 0.05
    print(f"  Will compare {len(multi_groups)} groups with Claude.")
    print(f"  Estimated cost: ~${est_cost:.2f}")
    print()
    response = input("  Type 'yes' to continue: ").strip().lower()
    if response not in ("yes", "y"):
        print("  Cancelled.")
        sys.exit(0)

    print()

    # Compare each group with Claude
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    groups_data = []

    for i, group in enumerate(tqdm(multi_groups, desc="  Comparing groups")):
        comparison = compare_group(client, group, CLAUDE_MODEL)

        # Determine best photo (Claude's pick, 1-indexed)
        best_idx = comparison.get("best_photo_index", 1)
        if isinstance(best_idx, int) and 1 <= best_idx <= len(group):
            best_photo = group[best_idx - 1]
        else:
            # Default to highest claude score
            best_photo = max(group, key=lambda p: p.get("claude_analysis", {}).get("score", 0))

        # Map photo index to photo ID for the notes
        photo_notes = {}
        for k, note in comparison.get("photos", {}).items():
            try:
                idx = int(k) - 1
                if 0 <= idx < len(group):
                    photo_notes[str(group[idx]["id"])] = note
            except (ValueError, IndexError):
                pass

        groups_data.append({
            "id": f"group_{i}",
            "photo_ids": [p["id"] for p in group],
            "best_photo_id": best_photo["id"],
            "theme": comparison.get("group_theme", "Similar shots"),
            "recommendation": comparison.get("recommendation", ""),
            "photo_notes": photo_notes,
            "is_group": True,
        })

    # Add singles
    for photo_list in single_groups:
        photo = photo_list[0]
        groups_data.append({
            "id": f"single_{photo['id']}",
            "photo_ids": [photo["id"]],
            "best_photo_id": photo["id"],
            "theme": photo.get("claude_analysis", {}).get("title", ""),
            "recommendation": "",
            "photo_notes": {},
            "is_group": False,
        })

    # Save groups
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
    print()
    print("  NEXT STEP:")
    print("    Run: python app.py")
    print("    Then open http://localhost:5000 in your browser")
    print()


if __name__ == "__main__":
    main()
