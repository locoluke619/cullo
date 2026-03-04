# Cullo — AI Photo Curation Studio

**Cullo scans your photo library, finds your best shots using AI, helps you pick keepers, and builds a beautiful portfolio website — all from your own computer.**

Built for photographers. No coding experience needed.

---

## What Cullo Does

| Step | What Happens | Cost |
|------|-------------|------|
| **Scan** | Scores every photo for sharpness, exposure, color, and composition | Free |
| **Analyze** | Sends your top shots to Claude AI for expert feedback and a 1–10 score | ~$0.50–$1 |
| **Group** | Finds burst shots and similar angles, compares them side-by-side | ~$0.20–$0.50 |
| **Review** | You approve or skip photos in a clean web dashboard | Free |
| **Publish** | Builds a portfolio website ready for GitHub Pages | Free |

**Bonus tools included:**
- **Browse All** — rescue any photo the scanner missed, send it to Claude on the spot
- **Sneak Peek** — auto-picks your 9 best diverse shots for Instagram (3×3 grid, square-cropped and ready)
- **Client Gallery** — share a link with your client so they can heart their favourites

---

## Getting Cullo

### Option A — Download from GitHub (recommended)

1. Go to the Cullo repository on GitHub
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. Find the ZIP in your Downloads folder, double-click it to unzip
5. Move the unzipped folder to your Desktop
6. Rename it `cullo` if you like

### Option B — Clone with Terminal (faster for future updates)

If you have Git installed, open Terminal and run:

```bash
git clone https://github.com/YOUR-USERNAME/cullo.git ~/Desktop/cullo
cd ~/Desktop/cullo
```

> **Don't have Git?** Stick with Option A. Git is optional for using Cullo — you only need it to push your website to GitHub Pages later.

---

## One-Time Setup

### 1. Open Terminal

- Press **Command + Space**, type **Terminal**, press **Enter**
- A window with a blinking cursor appears — that's where you type commands

### 2. Go to the Cullo folder

```bash
cd ~/Desktop/cullo
```

> Type `ls` and press Enter to confirm you see files like `run.py`, `README.md`, `app.py`.

### 3. Run setup

```bash
bash setup.sh
```

This installs everything automatically. You'll see **"Setup complete!"** when it's done.

### 4. Get your API key

Cullo uses Claude AI to analyze your photos. You need a free Anthropic account:

1. Go to **https://console.anthropic.com** and sign up
2. Click **"API Keys"** in the left sidebar → **"Create Key"**
3. Copy the key (it starts with `sk-ant-…`)
4. Add at least **$5 in credits** (Settings → Billing) — 50 photos costs about $1

### 5. Add your API key to Cullo

Open the `.env` file in a text editor and paste your key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
PHOTOS_FOLDER=/Users/yourname/Pictures/your-shoot
```

> **In Cursor:** click `.env` in the file list on the left
> **In Terminal:** type `nano .env`, paste your key, then `Ctrl+X` → `Y` → `Enter`

> **How to find your photo folder path:** In Finder, right-click your photo folder → "Get Info" — the path is under "Where". Combine it with the folder name.

---

## Running Cullo

Every time you open a new Terminal window:

```bash
cd ~/Desktop/cullo
python run.py
```

That's it. Cullo shows you a menu and walks you through everything.

```
  ╔══════════════════════════════════════╗
  ║   C U L L O                          ║
  ║   AI Photo Curation Studio           ║
  ╚══════════════════════════════════════╝

  What would you like to do?

  [1]  Full pipeline  (scan → AI analysis → group → review app)
  [2]  Scan & score photos
  [3]  AI analysis with Claude
  [4]  Group similar shots
  [5]  Launch review dashboard
  [6]  Sneak peek selector
  [7]  Build portfolio website
