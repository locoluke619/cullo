#!/usr/bin/env python3
"""
STEP 5 (OPTIONAL): EXPORT A CLIENT PROOF
=========================================
Generates a single self-contained HTML file you can email (or share via
Google Drive / iCloud / Dropbox) with your client.

The file works completely offline — no server, no localhost. The client
opens it in their browser, taps ♥ on the photos they love, then clicks
"Send My Picks" which opens their email client with their selections
pre-filled and addressed to you.

How to run:
    python scripts/05_export_client_proof.py

Output:
    exports/client_proof.html   — send this file to your client
"""

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

# ── Settings ──────────────────────────────────────────────────────────
MAX_IMAGE_PX = 900     # Longest edge in the embedded preview images
JPEG_QUALITY = 72      # JPEG quality — lower = smaller file
SNEAK_PHOTOS = None    # None = all approved; set e.g. 20 to cap it
# ──────────────────────────────────────────────────────────────────────


def encode_photo(file_path, max_px=MAX_IMAGE_PX, quality=JPEG_QUALITY):
    """Open any supported image and return a base64 data URI string."""
    img = open_image(file_path, half_size=False)
    if img.mode != "RGB":
        img = img.convert("RGB")
    if max(img.size) > max_px:
        ratio = max_px / max(img.size)
        img = img.resize(
            (int(img.width * ratio), int(img.height * ratio)),
            Image.LANCZOS,
        )
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def build_html(photos_data, photographer_name, photographer_email):
    """Render the standalone client proof HTML."""

    photos_json = json.dumps(photos_data)
    email_attr = f'value="{photographer_email}"' if photographer_email else 'placeholder="your photographer\'s email"'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{photographer_name} — Your Photo Proof</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0e0e10;--surface:#18181b;--border:rgba(255,255,255,0.08);
  --text:#f4f4f5;--muted:#71717a;--accent:#a78bfa;
  --heart:#f43f5e;--heart-bg:rgba(244,63,94,0.12);
}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}}

/* Header */
.header{{
  position:sticky;top:0;z-index:100;
  background:rgba(14,14,16,0.92);backdrop-filter:blur(12px);
  border-bottom:1px solid var(--border);
  padding:14px 20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;
}}
.header-left{{flex:1;min-width:160px}}
.header-left h1{{font-size:18px;font-weight:600}}
.header-left p{{font-size:12px;color:var(--muted);margin-top:2px}}
.counter{{
  display:flex;align-items:center;gap:6px;
  background:var(--heart-bg);border:1px solid rgba(244,63,94,0.25);
  border-radius:10px;padding:7px 14px;font-size:13px;font-weight:600;
  color:var(--heart);transition:transform 0.15s;
}}
.counter.bump{{transform:scale(1.15)}}
.btn-send{{
  background:var(--heart);color:#fff;border:none;border-radius:9px;
  padding:9px 18px;font-size:13px;font-weight:600;cursor:pointer;
  transition:opacity 0.2s;
}}
.btn-send:hover{{opacity:0.85}}
.btn-send:disabled{{opacity:0.35;cursor:default}}

