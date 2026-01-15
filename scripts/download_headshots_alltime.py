import argparse
import os
from pathlib import Path

import pandas as pd
import requests


def safe_filename(name: str) -> str:
    return name.replace(" ", "_").replace(".", "").replace("'", "").replace("-", "_")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/nfl_qb_season_passing_1950_current.csv",
        help="Season-level passing CSV",
    )
    parser.add_argument(
        "--output-dir",
        default="assets/headshots/qb_alltime_passing_1950_current",
        help="Folder to save headshots",
    )
    args = parser.parse_args()

    try:
        import nflreadpy  # type: ignore
    except Exception:
        print("Missing dependency: nflreadpy")
        print("Install with: pip install nflreadpy")
        return 1

    df = pd.read_csv(args.input)
    if "player" not in df.columns:
        print("Input CSV must include a 'player' column.")
        return 1

    players = sorted({p for p in df["player"].dropna().astype(str)})
    print(f"Found {len(players)} unique players in input.")

    try:
        stats = nflreadpy.load_player_stats(seasons=True, summary_level="reg")
    except Exception as exc:
        print(f"Failed to load nflreadpy data: {exc}")
        return 1

    stats = stats.to_pandas()
    cols = {"player_display_name", "headshot_url"}
    if not cols.issubset(set(stats.columns)):
        print("nflreadpy stats missing headshot_url columns.")
        return 1

    stats = stats.dropna(subset=["headshot_url"])
    url_map = (
        stats.groupby("player_display_name")["headshot_url"]
        .last()
        .to_dict()
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChartsHeadshotFetcher/1.0"
    })

    downloaded = 0
    skipped = 0
    for player in players:
        url = url_map.get(player)
        if not url:
            skipped += 1
            continue
        filename = safe_filename(player) + ".png"
        out_path = out_dir / filename
        if out_path.exists():
            skipped += 1
            continue
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(resp.content)
            downloaded += 1
            if downloaded % 25 == 0:
                print(f"Downloaded {downloaded} headshots...")
        except Exception:
            skipped += 1

    print(f"Downloaded: {downloaded}, skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
