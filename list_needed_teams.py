import pandas as pd

df = pd.read_csv("nfl_qb_passing_weekly_2025.csv")
teams = sorted(df["team"].dropna().unique())
print("Teams in dataset:", len(teams))
print(teams)
