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


def generate_html(photos_data, site_title, site_author):
    """Generate the complete website HTML with embedded CSS and JS."""

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

    # Generate gallery HTML
    gallery_html = ""
    for item in gallery_items:
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

        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;500;600;700&display=swap');

        :root {{
            --bg: #0a0a0a;
            --surface: #141414;
            --border: #222;
            --text: #f5f5f5;
            --text-muted: #777;
            --accent: #c8a97e;
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
            font-family: 'Playfair Display', Georgia, serif;
            font-size: clamp(36px, 8vw, 80px);
            font-weight: 600;
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
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 36px;
            font-weight: 500;
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

        /* --- Masonry Gallery --- */
        .gallery {{
            columns: 3;
            column-gap: 16px;
        }}

        .gallery-item {{
            break-inside: avoid;
            margin-bottom: 16px;
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
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 28px;
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
        <img class="hero-image" src="{hero_image}" alt="{site_title}">
        <div class="hero-gradient"></div>
        <div class="hero-content">
            <h1 class="hero-title">{site_title}</h1>
            <p class="hero-subtitle">A Curated Collection</p>
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

    # Generate HTML
    print("  Generating website...")
    html = generate_html(approved, SITE_TITLE, SITE_AUTHOR)

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
