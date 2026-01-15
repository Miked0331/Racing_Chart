import argparse
import re
from pathlib import Path

import pandas as pd


def detect_season(path: Path, df: pd.DataFrame) -> int:
    if "season" in df.columns:
        season = pd.to_numeric(df["season"], errors="coerce").dropna()
        if not season.empty:
            return int(season.iloc[0])
    match = re.search(r"(19|20)\d{2}", path.stem)
    if match:
        return int(match.group(0))
    raise ValueError(f"Could not detect season for {path}")


def normalize_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.copy()

    if "Player" not in df.columns or "Yds" not in df.columns:
        raise ValueError(f"{path} is missing required columns (Player, Yds).")

    team_col = "Tm" if "Tm" in df.columns else "Team" if "Team" in df.columns else None
    if not team_col:
        raise ValueError(f"{path} is missing team column (Tm/Team).")

    season = detect_season(path, df)
    df["season"] = season

    df["Player"] = (
        df["Player"]
        .astype(str)
        .str.replace("*", "", regex=False)
        .str.replace("+", "", regex=False)
        .str.strip()
    )
    df = df[df["Player"].notna()]
    df = df[df["Player"] != "League Average"]

    if "Pos" in df.columns:
        df = df[df["Pos"].astype(str) == "QB"]

    df["Yds"] = pd.to_numeric(df["Yds"], errors="coerce").fillna(0)
    df[team_col] = df[team_col].astype(str).str.strip()

    out = df[["season", "Player", team_col, "Yds"]].rename(
        columns={
            "Player": "player",
            team_col: "team",
            "Yds": "pass_yards",
        }
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="data/pfr_seasons", help="Folder of PFR CSVs")
    parser.add_argument(
        "--output",
        default="data/nfl_qb_season_passing_1950_1998.csv",
        help="Output CSV path",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    files = sorted(input_dir.glob("*.csv"))
    if not files:
        print(f"No CSVs found in {input_dir}")
        return 1

    frames = []
    for path in files:
        try:
            frames.append(normalize_file(path))
        except Exception as exc:
            print(f"Skipping {path.name}: {exc}")

    if not frames:
        print("No valid CSVs to process.")
        return 1

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values(["season", "player"])

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_path, index=False)
    print(f"Saved {len(merged)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
