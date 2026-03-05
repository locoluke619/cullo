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
import heapq
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import *
from utils import open_image


def resize_for_api(image_path, max_size=1280):
    """
    Resize a photo for sending to Claude's API.
    Supports both standard formats and RAW camera files.
    Returns base64-encoded JPEG data.
    """
    img = open_image(image_path, half_size=False)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


PROMPT_SHOOT = """You are a professional photography educator and critic helping a photographer cull and build a portfolio from unedited shots.

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

PROMPT_EDITED = """You are a professional photography editor and art director reviewing a photographer's finished, edited work.

Analyze this edited photograph and respond in EXACTLY this JSON format (no other text):

{
    "title": "A short, evocative title (2-6 words)",
    "score": 8.5,
    "summary": "One sentence about the single strongest quality of this photo and its edit.",
    "score_reasoning": {
        "strengths": "2-3 specific reasons this edit works — what the photographer got right in post.",
        "weaknesses": "2-3 honest notes on what could be refined in the edit. If near-perfect, note subtle things."
    },
    "composition": "2-3 sentences on framing, rule of thirds, leading lines, balance, use of negative space.",
    "technical": "2-3 sentences on the edit quality: exposure balance, color grade, skin tones, shadow/highlight detail, noise.",
    "mood": "1-2 sentences on the feeling or emotion this photo evokes — how the edit contributes to it.",
    "story": "1-2 sentences on the moment or story captured.",
    "editing_tips": [
        "Tip 1: Specific refinement suggestion (e.g. 'The highlights on the sky are slightly blown — pull highlights -20 to recover cloud detail')",
        "Tip 2: Another specific refinement",
        "Tip 3: A color or crop note if relevant, or a third refinement"
    ],
    "expression_notes": "For photos with people: quality of expressions, genuine vs forced smiles, eye contact, engagement. Write 'No people' if none.",
    "eyes_check": "For portraits/groups: explicitly note if anyone has closed eyes or is mid-blink. Write 'All eyes open' or describe the issue. Write 'N/A' if no people.",
    "website_worthy": true,
    "best_use": "hero image / gallery feature / supporting image"
}

Score 1-10 where the score reflects BOTH the photo and the quality of the edit:
  - 1-3: Poor result — either the photo or edit has serious problems
  - 4-5: Acceptable edit, nothing memorable
  - 6-7: Good edit with clear strengths
  - 8-9: Excellent — strong photo and polished edit, portfolio worthy
  - 10: Extraordinary — perfect execution from capture to final edit

Be honest and specific. Evaluate the edit as a professional would reviewing a photographer's delivered gallery."""


def analyze_photo(client, image_path, model, workspace_type="shoot"):
    """
    Send a photo to Claude Vision and get a detailed analysis.
    Returns a dictionary with Claude's analysis.
    """
    # Prepare the image
    image_data = resize_for_api(image_path)

    prompt = PROMPT_EDITED if workspace_type == "edited" else PROMPT_SHOOT

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

        # Track token usage for actual cost calculation
        # Pricing: input $3/M tokens, output $15/M tokens (Sonnet 4.6)
        if hasattr(message, "usage"):
            analyze_photo._input_tokens  += message.usage.input_tokens
            analyze_photo._output_tokens += message.usage.output_tokens

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


def _dhash(image_path, size=8):
    """
    Difference hash — fast perceptual fingerprint.
    Returns a list of bits, or None if the image can't be read.
    Used to cluster visually similar photos before Claude selection.
    """
    try:
        img = open_image(image_path, half_size=True)
        img = img.convert("L").resize((size + 1, size), Image.LANCZOS)
        px = list(img.tobytes())
        bits = []
        for row in range(size):
            for col in range(size):
                idx = row * (size + 1) + col
                bits.append(1 if px[idx] > px[idx + 1] else 0)
        return bits
    except Exception:
        return None


def _hamming(a, b):
    if a is None or b is None:
        return 999
    return sum(x != y for x, y in zip(a, b))


