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
PHOTOS_FOLDER = os.getenv("PHOTOS_FOLDER", str(PROJECT_DIR / "micheals_pictures"))

# --- API Settings ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# --- Scoring Settings ---
TOP_PERCENT = int(os.getenv("TOP_PERCENT", "20"))
MAX_CLAUDE_PHOTOS = int(os.getenv("MAX_CLAUDE_PHOTOS", "50"))

# --- Website Settings ---
SITE_TITLE = os.getenv("SITE_TITLE", "Photography Portfolio")
SITE_AUTHOR = os.getenv("SITE_AUTHOR", "Michael")

# --- Photo Formats We Can Process ---
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}

# --- File Paths for Data ---
CATALOG_FILE = DATA_DIR / "catalog.json"

# Make sure data directory exists
DATA_DIR.mkdir(exist_ok=True)
DOCS_DIR.mkdir(exist_ok=True)
