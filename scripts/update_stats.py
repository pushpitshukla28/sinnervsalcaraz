#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_stats.py
===============
Fetches the latest Sinner & Alcaraz stats from Wikipedia and updates data.json.

Data source  : Wikipedia (free, no API key, community-maintained)
Why Wikipedia: Static HTML API, human-verified, follows a consistent infobox
               template for all professional tennis players.

Stats auto-updated
------------------
  players.*   : currentRanking, careerRecord, winPct, totalTitles,
                grandSlams, prizeMoney
  surfaceStats: W-L records per surface (hard / indoor / clay / grass)
  seasonStats : current-year W-L and titles count
  meta        : lastUpdated timestamp

Stats that must be updated manually in data.json
-------------------------------------------------
  h2hMatches      — add new H2H matches as they happen
  grandSlamTitles — add specific slam entries (name, year)
  tournamentStats — per-tournament detail breakdown
  records         — notable historical records text
  otherTrophies   — honours / awards lists

Usage
-----
  python scripts/update_stats.py          # normal run
  python scripts/update_stats.py --dry    # show what would change, don't save
"""

import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"

# ── Wikipedia API ─────────────────────────────────────────────────────────────
WP_API = "https://en.wikipedia.org/w/api.php"

# Wikipedia page titles for each player
PLAYER_PAGES = {
    "sinner":  "Jannik_Sinner",
    "alcaraz": "Carlos_Alcaraz",
}

HEADERS = {
    "User-Agent": "SinnerAlcarazStatsBot/1.0 (https://sinnervsalcaraz.vercel.app)"
}

DRY_RUN = "--dry" in sys.argv

# Ensure UTF-8 output on all platforms (including Windows)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ── HTTP ──────────────────────────────────────────────────────────────────────
def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def wp_wikitext(page: str) -> str:
    """Return the raw wikitext for a Wikipedia page."""
    url = (
        f"{WP_API}?action=parse&page={page}"
        f"&prop=wikitext&format=json&redirects=1"
    )
    data = json.loads(http_get(url))
    return data["parse"]["wikitext"]["*"]


# ── Wikitext helpers ──────────────────────────────────────────────────────────
def strip_wiki(s: str) -> str:
    """Remove common wiki markup, returning plain text."""
    s = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", s)   # [[link|label]]
    s = re.sub(r"\{\{[^}]*\}\}", "", s)                         # {{template}}
    s = re.sub(r"'{2,}", "", s)                                  # '''bold'''
    s = re.sub(r"<[^>]+>", "", s)                               # <html tags>
    return s.strip()


def infobox_field(wikitext: str, *keys: str) -> str | None:
    """
    Return the cleaned value of the first infobox key that matches.
    Tries every key in order; returns None if none found.
    """
    for key in keys:
        m = re.search(
            rf"^\|\s*{re.escape(key)}\s*=\s*(.+)",
            wikitext,
            re.MULTILINE,
        )
        if m:
            v = strip_wiki(m.group(1))
            if v:
                return v
    return None


# ── Individual field parsers ──────────────────────────────────────────────────

def parse_ranking(wt: str) -> int | None:
    """Current ATP ranking from the infobox."""
    # Field: currentsinglesranking = No. '''2''' (13 April 2026)
    v = infobox_field(wt, "currentsinglesranking", "current_ranking", "world_ranking")
    if v:
        m = re.search(r"(\d+)", v)
        return int(m.group()) if m else None
    return None


def parse_career_record(wt: str) -> tuple[int | None, int | None]:
    """
    Career W-L.  Wikipedia tennis infobox uses:
      singlesrecord = 302-68   (plain text with en-dash or hyphen)
    """
    # Field: singlesrecord = 302-68  or  302–68
    v = infobox_field(wt, "singlesrecord", "career_record")
    if v:
        m = re.search(r"(\d+)\s*[–—\-]\s*(\d+)", v)
        if m:
            return int(m.group(1)), int(m.group(2))

    # Fallback: {{win-loss|W|L}} template (older format)
    m = re.search(
        r"\|\s*(?:singlesrecord|career_record)\s*=.*?\{\{\s*[Ww]in.?[Ll]oss\s*\|(\d+)\|(\d+)",
        wt,
    )
    if m:
        return int(m.group(1)), int(m.group(2))

    return None, None


def parse_titles(wt: str) -> int | None:
    """Total career singles titles."""
    # Field: singlestitles = 26
    v = infobox_field(wt, "singlestitles", "career_titles", "titles")
    if v:
        m = re.search(r"\d+", v)
        return int(m.group()) if m else None
    return None


def parse_prize_money(wt: str) -> str | None:
    """Career prize money, formatted as $XX.XM."""
    # Field: careerprizemoney = US$ '''64,948,871'''
    v = infobox_field(wt, "careerprizemoney", "prize_money")
    if v:
        m = re.search(r"([\d,]+)", v)
        if m:
            amount = int(m.group(1).replace(",", ""))
            return f"${amount / 1_000_000:.1f}M"
    return None


def parse_grand_slams(wt: str) -> int | None:
    """
    Grand Slam singles titles count.

    Wikipedia tennis infoboxes have four explicit result fields:
      AustralianOpenresult = '''W''' (2024, 2025)
      FrenchOpenresult     = '''W''' (2024, 2025)
      Wimbledonresult      = '''W''' (2023, 2024)
      USOpenresult         = '''W''' (2022, 2025)

    We count the number of year links inside each 'W' field.
    Falls back to section-header, Honours section, and prose counting.
    """
    SLAM_FIELDS = [
        "AustralianOpenresult",
        "FrenchOpenresult",
        "Wimbledonresult",
        "USOpenresult",
    ]
    total = 0
    for field_name in SLAM_FIELDS:
        # Match:  |AustralianOpenresult = '''W''' ([[2026 ...|2026]], [[2024...|2024]])
        pat = (
            r"\|\s*" + re.escape(field_name) +
            r"\s*=\s*(?:'{3})?W(?:'{3})?\s*(.*?)(?=\n\|)"
        )
        m = re.search(pat, wt, re.IGNORECASE | re.DOTALL)
        if m:
            # Count year links like [[2024 ...]] inside this field value
            years = re.findall(r"\[\[\d{4}", m.group(1))
            total += len(years)

    if total > 0:
        return total

    # Fallback 1: section header === Grand Slam singles titles (N) ===
    m = re.search(
        r"Grand Slam singles titles\s*\((\d+)\)",
        wt,
        re.IGNORECASE,
    )
    if m:
        return int(m.group(1))

    # Fallback 2: count linked slam titles in Honours section
    titles_section = re.search(
        r"(?:Grand Slam singles titles?|Honours?|Achievements?)(.*?)(?:\n==|\Z)",
        wt,
        re.DOTALL | re.IGNORECASE,
    )
    if titles_section:
        slam_pattern = re.compile(
            r"\[\[(?:\d{4}\s+)?(?:Australian Open|French Open|"
            r"Roland.Garros|Wimbledon|US Open)[^\]]*singles",
            re.IGNORECASE,
        )
        count = len(slam_pattern.findall(titles_section.group(1)))
        if count > 0:
            return count

    # Fallback 3: prose
    m = re.search(r"(?:has won|won)\s+(\d+)\s+Grand Slam", wt, re.IGNORECASE)
    if m:
        return int(m.group(1))

    return None


def parse_surface_stats(wt: str) -> dict[str, tuple[int, int]]:
    """
    Parse surface W-L from the career statistics table.

    Wikipedia career stats tables contain rows like:
        | Hard (outdoor) || 215–42 || ...
        | Clay || 48–23 || ...
    Returns: { "hard": (w, l), "clay": (w, l), "grass": (w, l), "indoor": (w, l) }
    """
    surface_patterns = {
        "hard":   [r"Hard\s*(?:\([Oo]utdoor\))?", r"Outdoor\s*hard"],
        "indoor": [r"Hard\s*\([Ii]ndoor\)", r"Indoor\s*hard", r"Carpet"],
        "clay":   [r"Clay"],
        "grass":  [r"Grass"],
    }
    result: dict[str, tuple[int, int]] = {}

    for surf_key, patterns in surface_patterns.items():
        for pat in patterns:
            # Style 1: combined "W–L" in a single cell
            m = re.search(
                rf"\|\s*{pat}\s*\|\|[^|\n]*?(\d+)\s*[–—\-]\s*(\d+)",
                wt,
                re.IGNORECASE,
            )
            if m:
                result[surf_key] = (int(m.group(1)), int(m.group(2)))
                break

            # Style 2: separate Win and Loss columns
            m = re.search(
                rf"\|\s*{pat}\s*\|\|[^|\n]*?\|\|\s*(\d+)\s*\|\|\s*(\d+)",
                wt,
                re.IGNORECASE,
            )
            if m:
                result[surf_key] = (int(m.group(1)), int(m.group(2)))
                break

    return result


def parse_season_stats(wt: str, year: int) -> tuple[str | None, int | None]:
    """
    Extract the current year's W-L and titles from the season statistics table.
    Returns (wl_string, titles_count) — either element may be None.
    """
    # Tables usually look like: | 2026 || 26–4 || 3 || ...
    m = re.search(
        rf"\|\s*{year}\s*\|\|[^|\n]*?(\d+)\s*[–\-]\s*(\d+)[^|\n]*?\|\|\s*(\d+)",
        wt,
    )
    if m:
        w, l, t = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{w}-{l}", t

    # Simpler fallback — just get the W-L for the current year row
    m = re.search(
        rf"\|\s*{year}\s*\|\|[^|\n]*?(\d+)\s*[–\-]\s*(\d+)",
        wt,
    )
    if m:
        w, l = int(m.group(1)), int(m.group(2))
        return f"{w}-{l}", None

    return None, None


# ── Apply updates to data dict ────────────────────────────────────────────────

def apply_player_updates(
    data: dict,
    player: str,
    wt: str,
    year: int,
) -> list[str]:
    """
    Parse the wikitext and update all relevant fields in `data` for one player.
    Returns a list of human-readable change descriptions (empty if nothing changed).
    """
    p    = data["players"][player]
    log: list[str] = []

    def set_val(path: str, new_val):
        """Dot-notation field setter; skips if new_val is None or unchanged."""
        if new_val is None:
            return
        keys = path.split(".")
        obj = p
        for k in keys[:-1]:
            obj = obj[k]
        k = keys[-1]
        old = obj.get(k)
        if old != new_val:
            log.append(f"    {player}.{path}: {old!r} -> {new_val!r}")
            obj[k] = new_val

    # ── Player profile fields ─────────────────────────────────────────────────
    set_val("currentRanking", parse_ranking(wt))

    w, l = parse_career_record(wt)
    if w is not None and l is not None:
        old_w = p["careerRecord"].get("w")
        old_l = p["careerRecord"].get("l")
        if old_w != w or old_l != l:
            log.append(f"    {player}.careerRecord: {old_w}-{old_l} -> {w}-{l}")
            p["careerRecord"]["w"] = w
            p["careerRecord"]["l"] = l
        set_val("winPct", round(w / (w + l) * 100, 1))

    set_val("totalTitles",  parse_titles(wt))
    set_val("grandSlams",   parse_grand_slams(wt))
    set_val("prizeMoney",   parse_prize_money(wt))

    # ── Surface stats ─────────────────────────────────────────────────────────
    surface_data = parse_surface_stats(wt)
    for surf, (sw, sl) in surface_data.items():
        if surf not in data["surfaceStats"]:
            continue
        sp = data["surfaceStats"][surf][player]
        old_w, old_l = sp.get("w"), sp.get("l")
        if old_w != sw or old_l != sl:
            new_pct = round(sw / (sw + sl) * 100, 1) if (sw + sl) > 0 else 0
            log.append(
                f"    surfaceStats.{surf}.{player}: "
                f"{old_w}-{old_l} -> {sw}-{sl} ({new_pct}%)"
            )
            sp["w"]   = sw
            sp["l"]   = sl
            sp["pct"] = new_pct

    # ── Current season ────────────────────────────────────────────────────────
    wl_str, titles = parse_season_stats(wt, year)
    for entry in data["seasonStats"]:
        if entry["year"] == year:
            ps = entry[player]
            if wl_str and ps.get("wl") != wl_str:
                log.append(
                    f"    seasonStats.{year}.{player}.wl: "
                    f"{ps.get('wl')!r} -> {wl_str!r}"
                )
                ps["wl"] = wl_str
            if titles is not None and ps.get("titles") != titles:
                log.append(
                    f"    seasonStats.{year}.{player}.titles: "
                    f"{ps.get('titles')!r} -> {titles!r}"
                )
                ps["titles"] = titles
            break

    return log


# ── Hero strip (index.html hardcoded fallback values) ─────────────────────────
# The hero strip in index.html has a few stats hardcoded in HTML (H2H pill,
# ranking labels, prize money display).  These are rendered via JS from
# data.json now, so no additional action needed here.


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{ts}] Sinner vs Alcaraz — stats updater")
    if DRY_RUN:
        print("  (dry run — data.json will NOT be written)\n")

    # Load current data
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    year = datetime.now(timezone.utc).year
    all_changes: list[str] = []

    for player, page in PLAYER_PAGES.items():
        print(f"\n  >> Fetching Wikipedia/{page} ...", flush=True)
        try:
            wt = wp_wikitext(page)
        except urllib.error.URLError as e:
            print(f"  [ERROR] Network error: {e}", file=sys.stderr)
            continue
        except (KeyError, json.JSONDecodeError) as e:
            print(f"  [ERROR] Parse error: {e}", file=sys.stderr)
            continue

        changes = apply_player_updates(data, player, wt, year)

        if changes:
            print(f"  [UPDATED] {player}: {len(changes)} change(s) detected")
            for c in changes:
                print(c)
            all_changes.extend(changes)
        else:
            print(f"  [OK] {player}: all fields up to date - no changes")

    if all_changes:
        # Update timestamp
        data["meta"]["lastUpdated"] = datetime.now(timezone.utc).strftime("%B %Y")

        if DRY_RUN:
            print(f"\n[dry run] Would save {len(all_changes)} change(s) to data.json.")
        else:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            print(f"\n[DONE] data.json updated ({len(all_changes)} change(s)).")
    else:
        print("\n[OK] No changes - data.json is already up to date.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
