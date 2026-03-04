#!/usr/bin/env python3
"""
STEP 1: SCAN AND SCORE YOUR PHOTOS
===================================
This script looks at every photo in your folder and rates each one
on quality (sharpness, exposure, color, etc.) — all on your computer.

No internet needed. No cost. Takes about 5-10 minutes for ~400 photos.

How to run:
    python scripts/01_scan_and_score.py
"""

import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageFilter, ImageStat
from tqdm import tqdm

# Add the scripts folder to the path so we can import config
sys.path.insert(0, str(Path(__file__).parent))
from config import *


def find_all_photos(folder_path):
    """Find every photo file in the folder (including subfolders)."""
    folder = Path(folder_path)
    photos = []

    if not folder.exists():
        print(f"\n  ERROR: Folder not found: {folder}")
        print(f"  Check the PHOTOS_FOLDER path in your .env file.\n")
        sys.exit(1)

    for file_path in sorted(folder.rglob("*")):
        if file_path.suffix.lower() in SUPPORTED_FORMATS:
            photos.append(file_path)

    return photos


def score_sharpness(image):
    """
    How sharp/in-focus is the photo?
    Uses edge detection — more edges = sharper image.
    Returns a score from 0 to 100.
    """
    gray = image.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edges)
    # Variance of edges — higher = sharper
    variance = stat.var[0]
    # Normalize to roughly 0-100 range
    score = min(100, variance / 5.0)
    return round(score, 1)


def score_exposure(image):
    """
    Is the photo well-exposed? (not too dark, not too bright)
    Looks at the average brightness and penalizes extremes.
    Returns a score from 0 to 100.
    """
    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    mean_brightness = stat.mean[0]  # 0 = black, 255 = white

    # Ideal brightness is around 110-145
    ideal_low, ideal_high = 110, 145
    if ideal_low <= mean_brightness <= ideal_high:
        score = 100
    elif mean_brightness < ideal_low:
        score = max(0, (mean_brightness / ideal_low) * 100)
    else:
        score = max(0, ((255 - mean_brightness) / (255 - ideal_high)) * 100)

    return round(score, 1)


def score_contrast(image):
    """
    Does the photo have good contrast? (range of light and dark)
    Higher standard deviation = more contrast.
    Returns a score from 0 to 100.
    """
    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    # Standard deviation of brightness
    stddev = stat.stddev[0]
    # Good contrast typically has stddev of 50-80
    score = min(100, (stddev / 65.0) * 100)
    return round(score, 1)


