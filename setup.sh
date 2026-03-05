#!/bin/bash
# ============================================
#  CULLO — One-Time Setup
# ============================================
#   bash setup.sh
# ============================================

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   C U L L O  —  Setup               ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ── Python check ──────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "  ERROR: Python 3 is not installed."
    echo "  Install it from: https://www.python.org/downloads/"
    echo ""
    exit 1
fi
echo "  Python: $(python3 --version)"
echo ""

# ── Virtual environment ───────────────────────
echo "  [1/6] Creating virtual environment…"
python3 -m venv venv
source venv/bin/activate
echo "        Done."
echo ""

# ── Install packages ──────────────────────────
echo "  [2/6] Installing packages…"
pip install -r requirements.txt --quiet
echo "        Done."
echo ""

# ── Create folders ────────────────────────────
echo "  [3/6] Creating folders…"
mkdir -p data docs photos
echo "        Done."
echo ""

# ── .env file ─────────────────────────────────
echo "  [4/6] Setting up configuration…"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "        Created .env file."
else
    echo "        .env already exists."
fi
echo ""

# ── Your name ─────────────────────────────────
echo "  [5/6] Personalise your portfolio"
echo ""
read -p "  Your name (for the website title): " USER_NAME
USER_NAME="${USER_NAME:-Photographer}"

# Write name into .env
sed -i '' "s|^SITE_TITLE=.*|SITE_TITLE=${USER_NAME}'s Photography|" .env
sed -i '' "s|^SITE_AUTHOR=.*|SITE_AUTHOR=${USER_NAME}|" .env
echo ""
echo "  Portfolio name set to: ${USER_NAME}'s Photography"
echo ""

# ── Photo folder ──────────────────────────────
echo "  [6/6] Where are your photos?"
echo ""
echo "  Option A (simplest): just drop your JPGs into the"
echo "            \"photos\" folder inside this project — press Enter."
echo ""
echo "  Option B: paste the full path to a folder on your computer,"
echo "            e.g.  /Users/yourname/Pictures/MyShoot"
echo ""

while true; do
    read -p "  Photo folder (Enter = use photos/ folder): " PHOTO_PATH

    if [ -z "$PHOTO_PATH" ]; then
        PHOTO_PATH="photos"
        FULL_PATH="$(pwd)/photos"
        echo ""
        echo "  Using the photos/ folder inside this project."
        echo "  Drop your JPGs in:  $FULL_PATH"
        break
    else
        # Expand ~ if present
        PHOTO_PATH="${PHOTO_PATH/#\~/$HOME}"

        if [ -d "$PHOTO_PATH" ]; then
            # Count JPGs in the folder
            JPG_COUNT=$(find "$PHOTO_PATH" -maxdepth 1 \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l | tr -d ' ')
            echo ""
            echo "  ✓ Found folder: $PHOTO_PATH"
            if [ "$JPG_COUNT" -eq 0 ]; then
                echo "  ⚠ No JPG/PNG photos found in that folder — make sure you're pointing to the right place."
                read -p "  Use it anyway? [y/n]: " CONFIRM
                [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ] && break || continue
            else
                echo "  ✓ Found $JPG_COUNT photos"
                break
            fi
        else
            echo ""
            echo "  ✗ That folder doesn't exist: $PHOTO_PATH"
            echo "    Check the path and try again (or press Enter to use the default)."
            echo ""
        fi
    fi
done

# Write photo path into .env
if grep -q "^PHOTOS_FOLDER=" .env; then
    sed -i '' "s|^PHOTOS_FOLDER=.*|PHOTOS_FOLDER=$PHOTO_PATH|" .env
else
    echo "PHOTOS_FOLDER=$PHOTO_PATH" >> .env
fi

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   Setup complete!                    ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
echo "  One thing left — add your Anthropic API key:"
echo ""
echo "    1. Go to https://console.anthropic.com"
echo "    2. Create an account and add \$5 in credits"
echo "    3. Click \"API Keys\" → \"Create Key\" → copy it"
echo "    4. Open the .env file and paste it next to ANTHROPIC_API_KEY="
echo ""
if [ "$PHOTO_PATH" = "photos" ]; then
echo "  Also: drop your photos into the  photos/  folder."
echo ""
fi
echo "  Then run:  python run.py"
echo ""
