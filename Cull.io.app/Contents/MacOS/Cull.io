#!/bin/bash
# ==============================================
#  cull.io — AI Photo Curation Studio
# ==============================================

# If not running inside a Terminal, reopen this script in one
if [ ! -t 1 ]; then
    SCRIPT="$0"
    osascript <<APPLESCRIPT
tell application "Terminal"
    activate
    do script "bash '$SCRIPT'"
end tell
APPLESCRIPT
    exit 0
fi

# Always run from the project folder (3 levels up from MacOS/)
PROJECT="$(cd "$(dirname "$0")/../../.."; pwd)"
cd "$PROJECT"

# ── First-time setup ───────────────────────────────────────────
if [ ! -d "venv" ]; then
    clear
    echo ""
    echo "  ╔══════════════════════════════════════╗"
    echo "  ║   c u l l . i o                      ║"
    echo "  ║   AI Photo Curation Studio            ║"
    echo "  ╚══════════════════════════════════════╝"
    echo ""
    echo "  Welcome! Let's get you set up."
    echo "  This takes about 2 minutes and only happens once."
    echo ""
    read -p "  Press Enter to begin…"
    echo ""

    # ── Python check ──────────────────────────────
    echo "  Checking your computer…"
    echo ""

    if ! command -v python3 &> /dev/null; then
        echo "  ✗  Python is not installed."
        echo ""
        echo "  No problem — here's how to get it:"
        echo "    1. Opening python.org in your browser now…"
        open "https://www.python.org/downloads/" 2>/dev/null || true
        echo "    2. Click the big yellow 'Download Python' button"
        echo "    3. Run the installer"
        echo "    4. Double-click cull.io again"
        echo ""
        read -p "  Press Enter to close…"
        exit 1
    fi

    echo "  ✓  Python found: $(python3 --version)"
    echo ""

    # ── Install dependencies ───────────────────────
    echo "  Installing cull.io… (about a minute)"
    echo ""
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt --quiet
    echo "  ✓  Done."
    echo ""

    # ── Create folders ─────────────────────────────
    mkdir -p data docs photos

    # ── .env file ──────────────────────────────────
    if [ ! -f .env ]; then
        cp .env.example .env
    fi

    # ── Step 1: Your name ──────────────────────────
    echo "  ─────────────────────────────────────────"
    echo "  Step 1 of 4 — Your Name"
    echo "  ─────────────────────────────────────────"
    echo ""
    echo "  This appears on your portfolio website."
    echo ""
    read -p "  What's your name? " USER_NAME
    USER_NAME="${USER_NAME:-Photographer}"
    sed -i '' "s|^SITE_TITLE=.*|SITE_TITLE=${USER_NAME}'s Photography|" .env
    sed -i '' "s|^SITE_AUTHOR=.*|SITE_AUTHOR=${USER_NAME}|" .env
    echo ""
    echo "  ✓  Portfolio: ${USER_NAME}'s Photography"
    echo ""

    # ── Step 2: Photo folder ───────────────────────
    echo "  ─────────────────────────────────────────"
    echo "  Step 2 of 4 — Your Photos"
    echo "  ─────────────────────────────────────────"
    echo ""
    echo "  Where are the photos you want to sort through?"
    echo ""
    echo "  Option A — Easy:   Put your photos in the 'photos' folder"
    echo "             inside this cull.io folder. Press Enter to use this."
    echo ""
    echo "  Option B — Custom: Drag your photo folder into this window"
    echo "             right now, then press Enter."
    echo ""

    while true; do
        read -p "  Photo folder (Enter = use the photos/ folder): " PHOTO_PATH

        if [ -z "$PHOTO_PATH" ]; then
            PHOTO_PATH="photos"
            echo ""
            echo "  ✓  Using the photos/ folder inside cull.io."
            echo "     → Drop your photos in:  $PROJECT/photos"
            echo ""
            echo "  Opening that folder for you now…"
            open photos 2>/dev/null || true
            break
        else
            PHOTO_PATH=$(echo "$PHOTO_PATH" | sed "s/^['\"]//;s/['\"]$//;s/^ //;s/ $//")
            PHOTO_PATH="${PHOTO_PATH/#\~/$HOME}"
            if [ -d "$PHOTO_PATH" ]; then
                JPG_COUNT=$(find "$PHOTO_PATH" -maxdepth 2 \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l | tr -d ' ')
                echo ""
                echo "  ✓  Found that folder!"
                [ "$JPG_COUNT" -gt 0 ] && echo "  ✓  Found $JPG_COUNT photos" || echo "  ⚠  No photos yet — you can add them later."
                break
            else
                echo ""
                echo "  ✗  Can't find that folder. Try again, or drag it into this window."
                echo ""
            fi
        fi
    done

    if grep -q "^PHOTOS_FOLDER=" .env; then
        sed -i '' "s|^PHOTOS_FOLDER=.*|PHOTOS_FOLDER=$PHOTO_PATH|" .env
    else
        echo "PHOTOS_FOLDER=$PHOTO_PATH" >> .env
    fi
    echo ""

    # ── Step 3: Photo type ─────────────────────────
    echo "  ─────────────────────────────────────────"
    echo "  Step 3 of 4 — Type of Photos"
    echo "  ─────────────────────────────────────────"
    echo ""
    echo "  Are these photos straight from your camera,"
    echo "  or have you already edited them?"
    echo ""
    echo "    1  Straight from camera  (RAW or unedited JPG)"
    echo "    2  Already edited        (Lightroom, Photoshop, etc.)"
    echo ""

    while true; do
        read -p "  Enter 1 or 2: " PHOTO_TYPE_CHOICE
        if [ "$PHOTO_TYPE_CHOICE" = "1" ]; then
            WORKSPACE_TYPE="shoot"
            echo ""
            echo "  ✓  Got it — cull.io will help you pick the keepers."
            break
        elif [ "$PHOTO_TYPE_CHOICE" = "2" ]; then
            WORKSPACE_TYPE="edited"
            echo ""
            echo "  ✓  Got it — cull.io will evaluate your edits."
            break
        else
            echo "  Please enter 1 or 2."
        fi
    done

    # Resolve full path for workspace
    if [ "$PHOTO_PATH" = "photos" ]; then
        WS_FOLDER="$PROJECT/photos"
    else
        WS_FOLDER="$PHOTO_PATH"
    fi

    mkdir -p "$PROJECT/data/default"
    python3 -c "