/* Grid */
.gallery{{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));
  gap:3px;padding:12px;
}}
.card{{
  position:relative;aspect-ratio:1;overflow:hidden;
  border-radius:6px;cursor:pointer;background:var(--surface);
}}
.card img{{
  width:100%;height:100%;object-fit:cover;display:block;
  transition:transform 0.3s,filter 0.3s;
}}
.card:hover img{{transform:scale(1.04)}}
.card.hearted img{{filter:brightness(0.82)}}
.hbtn{{
  position:absolute;top:9px;right:9px;
  width:36px;height:36px;border-radius:50%;
  background:rgba(0,0,0,0.5);backdrop-filter:blur(6px);
  border:none;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  font-size:19px;line-height:1;color:#fff;
  transition:transform 0.2s,background 0.2s;z-index:5;
}}
.hbtn:hover{{transform:scale(1.2);background:rgba(0,0,0,0.7)}}
.card.hearted .hbtn{{background:var(--heart)}}
.hbtn.pop{{animation:pop 0.3s cubic-bezier(.36,.07,.19,.97)}}
@keyframes pop{{0%{{transform:scale(1)}}40%{{transform:scale(1.45)}}80%{{transform:scale(0.9)}}100%{{transform:scale(1)}}}}
.overlay{{
  position:absolute;bottom:0;left:0;right:0;
  background:linear-gradient(transparent,rgba(0,0,0,0.72));
  padding:22px 11px 11px;opacity:0;transition:opacity 0.25s;pointer-events:none;
}}
.card:hover .overlay{{opacity:1}}
.overlay .ptitle{{font-size:13px;font-weight:600;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.overlay .psum{{font-size:11px;color:rgba(255,255,255,0.75);margin-top:2px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}

/* Lightbox */
.lb{{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.93);z-index:200;align-items:center;justify-content:center;flex-direction:column}}
.lb.open{{display:flex}}
.lb-inner{{position:relative;max-width:90vw;max-height:83vh;display:flex;align-items:center;justify-content:center}}
.lb-inner img{{max-width:100%;max-height:83vh;object-fit:contain;border-radius:8px}}
.lb-close{{position:absolute;top:-38px;right:0;background:none;border:none;color:#fff;font-size:28px;cursor:pointer;opacity:0.7;transition:opacity 0.2s}}
.lb-close:hover{{opacity:1}}
.lbnav{{
  position:absolute;top:50%;transform:translateY(-50%);
  background:rgba(255,255,255,0.12);border:none;color:#fff;
  font-size:22px;width:42px;height:42px;border-radius:50%;
  cursor:pointer;display:flex;align-items:center;justify-content:center;
  transition:background 0.2s;
}}
.lbnav:hover{{background:rgba(255,255,255,0.25)}}
.lbprev{{left:-54px}}.lbnext{{right:-54px}}
.lb-foot{{margin-top:14px;text-align:center}}
.lb-title{{font-size:15px;font-weight:600;margin-bottom:3px}}
.lb-sum{{font-size:13px;color:var(--muted);max-width:480px}}
.lb-hbtn{{
  margin-top:13px;background:var(--surface);border:2px solid var(--border);
  color:var(--text);border-radius:28px;padding:9px 26px;
  font-size:14px;font-weight:600;cursor:pointer;transition:all 0.2s;
  display:inline-flex;align-items:center;gap:7px;
}}
.lb-hbtn:hover{{border-color:var(--heart);color:var(--heart)}}
.lb-hbtn.active{{background:var(--heart-bg);border-color:var(--heart);color:var(--heart)}}

/* Send modal */
.modal{{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:300;align-items:center;justify-content:center}}
.modal.open{{display:flex}}
.mbox{{
  background:var(--surface);border:1px solid var(--border);border-radius:16px;
  padding:36px 44px;text-align:center;max-width:480px;width:90%;
}}
.mbox h2{{font-size:20px;margin-bottom:10px}}
.mbox p{{color:var(--muted);font-size:13px;line-height:1.6;margin-bottom:16px}}
.pick-list{{
  background:#111;border:1px solid var(--border);border-radius:8px;
  padding:12px 16px;text-align:left;font-size:13px;
  max-height:180px;overflow-y:auto;margin-bottom:16px;
}}
.pick-list li{{list-style:none;padding:3px 0;color:var(--text)}}
.pick-list li::before{{content:"♥ ";color:var(--heart)}}
.email-row{{display:flex;gap:8px;margin-bottom:16px}}
.email-row input{{
  flex:1;background:#111;border:1px solid var(--border);border-radius:8px;
  padding:9px 12px;color:var(--text);font-size:13px;outline:none;
}}
.email-row input:focus{{border-color:var(--accent)}}
.btn-row{{display:flex;gap:10px;justify-content:center}}
.btn-primary{{background:var(--heart);color:#fff;border:none;border-radius:9px;padding:10px 22px;font-size:14px;font-weight:600;cursor:pointer;transition:opacity 0.2s}}
.btn-primary:hover{{opacity:0.85}}
.btn-secondary{{background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:9px;padding:10px 22px;font-size:14px;cursor:pointer;transition:border-color 0.2s}}
.btn-secondary:hover{{border-color:var(--muted)}}
.hint{{font-size:11px;color:var(--muted);margin-top:10px}}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <h1>{photographer_name} — Your Photos</h1>
    <p>Tap ♥ on the ones you love, then click Send My Picks.</p>
  </div>
  <div class="counter" id="counter"><span>♥</span><span id="count">0</span> selected</div>
  <button class="btn-send" id="btn-send" disabled onclick="openModal()">Send My Picks</button>
</div>

<div class="gallery" id="gallery"></div>

<!-- Lightbox -->
<div class="lb" id="lb" onclick="lbOut(event)">
  <div class="lb-inner">
    <button class="lb-close" onclick="closeLb()">×</button>
    <button class="lbnav lbprev" onclick="lbNav(-1)">‹</button>
    <img id="lb-img" src="" alt="">
    <button class="lbnav lbnext" onclick="lbNav(1)">›</button>
  </div>
  <div class="lb-foot">
    <div class="lb-title" id="lb-title"></div>
    <div class="lb-sum" id="lb-sum"></div>
    <button class="lb-hbtn" id="lb-hbtn" onclick="toggleHeart(lbIdx)">♥ Add to Favourites</button>
  </div>
</div>

<!-- Send modal -->
<div class="modal" id="modal">
  <div class="mbox">
    <h2>Send Your Picks</h2>
    <p>Here are the photos you selected. Click "Open Email" to send them to your photographer.</p>
    <ul class="pick-list" id="pick-list"></ul>
    <div class="email-row">
      <input type="email" id="email-input" {email_attr}>
    </div>
    <div class="btn-row">
      <button class="btn-primary" onclick="sendEmail()">Open Email</button>
      <button class="btn-secondary" onclick="closeModal()">Cancel</button>
    </div>
    <p class="hint">Can't email? Copy the list above and paste it in a message.</p>
  </div>
</div>

<script>
const PHOTOS = {photos_json};

// Restore hearts from localStorage
const STORE_KEY = 'cullo_hearts';
const hearts = new Set(JSON.parse(localStorage.getItem(STORE_KEY) || '[]'));

let lbIdx = 0;

function saveHearts() {{
  localStorage.setItem(STORE_KEY, JSON.stringify([...hearts]));
}}

function render() {{
  const grid = document.getElementById('gallery');
  grid.innerHTML = PHOTOS.map((p, i) => `
    <div class="card ${{hearts.has(p.id) ? 'hearted' : ''}}" id="card-${{p.id}}" onclick="openLb(${{i}})">
      <img src="${{p.src}}" alt="${{p.title}}" loading="lazy">
      <button class="hbtn" id="hbtn-${{p.id}}" onclick="event.stopPropagation();toggleHeart(${{i}})">
        ${{hearts.has(p.id) ? '♥' : '♡'}}
      </button>
      <div class="overlay">
        <div class="ptitle">${{p.title}}</div>
        <div class="psum">${{p.summary}}</div>
      </div>
    </div>
  `).join('');
  updateCounter();
}}

function toggleHeart(i) {{
  const p = PHOTOS[i];
  if (hearts.has(p.id)) hearts.delete(p.id); else hearts.add(p.id);
  saveHearts();

  const card = document.getElementById('card-' + p.id);
  const btn  = document.getElementById('hbtn-' + p.id);
  if (card) card.classList.toggle('hearted', hearts.has(p.id));
  if (btn) {{
    btn.textContent = hearts.has(p.id) ? '♥' : '♡';
    btn.classList.add('pop');
    setTimeout(() => btn.classList.remove('pop'), 300);
  }}
  updateCounter();
  updateLbBtn(i);
}}

function updateCounter() {{
  const n = hearts.size;
  document.getElementById('count').textContent = n;
  document.getElementById('btn-send').disabled = n === 0;
  const c = document.getElementById('counter');
  c.classList.add('bump');
  setTimeout(() => c.classList.remove('bump'), 200);
}}

// Lightbox
function openLb(i) {{
  lbIdx = i;
  showLb();
  document.getElementById('lb').classList.add('open');
  document.body.style.overflow = 'hidden';
}}
function showLb() {{
  const p = PHOTOS[lbIdx];
  document.getElementById('lb-img').src = p.src;
  document.getElementById('lb-title').textContent = p.title;
  document.getElementById('lb-sum').textContent = p.summary;
  updateLbBtn(lbIdx);
}}
function closeLb() {{
  document.getElementById('lb').classList.remove('open');
  document.body.style.overflow = '';
}}
function lbOut(e) {{ if (e.target === document.getElementById('lb')) closeLb(); }}
function lbNav(d) {{ lbIdx = (lbIdx + d + PHOTOS.length) % PHOTOS.length; showLb(); }}
function updateLbBtn(i) {{
  const p = PHOTOS[i];
  const btn = document.getElementById('lb-hbtn');
  if (!btn) return;
  btn.className = 'lb-hbtn' + (hearts.has(p.id) ? ' active' : '');
  btn.textContent = hearts.has(p.id) ? '♥ In Your Favourites' : '♡ Add to Favourites';
}}
document.addEventListener('keydown', e => {{
  if (!document.getElementById('lb').classList.contains('open')) return;
  if (e.key === 'Escape') closeLb();
  if (e.key === 'ArrowRight') lbNav(1);
  if (e.key === 'ArrowLeft') lbNav(-1);
  if (e.key === 'h' || e.key === 'H') toggleHeart(lbIdx);
}});

// Send modal
function openModal() {{
  const picked = PHOTOS.filter(p => hearts.has(p.id));
  const list = document.getElementById('pick-list');
  list.innerHTML = picked.map(p => `<li>${{p.title}} (${{p.filename}})</li>`).join('');
  document.getElementById('modal').classList.add('open');
}}
function closeModal() {{ document.getElementById('modal').classList.remove('open'); }}
function sendEmail() {{
  const picked = PHOTOS.filter(p => hearts.has(p.id));
  const to = document.getElementById('email-input').value.trim();
  const subject = encodeURIComponent('My photo picks');
  const titles = picked.map(p => `  ♥ ${{p.title}} (${{p.filename}})`).join('\\n');
  const code = picked.map(p => p.filename).join(',');
  const body = encodeURIComponent(
    `Hi,\\n\\nHere are the photos I love from our session:\\n\\n${{titles}}\\n\\nLooking forward to seeing the edits!\\n\\n---\\n[PICKS:${{code}}]`
  );
  window.location.href = `mailto:${{to}}?subject=${{subject}}&body=${{body}}`;
}}

render();
</script>
</body>
</html>"""


def main():
    print()
    print("=" * 55)
    print("  STEP 5: Export Client Proof")
    print("=" * 55)
    print()

    if not CATALOG_FILE.exists():
        print("  ERROR: No catalog found. Run Steps 1 and 2 first.")
        sys.exit(1)

    with open(CATALOG_FILE) as f:
        catalog = json.load(f)

    approved = [
        p for p in catalog
        if p.get("approved") is True
        and p.get("claude_analysis")
        and "error" not in p.get("claude_analysis", {})
    ]

    if not approved:
        # Fall back to all analyzed photos if none approved yet
        approved = [
            p for p in catalog
            if p.get("claude_analysis")
            and "error" not in p.get("claude_analysis", {})
        ]
        if not approved:
            print("  ERROR: No analyzed photos found. Run Steps 1 and 2 first.")
            sys.exit(1)
        print(f"  ⚠  No approved photos yet — including all {len(approved)} analyzed photos.")
        print()
    else:
        print(f"  Found {len(approved)} approved photos to include.")
        print()

    if SNEAK_PHOTOS and len(approved) > SNEAK_PHOTOS:
        approved = approved[:SNEAK_PHOTOS]
        print(f"  Capped at top {SNEAK_PHOTOS} photos.")
        print()

    photographer_name = SITE_AUTHOR or "Your Photographer"
    photographer_email = os.getenv("PHOTOGRAPHER_EMAIL", "")

    print(f"  Embedding {len(approved)} photos (this takes a moment)…")
    print()

    photos_data = []
    for photo in tqdm(approved, desc="  Encoding", unit="photo"):
        file_path = Path(photo["file"])
        if not file_path.exists():
            continue
        try:
            src = encode_photo(file_path)
        except Exception as e:
            print(f"\n  ⚠  Could not encode {photo['filename']}: {e}")
            continue
        a = photo.get("claude_analysis", {})
        photos_data.append({
            "id": photo["id"],
            "filename": photo["filename"],
            "title": a.get("title", photo["filename"]),
            "summary": a.get("summary", ""),
            "src": src,
        })

    if not photos_data:
        print("  ERROR: No photos could be encoded.")
        sys.exit(1)

    html = build_html(photos_data, photographer_name, photographer_email)

    export_dir = PROJECT_DIR / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    out_path = export_dir / "client_proof.html"
    out_path.write_text(html, encoding="utf-8")

    size_mb = out_path.stat().st_size / (1024 * 1024)

    print()
    print("=" * 55)
    print("  CLIENT PROOF READY")
    print("=" * 55)
    print()
    print(f"  File:  exports/client_proof.html")
    print(f"  Size:  {size_mb:.1f} MB  ({len(photos_data)} photos embedded)")
    print()
    if size_mb < 10:
        print("  ✓  Small enough to email directly.")
    else:
        print("  ⚠  Too large to email — share via Google Drive, iCloud, or Dropbox.")
    print()
    print("  How to share with your client:")
    print("    1. Find the file at:  exports/client_proof.html")
    print("    2. Email it, or upload to Google Drive and share the link")
    print("    3. Your client opens it in their browser — no app needed")
    print("    4. They heart their favourites → click Send My Picks")
    print("    5. Their email opens pre-filled with their selections")
    print()

    # Open the file and containing folder
    try:
        import subprocess
        subprocess.run(["open", str(out_path)], check=False)
    except Exception:
        pass


if __name__ == "__main__":
    main()
