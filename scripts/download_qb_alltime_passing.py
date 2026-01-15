import argparse
import datetime
import random
import re
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


def pick_passing_table(tables: list[pd.DataFrame]) -> pd.DataFrame:
    for table in tables:
        cols = {str(c).strip() for c in table.columns}
        if "Player" in cols and "Yds" in cols and "Tm" in cols:
            return table
    raise ValueError("Could not find passing table with Player/Tm/Yds columns.")


def clean_season_table(df: pd.DataFrame, season: int) -> pd.DataFrame:
    df = df.copy()
    if "Rk" in df.columns:
        df = df[df["Rk"].astype(str) != "Rk"]
    df = df[df["Player"].notna()]

    df["Yds"] = pd.to_numeric(df["Yds"], errors="coerce").fillna(0)
    df["Player"] = df["Player"].astype(str).str.replace("*", "", regex=False).str.replace("+", "", regex=False).str.strip()
    df["Tm"] = df["Tm"].astype(str).str.strip()

    df["_is_multi_team"] = df["Tm"].str.endswith("TM")
    df = df.sort_values(["Player", "_is_multi_team", "Yds"], ascending=[True, False, False])
    df = df.drop_duplicates(subset=["Player"], keep="first")

    out = df[["Player", "Tm", "Yds"]].rename(
        columns={
            "Player": "player",
            "Tm": "team",
            "Yds": "pass_yards",
        }
    )
    out.insert(0, "season", season)
    return out


def read_tables_from_html(html: str) -> list[pd.DataFrame]:
    tables = []
    tables.extend(pd.read_html(StringIO(html)))
    for match in re.finditer(r"<!--(.*?)-->", html, flags=re.DOTALL):
        comment = match.group(1)
        if 'id="passing"' not in comment:
            continue
        try:
            tables.extend(pd.read_html(StringIO(comment)))
        except ValueError:
            continue
    return tables


def fetch_season_passing(
    season: int,
    session: requests.Session,
    retries: int = 6,
    retry_after_default: int = 60,
    jitter: float = 0.0,
) -> pd.DataFrame:
    url = f"https://www.pro-football-reference.com/years/{season}/passing.htm"
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else float(retry_after_default)
                wait = wait + random.uniform(0.0, jitter)
                print(f"429 Too Many Requests for {season}. Waiting {wait:.1f}s before retry.")
                time.sleep(wait)
                raise RuntimeError("429 Too Many Requests")
            resp.raise_for_status()
            tables = read_tables_from_html(resp.text)
            passing = pick_passing_table(tables)
            return clean_season_table(passing, season)
        except Exception as exc:
            last_exc = exc
            if attempt == retries:
                break
            backoff = min(120, 2 ** attempt)
            print(f"Retry {attempt}/{retries} for {season} after {backoff}s: {exc}")
            time.sleep(backoff)
    raise last_exc


def main() -> int:
    current_year = datetime.datetime.now().year
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1950, help="Start season year")
    parser.add_argument("--end", type=int, default=current_year, help="End season year (inclusive)")
    parser.add_argument(
        "--output",
        default="data/nfl_qb_season_passing_1950_current.csv",
        help="Output CSV path",
    )
    parser.add_argument("--sleep", type=float, default=8.0, help="Seconds to sleep between requests")
    parser.add_argument("--jitter", type=float, default=2.0, help="Random jitter added to sleeps")
    parser.add_argument("--retries", type=int, default=6, help="Retries per season")
    parser.add_argument(
        "--retry-after",
        type=int,
        default=60,
        help="Seconds to wait after 429 when no Retry-After header is set",
    )
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChartsDataFetcher/1.0"
    })

    frames = []
    for season in range(args.start, args.end + 1):
        try:
            print(f"Fetching {season}...")
            frame = fetch_season_passing(
                season,
                session,
                retries=args.retries,
                retry_after_default=args.retry_after,
                jitter=args.jitter,
            )
            frames.append(frame)
        except Exception as exc:
            print(f"Failed {season}: {exc}")
        base_sleep = max(0.0, args.sleep)
        if base_sleep:
            time.sleep(base_sleep + random.uniform(0.0, args.jitter))

    if not frames:
        print("No data fetched.")
        return 1

    all_data = pd.concat(frames, ignore_index=True)
    all_data.to_csv(out_path, index=False)
    print(f"Saved {len(all_data)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
