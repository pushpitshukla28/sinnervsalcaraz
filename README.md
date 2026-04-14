# Sinner vs Alcaraz — The Rivalry Defined

A dynamic, stat-heavy frontend comparison website for the modern tennis rivalry between **Jannik Sinner** and **Carlos Alcaraz**. Inspired by comprehensive stat tracking sites but built with a custom, sleek dark theme.

Live deployment: [https://sinnervsalcaraz.vercel.app](https://sinnervsalcaraz.vercel.app)

## Features

- **Single-File Architecture**: The entire frontend (HTML, CSS, JS and JSON data) is completely self-contained within `index.html`.
- **Comprehensive Head-to-Head**: Complete match log (2022-2026), filterable by Grand Slams, Masters 1000s, surface, and finals.
- **Deep Career Stats**: Dynamic comparison bars for total titles, win percentage, and tournament levels.
- **Surface Breakdown**: Detailed W-L records across Hard (Outdoor & Indoor), Clay, and Grass.
- **Tournament Insights**: Granular look at performance in all 4 Grand Slams, Masters 1000s, ATP 500s, and ATP 250s.
- **Season by Season**: Year-by-year trajectory comparing their rise from 2019 to present.
- **Honours & Records**: Curated list of notable achievements, trophies, and historical context.

## Design System

- **Background Palette**: Deep space darks (`#0a0a0c`, `#111114`).
- **Jannik Sinner Motif**: Electric blue (`#4f8ef7`) to symbolize ice/cool baseline dominance.
- **Carlos Alcaraz Motif**: Bold orange (`#f97316`) representing Spanish clay and fiery shot-making. 
- **Typography**: Clean, sans-serif readability powered by Google Fonts (Inter).

## Local Development

Since the site relies on no external frameworks, dependencies, or build tools, getting started is trivial:

1. Clone the repository: `git clone https://github.com/pushpitshukla28/sinnervsalcaraz.git`
2. Open `index.html` in any modern web browser.

### Adding Player Sketches

The Hero section supports custom player transparent image illustrations. To activate them:
1. Create isolated character sketches or photos with transparent backgrounds.
2. Name them `sinner.png` and `alcaraz.png`.
3. Drop them directly into the root project folder alongside `index.html`. 

The layout will automatically frame them and apply custom-colored drop shadow glows.

## Deployment

The project is linked to **Vercel** with GitHub integration.
Pushing to the `master` branch will automatically trigger a new production rollout.

```bash
git add .
git commit -m "Update stats"
git push
```

## Data Updates
All player data is hardcoded as structured Javascript Objects within `<script>` tags at the bottom of `index.html`. To update their total titles or add the latest tournament result, simply modify the variables (e.g. `PLAYERS`, `H2H_MATCHES`, `SEASON_STATS`) inside the file.
