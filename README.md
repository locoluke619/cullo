# Cullo — AI Photo Curation Studio

Cullo looks through your photos, finds the best ones using AI, and builds you a beautiful portfolio website. No coding required.

**What's new in this release:**
- **New dashboard** — shows your top 50 photos by AI score front-and-center. Similar groups are now a separate tab.
- **Arrow key navigation** — press ← → in any photo modal to move through your photos without closing.
- **Full comparison analysis** — the Compare page now shows Claude's full analysis (composition, technical, mood, editing tips) for every photo side-by-side.
- **Compare strip** — when a photo in the top 50 has similar shots, a banner appears in the modal to jump straight to the compare view.
- **AI Website Design Consultant** — chat with Claude to describe your vision before building. Claude asks you questions, captures your style preferences, and saves a design brief. Click **Design Website ✦** in the dashboard header.
- **Cost transparency** — every Claude API call shows estimated cost before and actual tokens + cost after. A running session total is visible in the header.

---

## Getting Started

### Step 1 — Download Cullo

1. On this GitHub page, click the green **Code** button
2. Click **Download ZIP**
3. Open your **Downloads** folder
4. Double-click the ZIP file to unzip it
5. Drag the unzipped **cullo** folder to your **Desktop**

### Step 2 — Run the Setup (one time only)

1. Open the **cullo** folder on your Desktop
2. Find the file called **START HERE.command**
3. Right-click it → choose **Open** → click **Open** in the popup

> **Why right-click instead of double-click?**
> The first time you run a downloaded file, Mac asks you to confirm it's safe.
> After that first time, you can double-click it directly.

A black window (Terminal) will open and walk you through everything:
- Installing the tools Cullo needs (~1 minute)
- Entering your name for the portfolio website
- Pointing Cullo to your photos
- Adding your AI key

### Step 3 — Get an AI Key

Cullo uses Claude AI to write expert analysis of your photos. You need a free Anthropic account with a small amount of credits:

