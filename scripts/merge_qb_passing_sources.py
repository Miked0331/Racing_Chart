import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"season", "player", "team", "pass_yards"}


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")
    df = df.copy()
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df["pass_yards"] = pd.to_numeric(df["pass_yards"], errors="coerce").fillna(0)
    df = df.dropna(subset=["season", "player"])
    return df


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre", required=True, help="CSV with seasons before 1999")
    parser.add_argument("--post", required=True, help="CSV with seasons 1999+ (nflreadpy output)")
    parser.add_argument(
        "--output",
        default="data/nfl_qb_season_passing_1950_current.csv",
        help="Merged output CSV path",
    )
    args = parser.parse_args()

    try:
        pre = load_csv(args.pre)
        post = load_csv(args.post)
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    merged = pd.concat([pre, post], ignore_index=True)
    merged = merged.sort_values(["season", "player"])

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_path, index=False)
    print(f"Saved {len(merged)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
