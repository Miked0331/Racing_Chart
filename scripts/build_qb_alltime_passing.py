import argparse
import sys
import pandas as pd


def build_alltime_passing(input_csv: str, output_csv: str) -> pd.DataFrame:
    df = pd.read_csv(input_csv)
    required = {"season", "player", "team", "pass_yards"}
    missing = required - set(df.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Input is missing required columns: {missing_list}")

    df = df.copy()
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df["pass_yards"] = pd.to_numeric(df["pass_yards"], errors="coerce").fillna(0)

    df = df.dropna(subset=["season", "player"])
    df = df.sort_values(["player", "season"])

    df["career_yards"] = df.groupby("player")["pass_yards"].cumsum()

    out = df[["season", "player", "team", "career_yards"]].rename(
        columns={
            "season": "time",
            "career_yards": "value",
        }
    )

    out.to_csv(output_csv, index=False)
    return out


def print_top10_summary(out: pd.DataFrame) -> None:
    last_rows = out.sort_values(["player", "time"]).groupby("player").tail(1)
    top10 = last_rows.sort_values("value", ascending=False).head(10)
    print("Top 10 final career passing yards:")
    for _, row in top10.iterrows():
        print(f"{row['player']}: {int(row['value']):,}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="nfl_qb_season_passing_1950_current.csv",
        help="Input season-level CSV",
    )
    parser.add_argument(
        "--output",
        default="nfl_qb_alltime_passing_1950_current.csv",
        help="Output all-time CSV",
    )
    args = parser.parse_args()

    try:
        out = build_alltime_passing(args.input, args.output)
        print_top10_summary(out)
    except Exception as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
