#!/usr/bin/env python3
"""
Cullo — main launcher.
Run this with:  python run.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
VENV_PYTHON = PROJECT_DIR / "venv" / "bin" / "python"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

ENV_FILE = PROJECT_DIR / ".env"
CATALOG_FILE = PROJECT_DIR / "data" / "catalog.json"


# ── Helpers ───────────────────────────────────

def header():
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║   C U L L O                          ║")
    print("  ║   AI Photo Curation Studio           ║")
    print("  ╚══════════════════════════════════════╝")
    print()


def load_env():
    """Read key=value pairs from .env without requiring dotenv."""
    env = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def check_api_key(env):
    key = env.get("ANTHROPIC_API_KEY", "")
    return key and key != "your-api-key-here" and key.startswith("sk-ant-")


def check_photos_folder(env):
    folder = env.get("PHOTOS_FOLDER", "photos").strip() or "photos"
    path = Path(folder) if Path(folder).is_absolute() else PROJECT_DIR / folder
    return path, path.exists()


PHOTO_EXTS = {
    ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".heic", ".heif",
    ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".raf",
    ".orf", ".rw2", ".pef", ".ptx", ".dng", ".3fr",
}

def count_photos(folder_path):
    if not folder_path.exists():
        return 0
    return sum(1 for f in folder_path.iterdir() if f.suffix.lower() in PHOTO_EXTS)


def find_shoots(base=None):
    """
    Return a sorted list of (folder_path, photo_count) for every
    subfolder inside photos/ that contains at least one image.
    """
    if base is None:
        base = PROJECT_DIR / "photos"
    if not base.exists():
        return []
    shoots = []
    for sub in sorted(base.iterdir()):
        if sub.is_dir() and not sub.name.startswith("."):
            n = count_photos(sub)
            if n > 0:
                shoots.append((sub, n))
    return shoots


def pick_shoot():
    """
    Show a numbered list of shoots found inside photos/ and let the user
    choose one. Returns the chosen Path, or None if they want to type manually.
    """
    shoots = find_shoots()
    if not shoots:
        return None

    print("  ── Shoots found in your photos/ folder ──")
    print()
    for i, (path, n) in enumerate(shoots, 1):
        print(f"  [{i}]  {path.name:<35}  {n} photos")
    print()
    print("  [m]  Type a path manually")
    print()

    while True:
        choice = input("  Choose a shoot: ").strip().lower()
        if choice == "m":
            return None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(shoots):
                return shoots[idx][0]
        print("  Please enter a number from the list, or m to type a path.")


def run_script(script, label):
    print(f"  ── {label} ──")
    print()
    result = subprocess.run([PYTHON, str(PROJECT_DIR / script)])
    print()
    return result.returncode == 0


def ask_yes(question):
    ans = input(f"  {question} [y/n]: ").strip().lower()
    return ans in ("y", "yes", "")


def pause(msg="  Press Enter to continue…"):
    input(msg)


# ── Pre-flight checks ─────────────────────────

def preflight():
    """Check that everything is configured before running anything."""
    env = load_env()
    ok = True

    # API key
    if not check_api_key(env):
        print("  ⚠  No API key found.")
        print()
        print("  Cullo needs an Anthropic API key to analyze your photos.")
        print("  Get one free at: https://console.anthropic.com")
        print()
        print("  Then open the  .env  file in this folder and paste it")
        print("  next to  ANTHROPIC_API_KEY=")
        print()
        ok = False

    # Photos folder
    folder_path, exists = check_photos_folder(env)
    no_photos = not exists or count_photos(folder_path) == 0

    if no_photos:
        # Before erroring, check if photos/ has shoot subfolders to choose from
        shoots = find_shoots()
        if shoots:
            print("  Choose which shoot to work on:")
            print()
            chosen = pick_shoot()
            if chosen:
                try:
                    save_as = str(chosen.relative_to(PROJECT_DIR))
                except ValueError:
                    save_as = str(chosen)
                save_env_value("PHOTOS_FOLDER", save_as)
                folder_path = chosen
                no_photos = False
                print()

    if no_photos:
        if not exists:
            print(f"  ⚠  Photo folder not found:  {folder_path}")
        else:
            print(f"  ⚠  No photos found in:  {folder_path}")
        print()
        print("  Drop your photos into a folder inside  photos/  and try again.")
        print("  Example:  photos/Wedding_June2025/")
        print()
        ok = False

    return ok, env, folder_path


# ── Actions ───────────────────────────────────

def _export_raws_cli():
    """CLI version of the RAW export — mirrors the Flask endpoint logic."""
    import shutil
    sys.path.insert(0, str(PROJECT_DIR / "scripts"))
    from config import RAW_FORMATS, CATALOG_FILE

    if not CATALOG_FILE.exists():
        print("  No catalog yet — run Step 1 and 2 first.")
        return

    with open(CATALOG_FILE) as f:
        catalog = json.load(f)

    approved = [p for p in catalog if p.get("approved") is True]
    if not approved:
        print("  No approved photos yet. Review your photos first (option 5).")
        return

    export_dir = PROJECT_DIR / "exports" / "ready_to_edit"
    export_dir.mkdir(parents=True, exist_ok=True)
    for old in export_dir.iterdir():
        old.unlink()

    copied, missing = [], []
    for photo in approved:
        jpg_path = Path(photo["file"])
        found_raw = None
        for ext in RAW_FORMATS:
            for candidate in [jpg_path.stem + ext, jpg_path.stem + ext.upper()]:
                raw_path = jpg_path.parent / candidate
                if raw_path.exists():
                    found_raw = raw_path
                    break
            if found_raw:
                break
        if found_raw:
            shutil.copy2(found_raw, export_dir / found_raw.name)
            copied.append(found_raw.name)
        else:
            missing.append(jpg_path.name)

    print(f"  ── Export RAWs to Edit ──")
    print()
    print(f"  Approved photos:   {len(approved)}")
    print(f"  RAW files found:   {len(copied)}")
    if missing:
        print(f"  No RAW found for:  {len(missing)} photos (JPG-only shoots)")
    print()
    print(f"  Saved to:  exports/ready_to_edit/")
    print()
    if copied:
        print("  Opening folder…")
        subprocess.run(["open", str(export_dir)], check=False)
    print()


def save_env_value(key, value):
    """Update a single key in the .env file."""
    lines = ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else []
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n")


def _save_folder(path):
    """Save a folder path to .env and print confirmation."""
    n = count_photos(path)
    try:
        save_as = str(path.relative_to(PROJECT_DIR))
    except ValueError:
        save_as = str(path)
    save_env_value("PHOTOS_FOLDER", save_as)
    print()
    print(f"  ✓  Shoot set to: {path.name}")
    print(f"     {n} photos  •  {path}")
    print()
    print("  Saved — this will be used next time too.")
    print()


def change_folder():
    """Interactively change the photo folder and save it to .env."""
    print("  ── Choose a Shoot ──")
    print()

    # If photos/ has subfolders, show the picker first
    shoots = find_shoots()
    if shoots:
        chosen = pick_shoot()
        if chosen:
            _save_folder(chosen)
            return

    # Manual path entry
    print("  Tip: drag your photo folder into this Terminal window, then press Enter.")
    print("  Or press Enter to use the  photos/  folder.")
    print()

    while True:
        raw = input("  Photo folder path: ").strip().strip("'\"")

        if not raw:
            path = PROJECT_DIR / "photos"
        else:
            path = Path(raw.replace("~", str(Path.home())))
            if not path.is_absolute():
                path = PROJECT_DIR / raw

        if not path.exists():
            print(f"\n  ✗  Folder not found: {path}")
            print("     Check the path and try again.\n")
            continue

        n = count_photos(path)
        if n == 0:
            # Maybe they pointed at a parent folder that has shoot subfolders
            sub_shoots = find_shoots(path)
            if sub_shoots:
                print(f"\n  Found {len(sub_shoots)} shoot folders inside that directory:\n")
                chosen = _pick_from(sub_shoots)
                if chosen:
                    _save_folder(chosen)
                    return
                continue
            print(f"\n  ⚠  No photos found in that folder.")
            ans = input("  Use it anyway? [y/n]: ").strip().lower()
            if ans not in ("y", "yes"):
                continue

        _save_folder(path)
        break


def _pick_from(shoots):
    """Numbered picker for an arbitrary list of (path, count) tuples."""
    for i, (path, n) in enumerate(shoots, 1):
        print(f"  [{i}]  {path.name:<35}  {n} photos")
    print()
    while True:
        choice = input("  Choose a shoot: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(shoots):
                return shoots[idx][0]
        print("  Please enter a number from the list.")


def launch_app():
    print("  ── Cullo Review Dashboard ──")
    print()
    print("  Your browser will open automatically.")
    print("  Press Ctrl+C here to stop the app.")
    print()
    subprocess.run([PYTHON, str(PROJECT_DIR / "app.py")])


def full_pipeline(env, folder_path):
    n = count_photos(folder_path)
    top_pct = int(env.get("TOP_PERCENT", 20))
    max_photos = int(env.get("MAX_CLAUDE_PHOTOS", 50))
    estimated = min(int(n * top_pct / 100), max_photos)
    est_cost = estimated * 0.015

    print(f"  Found {n} photos in your folder.")
    print()

    # Step 1
    if CATALOG_FILE.exists():
        import json as _json
        try:
            with open(CATALOG_FILE) as _f:
                _existing = _json.load(_f)
            already_scanned = len([p for p in _existing if "error" not in p])
        except Exception:
            already_scanned = 0
        print(f"  Found existing scan ({already_scanned} photos already scored).")
        print(f"  New photos in folder will be added automatically.")
        print()
        if ask_yes("Re-scan everything from scratch instead?"):
            CATALOG_FILE.unlink()
        run_script("scripts/01_scan_and_score.py", "Scanning & Scoring Your Photos")
    else:
        print("  Step 1 — Scanning your photos (free, no internet needed)")
        print()
        run_script("scripts/01_scan_and_score.py", "Scanning & Scoring")

    # Step 2
    print()
    print(f"  Step 2 — Claude AI will look at your top {estimated} photos")
    if est_cost < 5.00:
        cost_note = "yes, really — cheaper than a coffee"
    elif est_cost < 12.00:
        cost_note = "about the price of a coffee"
    elif est_cost < 20.00:
        cost_note = "about the price of a meal out"
    else:
        cost_note = "consider lowering MAX_CLAUDE_PHOTOS in .env"
    print(f"  Estimated cost: ~${est_cost:.2f}  ({cost_note})")
    print()
    if ask_yes("Ready to run AI analysis?"):
        ok = run_script("scripts/02_analyze_with_claude.py", "Claude AI Analysis")
        if not ok:
            print("  Something went wrong in Step 2. Check the messages above.")
            return

        # Step 2B
        print()
        print("  Step 2B — Finding similar/burst shots to compare (optional)")
        print("  Estimated cost: ~$0.20–$0.50")
        print()
        if ask_yes("Group similar shots for side-by-side comparison?"):
            run_script("scripts/02b_group_photos.py", "Grouping Similar Shots")

    # Step 3
    print()
    print("  Ready to review your photos!")
    print()
    if ask_yes("Open the review dashboard?"):
        launch_app()


# ── Menu ──────────────────────────────────────

def menu(folder_path):
    n = count_photos(folder_path)
    has_catalog = CATALOG_FILE.exists()

    # Show current folder — shorten to relative if inside project
    try:
        display_path = folder_path.relative_to(PROJECT_DIR)
    except ValueError:
        display_path = folder_path

    print(f"  Folder:   {display_path}  ({n} photos)")
    print(f"  Catalog:  {'ready ✓' if has_catalog else 'not scanned yet'}")
    print()
    print("  What would you like to do?")
    print()
    print("  [1]  Full pipeline      scan → AI analysis → compare groups → review")
    print("  [2]  Scan & score       analyze photo quality locally (free)")
    print("  [3]  AI analysis        send top photos to Claude (uses credits)")
    print("  [4]  Group similar      find burst shots & compare them (visual hash)")
    print("  [4c] Caption & group    one-sentence caption per photo + smart scene grouping")
    print("  [5]  Review dashboard   open the review app in your browser")
    print("  [6]  Export RAWs        copy selected RAWs to ready_to_edit/ for Lightroom")
    print("  [7]  Sneak peek         export best 9 photos for Instagram")
    print("  [8]  Build website      generate your portfolio website")
    print("  [9]  Client proof       export a file you can email to your client")
    print("  [c]  Change folder      switch to a different shoot")
    print()
    choice = input("  Enter a number (or press Enter for full pipeline): ").strip().lower()
    return choice or "1"


def main():
    header()

    ok, env, folder_path = preflight()
    if not ok:
        pause("  Fix the issues above, then press Enter to try again…")
        # Re-check after user has had a chance to fix things
        ok, env, folder_path = preflight()
        if not ok:
            print("  Still not ready. Close this window, fix the settings, and try again.")
            print()
            return

    while True:
        choice = menu(folder_path)
        print()

        if choice == "c":
            change_folder()
            # Reload env and folder after change
            ok, env, folder_path = preflight()
            if not ok:
                print("  Folder issue — try again.")
            continue

        if choice == "1":
            full_pipeline(env, folder_path)
        elif choice == "2":
            run_script("scripts/01_scan_and_score.py", "Scan & Score")
        elif choice == "3":
            run_script("scripts/02_analyze_with_claude.py", "Claude AI Analysis")
        elif choice == "4":
            run_script("scripts/02b_group_photos.py", "Group Similar Shots")
        elif choice == "4c":
            run_script("scripts/02c_caption_and_group.py", "Caption & Semantic Group")
        elif choice == "5":
            launch_app()
        elif choice == "6":
            _export_raws_cli()
        elif choice == "7":
            run_script("scripts/04_sneak_peek.py", "Sneak Peek Selector")
        elif choice == "8":
            run_script("scripts/03_build_website.py", "Build Portfolio Website")
        elif choice == "9":
            run_script("scripts/05_export_client_proof.py", "Export Client Proof")
        else:
            print(f"  Unknown option — please enter a number from 1–9 or c.")

        print()
        if not ask_yes("Back to menu?"):
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("  Stopped. Come back anytime — double-click Cullo.command to start.")
        print()
