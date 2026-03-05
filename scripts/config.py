"""
Shared settings used by all scripts.
Reads your .env file so you only configure things in one place.
"""

import json as _json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load settings from .env file
PROJECT_DIR = Path(__file__).parent.parent
load_dotenv(PROJECT_DIR / ".env")

# --- Folder Paths ---
DATA_DIR = PROJECT_DIR / "data"
DOCS_DIR = PROJECT_DIR / "docs"

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

# --- Workspace System ---
WORKSPACES_FILE = DATA_DIR / "workspaces.json"
ACTIVE_WS_FILE  = DATA_DIR / "active_workspace.json"

def _get_active_workspace_dict():
    """Return the active workspace dict from workspaces.json, or a .env-based fallback."""
    ws_list = []
    if WORKSPACES_FILE.exists():
        try:
            ws_list = _json.loads(WORKSPACES_FILE.read_text()).get("workspaces", [])
        except Exception:
            pass

    if not ws_list:
        _photos_raw = os.getenv("PHOTOS_FOLDER", "photos").strip() or "photos"
        return {
            "id": "default",
            "name": "Main Shoot",
            "folder": _photos_raw,
            "type": os.getenv("WORKSPACE_TYPE", "shoot"),
        }

    active_id = ws_list[0]["id"]
    if ACTIVE_WS_FILE.exists():
        try:
            active_id = _json.loads(ACTIVE_WS_FILE.read_text()).get("id", active_id)
        except Exception:
            pass

    for ws in ws_list:
        if ws["id"] == active_id:
            return ws
    return ws_list[0]

_active_ws     = _get_active_workspace_dict()
ACTIVE_WORKSPACE_ID = _active_ws["id"]
WORKSPACE_TYPE = _active_ws.get("type", os.getenv("WORKSPACE_TYPE", "shoot"))

# PHOTOS_FOLDER comes from the active workspace's folder
_ws_folder = _active_ws.get("folder", os.getenv("PHOTOS_FOLDER", "photos")).strip() or "photos"
_wp = Path(_ws_folder)
PHOTOS_FOLDER = str(_wp if _wp.is_absolute() else PROJECT_DIR / _ws_folder)

# Per-workspace data directory
WS_DIR = DATA_DIR / ACTIVE_WORKSPACE_ID
WS_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_FILE = WS_DIR / "catalog.json"
GROUPS_FILE  = WS_DIR / "groups.json"

# --- One-time migration: move flat data/catalog.json → data/default/catalog.json ---
for _fname in ("catalog.json", "groups.json", "semantic_groups.json"):
    _old = DATA_DIR / _fname
    _new = DATA_DIR / "default" / _fname
    if _old.exists() and not _new.exists():
        (DATA_DIR / "default").mkdir(exist_ok=True)
        _old.rename(_new)

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
