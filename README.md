# cull.io — AI Photo Curation Studio

cull.io looks through your photos, finds the best ones using AI, and builds you a beautiful portfolio website. No coding required.

---

## Getting Started

### Step 1 — Download

1. On this GitHub page, click the green **Code** button
2. Click **Download ZIP**
3. Open your **Downloads** folder
4. Double-click the ZIP file to unzip it
5. Drag the **cull.io** folder to your **Desktop**

### Step 2 — Open cull.io

1. Open the **cull.io** folder on your Desktop
2. Double-click **Cull.io**

> **Mac security prompt?** If you see "Apple cannot verify this app", go to **System Settings → Privacy & Security**, scroll down, and click **Open Anyway**. This is standard for any app downloaded outside the App Store — you only need to do it once.

**First time only:** A setup wizard walks you through everything in a Terminal window:
- Installing the tools cull.io needs (~1 minute)
- Entering your name for the portfolio website
- Pointing cull.io at your photos
- Choosing whether your photos are straight-from-camera or already edited
- Adding your AI key

After that, double-clicking **Cull.io** goes straight to the menu.

### Step 3 — Get an AI Key

cull.io uses Claude AI to write expert analysis of your photos. You need a free Anthropic account with a small amount of credits:

1. Go to **https://console.anthropic.com** and sign up
2. Go to **Settings → Billing** and add $5 in credits
   *(analyzing your best photos shouldn't cost more than a cup of coffee!)*
3. Click **API Keys** in the left sidebar → **Create Key**
4. Copy the key — it looks like: `sk-ant-api03-...`
5. Paste it when Setup asks for it

### Step 4 — Add Your Photos

**Easiest:** Drop your photos into the **photos** folder inside the cull.io folder.

**Already in another folder?** No problem — Setup asks where your photos are. You can type a path or drag the folder straight into the Terminal window.

**Multiple shoots?** Use **[c] Workspaces** in the menu to add more folders and switch between them any time.

### Step 5 — Run

Press **Enter** at the menu for Quick Start — cull.io asks a couple of questions then runs everything and opens your dashboard automatically.

---

## What cull.io Does (Step by Step)

| Step | What Happens | Time | Cost |
|------|-------------|------|------|
| **Scan** | Scores every photo for sharpness, exposure, color, and composition. Saves as it goes — safe to interrupt and resume | ~5 min | Free |
| **AI Analysis** | Picks the best shot from each distinct scene, then sends those to Claude for expert feedback and a 1–10 score | ~15–20 min | ~$0.50–$1 |
| **Group** | Finds burst shots and similar angles, compares them side-by-side | ~5 min | ~$0.20–$0.50 |
| **Review** | You approve or skip photos in a browser dashboard | Your pace | Free |
| **Client Proof** | Export a file you can email your client — they tap ♥ on favourites | ~30 sec | Free |
| **Build** | Generates your portfolio website | ~2 min | Free |

cull.io tells you the **estimated cost before charging anything** and shows you the **actual cost** when analysis finishes.

---

## Workspaces

cull.io supports multiple workspaces — each one is a different folder of photos with its own analysis results and settings.

**Common uses:**
- Switch between different shoots (wedding, portraits, landscape)
- Keep edited photos separate from unedited ones
- Compare results from different shoots without mixing them up

**Each workspace has a type:**
- **Straight from camera** — Claude focuses on which shots to keep, technical quality, and best-of-series comparisons
- **Already edited** — Claude evaluates the edit itself: color grade, exposure balance, post-processing quality

**Adding a workspace:**
- In the cull.io menu, choose **[c] Workspaces**
- Or in the dashboard, click **+ Add Folder** in the workspace bar at the top

Switching workspaces swaps the entire dataset — photos, scores, analysis, and groups — to that folder.

---

## The Menu

Every time you run cull.io you'll see:

```
  Workspace: Wedding June 2024  (RAW)
  Folder:    photos/Wedding_June2024  (847 photos)
  Catalog:   ready ✓

  [1]  Full pipeline      scan → AI analysis → compare groups → review
  [2]  Scan & score       analyze photo quality locally (free)
  [3]  AI analysis        send top photos to Claude (uses credits)
  [4]  Group similar      find burst shots & compare them
  [5]  Review dashboard   open the review app in your browser
  [6]  Export RAWs        copy selected RAWs to ready_to_edit/ for Lightroom
  [7]  Sneak peek         export best 9 photos for Instagram
  [8]  Build website      generate your portfolio website
  [9]  Client proof       export a file you can email to your client
  [c]  Workspaces         switch folders or add a new shoot
```

---

## Using the Review Dashboard

After running the pipeline, your browser opens automatically to the review dashboard at `http://localhost:5000`.

**Workspace switcher:** If you have multiple workspaces, a tab bar appears at the top of the dashboard. Click any tab to switch — the dashboard reloads with that workspace's photos instantly.

**Reviewing photos:**
- Each photo shows Claude's title, score out of 10, and a one-line summary
- Click any photo to see the full analysis — what it got right, what held it back, composition notes, technical feedback, and 3 specific Lightroom editing tips
- Click **Add to Website** to keep it, **Skip** to pass
- Keyboard shortcuts: **A** = add, **S** = skip, **Escape** = close

**Comparing similar shots:**
- Groups of similar/burst shots show as stacked cards with a "N shots" badge
- Click them to see all shots side-by-side with Claude's notes on what's different
- Claude flags things like: "better exposed", "all eyes open", "slightly sharper"
- Keyboard: **B** = add Claude's best pick, **X** = skip all

**Rescuing photos:**
- Click **Browse All Photos** in the top bar to see every photo with its quality score
- Photos Claude hasn't seen yet appear **desaturated** — hover to see them in full colour
- Photos Claude has analyzed show a purple **✦ Analyzed** badge
- Click any unanalyzed photo → **Send to Claude** to get a full analysis on the spot
- Good for intentionally dark/moody shots that the quality scorer penalised

**Sharing with your client:**
- Click **Export Client Proof ♥** in the top bar (or choose **9** in the menu)
- cull.io generates a single file: `exports/client_proof.html`
- Email it directly, or upload to Google Drive / iCloud / Dropbox and share the link
- Your client opens the file in their browser — no app, no account needed
- They tap ♥ on the photos they love, then click **Send My Picks** — their email opens pre-filled with their selections addressed to you

**Getting client picks back into your dashboard:**
- When the client sends their picks email, paste the whole email into **Import Client Picks** in the dashboard header
- cull.io reads the picks code automatically and marks those photos with a **♥ Client Pick** badge
- A **Client Picks** filter tab appears so you can see exactly what they loved

---

## Editing Your Picks in Lightroom

After approving your keepers, click **Export RAWs to Edit** in the dashboard header (or choose **6** in the menu).

cull.io finds the RAW file matching each approved photo and copies them all into **exports/ready_to_edit/** — then opens that folder automatically.

Drag it straight into Lightroom or Capture One. Every file in there is already a keeper you chose.

**RAW+JPG shooters (most camera users):** cull.io uses the JPG for scoring and display, keeps the RAW for this export. No extra work needed.

**RAW-only shooters:** cull.io reads RAW files directly — just point it at your RAW folder and it handles everything.

---

## Sneak Peek for Social Media

Choose **7 — Sneak peek** in the menu.

cull.io picks your 9 best, most visually varied approved photos and exports them as square 1080×1080 crops into **docs/sneak_peek/**. Drag those 9 files into an Instagram carousel — ready to post.

---

## Putting Your Website Online (Free)

### 1. Create a GitHub account

Go to **https://github.com** and sign up. Your username becomes part of your website address.

### 2. Create a new repository

1. Click **+** (top right on GitHub) → **New repository**
2. Name it `cullo` or `my-photography`
3. Set it to **Public**
4. Leave everything else unchecked → **Create repository**

### 3. Push cull.io to GitHub

Open Terminal and run these one at a time:

```bash
git init
git add .
git commit -m "My photography portfolio"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

> Replace `YOUR-USERNAME` and `YOUR-REPO` with your actual GitHub username and repo name.

### 4. Turn on GitHub Pages

1. In your repo on GitHub, click **Settings** → **Pages**
2. Under **Source** → **Deploy from a branch**
3. Set Branch to **main**, folder to **/docs**
4. Click **Save**

Your site goes live in about 60 seconds at:
```
https://YOUR-USERNAME.github.io/YOUR-REPO/
```

### 5. Updating after a new shoot

Run cull.io, approve your picks, build the website, then:

```bash
git add docs/
git commit -m "New shoot"
git push
```

Done — GitHub Pages updates within a minute.

---

## Supported Photo Formats

| Format | Extensions | Notes |
|--------|-----------|-------|
| JPEG | .jpg, .jpeg | Universal — works perfectly |
| PNG | .png | Lossless |
| TIFF | .tiff, .tif | Professional exports |
| WEBP | .webp | Modern web format |
| HEIC / HEIF | .heic, .heif | iPhone photos — fully supported |
| Canon RAW | .cr2, .cr3 | Fully supported |
| Nikon RAW | .nef, .nrw | Fully supported |
| Sony RAW | .arw, .srf, .sr2 | Fully supported |
| Fujifilm RAW | .raf | Fully supported |
| Olympus RAW | .orf | Fully supported |
| Panasonic RAW | .rw2 | Fully supported |
| Pentax RAW | .pef, .ptx | Fully supported |
| Adobe DNG | .dng | Fully supported (also iPhone ProRAW + Android) |
| Hasselblad RAW | .3fr | Fully supported |

**RAW+JPG shooters:** If your camera saves both, cull.io uses the JPG for speed and keeps the RAW untouched for Lightroom. You get the best of both.

**RAW-only shooters:** cull.io reads your RAW files directly — no conversion needed.

---

## Privacy & Security

**Completely reasonable to ask.** Here's exactly what cull.io does:

### What leaves your computer
- **Your photos** — sent to Anthropic (the company that makes Claude AI) for analysis over an encrypted connection. Same as uploading to Google Photos or iCloud. Anthropic's privacy policy: anthropic.com/privacy
- **Nothing else** — no filenames, no folder paths, no personal information

### What stays on your computer
- Your API key (in `.env` — never uploaded to GitHub)
- All photo scores and analysis (in `data/`)
- Your website files (in `docs/`)

### The review dashboard
Runs at `http://localhost:5000` — only accessible from your own computer. Not reachable from the internet.

---

## Troubleshooting

**"Apple cannot verify this app"**
Go to **System Settings → Privacy & Security**, scroll down, and click **Open Anyway**. You only need to do this once per app.

**"Python is not installed"**
Setup opens python.org automatically. Install Python, then run Setup again.

**"No API key" or "Invalid API key"**
Open the `.env` file in the cullo folder with a text editor. Paste your key next to `ANTHROPIC_API_KEY=`. Keys look like `sk-ant-api03-...`

**"credit balance too low"**
Go to console.anthropic.com → Settings → Billing → add $5.

**"No photos found"**
Make sure your photos are in the folder shown at the top of the cull.io menu. Press **C** to open Workspaces and switch to a different folder.

**Browser doesn't open automatically**
Go to `http://localhost:5000` in your browser manually.

**Good photos not showing in the dashboard**
cull.io only sends the top-scoring photos to Claude by default, but picks the best shot from each distinct scene so your whole shoot is represented. If you still feel something's missing, click **Browse All Photos** — unanalyzed photos appear desaturated. Click any → **Send to Claude** to analyze it on the spot.

**Something went wrong mid-way through**
Both steps save as they go. The scan saves every 50 photos; Claude analysis saves after every single photo. Just run again — cull.io resumes where it stopped and skips anything already done.

**Start completely fresh**
Delete the **data** folder inside the cull.io folder, then run cull.io again.

---

## What Each File Does

| File / Folder | What it is |
|--------------|-----------|
| `Cull.io` | Double-click to launch — handles setup on first run, then opens the menu |
| `Cull.io` | Double-click every time you want to use cull.io |
| `run.py` | The main cull.io program |
| `photos/` | Default location to drop your photos |
| `.env` | Your settings — API key, your name |
| `data/` | cull.io's working files (scores, analysis, groups) |
| `data/workspaces.json` | Your workspace list — folders and their types |
| `data/<workspace>/catalog.json` | Scores and AI analysis per workspace |
| `data/design_brief.json` | Your website design preferences (saved from Design Consultant chat) |
| `docs/` | Your generated website |
| `logos/` | cull.io brand assets (logo, hero background) |
| `exports/ready_to_edit/` | RAW files copied here after you approve keepers |
| `exports/client_proof.html` | The file you send your client to pick favourites |
| `docs/sneak_peek/` | Square-cropped photos exported for Instagram |

---

## AI Website Design Consultant

Before building your website, click **Design Website ✦** in the dashboard header to open the consultant.

Claude will ask you questions about:
- Your style (editorial, minimal, bold, warm lifestyle, etc.)
- Color preferences and mood
- What sections you want (about, services, contact, etc.)
- What emotions visitors should feel
- 2–3 sites you admire for reference

Your answers are saved to `data/design_brief.json` and used when building your website.

**Cost transparency:** Every message shows estimated tokens before and actual token count + cost after. The total session cost is shown in the top bar. A typical design brief conversation costs under $0.05.

---

## Understanding What's Happening (For the Curious)

- **Culling** — the photography industry word for sorting through a shoot to find the keepers. That's where the name cull.io comes from.
- **Local scoring** — cull.io looks at pixel data to score sharpness, exposure, contrast, colour, and composition. Free, instant, no internet.
- **Scene clustering** — before sending photos to Claude, cull.io computes a quick visual fingerprint (perceptual hash) for each photo and groups visually similar ones together. It then picks the best shot from each group. This means a wedding with 50 altar shots sends 3–4 to Claude, not all 50 — so your whole shoot gets represented instead of one moment dominating.
- **Claude AI** — reads your actual photos like a professional photography critic and writes detailed analysis for each one.
- **Workspace type** — tells Claude how to evaluate your photos. "Straight from camera" means Claude helps you decide what to keep. "Already edited" means Claude evaluates how well the edit turned out.
- **RAW files** — your camera's original uncompressed sensor data. Much more editing flexibility in Lightroom than a JPG. cull.io reads them using a library called rawpy.
- **Virtual environment** — an isolated Python workspace so cull.io's tools don't interfere with anything else on your computer.
- **localhost** — your own computer. `http://localhost:5000` means "open the cull.io app running on this machine."
- **GitHub Pages** — a free service that turns your `docs/` folder into a live website.

---
