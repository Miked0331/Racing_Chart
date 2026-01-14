import pandas as pd
import nflreadpy as nfl

YEAR = 2025

# nflreadpy returns Polars DF by default
player_stats = nfl.load_player_stats([YEAR]).to_pandas()

# Columns can vary slightly by release; print columns once if needed:
# print(player_stats.columns)

# Filter regular season + QBs (position naming can be "QB" or inferred from passing attempts)
# Most releases include: season_type, week, player_display_name, recent_team, passing_yards
reg = player_stats[player_stats["season_type"] == "REG"].copy()

# Keep rows where passing_yards exists (covers QBs)
reg["passing_yards"] = pd.to_numeric(reg["passing_yards"], errors="coerce").fillna(0).astype(int)
reg = reg[reg["passing_yards"] > 0].copy()

# Build weekly table
TEAM_COL = next(
    c for c in ["recent_team", "team", "team_abbr", "posteam", "club"]
    if c in reg.columns
)

weekly = reg[[
    "season",
    "week",
    "player_display_name",
    TEAM_COL,
    "passing_yards"
]].copy()

weekly.rename(columns={TEAM_COL: "team"}, inplace=True)

weekly.rename(columns={
    "player_display_name": "player",
    "recent_team": "team",
    "passing_yards": "weekly_yards"
}, inplace=True)

weekly = weekly[weekly["season"] == YEAR].copy()
weekly = weekly.sort_values(["player", "week"])
weekly["cumulative_yards"] = weekly.groupby("player")["weekly_yards"].cumsum()

out = f"nfl_qb_passing_weekly_{YEAR}.csv"
weekly.to_csv(out, index=False)
print("Saved:", out)
print("Weeks:", weekly["week"].min(), "→", weekly["week"].max())
print("Rows:", len(weekly))


print(player_stats.columns.tolist())
