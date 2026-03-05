#!/usr/bin/env python3
"""
STEP 2C: CAPTION EVERY PHOTO + SEMANTIC GROUPING
=================================================
Two things happen here, both cheap and fast:

1. CAPTION (using Claude Haiku — ~$0.001 per photo)
   Every photo gets a one-sentence plain-English description stored as
   `caption` in the catalog. For already-analyzed photos the existing
   summary is reused — no extra cost. Only unanalyzed photos need captions.

2. SEMANTIC GROUPING (text-only — almost free)
   All captions are sent to Claude in a single text message.
   Claude groups them by subject/scene (ceremony, portraits, dance floor,
   mountains, etc.) using language understanding rather than pixel similarity.
   This complements the visual hash clustering in Step 2B.

How to run:
    python scripts/02c_caption_and_group.py
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

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SEMANTIC_GROUPS_FILE = DATA_DIR / "semantic_groups.json"


# ── Caption generation ────────────────────────────────────────────────────────

def _encode(image_path, max_size=512):
    """Resize and base64-encode a photo for the API."""
    img = open_image(image_path, half_size=True)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def generate_caption(client, image_path):
    """
    Ask Haiku for a single descriptive sentence about the photo.
    Returns a string, or None on error.
    """
    try:
        data = _encode(image_path)
        msg = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=80,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Describe this photo in exactly one sentence. "
                            "Be specific about the subject, setting, and mood. "
                            "No preamble — just the sentence."
                        ),
                    },
                ],
            }],
        )
        return msg.content[0].text.strip().rstrip(".")
    except Exception as e:
        return None


# ── Semantic grouping ─────────────────────────────────────────────────────────

def semantic_group(client, photos):
    """
    Send all captions as text to Claude and ask it to group by subject/scene.
    Returns a dict: { "group name": [photo_id, ...], ... }
    """
    lines = "\n".join(
        f'{p["id"]}: {p.get("caption", p.get("filename", ""))}'
        for p in photos
    )

    prompt = f"""You are organizing a photo shoot. Below is a numbered list of photos with one-sentence descriptions.

Group them by subject or scene (e.g. "Ceremony", "First dance", "Portraits", "Sunset landscape", "Group team photo", etc.).
Each photo belongs to exactly one group. Use clear, short group names.

Respond in EXACTLY this JSON format (no other text):
{{
  "Group Name": [id1, id2, id3],
  "Another Group": [id4, id5]
}}

Photos:
{lines}"""

    try:
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        if "```" in text:
            text = text[text.find("{"):text.rfind("}") + 1]
        return json.loads(text)
    except Exception as e:
        print(f"\n  Warning: semantic grouping failed — {e}")
        return {}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 55)
    print("  STEP 2C: Caption Every Photo + Semantic Groups")
    print("=" * 55)
    print()

    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your-api-key-here":
        print("  ERROR: No API key found in .env")
        sys.exit(1)

    if not CATALOG_FILE.exists():
        print("  ERROR: Run Step 1 first.")
        sys.exit(1)

    with open(CATALOG_FILE) as f:
        catalog = json.load(f)

    valid = [p for p in catalog if "error" not in p and Path(p.get("file", "")).exists()]

    # ── Phase 1: captions ────────────────────────────────────────────────────
    # Reuse existing summary for analyzed photos; generate new for the rest.
    needs_caption = []
    reused = 0
    for p in valid:
        if p.get("caption"):
            reused += 1
            continue
        analysis = p.get("claude_analysis")
        if isinstance(analysis, dict) and analysis.get("summary") and "error" not in analysis:
            p["caption"] = analysis["summary"]
            reused += 1
        else:
            needs_caption.append(p)

    print(f"  {len(valid)} photos total")
    print(f"  {reused} already have captions (reused from Claude analysis)")
    print(f"  {len(needs_caption)} need new captions via Haiku")

    if needs_caption:
        est_cost = len(needs_caption) * 0.001
        print(f"  Estimated cost: ~${est_cost:.2f}  (Claude Haiku, fast + cheap)")
        print()
        ans = input("  Generate captions? [y/n]: ").strip().lower()
        if ans not in ("y", "yes", ""):
            print("  Skipped caption generation.")
            needs_caption = []
        else:
            print()
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            failed = 0
            for p in tqdm(needs_caption, desc="  Captioning", unit="photo"):
                caption = generate_caption(client, Path(p["file"]))
                if caption:
                    p["caption"] = caption
                else:
                    p["caption"] = p.get("filename", "")
                    failed += 1

            print()
            if failed:
                print(f"  {len(needs_caption) - failed} captions generated  •  {failed} failed (filename used as fallback)")
            else:
                print(f"  {len(needs_caption)} captions generated")

            # Save captions to catalog
            with open(CATALOG_FILE, "w") as f:
                json.dump(catalog, f, indent=2)
            print("  Captions saved to catalog.")

    # ── Phase 2: semantic grouping ───────────────────────────────────────────
    captioned = [p for p in valid if p.get("caption")]
    if not captioned:
        print()
        print("  No captions available — skipping semantic grouping.")
        return

    print()
    print(f"  {len(captioned)} photos have captions — ready for semantic grouping.")
    print(f"  This sends all captions as text to Claude (no images = very cheap, ~$0.02).")
    print()
    ans = input("  Run semantic grouping? [y/n]: ").strip().lower()
    if ans not in ("y", "yes", ""):
        print("  Skipped.")
        return

    if 'client' not in dir():
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print()
    print("  Grouping by subject/scene…", flush=True)
    raw_groups = semantic_group(client, captioned)

    if not raw_groups:
        print("  Could not generate semantic groups.")
        return

    # Save semantic groups
    semantic_data = []
    photo_by_id = {p["id"]: p for p in catalog}
    for name, ids in raw_groups.items():
        valid_ids = [i for i in ids if i in photo_by_id]
        if valid_ids:
            semantic_data.append({
                "name": name,
                "photo_ids": valid_ids,
                "count": len(valid_ids),
            })
    semantic_data.sort(key=lambda g: g["count"], reverse=True)

    with open(SEMANTIC_GROUPS_FILE, "w") as f:
        json.dump(semantic_data, f, indent=2)

    print()
    print("=" * 55)
    print("  SEMANTIC GROUPS")
    print("=" * 55)
    print()
    for g in semantic_data:
        print(f"  {g['name']:<35}  {g['count']} photos")
    print()
    print(f"  Saved to data/semantic_groups.json")
    print()


if __name__ == "__main__":
    main()
