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

ENV_FILE        = PROJECT_DIR / ".env"
DATA_DIR        = PROJECT_DIR / "data"
WORKSPACES_FILE = DATA_DIR / "workspaces.json"
ACTIVE_WS_FILE  = DATA_DIR / "active_workspace.json"


def _read_workspaces():
    if WORKSPACES_FILE.exists():
        try:
            return json.loads(WORKSPACES_FILE.read_text()).get("workspaces", [])
        except Exception:
            pass
    return []

def _write_workspaces(ws_list):
    WORKSPACES_FILE.parent.mkdir(parents=True, exist_ok=True)
    WORKSPACES_FILE.write_text(json.dumps({"workspaces": ws_list}, indent=2))

def _get_active_workspace():
    ws_list = _read_workspaces()
    if not ws_list:
        env = load_env()
        return {"id": "default", "name": "Main Shoot",
                "folder": env.get("PHOTOS_FOLDER", "photos"),
                "type": env.get("WORKSPACE_TYPE", "shoot")}
    active_id = ws_list[0]["id"]
    if ACTIVE_WS_FILE.exists():
        try:
            active_id = json.loads(ACTIVE_WS_FILE.read_text()).get("id", active_id)
        except Exception:
            pass
    for ws in ws_list:
        if ws["id"] == active_id:
            return ws
    return ws_list[0]

def _set_active_workspace(ws_id):
    ACTIVE_WS_FILE.write_text(json.dumps({"id": ws_id}))

def get_catalog_file():
    ws = _get_active_workspace()
    return DATA_DIR / ws["id"] / "catalog.json"


# ── Helpers ───────────────────────────────────

def header():
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║   c u l l . i o                      ║")
    print("  ║   AI Photo Curation Studio            ║")
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
        print("  cull.io needs an Anthropic API key to analyze your photos.")
        print("  Get one free at: https://console.anthropic.com")
        print()
        print("  Then open the  .env  file in this folder and paste it")
        print("  next to  ANTHROPIC_API_KEY=")
        print()
        ok = False

    # Active workspace folder
    ws = _get_active_workspace()
    ws_folder = ws.get("folder", "photos").strip() or "photos"
    folder_path = Path(ws_folder) if Path(ws_folder).is_absolute() else PROJECT_DIR / ws_folder
    no_photos = not folder_path.exists() or count_photos(folder_path) == 0

    if no_photos and folder_path.exists():
        # Maybe they pointed at a parent folder — check for shoot subfolders
        shoots = find_shoots(folder_path)
        if shoots:
            print("  Found photo folders inside your photos directory:")
            print()
            for i, (path, n) in enumerate(shoots, 1):
                print(f"  [{i}]  {path.name:<35}  {n} photos")
            print()
            while True:
                choice = input("  Choose a folder to work on: ").strip()
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(shoots):
                        chosen = shoots[idx][0]
                        # Save as active workspace folder (create if list is empty)
                        ws_list = _read_workspaces()
                        matched = False
                        for w in ws_list:
                            if w["id"] == ws["id"]:
                                w["folder"] = str(chosen)
                                matched = True
                        if not matched:
                            ws_list.append({
                                "id": ws["id"],
                                "name": ws.get("name", "Main Shoot"),
                                "folder": str(chosen),
                                "type": ws.get("type", "shoot"),
                            })
                        _write_workspaces(ws_list)
                        _set_active_workspace(ws["id"])
                        folder_path = chosen
                        no_photos = False
                        print()
                        break
                print("  Please enter a number from the list.")

    if no_photos:
        if not folder_path.exists():
            print(f"  ⚠  Photo folder not found:  {folder_path}")
        else:
            print(f"  ⚠  No photos found in:  {folder_path}")
        print()
        print("  Use  [c] Workspaces  to point cull.io at your photo folder.")
        print()
        ok = False

    return ok, env, folder_path


# ── Actions ───────────────────────────────────

def _export_raws_cli():
    """CLI version of the RAW export — mirrors the Flask endpoint logic."""
    import shutil
    sys.path.insert(0, str(PROJECT_DIR / "scripts"))
    from config import RAW_FORMATS, CATALOG_FILE

    catalog_file = get_catalog_file()
    if not catalog_file.exists():
        print("  No catalog yet — run Step 1 and 2 first.")
        return

    with open(catalog_file) as f:
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