def _diverse_select(photos, budget, hash_threshold=12):
    """
    Pick `budget` photos from `photos` with diversity across visual scenes.

    Two-phase algorithm — all local, no API cost:

    Phase 1 — Diversity guarantee:
      Every cluster whose best photo scores above the median gets exactly one
      guaranteed slot (its best photo), regardless of how other clusters rank.
      This ensures a proposal cluster and a kiss cluster both get seen by Claude
      even if the kiss shots happen to outscore every proposal shot.
      Lame clusters (below median) don't get a guaranteed slot.

    Phase 2 — Quality fill:
      Remaining budget slots go to the globally highest-scoring next photos
      across all clusters (priority queue). The kiss cluster's shots #2-10
      compete here on actual score — great burst shots keep winning slots.

    Budget warning:
      If the number of worthy clusters (above-median) exceeds the budget,
      Cullo warns you to raise MAX_CLAUDE_PHOTOS so no key scene is left out.
    """
    print()
    print(f"  Fingerprinting {len(photos)} photos locally (free, no internet)…")

    # Compute hashes in parallel — image decoding is I/O bound
    hashed_map = {}

    def _hash_one(p):
        return p, _dhash(Path(p["file"]))

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_hash_one, p): p for p in photos}
        for future in tqdm(as_completed(futures), total=len(futures),
                           desc="  Hashing", unit="photo", leave=False):
            p, h = future.result()
            hashed_map[id(p)] = (p, h)

    # Preserve original order so score-sorting works correctly
    hashed = [hashed_map[id(p)] for p in photos]

    # Greedy cluster
    clusters = []   # list of [ (photo, hash), ... ]
    centroids = []  # one representative hash per cluster

    for photo, h in hashed:
        best_cluster = None
        best_dist = hash_threshold + 1
        for i, centroid in enumerate(centroids):
            d = _hamming(h, centroid)
            if d < best_dist:
                best_dist = d
                best_cluster = i
        if best_cluster is not None:
            clusters[best_cluster].append((photo, h))
        else:
            clusters.append([(photo, h)])
            centroids.append(h)

    # Sort photos within each cluster by quality score (best first)
    for c in clusters:
        c.sort(key=lambda x: x[0].get("overall_score", 0), reverse=True)

    # Sort clusters by their best photo's score (descending)
    clusters.sort(key=lambda c: c[0][0].get("overall_score", 0), reverse=True)

    # Quality threshold: median score across all best-of-cluster photos.
    # Clusters above this are "worthy" and get a guaranteed Phase 1 slot.
    best_scores = sorted(
        [c[0][0].get("overall_score", 0) for c in clusters], reverse=True
    )
    median_score = best_scores[len(best_scores) // 2] if best_scores else 0
    worthy_clusters   = [c for c in clusters if c[0][0].get("overall_score", 0) >= median_score]
    unworthy_clusters = [c for c in clusters if c[0][0].get("overall_score", 0) <  median_score]

    print(f"  → Found {len(clusters)} distinct scenes across {len(photos)} photos.")
    print(f"     {len(worthy_clusters)} scenes above quality threshold, {len(unworthy_clusters)} below.")

    # ── Budget tip ───────────────────────────────────────────────────────────
    # If worthy scenes exceed the budget, some won't get auto-analyzed this run.
    # They're still in Browse All and can be sent to Claude one at a time.
    if len(worthy_clusters) > budget:
        suggested = len(worthy_clusters) + 10
        pct_limit = int(len(photos) * TOP_PERCENT / 100)
        if pct_limit < MAX_CLAUDE_PHOTOS:
            setting = f"MAX_CLAUDE_PHOTOS={suggested}  (or raise TOP_PERCENT in .env)"
        else:
            setting = f"MAX_CLAUDE_PHOTOS={suggested}"
        print()
        print(f"  💡 {len(worthy_clusters)} scenes detected — sending the best {budget} to Claude now.")
        print(f"     The rest will appear in Browse All. You can click any photo → Send to Claude")
        print(f"     to analyze it on the spot, or raise {setting}")
        print(f"     to auto-analyze everything next run (~${suggested * 0.015:.2f}).")
        print()

    selected = []

    # ── Phase 1: one guaranteed slot per worthy cluster ─────────────────────
    for cluster in worthy_clusters:
        if len(selected) >= budget:
            break
        selected.append(cluster[0][0])  # best photo from this cluster
    guaranteed = len(selected)

    # ── Phase 2: fill remaining slots by score (priority queue) ─────────────
    # Each cluster contributes its next-best photo to the heap.
    # Already-selected Phase 1 photos are at index 0 — start Phase 2 at index 1
    # for worthy clusters, index 0 for unworthy clusters.
    heap = []
    for ci, cluster in enumerate(clusters):
        is_worthy = cluster in worthy_clusters
        start_idx = 1 if is_worthy else 0
        if start_idx < len(cluster):
            score = cluster[start_idx][0].get("overall_score", 0)
            heapq.heappush(heap, (-score, ci, start_idx))

    while heap and len(selected) < budget:
        neg_score, ci, photo_idx = heapq.heappop(heap)
        selected.append(clusters[ci][photo_idx][0])
        next_idx = photo_idx + 1
        if next_idx < len(clusters[ci]):
            next_score = clusters[ci][next_idx][0].get("overall_score", 0)
            heapq.heappush(heap, (-next_score, ci, next_idx))

    phase2 = len(selected) - guaranteed
    if phase2 > 0:
        print(f"     Phase 1: {guaranteed} scene representatives  •  Phase 2: {phase2} additional best shots")

    return selected


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

    # Budget: how many photos to send to Claude total
    budget = min(
        int(len(valid) * TOP_PERCENT / 100),
        MAX_CLAUDE_PHOTOS
    )

    # ── Diversity-aware selection ─────────────────────────────────────────
    # Problem: a wedding with 847 photos might have 50 sharp altar shots
    # that all score 85+. Without diversity, Claude only sees altar shots.
    #
    # Solution: cluster photos by visual similarity first (cheap hash),
    # then pick the best representative from each cluster before filling
    # remaining slots. This ensures Claude sees every distinct moment.
    #
    # Already-analyzed photos keep their analysis and count toward the pool
    # but don't consume budget (no API call needed).

    already_analyzed = [p for p in valid if p.get("claude_analysis") and "error" not in p.get("claude_analysis", {})]
    needs_analysis   = [p for p in valid if not p.get("claude_analysis") or "error" in p.get("claude_analysis", {})]

    remaining_budget = max(0, budget - len(already_analyzed))

    top_photos = already_analyzed[:]  # start with what we have

    if remaining_budget > 0 and needs_analysis:
        top_photos += _diverse_select(needs_analysis, remaining_budget)

    # Keep only up to budget total
    top_photos = top_photos[:budget]
    top_count  = len(top_photos)

    est_cost = top_count * 0.015
    if est_cost < 5.00:
        cost_note = "yes, really — cheaper than a coffee"
    elif est_cost < 12.00:
        cost_note = "about the price of a coffee"
    elif est_cost < 20.00:
        cost_note = "about the price of a meal out"
    else:
        cost_note = "consider lowering MAX_CLAUDE_PHOTOS in .env"

    new_count = len([p for p in top_photos if not p.get("claude_analysis") or "error" in p.get("claude_analysis", {})])

    print(f"  Total photos in catalog: {len(catalog)}")
    print(f"  Budget: {budget} photos  (top {TOP_PERCENT}%, capped at {MAX_CLAUDE_PHOTOS})")
    if already_analyzed:
        print(f"  Already analyzed: {len(already_analyzed)}  •  New to analyze: {new_count}")
    print(f"  Diversity selection: scans ALL {len(needs_analysis)} unanalyzed photos locally, picks best from each scene")
    print(f"  Estimated cost: ~${new_count * 0.015:.2f}  ({cost_note})")
    print(f"  Using model: {CLAUDE_MODEL}")
    print()

    # Skip confirmation if nothing new to analyze
    new_to_analyze = [p for p in top_photos if not p.get("claude_analysis") or "error" in p.get("claude_analysis", {})]
    if not new_to_analyze:
        print("  ✓  All selected photos already analyzed — nothing new to send.")
        print()
        sys.exit(0)

    # Confirm before spending money
    print("  Ready to analyze? This will use your API credits.")
    response = input("  Type 'yes' to continue: ").strip().lower()
    if response not in ("yes", "y"):
        print("  Cancelled. No charges made.")
        sys.exit(0)

    print()

    # Create API client
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Token counters for actual cost tracking
    analyze_photo._input_tokens = 0
    analyze_photo._output_tokens = 0

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

        analysis = analyze_photo(client, image_path, CLAUDE_MODEL, WORKSPACE_TYPE)
        photo["claude_analysis"] = analysis

        if "error" in analysis:
            errors += 1
        else:
            analyzed += 1

        # Save progress after each photo (in case of interruption)
        with open(CATALOG_FILE, "w") as f:
            json.dump(catalog, f, indent=2)

    # Final save
    with open(CATALOG_FILE, "w") as f:
        json.dump(catalog, f, indent=2)

    # Print results
    print()
    print("=" * 55)
    print("  ANALYSIS COMPLETE")
    print("=" * 55)
    print()
    # Calculate actual cost from token usage
    # claude-sonnet-4-6 pricing: $3/M input, $15/M output
    input_cost  = analyze_photo._input_tokens  / 1_000_000 * 3.00
    output_cost = analyze_photo._output_tokens / 1_000_000 * 15.00
    actual_cost = input_cost + output_cost

    print(f"  Photos analyzed: {analyzed}")
    if errors:
        print(f"  Errors:          {errors}")
    if actual_cost > 0:
        print(f"  Actual cost:     ${actual_cost:.4f}  ({analyze_photo._input_tokens:,} input tokens, {analyze_photo._output_tokens:,} output tokens)")
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