```

Choose **1** for a fresh shoot — it runs everything in order and asks before each step.

---

## The Review Dashboard

After running the pipeline, the dashboard opens at **http://localhost:5000**

**Review page:**
- Each photo (or group of similar shots) shows as a card with Claude's title, score, and summary
- Click a single photo → full analysis modal with score reasoning, editing tips, and eye check
- Click a group → dedicated comparison page showing all similar shots side by side
- Keyboard shortcuts: **A** = approve, **S** = skip, **Escape** = close

**Compare page (for grouped shots):**
- See every similar shot from the same scene
- Claude highlights the subtle differences: "slightly better exposed", "all eyes open", "wider framing"
- **B** = add Claude's best pick, **X** = skip all, **Escape** = close zoom

**Browse page** (`/browse`):
- Shows every photo in your library, even ones the scanner filtered out
- See local quality scores for each
- Click "Send to Claude" to analyze any photo on the spot

**Client Gallery** (`/client`):
- Share this link with your clients
- They heart the photos they love
- Their picks save automatically — you see which ones they chose

---

## Putting Your Website Online

### 1. Build your website

From the review dashboard, click **"Build Website"** — or run:

```bash
python run.py
# Choose option 7
```

Your website is generated in the `docs/` folder. Preview it by opening `docs/index.html` in your browser.

### 2. Create a GitHub account

Go to **https://github.com** and sign up for a free account. Your username becomes part of your website URL.

### 3. Create a new repository

1. Click the **+** button (top right) → **"New repository"**
2. Name it `cullo` (or `photography-portfolio`, or your name)
3. Set it to **Public**
4. **Do not** check "Add a README" — Cullo already has one
5. Click **"Create repository"**

### 4. Push Cullo to GitHub

GitHub will show you commands. In your Terminal, run these one at a time:

```bash
cd ~/Desktop/cullo
git init
git add .
git commit -m "Initial Cullo setup"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git
git push -u origin main
```

> Replace `YOUR-USERNAME` and `YOUR-REPO-NAME` with your actual GitHub username and the repo name you chose.

### 5. Enable GitHub Pages

1. In your GitHub repo, click **Settings** (top tab)
2. Click **Pages** (left sidebar)
3. Under **Source**, select **"Deploy from a branch"**
4. Set **Branch** to `main`, folder to `/docs`
5. Click **Save**

After about 60 seconds, your website is live at:

```
https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/
```

### 6. Updating your website after a new shoot

```bash
cd ~/Desktop/cullo
python run.py    # run the pipeline, approve photos, build website
git add docs/
git commit -m "Add new shoot"
git push
```

GitHub Pages updates automatically within a minute.

---

## Sneak Peek (Social Media)

```bash
python run.py
# Choose option 6
```

Cullo picks your 9 best, most visually diverse approved photos and exports them as 1080×1080px square crops into `docs/sneak_peek/`. Drag those 9 files straight into an Instagram carousel post.

---

## Troubleshooting

**"command not found: python"**
Install Python from https://www.python.org/downloads/ — get the latest version.

**"No module named 'PIL'" or "No module named 'flask'"**
You skipped the venv activation. Run `bash setup.sh` again, or:
```bash
source venv/bin/activate
```

**"ERROR: No API key found!"**
Open `.env` and paste your key next to `ANTHROPIC_API_KEY=`.

**"credit balance too low"**
Add credits at https://console.anthropic.com → Settings → Billing. $5 covers dozens of shoots.

**"ERROR: Folder not found"**
The path in `PHOTOS_FOLDER` doesn't match your actual photo folder. Check the exact path in Finder → Get Info.

**Review app won't open**
Go to exactly `http://localhost:5000` (not https, no different port number).

**Photos show as broken images**
Cullo displays JPGs and PNGs. RAW files (.CR2, .ARW) are scored in Step 1 but not shown — use the JPG versions your camera also saves.

**Start completely fresh**
```bash
rm data/catalog.json
python run.py
```

---

## Quick Reference

```bash
cd ~/Desktop/cullo          # go to the folder
python run.py               # do everything (menu-driven)

# Or run individual steps:
source venv/bin/activate
python scripts/01_scan_and_score.py       # scan photos
python scripts/02_analyze_with_claude.py  # AI analysis
python scripts/02b_group_photos.py        # group similar shots
python app.py                             # review dashboard → localhost:5000
python scripts/03_build_website.py        # build website
python scripts/04_sneak_peek.py           # sneak peek export
```

---

## What Each File Does

| File | What It Does |
|------|-------------|
| `run.py` | **Start here** — one-command menu for the full pipeline |
| `setup.sh` | One-time installer |
| `.env` | Your settings (API key, photo folder) — never shared |
| `app.py` | The review web app (Flask) |
| `scripts/01_scan_and_score.py` | Scores every photo locally |
| `scripts/02_analyze_with_claude.py` | Claude AI analysis for top photos |
| `scripts/02b_group_photos.py` | Groups similar/burst shots |
| `scripts/03_build_website.py` | Builds the portfolio website |
| `scripts/04_sneak_peek.py` | Exports best 9 for social media |
| `templates/review.html` | Review dashboard |
| `templates/compare.html` | Side-by-side shot comparison |
| `templates/browse.html` | Browse all photos + rescue page |
| `templates/client_gallery.html` | Client heart-selection gallery |
| `data/catalog.json` | All photo scores and analyses |
| `data/groups.json` | Grouped shot data |
| `data/client_picks.json` | Client's hearted photos |
| `docs/` | Your generated website |

---

## Key Concepts (For the Curious)

- **Python** — the programming language Cullo is written in. You don't need to know it to use Cullo.
- **Virtual environment (venv)** — a clean sandbox so Cullo's tools don't interfere with anything else on your computer.
- **API key** — like a password that lets Cullo talk to Claude's AI over the internet.
- **Culling** — the photography industry term for sorting through a shoot and selecting the keepers. That's where the name comes from.
- **Flask** — the lightweight Python tool that powers the review dashboard web app.
- **GitHub Pages** — a free service from GitHub that turns a folder of files into a live website.

---

*Made with Claude — because every photographer deserves a second pair of eyes.*
