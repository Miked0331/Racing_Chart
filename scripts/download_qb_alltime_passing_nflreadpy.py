import argparse
import datetime
from pathlib import Path

import pandas as pd

MIN_SEASON = 1999


def fetch_season_stats(season: int, summary_level: str):
    import nflreadpy  # type: ignore

    stats = nflreadpy.load_player_stats(seasons=season, summary_level=summary_level)
    return stats.to_pandas()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1950, help="Start season year")
    parser.add_argument("--end", type=int, default=None, help="End season year (inclusive)")
    parser.add_argument(
        "--summary-level",
        default="reg",
        choices=["week", "reg", "post", "reg+post"],
        help="Season summary level to pull from nflreadpy",
    )
    parser.add_argument(
        "--output",
        default="data/nfl_qb_season_passing_1950_current.csv",
        help="Output CSV path",
    )
    args = parser.parse_args()

    try:
        import nflreadpy  # type: ignore
    except Exception:
        print("Missing dependency: nflreadpy")
        print("Install with: pip install nflreadpy")
        return 1

    end = int(args.end or datetime.datetime.now().year)
    start = int(args.start)
    if start < MIN_SEASON:
        print(f"nflreadpy data starts at {MIN_SEASON}. Clamping start year from {start} to {MIN_SEASON}.")
        start = MIN_SEASON

    seasons = list(range(start, end + 1))
    print(f"Loading player stats for seasons {seasons[0]}-{seasons[-1]} ({args.summary_level})...")

    frames = []
    for season in seasons:
        try:
            stats = fetch_season_stats(season, args.summary_level)
        except Exception as exc:
            print(f"Failed {season}: {exc}")
            continue

        required = {"season", "player_display_name", "position", "passing_yards", "recent_team"}
        missing = required - set(stats.columns)
        if missing:
            print(f"Skipping {season}: missing columns {', '.join(sorted(missing))}")
            continue

        frames.append(stats)

    if not frames:
        print("No data fetched.")
        return 1

    df = pd.concat(frames, ignore_index=True)
    df = df[df["position"].astype(str) == "QB"].copy()
    df["passing_yards"] = pd.to_numeric(df["passing_yards"], errors="coerce").fillna(0)
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df = df.dropna(subset=["season", "player_display_name"])

    out = df[["season", "player_display_name", "recent_team", "passing_yards"]].rename(
        columns={
            "season": "season",
            "player_display_name": "player",
            "recent_team": "team",
            "passing_yards": "pass_yards",
        }
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"Saved {len(out)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
