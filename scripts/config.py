"""
Shared settings used by all scripts.
Reads your .env file so you only configure things in one place.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load settings from .env file
PROJECT_DIR = Path(__file__).parent.parent
load_dotenv(PROJECT_DIR / ".env")

# --- Folder Paths ---
DATA_DIR = PROJECT_DIR / "data"
DOCS_DIR = PROJECT_DIR / "docs"

# Resolve PHOTOS_FOLDER: if it's a relative path, treat it as relative to the project root
# Fall back to "photos" if the value is missing or blank
_photos_raw = os.getenv("PHOTOS_FOLDER", "photos").strip() or "photos"
_photos_path = Path(_photos_raw)
PHOTOS_FOLDER = str(_photos_path if _photos_path.is_absolute() else PROJECT_DIR / _photos_raw)

# --- API Settings ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# --- Scoring Settings ---
TOP_PERCENT = int(os.getenv("TOP_PERCENT", "20"))
MAX_CLAUDE_PHOTOS = int(os.getenv("MAX_CLAUDE_PHOTOS", "50"))

# --- Website Settings ---
SITE_TITLE = os.getenv("SITE_TITLE", "Photography Portfolio")
SITE_AUTHOR = os.getenv("SITE_AUTHOR", "Photographer")

# --- Client Proof ---
PHOTOGRAPHER_EMAIL = os.getenv("PHOTOGRAPHER_EMAIL", "")

# --- Workspace Type ---
# "shoot"  = straight from camera (RAW or unedited JPG) — evaluate which shots to keep
# "edited" = photos already edited in Lightroom/Photoshop — evaluate the edit quality
WORKSPACE_TYPE = os.getenv("WORKSPACE_TYPE", "shoot")

# --- Budget Tracker ---
# Optional: set MONTHLY_BUDGET=20 in .env to show "Total: $X.XX / $20.00" in the dashboard
MONTHLY_BUDGET = float(os.getenv("MONTHLY_BUDGET", "0") or "0")

# --- Photo Formats We Can Process ---
# Standard formats read directly by Pillow
STANDARD_FORMATS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".heic", ".heif"}

# RAW camera formats — read via rawpy (decoded to RGB for scoring and analysis)
# When both a RAW and a JPG exist for the same filename, the JPG is used
# (faster, and the RAW is preserved for Lightroom export anyway).
RAW_FORMATS = {
    ".cr2", ".cr3",           # Canon
    ".nef", ".nrw",           # Nikon
    ".arw", ".srf", ".sr2",   # Sony
    ".raf",                   # Fujifilm
    ".orf",                   # Olympus
    ".rw2",                   # Panasonic
    ".pef", ".ptx",           # Pentax
    ".dng",                   # Adobe universal RAW / iPhone ProRAW / Android
    ".3fr",                   # Hasselblad
    ".mos",                   # Leaf
    ".iiq",                   # Phase One
}

# All formats Cullo can handle
SUPPORTED_FORMATS = STANDARD_FORMATS | RAW_FORMATS

# --- File Paths for Data ---
CATALOG_FILE = DATA_DIR / "catalog.json"

# Make sure data directory exists
DATA_DIR.mkdir(exist_ok=True)
DOCS_DIR.mkdir(exist_ok=True)
