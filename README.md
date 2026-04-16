# Sinner vs Alcaraz — The Rivalry Defined

A dynamic, stat-heavy frontend comparison website for the modern tennis rivalry between **Jannik Sinner** and **Carlos Alcaraz**.

🔗 **Live site:** [sinnervsalcaraz.vercel.app](https://sinnervsalcaraz.vercel.app)

---

## Features

- **Head-to-Head** — Complete match log (2022–2026), filterable by Grand Slams, Masters 1000, surface, and finals only.
- **Career Stats** — Dynamic comparison bars for titles, win %, prize money, and more.
- **Surface Breakdown** — Detailed W-L records across Hard (Outdoor & Indoor), Clay, and Grass.
- **Tournament Insights** — Performance at every Grand Slam, Masters 1000, ATP 500/250, and ATP Finals.
- **Season by Season** — Year-by-year trajectory comparing their rise from 2019 to present.
- **Honours & Records** — Curated list of trophies, achievements, and historical milestones.

---

## How Stats Stay Up to Date

Stats are stored in [`data.json`](./data.json) and loaded by the page at runtime via `fetch()`.

A **GitHub Actions** workflow ([`.github/workflows/update-stats.yml`](.github/workflows/update-stats.yml)) runs automatically **every 45 minutes**:

```
GitHub Actions (every 45 min)
  → scripts/update_stats.py runs
  → Pulls latest stats from Wikipedia (free, no API key)
  → Updates data.json if anything changed
  → Commits & pushes to GitHub
  → Vercel detects new commit → redeploys in ~15 seconds
```

### What gets auto-updated

| Field | Source |
|---|---|
| Current ATP Ranking | Wikipedia infobox |
| Career W-L Record & Win % | Wikipedia infobox |
| Total Titles | Wikipedia infobox |
| Grand Slam count | Wikipedia career stats |
| Prize Money | Wikipedia infobox |
| Surface W-L (Hard / Clay / Grass / Indoor) | Wikipedia career stats |
| Current season W-L & titles | Wikipedia career stats |
| `meta.lastUpdated` timestamp | Auto-set on each change |

### What must be updated manually

Edit [`data.json`](./data.json) directly for:

| Field | Why manual |
|---|---|
| `h2hMatches` | New matches need score, round, surface — not reliably scrapable |
| `grandSlamTitles` | Specific slam name and year list |
| `tournamentStats` | Per-tournament breakdown detail |
| `records` | Notable historical records text |
| `otherTrophies` | Honours / awards list |
| Player profile (DOB, height, coach) | Static biographical info |

### Triggering a manual update

Go to the **Actions** tab on GitHub → select **"Update Stats"** → click **"Run workflow"**.

---

## Running the scraper locally

Requires Python 3.10+ (no external packages needed — only stdlib):

```bash
# Normal run — updates data.json
python scripts/update_stats.py

# Dry run — shows what would change without saving
python scripts/update_stats.py --dry
```

---

## Local Development

The site is a static HTML/JS/JSON bundle — no build step required.

```bash
# Option 1: any static server (required for fetch() to work)
npx serve .

# Option 2: Python
python -m http.server 3000
```

Then open `http://localhost:3000`.

> ⚠️  Opening `index.html` directly via `file://` will block the `fetch('data.json')` call. Always use a local server.

### Adding player images

The hero section supports transparent PNG character art:

1. Name them `sinner.png` and `alcaraz.png`
2. Drop them in the root folder alongside `index.html`

The layout automatically applies the correct drop-shadow glow.

---

## Design System

| Token | Value | Role |
|---|---|---|
| Background | `#0a0a0c`, `#111114` | Deep space darks |
| Sinner accent | `#4f8ef7` | Electric blue |
| Alcaraz accent | `#f97316` | Bold orange |
| Typography | Inter (Google Fonts) | Clean sans-serif |

---

## Deployment

Linked to **Vercel** with GitHub integration. Any push to `master` triggers an automatic production redeploy.

```bash
git add .
git commit -m "Update stats"
git push
```

---

## Project Structure

```
sinnervsalcaraz/
├── index.html               # Full frontend (HTML + CSS + JS)
├── data.json                # All stats — the single source of truth
├── scripts/
│   └── update_stats.py      # Auto-updater script (Wikipedia scraper)
├── .github/
│   └── workflows/
│       └── update-stats.yml # GitHub Actions schedule (every 45 min)
└── README.md
```