1. Go to **https://console.anthropic.com** and sign up
2. Go to **Settings → Billing** and add $5 in credits
   *(analyzing your best photos shouldn't cost more than a cup of coffee!)*
3. Click **API Keys** in the left sidebar → **Create Key**
4. Copy the key — it looks like: `sk-ant-api03-...`
5. Paste it when Setup asks for it

### Step 4 — Add Your Photos

**Easiest:** Drop your photos into the **photos** folder inside the cullo folder.

**Already in another folder?** No problem — Setup asks where your photos are. You can type a path or drag the folder straight into the Terminal window.

**Can change later:** In the Cullo menu, choose **C — Change folder** to switch to a different shoot any time without editing any files.

### Step 5 — Run Cullo

Double-click **Cullo.command** in the cullo folder.

A menu appears. Choose **1** for the full pipeline — it walks through everything in order and asks before each step.

---

## What Cullo Does (Step by Step)

| Step | What Happens | Time | Cost |
|------|-------------|------|------|
| **Scan** | Scores every photo for sharpness, exposure, color, and composition. Saves as it goes — safe to interrupt and resume | ~5 min | Free |
| **AI Analysis** | Picks the best shot from each distinct scene, then sends those to Claude for expert feedback and a 1–10 score | ~15–20 min | ~$0.50–$1 |
| **Group** | Finds burst shots and similar angles, compares them side-by-side | ~5 min | ~$0.20–$0.50 |
| **Review** | You approve or skip photos in a browser dashboard | Your pace | Free |
| **Client Proof** | Export a file you can email your client — they tap ♥ on favourites | ~30 sec | Free |
| **Build** | Generates your portfolio website | ~2 min | Free |

Cullo tells you the **estimated cost before charging anything** and shows you the **actual cost** when analysis finishes.

---

## The Menu

Every time you run Cullo you'll see:

```
  Folder:   Wedding_June2025  (847 photos)
  Catalog:  ready ✓

  [1]  Full pipeline      scan → AI analysis → compare groups → review
  [2]  Scan & score       analyze photo quality locally (free)
  [3]  AI analysis        send top photos to Claude (uses credits)
  [4]  Group similar      find burst shots & compare them
  [5]  Review dashboard   open the review app in your browser
  [6]  Export RAWs        copy selected RAWs to ready_to_edit/ for Lightroom
  [7]  Sneak peek         export best 9 photos for Instagram
  [8]  Build website      generate your portfolio website
  [9]  Client proof       export a file you can email to your client
  [c]  Change folder      switch to a different shoot
```

**[c] Change folder** is especially useful for working photographers — swap between shoots without touching any files.

---

## Using the Review Dashboard

After running the pipeline, your browser opens automatically to the review dashboard at `http://localhost:5000`.

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
- Cullo generates a single file: `exports/client_proof.html`
- Email it directly, or upload to Google Drive / iCloud / Dropbox and share the link
- Your client opens the file in their browser — no app, no account needed
- They tap ♥ on the photos they love, then click **Send My Picks** — their email opens pre-filled with their selections addressed to you

**Getting client picks back into your dashboard:**
- When the client sends their picks email, paste the whole email into **Import Client Picks** in the dashboard header
- Cullo reads the picks code automatically and marks those photos with a **♥ Client Pick** badge
- A **Client Picks** filter tab appears so you can see exactly what they loved

---

## Editing Your Picks in Lightroom

After approving your keepers, click **Export RAWs to Edit** in the dashboard header (or choose **6** in the menu).

Cullo finds the RAW file matching each approved photo and copies them all into **exports/ready_to_edit/** — then opens that folder automatically.

Drag it straight into Lightroom or Capture One. Every file in there is already a keeper you chose.

**RAW+JPG shooters (most camera users):** Cullo uses the JPG for scoring and display, keeps the RAW for this export. No extra work needed.

**RAW-only shooters:** Cullo now reads RAW files directly — just point it at your RAW folder and it handles everything.

---

## Sneak Peek for Social Media

Choose **7 — Sneak peek** in the menu.

Cullo picks your 9 best, most visually varied approved photos and exports them as square 1080×1080 crops into **docs/sneak_peek/**. Drag those 9 files into an Instagram carousel — ready to post.

---

## Putting Your Website Online (Free)

### 1. Create a GitHub account

Go to **https://github.com** and sign up. Your username becomes part of your website address.

### 2. Create a new repository

1. Click **+** (top right on GitHub) → **New repository**
2. Name it `cullo` or `my-photography`
3. Set it to **Public**
4. Leave everything else unchecked → **Create repository**

### 3. Push Cullo to GitHub

Open Terminal (or the Cullo.command window already open) and run these one at a time:

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

Run Cullo, approve your picks, build the website, then:

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

**RAW+JPG shooters:** If your camera saves both, Cullo uses the JPG for speed and keeps the RAW untouched for Lightroom. You get the best of both.

**RAW-only shooters:** Cullo reads your RAW files directly — no conversion needed.

---

## Privacy & Security

**Completely reasonable to ask.** Here's exactly what Cullo does:

### What leaves your computer
- **Your photos** — sent to Anthropic (the company that makes Claude AI) for analysis over an encrypted connection. Same as uploading to Google Photos or iCloud. Anthropic's privacy policy: anthropic.com/privacy
- **Nothing else** — no filenames, no folder paths, no personal information

### What stays on your computer
- Your API key (in `.env` — never uploaded to GitHub)
- All photo scores and analysis (in `data/`)
- Your website files (in `docs/`)

### The review dashboard
Runs at `http://localhost:5000` — only accessible from your own computer. Not reachable from the internet.

### The .command files
Plain text scripts — identical to commands you'd type yourself in Terminal. No admin access. Right-click → **Open With → TextEdit** to read every line before running.

---

## Troubleshooting

**"The .command file won't open"**
Right-click → Open → Open. Mac requires this the first time for downloaded files.

**"Python is not installed"**
Setup opens python.org automatically. Install Python, then run Setup again.

**"No API key" or "Invalid API key"**
Open the `.env` file in the cullo folder with a text editor. Paste your key next to `ANTHROPIC_API_KEY=`. Keys look like `sk-ant-api03-...`

**"credit balance too low"**
Go to console.anthropic.com → Settings → Billing → add $5.

**"No photos found"**
Make sure your photos are in the folder shown at the top of the Cullo menu. Press **C** to change the folder if needed.

**Browser doesn't open automatically**
Go to `http://localhost:5000` in your browser manually.

**Good photos not showing in the dashboard**
Cullo only sends the top-scoring photos to Claude by default, but picks the best shot from each distinct scene so your whole shoot is represented. If you still feel something's missing, click **Browse All Photos** — unanalyzed photos appear desaturated. Click any → **Send to Claude** to analyze it on the spot.

**Something went wrong mid-way through**
Both steps save as they go. The scan saves every 50 photos; Claude analysis saves after every single photo. Just run again — Cullo resumes where it stopped and skips anything already done.

**Start completely fresh**
Delete the **data** folder inside cullo, then run Cullo again.

---

## What Each File Does

| File / Folder | What it is |
|--------------|-----------|
| `START HERE.command` | Run once to set everything up |
| `Cullo.command` | Run this every time you want to use Cullo |
| `run.py` | The main Cullo program |
| `photos/` | Default location to drop your photos |
| `.env` | Your settings — API key, photo folder, your name |
| `data/` | Cullo's working files (scores, analysis, groups) |
| `data/design_brief.json` | Your website design preferences (saved from Design Consultant chat) |
| `docs/` | Your generated website |
| `logos/` | Cullo brand assets (logo, hero background) |
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

- **Culling** — the photography industry word for sorting through a shoot to find the keepers. That's where the name Cullo comes from.
- **Local scoring** — Cullo looks at pixel data to score sharpness, exposure, contrast, colour, and composition. Free, instant, no internet.
- **Scene clustering** — before sending photos to Claude, Cullo computes a quick visual fingerprint (perceptual hash) for each photo and groups visually similar ones together. It then picks the best shot from each group. This means a wedding with 50 altar shots sends 3–4 to Claude, not all 50 — so your whole shoot gets represented instead of one moment dominating.
- **Claude AI** — reads your actual photos like a professional photography critic and writes detailed analysis for each one.
- **RAW files** — your camera's original uncompressed sensor data. Much more editing flexibility in Lightroom than a JPG. Cullo reads them using a library called rawpy.
- **Virtual environment** — an isolated Python workspace so Cullo's tools don't interfere with anything else on your computer.
- **localhost** — your own computer. `http://localhost:5000` means "open the Cullo app running on this machine."
- **GitHub Pages** — a free service that turns your `docs/` folder into a live website.

---