def score_color_richness(image):
    """
    How colorful and vibrant is the photo?
    Measures saturation (color intensity).
    Returns a score from 0 to 100.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    hsv = image.convert("HSV")
    stat = ImageStat.Stat(hsv)
    # Channel 1 in HSV is Saturation (0-255)
    avg_saturation = stat.mean[1]
    score = min(100, (avg_saturation / 140.0) * 100)
    return round(score, 1)


def score_resolution(image):
    """
    How high-resolution is the photo?
    Higher megapixels = better (with diminishing returns).
    Returns a score from 0 to 100.
    """
    megapixels = (image.width * image.height) / 1_000_000
    # Log scale: 1MP=40, 5MP=70, 12MP=85, 24MP=95
    if megapixels <= 0:
        return 0
    score = min(100, 40 * math.log10(megapixels + 1) / math.log10(2))
    return round(score, 1)


def score_composition(image):
    """
    Basic composition check using the rule of thirds.
    Looks at whether the brightest/most interesting parts
    are near the thirds lines (not dead center).
    Returns a score from 0 to 100.
    """
    gray = image.convert("L")
    width, height = gray.size

    # Divide image into a 3x3 grid
    w3, h3 = width // 3, height // 3

    # Calculate average brightness in each third
    regions = []
    for row in range(3):
        for col in range(3):
            box = (col * w3, row * h3, (col + 1) * w3, (row + 1) * h3)
            region = gray.crop(box)
            stat = ImageStat.Stat(region)
            regions.append(stat.mean[0])

    # Center region (index 4) vs edge/third regions
    center = regions[4]
    thirds = [regions[i] for i in [1, 3, 5, 7]]  # top, left, right, bottom
    corners = [regions[i] for i in [0, 2, 6, 8]]

    # Good composition: variety between regions (not flat/uniform)
    all_regions = regions
    if max(all_regions) - min(all_regions) < 10:
        # Very uniform image — probably not great composition
        return 30.0

    # Reward images where interest is NOT just in the center
    thirds_avg = sum(thirds) / len(thirds)
    variance = sum((r - sum(all_regions)/9) ** 2 for r in all_regions) / 9
    score = min(100, 30 + (variance / 50.0) * 10 + 30)

    return round(score, 1)


def score_photo(image_path):
    """
    Score a single photo on all quality metrics.
    Returns a dictionary with individual scores and an overall score.
    """
    try:
        with Image.open(image_path) as img:
            # Resize for faster processing (scoring doesn't need full resolution)
            max_dim = 1024
            if max(img.size) > max_dim:
                ratio = max_dim / max(img.size)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img_resized = img.resize(new_size, Image.LANCZOS)
            else:
                img_resized = img.copy()

            # Get original dimensions for resolution scoring
            original_width, original_height = img.size

            scores = {
                "sharpness": score_sharpness(img_resized),
                "exposure": score_exposure(img_resized),
                "contrast": score_contrast(img_resized),
                "color": score_color_richness(img_resized),
                "resolution": score_resolution(img),  # Use original size
                "composition": score_composition(img_resized),
            }

            # Weighted overall score
            weights = {
                "sharpness": 0.25,    # Most important — nobody wants blurry photos
                "exposure": 0.20,     # Proper exposure matters a lot
                "contrast": 0.15,     # Good contrast makes photos pop
                "color": 0.15,        # Vibrant colors are appealing
                "resolution": 0.10,   # Higher res is better but less critical
                "composition": 0.15,  # Composition adds visual interest
            }

            overall = sum(scores[k] * weights[k] for k in scores)
            scores["overall"] = round(overall, 1)

            return {
                "file": str(image_path),
                "filename": image_path.name,
                "width": original_width,
                "height": original_height,
                "megapixels": round((original_width * original_height) / 1_000_000, 1),
                "file_size_mb": round(image_path.stat().st_size / (1024 * 1024), 1),
                "scores": scores,
                "overall_score": scores["overall"],
                "approved": None,       # Will be set in the review app
                "claude_analysis": None, # Will be filled by step 2
            }

    except Exception as e:
        return {
            "file": str(image_path),
            "filename": image_path.name,
            "error": str(e),
            "overall_score": 0,
        }


def main():
    print()
    print("=" * 55)
    print("  STEP 1: Scanning and Scoring Your Photos")
    print("=" * 55)
    print()
    print(f"  Photo folder: {PHOTOS_FOLDER}")
    print()

    # Find all photos
    print("  Finding photos...", end=" ", flush=True)
    photos = find_all_photos(PHOTOS_FOLDER)
    print(f"Found {len(photos)} photos!")
    print()

    if not photos:
        print("  No supported photos found.")
        print(f"  Supported formats: {', '.join(SUPPORTED_FORMATS)}")
        print()
        sys.exit(1)

    # Score each photo
    print("  Scoring each photo on quality metrics...")
    print("  (sharpness, exposure, contrast, color, resolution, composition)")
    print()

    catalog = []
    errors = 0

    for i, photo_path in enumerate(tqdm(photos, desc="  Scoring", unit="photo")):
        result = score_photo(photo_path)
        if "error" in result:
            errors += 1
        catalog.append(result)

    # Sort by overall score (best first)
    catalog.sort(key=lambda x: x.get("overall_score", 0), reverse=True)

    # Add rank and ID
    for i, photo in enumerate(catalog):
        photo["id"] = i
        photo["rank"] = i + 1

    # Save catalog
    CATALOG_FILE.parent.mkdir(exist_ok=True)
    with open(CATALOG_FILE, "w") as f:
        json.dump(catalog, f, indent=2)

    # Calculate how many will go to Claude
    valid_photos = [p for p in catalog if "error" not in p]
    top_count = min(
        int(len(valid_photos) * TOP_PERCENT / 100),
        MAX_CLAUDE_PHOTOS
    )

    # Print summary
    print()
    print("=" * 55)
    print("  RESULTS")
    print("=" * 55)
    print()
    print(f"  Total photos scanned:  {len(photos)}")
    print(f"  Successfully scored:   {len(valid_photos)}")
    if errors:
        print(f"  Skipped (errors):      {errors}")
    print()
    print(f"  Top {TOP_PERCENT}% = {top_count} photos will be sent to Claude")
    print()
    print("  TOP 10 PHOTOS:")
    print("  " + "-" * 50)
    for photo in catalog[:10]:
        if "error" not in photo:
            s = photo["scores"]
            print(f"  #{photo['rank']:>3}  {photo['filename']:<25} "
                  f"Score: {photo['overall_score']:>5.1f}")
            print(f"       Sharp:{s['sharpness']:>5.1f}  "
                  f"Exp:{s['exposure']:>5.1f}  "
                  f"Color:{s['color']:>5.1f}  "
                  f"Comp:{s['composition']:>5.1f}")
    print()
    print(f"  Results saved to: {CATALOG_FILE}")
    print()
    print("  NEXT STEP:")
    print("    Run: python scripts/02_analyze_with_claude.py")
    print()


if __name__ == "__main__":
    main()
