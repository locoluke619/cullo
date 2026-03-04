#!/bin/bash
# ============================================
#  CULLO — One-Time Setup
# ============================================
# Run this once to get everything installed.
#
#   bash setup.sh
# ============================================

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   C U L L O  —  Setup               ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "  ERROR: Python 3 is not installed."
    echo ""
    echo "  Install it from: https://www.python.org/downloads/"
    echo "  Then run this script again."
    echo ""
    exit 1
fi

echo "  Python: $(python3 --version)"
echo ""

# Virtual environment
echo "  [1/4] Creating virtual environment…"
python3 -m venv venv
echo "        Done."
echo ""

# Activate
source venv/bin/activate

# Install packages
echo "  [2/4] Installing packages…"
pip install -r requirements.txt --quiet
echo "        Done."
echo ""

# Create data / docs directories
echo "  [3/4] Creating folders…"
mkdir -p data docs
echo "        Done."
echo ""

# .env file
echo "  [4/4] Setting up configuration…"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "        Created .env — you need to add your API key."
else
    echo "        .env already exists, skipping."
fi
echo ""

echo "  ╔══════════════════════════════════════╗"
echo "  ║   Setup complete!                    ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
echo "  Next: add your Anthropic API key to the .env file."
echo "  Get a key at: https://console.anthropic.com"
echo ""
echo "  Then run:  python run.py"
echo ""