def _ask_folder():
    """Prompt user for a folder path. Returns Path or None."""
    print("  Tip: drag your photo folder into this window, then press Enter.")
    print()
    while True:
        raw = input("  Photo folder path: ").strip().strip("'\"")
        if not raw:
            return None
        path = Path(raw.replace("~", str(Path.home())))
        if not path.is_absolute():
            path = PROJECT_DIR / raw
        if not path.exists():
            print(f"\n  ✗  Folder not found: {path}\n")
            continue
        return path


def workspace_manager():
    """Interactively manage workspaces — switch, add, or delete."""
    import re, time as _time

    while True:
        ws_list = _read_workspaces()
        active  = _get_active_workspace()

        print("  ── Your Workspaces ──")
        print()
        if ws_list:
            for i, ws in enumerate(ws_list, 1):
                star  = "★" if ws["id"] == active["id"] else " "
                badge = "RAW" if ws.get("type") == "shoot" else "Edited"
                folder_path = Path(ws["folder"])
                n = count_photos(folder_path) if folder_path.exists() else 0
                print(f"  [{i}] {star} {ws['name']:<28} ({badge})  {n} photos")
        else:
            print("  No workspaces yet.")
        print()
        print("  [n]  Add new workspace")
        print("  [q]  Back to menu")
        print()

        choice = input("  Switch to workspace # (or n/q): ").strip().lower()

        if choice == "q":
            break

        elif choice == "n":
            print()
            print("  ── Add New Workspace ──")
            print()
            name = input("  Name this workspace (e.g. Wedding June 2024): ").strip()
            if not name:
                print("  Cancelled.")
                continue

            print()
            folder = _ask_folder()
            if folder is None:
                print("  Cancelled.")
                continue

            print()
            print("  Type of photos:")
            print("    [1]  Straight from camera  (RAW or unedited JPG)")
            print("    [2]  Already edited        (Lightroom, Photoshop, etc.)")
            print()
            while True:
                t = input("  Enter 1 or 2: ").strip()
                if t == "1":
                    ws_type = "shoot"
                    break
                elif t == "2":
                    ws_type = "edited"
                    break
                print("  Please enter 1 or 2.")

            ws_id = re.sub(r"[^a-z0-9]", "_", name.lower())[:20].strip("_") + f"_{int(_time.time()) % 100000}"
            ws_list.append({"id": ws_id, "name": name, "folder": str(folder), "type": ws_type})
            _write_workspaces(ws_list)
            (DATA_DIR / ws_id).mkdir(parents=True, exist_ok=True)
            _set_active_workspace(ws_id)
            badge = "RAW" if ws_type == "shoot" else "Edited"
            print()
            print(f"  ✓  Workspace '{name}' ({badge}) created and activated.")
            print()
            break

        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(ws_list):
                ws = ws_list[idx]
                _set_active_workspace(ws["id"])
                badge = "RAW" if ws.get("type") == "shoot" else "Edited"
                print()
                print(f"  ✓  Switched to: {ws['name']} ({badge})")
                print()
                break
            else:
                print("  Invalid number.")
        else:
            print("  Enter a workspace number, n, or q.")


def launch_app():
    print("  Your browser will open automatically.")
    print("  Press Ctrl+C here when you're done.")
    print()
    subprocess.run([PYTHON, str(PROJECT_DIR / "app.py")])


