import os
import pandas as pd

CSV_PATH = "nfl_qb_passing_weekly_2025.csv"
LOGO_DIR = "assets/team_logos"

os.makedirs(LOGO_DIR, exist_ok=True)

df = pd.read_csv(CSV_PATH)

teams = sorted(df["team"].dropna().unique())
print("\nTeams found in CSV:", len(teams))
print(teams)

missing = []
for t in teams:
    if not os.path.exists(os.path.join(LOGO_DIR, f"{t}.png")):
        missing.append(t)

print("\nMissing logo PNGs (put these in assets/team_logos as TEAM.png):")
print(missing)
