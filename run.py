#!/usr/bin/env python3
"""
cullo — run this to do everything.
Usage: python run.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
VENV_PYTHON = PROJECT_DIR / "venv" / "bin" / "python"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def header():
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║                                      ║")
    print("  ║   C U L L O                          ║")
    print("  ║   AI Photo Curation Studio           ║")
    print("  ║                                      ║")
    print("  ╚══════════════════════════════════════╝")
    print()


def run(script, label):
    print(f"  ── {label} ──")
    print()
    result = subprocess.run([PYTHON, str(PROJECT_DIR / script)])
    print()
    return result.returncode == 0


def ask(question):
    ans = input(f"  {question} [y/n]: ").strip().lower()
    return ans in ("y", "yes")


def menu():
    print("  What would you like to do?\n")
    print("  [1]  Full pipeline  (scan → AI analysis → group → review app)")
    print("  [2]  Scan & score photos             (Step 1 — free, no internet)")
    print("  [3]  AI analysis with Claude          (Step 2 — uses API credits)")
    print("  [4]  Group similar shots              (Step 2B — uses API credits)")
    print("  [5]  Launch review dashboard          (Step 3 — open localhost:5000)")
    print("  [6]  Sneak peek selector              (Step 4 — picks best 9 for social)")
    print("  [7]  Build portfolio website          (generates docs/)")
    print()
    choice = input("  Enter a number (or press Enter for full pipeline): ").strip()
    return choice or "1"


def launch_app():
    print("  ── Review Dashboard ──")
    print()
    print("  Starting Cullo…  Open your browser to: http://localhost:5000")
    print("  Press Ctrl+C to stop.")
    print()
    subprocess.run([PYTHON, str(PROJECT_DIR / "app.py")])


def full_pipeline():
    print("  Running the full Cullo pipeline.\n")

    # Step 1
    run("scripts/01_scan_and_score.py", "Step 1 — Scan & Score")

    # Step 2
    if ask("Send best photos to Claude AI for analysis? (uses ~$0.50-$1)"):
        ok = run("scripts/02_analyze_with_claude.py", "Step 2 — Claude AI Analysis")
        if not ok:
            print("  Step 2 had an error. Check messages above.")
            return

        # Step 2B
        if ask("Group similar shots and compare them? (uses ~$0.20-$0.50)"):
            run("scripts/02b_group_photos.py", "Step 2B — Group Similar Shots")

    # Step 3
    print("  Ready to review your photos.")
    if ask("Open the review dashboard now?"):
        launch_app()


def main():
    header()
    choice = menu()
    print()

    if choice == "1":
        full_pipeline()
    elif choice == "2":
        run("scripts/01_scan_and_score.py", "Scan & Score")
    elif choice == "3":
        run("scripts/02_analyze_with_claude.py", "Claude AI Analysis")
    elif choice == "4":
        run("scripts/02b_group_photos.py", "Group Similar Shots")
    elif choice == "5":
        launch_app()
    elif choice == "6":
        run("scripts/04_sneak_peek.py", "Sneak Peek Selector")
    elif choice == "7":
        run("scripts/03_build_website.py", "Build Portfolio Website")
    else:
        print(f"  Unknown option: {choice}")
        sys.exit(1)

    print()
    print("  Done. ✓")
    print()


if __name__ == "__main__":
    main()
