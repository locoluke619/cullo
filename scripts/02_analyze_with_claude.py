#!/usr/bin/env python3
"""
STEP 2: ANALYZE YOUR BEST PHOTOS WITH CLAUDE AI
=================================================
This script takes the top-scoring photos from Step 1 and sends them
to Claude (an AI that can see and understand images) for a detailed
professional analysis.

Claude will look at each photo and tell you:
  - What makes it a great photo
  - A suggested title
  - A quality score from 1-10
  - Composition and technical feedback
  - The mood/feeling the photo creates

Cost: About $0.01-0.02 per photo (~$0.50-$1.00 for 50 photos)

How to run:
    python scripts/02_analyze_with_claude.py
"""

import anthropic
import base64
import json
import sys
import time
from io import BytesIO
from pathlib import Path
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import *


def resize_for_api(image_path, max_size=1280):
    """
    Resize a photo for sending to Claude's API.
    Makes the image smaller so it uploads faster and costs less.
    Returns base64-encoded JPEG data.
    """
    with Image.open(image_path) as img:
        # Convert to RGB if needed (handles RGBA, palette modes, etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Resize if larger than max_size
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # Save to bytes as JPEG
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


def analyze_photo(client, image_path, model):
    """
    Send a photo to Claude Vision and get a detailed analysis.
    Returns a dictionary with Claude's analysis.
    """
    # Prepare the image
    image_data = resize_for_api(image_path)

    # Ask Claude to analyze the photo
    prompt = """You are a professional photography educator and critic helping a photographer build a portfolio.

Analyze this photograph and respond in EXACTLY this JSON format (no other text):

{
    "title": "A short, evocative title (2-6 words)",
    "score": 8.5,
    "summary": "One sentence about the single strongest quality of this photo.",
    "score_reasoning": {
        "strengths": "2-3 specific reasons why this photo earned its score — what works well.",
        "weaknesses": "2-3 honest specific issues holding it back from a higher score. If near-perfect, note minor things."
    },
    "composition": "2-3 sentences on framing, rule of thirds, leading lines, balance, use of negative space.",
    "technical": "2-3 sentences on sharpness, exposure, noise, color balance, depth of field.",
    "mood": "1-2 sentences on the feeling or emotion this photo evokes.",
    "story": "1-2 sentences on the moment or story captured.",
    "editing_tips": [
        "Tip 1: Specific, actionable suggestion referencing Lightroom/Photoshop (e.g. 'Lift shadows +25 to recover face detail in the darker areas')",
        "Tip 2: Another specific adjustment",
        "Tip 3: A crop or straighten suggestion if needed, or a third editing note"
    ],
    "expression_notes": "For photos with people: quality of expressions, genuine vs forced smiles, eye contact, engagement. Write 'No people' if none.",
    "eyes_check": "For portraits/groups: explicitly note if anyone has closed eyes or is mid-blink. Write 'All eyes open' or describe the issue. Write 'N/A' if no people.",
    "website_worthy": true,
    "best_use": "hero image / gallery feature / supporting image"
}

Score 1-10 where:
  - 1-3: Poor quality, skip it
  - 4-5: Decent snapshot, nothing special
  - 6-7: Good photo with clear strengths
  - 8-9: Excellent, portfolio worthy
  - 10: Extraordinary — a once-in-a-career shot

Be honest. A 10 requires perfect technique + perfect light + unrepeatable moment + strong emotion.
For editing_tips: be specific like a photography teacher — name actual values and tools."""

    try:
        message = client.messages.create(
            model=model,
            max_tokens=900,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        # Parse Claude's response
        response_text = message.content[0].text.strip()

        # Try to extract JSON from the response
        # Sometimes Claude wraps it in markdown code blocks
        if "```" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            response_text = response_text[start:end]

        analysis = json.loads(response_text)
        return analysis

    except json.JSONDecodeError:
        # If we can't parse JSON, return the raw text
        return {
            "title": "Untitled",
            "score": 5.0,
            "summary": response_text[:200],
            "raw_response": response_text,
            "website_worthy": False,
        }
    except anthropic.APIError as e:
        return {
            "error": f"API Error: {str(e)}",
            "title": "Error",
            "score": 0,
        }


def main():
    print()
    print("=" * 55)
    print("  STEP 2: Claude AI Photo Analysis")
    print("=" * 55)
    print()

    # Check API key
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your-api-key-here":
        print("  ERROR: No API key found!")
        print()
        print("  You need to add your Anthropic API key to the .env file.")
        print("  1. Open .env in your text editor")
        print("  2. Replace 'your-api-key-here' with your actual key")
        print("  3. Save the file and run this script again")
        print()
        print("  Don't have a key? Get one free at:")
        print("  https://console.anthropic.com")
        print()
        sys.exit(1)

    # Load catalog from Step 1
    if not CATALOG_FILE.exists():
        print("  ERROR: No photo catalog found!")
        print("  You need to run Step 1 first:")
        print("    python scripts/01_scan_and_score.py")
        print()
        sys.exit(1)

    with open(CATALOG_FILE) as f:
        catalog = json.load(f)

    # Filter to valid photos only (no errors)
    valid = [p for p in catalog if "error" not in p]

    # Select top photos
    top_count = min(
        int(len(valid) * TOP_PERCENT / 100),
        MAX_CLAUDE_PHOTOS
    )
    top_photos = valid[:top_count]  # Already sorted by score from Step 1

    print(f"  Total photos in catalog: {len(catalog)}")
    print(f"  Selecting top {TOP_PERCENT}%: {top_count} photos")
    print(f"  Estimated cost: ~${top_count * 0.015:.2f}")
    print(f"  Using model: {CLAUDE_MODEL}")
    print()

    # Confirm before spending money
    print("  Ready to analyze? This will use your API credits.")
    response = input("  Type 'yes' to continue: ").strip().lower()
    if response not in ("yes", "y"):
        print("  Cancelled. No charges made.")
        sys.exit(0)

    print()

    # Create API client
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Analyze each top photo
    analyzed = 0
    errors = 0

    for photo in tqdm(top_photos, desc="  Analyzing", unit="photo"):
        image_path = Path(photo["file"])

        if not image_path.exists():
            photo["claude_analysis"] = {"error": "File not found"}
            errors += 1
            continue

        # Check if already analyzed (in case of restart)
        if photo.get("claude_analysis") and "error" not in photo.get("claude_analysis", {}):
            analyzed += 1
            continue

        analysis = analyze_photo(client, image_path, CLAUDE_MODEL)
        photo["claude_analysis"] = analysis

        if "error" in analysis:
            errors += 1
        else:
            analyzed += 1

        # Save progress after each photo (in case of interruption)
        with open(CATALOG_FILE, "w") as f:
            json.dump(catalog, f, indent=2)

        # Brief pause to be nice to the API
        time.sleep(0.5)

    # Final save
    with open(CATALOG_FILE, "w") as f:
        json.dump(catalog, f, indent=2)

    # Print results
    print()
    print("=" * 55)
    print("  ANALYSIS COMPLETE")
    print("=" * 55)
    print()
    print(f"  Photos analyzed: {analyzed}")
    if errors:
        print(f"  Errors: {errors}")
    print()

    # Show top results
    analyzed_photos = [
        p for p in catalog
        if p.get("claude_analysis") and "error" not in p.get("claude_analysis", {})
    ]
    analyzed_photos.sort(
        key=lambda x: x["claude_analysis"].get("score", 0), reverse=True
    )

    print("  CLAUDE'S TOP PICKS:")
    print("  " + "-" * 50)
    for photo in analyzed_photos[:10]:
        a = photo["claude_analysis"]
        print(f"  '{a.get('title', 'Untitled')}'")
        print(f"    Score: {a.get('score', '?')}/10 — {a.get('summary', '')}")
        print(f"    Best use: {a.get('best_use', '?')}")
        print(f"    File: {photo['filename']}")
        print()

    website_worthy = [
        p for p in analyzed_photos
        if p.get("claude_analysis", {}).get("website_worthy", False)
    ]
    print(f"  Website-worthy photos: {len(website_worthy)} out of {len(analyzed_photos)}")
    print()
    print(f"  Results saved to: {CATALOG_FILE}")
    print()
    print("  NEXT STEP:")
    print("    Run: python app.py")
    print("    Then open http://localhost:5000 in your browser")
    print("    to review and approve photos for your website!")
    print()


if __name__ == "__main__":
    main()