def quick_start(folder_path, env):
    """Ask minimal questions then run scan → AI → group → dashboard hands-free."""
    import re, time as _time

    ws = _get_active_workspace()
    ws_list = _read_workspaces()

    # ── Ask shoot name if still default ──────────────────────────
    if ws.get("name") in ("Main Shoot", "", None):
        print("  What's a good name for this shoot?")
        print("  (e.g. Wedding June 2024, Family Portraits, Landscape Trip)")
        print()
        name = input("  Name (or Enter to skip): ").strip()
        if name:
            for w in ws_list:
                if w["id"] == ws["id"]:
                    w["name"] = name
            _write_workspaces(ws_list)
            ws["name"] = name
        print()

    # ── Ask type if not set ───────────────────────────────────────
    ws_type = ws.get("type") or ""
    if ws_type not in ("shoot", "edited"):
        print("  Are these photos straight from your camera, or already edited?")
        print()
        print("    [1]  Straight from camera  (RAW or unedited JPG)")
        print("    [2]  Already edited        (Lightroom, Photoshop, etc.)")
        print()
        while True:
            t = input("  Enter 1 or 2: ").strip()
            if t == "1":   ws_type = "shoot";  break
            elif t == "2": ws_type = "edited"; break
            print("  Please enter 1 or 2.")
        for w in ws_list:
            if w["id"] == ws["id"]:
                w["type"] = ws_type
        _write_workspaces(ws_list)
        print()

    # ── Summary + cost estimate ───────────────────────────────────
    n         = count_photos(folder_path)
    top_pct   = int(env.get("TOP_PERCENT", 20))
    max_p     = int(env.get("MAX_CLAUDE_PHOTOS", 50))
    estimated = min(int(n * top_pct / 100), max_p)
    est_cost  = estimated * 0.015
    badge     = "RAW" if ws_type == "shoot" else "Edited"

    print("  ╔══════════════════════════════════════════════╗")
    print("  ║   Your dashboard is on the way!              ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()
    print(f"  Shoot:    {ws.get('name', 'My Shoot')}  ({badge})")
    print(f"  Photos:   {n}")
    print(f"  AI cost:  ~${est_cost:.2f} estimated  ({estimated} photos to Claude)")
    print()
    print("  cull.io will scan, analyze, and group your photos")
    print("  then open the dashboard automatically.")
    print()

    if not ask_yes("Ready? (this takes ~15–20 min for a full shoot)"):
        return

    print()

    # ── Step 1: Scan ──────────────────────────────────────────────
    print("  ── [1/3] Scanning & scoring  (free) ──────────────────────")
    print()
    ok = run_script("scripts/01_scan_and_score.py", "Scan & Score")
    if not ok:
        print("  Scan failed — check messages above.")
        return

    # ── Step 2: AI Analysis ───────────────────────────────────────
    print()
    print("  ── [2/3] AI analysis ──────────────────────────────────────")
    print()
    ok = run_script("scripts/02_analyze_with_claude.py", "AI Analysis")
    if not ok:
        print("  AI analysis failed — check messages above.")
        return

    # ── Step 3: Group similar shots ───────────────────────────────
    print()
    print("  ── [3/3] Grouping similar shots ───────────────────────────")
    print()
    run_script("scripts/02b_group_photos.py", "Grouping")

    # ── Open dashboard ────────────────────────────────────────────
    print()
    print("  ✓  All done! Opening your dashboard…")
    print()
    launch_app()


def full_pipeline(env, folder_path):
    n = count_photos(folder_path)
    top_pct = int(env.get("TOP_PERCENT", 20))
    max_photos = int(env.get("MAX_CLAUDE_PHOTOS", 50))
    estimated = min(int(n * top_pct / 100), max_photos)
    est_cost = estimated * 0.015

    print(f"  Found {n} photos in your folder.")
    print()

    # Step 1
    catalog_file = get_catalog_file()
    if catalog_file.exists():
        import json as _json
        try:
            with open(catalog_file) as _f:
                _existing = _json.load(_f)
            already_scanned = len([p for p in _existing if "error" not in p])
        except Exception:
            already_scanned = 0
        print(f"  Found existing scan ({already_scanned} photos already scored).")
        print(f"  New photos in folder will be added automatically.")
        print()
        if ask_yes("Re-scan everything from scratch instead?"):
            catalog_file.unlink()
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
    ws = _get_active_workspace()
    n = count_photos(folder_path)
    has_catalog = get_catalog_file().exists()
    badge = "RAW" if ws.get("type") == "shoot" else "Edited"

    try:
        display_path = folder_path.relative_to(PROJECT_DIR)
    except ValueError:
        display_path = folder_path

    print(f"  Workspace: {ws['name']}  ({badge})")
    print(f"  Folder:    {display_path}  ({n} photos)")
    print(f"  Catalog:   {'ready ✓' if has_catalog else 'not scanned yet'}")
    print()
    print("  What would you like to do?")
    print()
    print("  [Enter]  Quick Start    scan → AI → group → open dashboard  ✦")
    print()
    print("  [2]  Scan & score       analyze photo quality locally (free)")
    print("  [3]  AI analysis        send top photos to Claude (uses credits)")
    print("  [4]  Group similar      find burst shots & compare them")
    print("  [5]  Review dashboard   open the review app in your browser")
    print("  [6]  Export RAWs        copy selected RAWs to ready_to_edit/ for Lightroom")
    print("  [7]  Sneak peek         export best 9 photos for Instagram")
    print("  [8]  Build website      generate your portfolio website")
    print("  [9]  Client proof       export a file you can email to your client")
    print("  [c]  Workspaces         switch folders or add a new shoot")
    print()
    choice = input("  Choose (or press Enter to Quick Start): ").strip().lower()
    return choice or "0"


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
            workspace_manager()
            ok, env, folder_path = preflight()
            if not ok:
                print("  Folder issue — try again.")
            continue

        if choice == "0":
            quick_start(folder_path, env)
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
        print("  Stopped. Come back anytime — double-click cull.io to start.")
        print()
