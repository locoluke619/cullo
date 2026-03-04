#!/usr/bin/env python3
"""
STEP 4 (OPTIONAL): SNEAK PEEK AUTO-SELECTOR
============================================
After a shoot, automatically picks 8-10 of the most diverse,
highest-quality shots to tease on social media.

Selects photos that:
  - Have a high Claude score (7.5+)
  - Are visually diverse (not just 5 portraits in a row)
  - Cover different moments / subjects from the session
  - Are already approved OR just the top-scoring photos

How to run:
    python scripts/04_sneak_peek.py

Output:
    data/sneak_peek.json  — list of selected photo IDs with notes
    docs/sneak_peek/      — folder with resized 1080px copies ready for Instagram/social
"""

import json
import shutil
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import *


# ==========================================
# SETTINGS
# ==========================================

SNEAK_PEEK_COUNT = 9          # Target number of photos (3x3 grid for IG)
MIN_SCORE = 6.5               # Minimum Claude score to consider
OUTPUT_SIZE = 1080            # Square crop size for social media
OUTPUT_QUALITY = 88           # JPEG quality for output files
SNEAK_PEEK_FILE = DATA_DIR / "sneak_peek.json"
OUTPUT_DIR = DOCS_DIR / "sneak_peek"


# ==========================================
# DIVERSITY SCORING
# ==========================================

def score_diversity(selected, candidate):
    """
    Penalize candidates that are too similar to already-selected photos.
    Uses Claude's 'best_use' field and score to spread across categories.
    """
    if not selected:
        return 1.0

    candidate_use = (candidate.get("claude_analysis") or {}).get("best_use", "")
    candidate_score = (candidate.get("claude_analysis") or {}).get("score", 0)

    # Count how many selected photos share the same best_use category
    same_use_count = sum(
        1 for p in selected
        if (p.get("claude_analysis") or {}).get("best_use", "") == candidate_use
    )

    # Penalty: -0.2 per same-category photo already selected
    diversity_bonus = max(0.0, 1.0 - same_use_count * 0.2)

    # Bonus for very high scores
    score_bonus = 1.0 + (candidate_score - MIN_SCORE) * 0.1

    return diversity_bonus * score_bonus


def pick_sneak_peek(photos, count):
    """
    Greedy selection: repeatedly pick the photo with the best
    (score × diversity) that hasn't been picked yet.
    """
    pool = [
        p for p in photos
        if (p.get("claude_analysis") or {}).get("score", 0) >= MIN_SCORE
        and "error" not in (p.get("claude_analysis") or {})
    ]

    # Sort by score descending as starting point
    pool.sort(
        key=lambda p: (p.get("claude_analysis") or {}).get("score", 0),
        reverse=True,
    )

    selected = []
    remaining = list(pool)

    while len(selected) < count and remaining:
        # Score each candidate by score × diversity
        best = max(
            remaining,
            key=lambda p: (
                (p.get("claude_analysis") or {}).get("score", 0)
                * score_diversity(selected, p)
            ),
        )
        selected.append(best)
        remaining.remove(best)

    return selected


# ==========================================
# IMAGE EXPORT
# ==========================================

def export_square(photo, output_path, size=OUTPUT_SIZE):
    """
    Export photo as a square center-crop at the given pixel size.
    Perfect for Instagram grid posts.
    """
    with Image.open(photo["file"]) as img:
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Center crop to square
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))

        # Resize to target
        if side > size:
            img = img.resize((size, size), Image.LANCZOS)

        img.save(output_path, format="JPEG", quality=OUTPUT_QUALITY)


# ==========================================
# MAIN
# ==========================================

def main():
    print()
    print("=" * 55)
    print("  STEP 4: Sneak Peek Auto-Selector")
    print("=" * 55)
    print()

    if not CATALOG_FILE.exists():
        print("  ERROR: No catalog found. Run Steps 1 and 2 first.")
        sys.exit(1)

    with open(CATALOG_FILE) as f:
        catalog = json.load(f)

    # Prefer approved photos, fall back to all analyzed
    approved = [
        p for p in catalog
        if p.get("approved") is True
        and p.get("claude_analysis")
        and "error" not in p.get("claude_analysis", {})
    ]

    analyzed = [
        p for p in catalog
        if p.get("claude_analysis")
        and "error" not in p.get("claude_analysis", {})
    ]

    pool_label = "approved"
    pool = approved if len(approved) >= SNEAK_PEEK_COUNT else analyzed
    if pool is analyzed and approved:
        pool_label = "all analyzed (not enough approved yet)"
    elif pool is analyzed:
        pool_label = "all analyzed"

    eligible = [
        p for p in pool
        if (p.get("claude_analysis") or {}).get("score", 0) >= MIN_SCORE
    ]

    print(f"  Photos in pool ({pool_label}): {len(pool)}")
    print(f"  Eligible (score ≥ {MIN_SCORE}): {len(eligible)}")
    print()

    if not eligible:
        print(f"  No photos score {MIN_SCORE}+ yet. Lower MIN_SCORE or run Step 2 first.")
        sys.exit(1)

    count = min(SNEAK_PEEK_COUNT, len(eligible))
    picks = pick_sneak_peek(pool, count)

    print(f"  Selected {len(picks)} photos for your sneak peek:")
    print()

    results = []
    for i, p in enumerate(picks, 1):
        a = p.get("claude_analysis", {})
        score = a.get("score", "?")
        title = a.get("title", p["filename"])
        best_use = a.get("best_use", "")
        print(f"  {i}. [{score}/10] {title}")
        print(f"     {p['filename']}  •  {best_use}")
        print()
        results.append({
            "rank": i,
            "id": p["id"],
            "filename": p["filename"],
            "score": score,
            "title": title,
            "summary": a.get("summary", ""),
            "best_use": best_use,
        })

    # Save JSON
    with open(SNEAK_PEEK_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved selection to: data/sneak_peek.json")
    print()

    # Export resized copies
    print(f"  Exporting {size}px square crops for social media...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Clean old exports
    for old in OUTPUT_DIR.glob("*.jpg"):
        old.unlink()

    for item in tqdm(results, desc="  Exporting", unit="photo"):
        photo = next((p for p in catalog if p["id"] == item["id"]), None)
        if not photo:
            continue
        out_name = f"{item['rank']:02d}_{Path(photo['filename']).stem}.jpg"
        export_square(photo, OUTPUT_DIR / out_name)

    print()
    print("=" * 55)
    print("  SNEAK PEEK READY")
    print("=" * 55)
    print()
    print(f"  Square crops saved to: docs/sneak_peek/")
    print(f"  Just drag those {len(results)} files into Instagram!")
    print()
    print(f"  Caption idea:")
    print(f"  \"Sneak peek from today's session! Full gallery coming soon. 📸\"")
    print()

    size = OUTPUT_SIZE  # referenced in loop above — reassign for clarity


if __name__ == "__main__":
    main()
