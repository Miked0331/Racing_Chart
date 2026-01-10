import pandas as pd
import nflreadpy as nfl

YEAR = 2025

player_stats = nfl.load_player_stats([YEAR]).to_pandas()

# Regular season only
reg = player_stats[player_stats["season_type"] == "REG"].copy()

# Ensure numeric
reg["passing_yards"] = pd.to_numeric(reg["passing_yards"], errors="coerce").fillna(0).astype(int)
reg = reg[reg["passing_yards"] > 0].copy()

# Keep only the fields we need (includes headshot_url)
keep_cols = ["season", "week", "player_display_name", "team", "passing_yards", "headshot_url"]
missing = [c for c in keep_cols if c not in reg.columns]
if missing:
    raise RuntimeError(f"Missing columns in nflreadpy output: {missing}")

weekly = reg[keep_cols].copy()

weekly.rename(columns={
    "player_display_name": "player",
    "passing_yards": "weekly_yards"
}, inplace=True)

weekly = weekly.sort_values(["player", "week"])
weekly["cumulative_yards"] = weekly.groupby("player")["weekly_yards"].cumsum()

out = f"nfl_qb_passing_weekly_{YEAR}_with_headshots.csv"
weekly.to_csv(out, index=False)

print("Saved:", out)
print("Columns:", list(weekly.columns))
print("Rows:", len(weekly))