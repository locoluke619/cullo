#!/usr/bin/env python3
"""
STEP 4: BUILD YOUR PHOTOGRAPHY WEBSITE
========================================
This script takes your approved photos and creates a beautiful,
professional photography website ready for GitHub Pages.

How to run:
    python scripts/03_build_website.py

Or click "Build Website" in the review app.
"""

import json
import shutil
import sys
from pathlib import Path
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import *


def optimize_photo(source_path, dest_folder, max_full=1920, max_thumb=600):
    """
    Create optimized versions of a photo for the web.
    Returns (full_filename, thumb_filename).
    """
    filename = Path(source_path).stem
    full_name = f"{filename}_full.jpg"
    thumb_name = f"{filename}_thumb.jpg"

    with Image.open(source_path) as img:
        if img.mode not in ("RGB",):
            img = img.convert("RGB")

        # Full-size version (max 1920px, good quality)
        full = img.copy()
        if max(full.size) > max_full:
            ratio = max_full / max(full.size)
            full = full.resize(
                (int(full.width * ratio), int(full.height * ratio)),
                Image.LANCZOS,
            )
        full.save(dest_folder / full_name, "JPEG", quality=88, optimize=True)

        # Thumbnail version (max 600px, lighter)
        thumb = img.copy()
        if max(thumb.size) > max_thumb:
            ratio = max_thumb / max(thumb.size)
            thumb = thumb.resize(
                (int(thumb.width * ratio), int(thumb.height * ratio)),
                Image.LANCZOS,
            )
        thumb.save(dest_folder / thumb_name, "JPEG", quality=80, optimize=True)

    return full_name, thumb_name