import json, pathlib
ws_file = pathlib.Path('$PROJECT/data/workspaces.json')
active_file = pathlib.Path('$PROJECT/data/active_workspace.json')
ws_list = json.loads(ws_file.read_text()).get('workspaces', []) if ws_file.exists() else []
default = next((w for w in ws_list if w['id'] == 'default'), None)
if default:
    default['folder'] = '$WS_FOLDER'
    default['type']   = '$WORKSPACE_TYPE'
else:
    ws_list.insert(0, {'id': 'default', 'name': 'My Shoot', 'folder': '$WS_FOLDER', 'type': '$WORKSPACE_TYPE'})
ws_file.write_text(json.dumps({'workspaces': ws_list}, indent=2))
active_file.write_text(json.dumps({'id': 'default'}))
"
    echo ""

    # ── Step 4: API Key ────────────────────────────
    echo "  ─────────────────────────────────────────"
    echo "  Step 4 of 4 — Claude AI Key"
    echo "  ─────────────────────────────────────────"
    echo ""
    echo "  cull.io uses Claude AI to write expert analysis of your photos."
    echo "  You need an Anthropic account with about \$5 in credits."
    echo "  (50 photos costs roughly \$1.)"
    echo ""
    echo "  Opening the Anthropic website for you now…"
    open "https://console.anthropic.com" 2>/dev/null || true
    echo ""
    echo "    1. Create a free account (or sign in)"
    echo "    2. Settings → Billing → add \$5 in credits"
    echo "    3. API Keys → Create Key → copy it  (starts with sk-ant-…)"
    echo "    4. Paste it below"
    echo ""

    while true; do
        read -p "  Paste your API key (or Enter to skip for now): " API_KEY
        if [ -z "$API_KEY" ]; then
            echo ""
            echo "  Skipped. You can add it later in the .env file."
            break
        elif [[ "$API_KEY" == sk-ant-* ]]; then
            sed -i '' "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$API_KEY|" .env
            echo ""
            echo "  ✓  API key saved!"
            break
        else
            echo ""
            echo "  ✗  That doesn't look right — keys start with sk-ant-"
            echo "     Try again, or press Enter to skip."
            echo ""
        fi
    done
    echo ""

    echo "  ╔══════════════════════════════════════╗"
    echo "  ║   You're all set!  Starting cull.io… ║"
    echo "  ╚══════════════════════════════════════╝"
    echo ""
    sleep 1
fi

# ── Launch ─────────────────────────────────────────────────────
source venv/bin/activate
python run.py

read -p "  Press Enter to close…"