def load_design_brief():
    """Load the design brief saved by the AI Website Design Consultant."""
    brief_path = DATA_DIR / "design_brief.json"
    if brief_path.exists():
        try:
            with open(brief_path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def resolve_brief_styles(brief):
    """
    Translate the free-text design brief into concrete CSS/layout values.
    Returns a dict of resolved design tokens.
    """
    style_raw    = (brief.get("style", "") or "").lower()
    color_raw    = (brief.get("primary_color", "") or "").lower()
    accent_raw   = (brief.get("accent_color", "") or "").lower()
    typo_raw     = (brief.get("typography", "") or "").lower()
    layout_raw   = (brief.get("layout", "") or "").lower()
    hero_mood    = brief.get("hero_mood", "") or ""
    color_desc   = (brief.get("color_palette_description", "") or "").lower()

    # ── Background / surface ──────────────────────────────────────────────
    if any(k in style_raw for k in ["warm", "lifestyle", "earthy"]):
        bg      = "#0d0b09"
        surface = "#161210"
        border  = "#2a2218"
    elif any(k in style_raw for k in ["minimal", "clean", "light"]):
        bg      = "#0f0f0f"
        surface = "#181818"
        border  = "#242424"
    elif any(k in style_raw for k in ["bold", "dramatic"]):
        bg      = "#050507"
        surface = "#0f0f12"
        border  = "#1e1e24"
    else:  # editorial / moody / default
        bg      = "#0a0a0a"
        surface = "#141414"
        border  = "#222"

    # ── Accent color ──────────────────────────────────────────────────────
    # Priority: explicit accent_color from brief → primary_color keyword → style fallback
    accent = None
    for src in [accent_raw, color_raw, color_desc]:
        if not src:
            continue
        if any(k in src for k in ["violet", "purple", "lavender"]):
            accent = "#A78BFA"; break
        if any(k in src for k in ["warm", "gold", "amber", "orange", "earthy", "earth"]):
            accent = "#c8a97e"; break
        if any(k in src for k in ["cool", "blue", "teal", "cyan", "slate"]):
            accent = "#7ba7bc"; break
        if any(k in src for k in ["white", "b&w", "black and white", "monochrome", "mono"]):
            accent = "#e0e0e0"; break
        if any(k in src for k in ["green", "sage", "olive", "forest"]):
            accent = "#6db896"; break
        if any(k in src for k in ["pink", "rose", "blush"]):
            accent = "#f4a7b9"; break
        if any(k in src for k in ["red", "crimson", "coral"]):
            accent = "#e05c5c"; break
        # Hex color directly mentioned
        import re
        hex_match = re.search(r'#[0-9a-fA-F]{6}', src)
        if hex_match:
            accent = hex_match.group(0); break

    if not accent:
        # Fall back by style
        if any(k in style_raw for k in ["warm", "lifestyle"]):
            accent = "#c8a97e"
        elif any(k in style_raw for k in ["bold", "dramatic"]):
            accent = "#A78BFA"
        elif any(k in style_raw for k in ["minimal", "clean"]):
            accent = "#e0e0e0"
        else:
            accent = "#c8a97e"  # classic warm gold default

    # ── Typography ────────────────────────────────────────────────────────
    if any(k in typo_raw for k in ["sans", "modern", "clean", "minimal"]):
        heading_font  = "'Inter', sans-serif"
        heading_weight = "600"
        font_import   = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');"
    elif any(k in typo_raw for k in ["serif", "classic", "editorial", "traditional"]):
        heading_font  = "'Playfair Display', Georgia, serif"
        heading_weight = "500"
        font_import   = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&display=swap');"
    else:  # mixed (default)
        heading_font  = "'Playfair Display', Georgia, serif"
        heading_weight = "500"
        font_import   = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;500;600;700&display=swap');"

    # ── Gallery layout ────────────────────────────────────────────────────
    if any(k in layout_raw for k in ["grid", "uniform", "square"]):
        gallery_layout = "grid"        # CSS grid, uniform thumbnails
    elif any(k in layout_raw for k in ["magazine", "editorial", "feature"]):
        gallery_layout = "magazine"    # first photo featured large, rest masonry
    else:
        gallery_layout = "masonry"     # default: CSS columns masonry

    # ── Hero subtitle / mood ──────────────────────────────────────────────
    if hero_mood:
        subtitle = hero_mood[:60]   # trim to keep it short
    elif any(k in style_raw for k in ["editorial", "moody"]):
        subtitle = "An Editorial Collection"
    elif any(k in style_raw for k in ["warm", "lifestyle"]):
        subtitle = "Moments Worth Keeping"
    elif any(k in style_raw for k in ["bold", "dramatic"]):
        subtitle = "Captured Without Compromise"
    elif any(k in style_raw for k in ["minimal", "clean"]):
        subtitle = "Photography"
    else:
        subtitle = "A Curated Collection"

    # ── Hero brightness ───────────────────────────────────────────────────
    hero_brightness = "0.45" if any(k in style_raw for k in ["moody", "dramatic", "editorial"]) else "0.5"

    return {
        "bg":             bg,
        "surface":        surface,
        "border":         border,
        "accent":         accent,
        "heading_font":   heading_font,
        "heading_weight": heading_weight,
        "font_import":    font_import,
        "gallery_layout": gallery_layout,
        "subtitle":       subtitle,
        "hero_brightness": hero_brightness,
        "has_brief":      bool(brief),
    }


def generate_html(photos_data, site_title, site_author, brief=None):
    """Generate the complete website HTML with embedded CSS and JS."""
    # Resolve design tokens from brief (or use defaults)
    tokens = resolve_brief_styles(brief or {})

    bg             = tokens["bg"]
    surface        = tokens["surface"]
    border         = tokens["border"]
    accent         = tokens["accent"]
    heading_font   = tokens["heading_font"]
    heading_weight = tokens["heading_weight"]
    font_import    = tokens["font_import"]
    gallery_layout = tokens["gallery_layout"]
    subtitle       = tokens["subtitle"]
    hero_brightness = tokens["hero_brightness"]

    # Build photo entries for the gallery
    gallery_items = []
    hero_photo = photos_data[0] if photos_data else None

    for i, photo in enumerate(photos_data):
        analysis = photo.get("claude_analysis", {})
        title = analysis.get("title", "Untitled")
        summary = analysis.get("summary", "")
        score = analysis.get("score", "")
        composition = analysis.get("composition", "")
        technical = analysis.get("technical", "")
        mood = analysis.get("mood", "")
        story = analysis.get("story", "")
        best_use = analysis.get("best_use", "")

        gallery_items.append({
            "full": photo["full_web"],
            "thumb": photo["thumb_web"],
            "title": title,
            "summary": summary,
            "score": score,
            "composition": composition,
            "technical": technical,
            "mood": mood,
            "story": story,
            "best_use": best_use,
            "index": i,
        })

    # Generate gallery HTML based on layout choice
    gallery_html = ""
    for item in gallery_items:
        if gallery_layout == "magazine" and item["index"] == 0:
            # Featured first photo — full-width hero tile
            gallery_html += f"""
        <div class="gallery-item gallery-featured" onclick="openLightbox({item['index']})">
            <img src="photos/{item['full']}" alt="{item['title']}" loading="lazy">
            <div class="gallery-overlay">
                <div>
                    <span class="gallery-title" style="font-size:20px">{item['title']}</span>
                    <p style="font-size:13px;margin-top:4px;opacity:0.8">{item['summary'][:80] + '…' if len(item['summary']) > 80 else item['summary']}</p>
                </div>
                <span class="gallery-score">{item['score']}/10</span>
            </div>
        </div>"""
        else:
            gallery_html += f"""
        <div class="gallery-item" onclick="openLightbox({item['index']})">
            <img src="photos/{item['thumb']}" alt="{item['title']}" loading="lazy">
            <div class="gallery-overlay">
                <span class="gallery-title">{item['title']}</span>
                <span class="gallery-score">{item['score']}/10</span>
            </div>
        </div>"""

    # Generate lightbox data as JSON
    lightbox_data = json.dumps(gallery_items)

    hero_image = f"photos/{hero_photo['full_web']}" if hero_photo else ""
    hero_title = hero_photo.get("claude_analysis", {}).get("title", "") if hero_photo else ""

    # Choose gallery CSS based on layout
    if gallery_layout == "grid":
        gallery_css = """
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 12px;
        }
        .gallery-item img { aspect-ratio: 4/3; object-fit: cover; width: 100%; display: block; }"""
    elif gallery_layout == "magazine":
        gallery_css = """
        .gallery { columns: 3; column-gap: 16px; }
        .gallery-item { break-inside: avoid; margin-bottom: 16px; }
        .gallery-featured { break-inside: avoid; column-span: all; margin-bottom: 16px; }
        .gallery-featured img { width: 100%; max-height: 70vh; object-fit: cover; display: block; }"""
    else:  # masonry (default)
        gallery_css = """
        .gallery { columns: 3; column-gap: 16px; }
        .gallery-item { break-inside: avoid; margin-bottom: 16px; }"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_title}</title>
    <style>
        /* ==========================================
           PHOTOGRAPHY PORTFOLIO - STYLES
           ========================================== */

        {font_import}

        :root {{
            --bg: {bg};
            --surface: {surface};
            --border: {border};
            --text: #f5f5f5;
            --text-muted: #777;
            --accent: {accent};
            --heading-font: {heading_font};
            --heading-weight: {heading_weight};
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            overflow-x: hidden;
        }}

        /* --- Hero Section --- */
        .hero {{
            height: 100vh;
            width: 100%;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }}

        .hero-image {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            filter: brightness(0.5);
        }}

        .hero-content {{
            position: relative;
            z-index: 2;
            text-align: center;
            padding: 0 20px;
        }}

        .hero-title {{
            font-family: var(--heading-font);
            font-size: clamp(36px, 8vw, 80px);
            font-weight: var(--heading-weight);
            letter-spacing: 2px;
            margin-bottom: 16px;
            opacity: 0;
            animation: fadeUp 1.2s ease forwards 0.3s;
        }}

        .hero-subtitle {{
            font-size: clamp(14px, 2vw, 18px);
            color: var(--accent);
            letter-spacing: 4px;
            text-transform: uppercase;
            font-weight: 300;
            opacity: 0;
            animation: fadeUp 1.2s ease forwards 0.6s;
        }}

        .hero-scroll {{
            position: absolute;
            bottom: 40px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 2;
            color: var(--text);
            text-decoration: none;
            font-size: 13px;
            letter-spacing: 2px;
            text-transform: uppercase;
            opacity: 0;
            animation: fadeUp 1.2s ease forwards 0.9s;
            cursor: pointer;
            background: none;
            border: none;
            font-family: inherit;
        }}

        .hero-scroll::after {{
            content: '';
            display: block;
            width: 1px;
            height: 40px;
            background: var(--accent);
            margin: 12px auto 0;
            animation: pulse 2s ease-in-out infinite;
        }}

        @keyframes fadeUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 0.3; }}
            50% {{ opacity: 1; }}
        }}

        .hero-gradient {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 40%;
            background: linear-gradient(transparent, var(--bg));
            z-index: 1;
        }}

        /* --- Gallery Section --- */
        .gallery-section {{
            padding: 80px 24px;
            max-width: 1400px;
            margin: 0 auto;
        }}

        .section-header {{
            text-align: center;
            margin-bottom: 60px;
        }}

        .section-title {{
            font-family: var(--heading-font);
            font-size: 36px;
            font-weight: var(--heading-weight);
            margin-bottom: 12px;
        }}

        .section-divider {{
            width: 60px;
            height: 2px;
            background: var(--accent);
            margin: 0 auto 16px;
        }}

        .section-subtitle {{
            color: var(--text-muted);
            font-size: 15px;
        }}

        /* --- Gallery Layout --- */
        {gallery_css}

        .gallery-item {{
            position: relative;
            border-radius: 8px;
            overflow: hidden;
            cursor: pointer;
        }}

        .gallery-item img {{
            width: 100%;
            display: block;
            transition: transform 0.5s ease;
        }}

        .gallery-item:hover img {{
            transform: scale(1.03);
        }}

        .gallery-overlay {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 40px 16px 16px;
            background: linear-gradient(transparent, rgba(0,0,0,0.8));
            opacity: 0;
            transition: opacity 0.3s ease;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}

        .gallery-item:hover .gallery-overlay {{
            opacity: 1;
        }}

        .gallery-title {{
            font-size: 14px;
            font-weight: 500;
        }}

        .gallery-score {{
            font-size: 12px;
            color: var(--accent);
            font-weight: 600;
        }}

        /* --- Lightbox --- */
        .lightbox {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.95);
            z-index: 9999;
            overflow-y: auto;
        }}

        .lightbox.active {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }}

        .lightbox-close {{
            position: fixed;
            top: 20px;
            right: 24px;
            width: 44px;
            height: 44px;
            border: none;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 24px;
            border-radius: 50%;
            cursor: pointer;
            z-index: 10001;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }}

        .lightbox-close:hover {{
            background: rgba(255,255,255,0.2);
        }}

        .lightbox-nav {{
            position: fixed;
            top: 50%;
            transform: translateY(-50%);
            width: 50px;
            height: 50px;
            border: none;
            background: rgba(255,255,255,0.08);
            color: white;
            font-size: 24px;
            border-radius: 50%;
            cursor: pointer;
            z-index: 10001;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }}

        .lightbox-nav:hover {{
            background: rgba(255,255,255,0.15);
        }}

        .lightbox-prev {{ left: 20px; }}
        .lightbox-next {{ right: 20px; }}

        .lightbox-image {{
            max-width: 90%;
            max-height: 65vh;
            object-fit: contain;
            border-radius: 4px;
            margin-bottom: 30px;
        }}

        .lightbox-info {{
            max-width: 700px;
            width: 100%;
            text-align: center;
        }}

        .lightbox-title {{
            font-family: var(--heading-font);
            font-size: 28px;
            font-weight: var(--heading-weight);
            margin-bottom: 6px;
        }}

        .lightbox-score-display {{
            color: var(--accent);
            font-size: 14px;
            letter-spacing: 2px;
            margin-bottom: 20px;
        }}

        .lightbox-details {{
            text-align: left;
            display: grid;
            gap: 16px;
        }}

        .lightbox-detail {{
            padding: 16px;
            background: rgba(255,255,255,0.04);
            border-radius: 8px;
            border-left: 3px solid var(--accent);
        }}

        .lightbox-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text-muted);
            margin-bottom: 6px;
        }}

        .lightbox-text {{
            font-size: 14px;
            line-height: 1.7;
            color: #ccc;
        }}

        /* --- Footer --- */
        .footer {{
            text-align: center;
            padding: 40px 20px;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 13px;
        }}

        .footer a {{
            color: var(--accent);
            text-decoration: none;
        }}

        /* --- Responsive --- */
        @media (max-width: 1024px) {{
            .gallery {{ columns: 2; }}
        }}

        @media (max-width: 640px) {{
            .gallery {{ columns: 1; }}
            .gallery-section {{ padding: 40px 16px; }}
            .lightbox-nav {{ display: none; }}
        }}
    </style>
</head>
<body>

    <!-- Hero Section -->
    <section class="hero">
        <img class="hero-image" src="{hero_image}" alt="{site_title}" style="filter:brightness({hero_brightness})">
        <div class="hero-gradient"></div>
        <div class="hero-content">
            <h1 class="hero-title">{site_title}</h1>
            <p class="hero-subtitle">{subtitle}</p>
        </div>
        <button class="hero-scroll" onclick="document.getElementById('gallery').scrollIntoView({{behavior:'smooth'}})">
            Explore
        </button>
    </section>

    <!-- Gallery Section -->
    <section class="gallery-section" id="gallery">
        <div class="section-header">
            <h2 class="section-title">The Collection</h2>
            <div class="section-divider"></div>
            <p class="section-subtitle">{len(photos_data)} photographs, curated with AI</p>
        </div>
        <div class="gallery">
            {gallery_html}
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <p>&copy; {site_author} &mdash; Curated with AI</p>
    </footer>

    <!-- Lightbox -->
    <div class="lightbox" id="lightbox">
        <button class="lightbox-close" onclick="closeLightbox()">&times;</button>
        <button class="lightbox-nav lightbox-prev" onclick="prevPhoto()">&lsaquo;</button>
        <button class="lightbox-nav lightbox-next" onclick="nextPhoto()">&rsaquo;</button>
        <img class="lightbox-image" id="lb-image" src="" alt="">
        <div class="lightbox-info">
            <h3 class="lightbox-title" id="lb-title"></h3>
            <div class="lightbox-score-display" id="lb-score"></div>
            <div class="lightbox-details">
                <div class="lightbox-detail">
                    <div class="lightbox-label">Why This Photo</div>
                    <div class="lightbox-text" id="lb-summary"></div>
                </div>
                <div class="lightbox-detail">
                    <div class="lightbox-label">Composition</div>
                    <div class="lightbox-text" id="lb-composition"></div>
                </div>
                <div class="lightbox-detail">
                    <div class="lightbox-label">Technical Quality</div>
                    <div class="lightbox-text" id="lb-technical"></div>
                </div>
                <div class="lightbox-detail">
                    <div class="lightbox-label">Mood &amp; Story</div>
                    <div class="lightbox-text" id="lb-mood"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Photo data
        const photos = {lightbox_data};
        let currentIndex = 0;

        function openLightbox(index) {{
            currentIndex = index;
            updateLightbox();
            document.getElementById('lightbox').classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        function closeLightbox() {{
            document.getElementById('lightbox').classList.remove('active');
            document.body.style.overflow = '';
        }}

        function prevPhoto() {{
            currentIndex = (currentIndex - 1 + photos.length) % photos.length;
            updateLightbox();
        }}

        function nextPhoto() {{
            currentIndex = (currentIndex + 1) % photos.length;
            updateLightbox();
        }}

        function updateLightbox() {{
            const photo = photos[currentIndex];
            document.getElementById('lb-image').src = 'photos/' + photo.full;
            document.getElementById('lb-title').textContent = photo.title;
            document.getElementById('lb-score').textContent = photo.score + '/10';
            document.getElementById('lb-summary').textContent = photo.summary;
            document.getElementById('lb-composition').textContent = photo.composition;
            document.getElementById('lb-technical').textContent = photo.technical;
            document.getElementById('lb-mood').textContent =
                (photo.mood || '') + (photo.story ? ' ' + photo.story : '');
        }}

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            if (!document.getElementById('lightbox').classList.contains('active')) return;
            if (e.key === 'Escape') closeLightbox();
            if (e.key === 'ArrowLeft') prevPhoto();
            if (e.key === 'ArrowRight') nextPhoto();
        }});

        // Click outside lightbox image to close
        document.getElementById('lightbox').addEventListener('click', (e) => {{
            if (e.target === document.getElementById('lightbox')) closeLightbox();
        }});

        // Fade in gallery items on scroll
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }}
            }});
        }}, {{ threshold: 0.1 }});

        document.querySelectorAll('.gallery-item').forEach(item => {{
            item.style.opacity = '0';
            item.style.transform = 'translateY(20px)';
            item.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(item);
        }});
    </script>
</body>
</html>"""
    return html


def main():
    print()
    print("=" * 55)
    print("  STEP 4: Building Your Photography Website")
    print("=" * 55)
    print()

    # Load catalog
    if not CATALOG_FILE.exists():
        print("  ERROR: No catalog found! Run Steps 1-3 first.")
        sys.exit(1)

    with open(CATALOG_FILE) as f:
        catalog = json.load(f)

    # Get approved photos
    approved = [
        p for p in catalog
        if p.get("approved") is True
        and p.get("claude_analysis")
        and "error" not in p.get("claude_analysis", {})
    ]

    if not approved:
        # If nothing explicitly approved, use all website-worthy photos
        approved = [
            p for p in catalog
            if p.get("claude_analysis", {}).get("website_worthy", False)
            and "error" not in p.get("claude_analysis", {})
        ]
        if approved:
            print(f"  No photos were manually approved.")
            print(f"  Using {len(approved)} photos Claude marked as website-worthy.")
            print()
        else:
            print("  ERROR: No approved photos found!")
            print("  Run 'python app.py' and approve some photos first,")
            print("  or run Step 2 to get Claude's recommendations.")
            sys.exit(1)

    # Sort by Claude's score (best first)
    approved.sort(
        key=lambda x: x.get("claude_analysis", {}).get("score", 0),
        reverse=True,
    )

    print(f"  Building website with {len(approved)} photos...")
    print()

    # Prepare docs folder
    photos_dir = DOCS_DIR / "photos"
    if photos_dir.exists():
        shutil.rmtree(photos_dir)
    photos_dir.mkdir(parents=True, exist_ok=True)

    # Process each photo
    print("  Optimizing photos for web...")
    for photo in tqdm(approved, desc="  Processing", unit="photo"):
        source = Path(photo["file"])
        if not source.exists():
            print(f"  WARNING: File not found: {source}")
            continue

        full_name, thumb_name = optimize_photo(source, photos_dir)
        photo["full_web"] = full_name
        photo["thumb_web"] = thumb_name

    # Filter out any that failed
    approved = [p for p in approved if "full_web" in p]

    # Load design brief (if the user ran the Design Consultant)
    brief = load_design_brief()
    if brief:
        tokens = resolve_brief_styles(brief)
        print(f"  Design brief found — applying your style preferences:")
        print(f"    Style:    {brief.get('style', 'default')}")
        print(f"    Accent:   {tokens['accent']}")
        print(f"    Layout:   {tokens['gallery_layout']}")
        print(f"    Subtitle: {tokens['subtitle']}")
        print()
    else:
        print("  No design brief found — using default style.")
        print("  Tip: click 'Design Website ✦' in the dashboard to customize!")
        print()

    # Generate HTML
    print("  Generating website...")
    html = generate_html(approved, SITE_TITLE, SITE_AUTHOR, brief=brief)

    # Write index.html
    index_path = DOCS_DIR / "index.html"
    with open(index_path, "w") as f:
        f.write(html)

    # Calculate total size
    total_size = sum(
        f.stat().st_size for f in photos_dir.rglob("*") if f.is_file()
    )
    total_size_mb = total_size / (1024 * 1024)

    print()
    print("=" * 55)
    print("  WEBSITE BUILT SUCCESSFULLY!")
    print("=" * 55)
    print()
    print(f"  Photos included:    {len(approved)}")
    print(f"  Website location:   {DOCS_DIR}")
    print(f"  Total size:         {total_size_mb:.1f} MB")
    print()
    print("  TO PREVIEW YOUR WEBSITE:")
    print(f"    Open this file in your browser:")
    print(f"    {index_path}")
    print()
    print("  TO PUT IT ONLINE (GitHub Pages):")
    print("    See README.md for step-by-step instructions")
    print()


if __name__ == "__main__":
    main()
