import os
import pandas as pd
import requests
from PIL import Image

CSV_PATH = "nfl_qb_passing_weekly_2025_with_headshots.csv"
OUT_DIR = "assets/headshots"

os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(CSV_PATH)

if "headshot_url" not in df.columns:
    raise RuntimeError("CSV does not contain headshot_url column")

players = (
    df[["player", "headshot_url"]]
    .dropna()
    .drop_duplicates()
)

def safe_name(name):
    return name.replace(" ", "_").replace(".", "").replace("'", "").replace("-", "_")

downloaded = 0
for _, row in players.iterrows():
    name = safe_name(row["player"])
    url = row["headshot_url"]
    out_path = os.path.join(OUT_DIR, f"{name}.png")

    if os.path.exists(out_path):
        continue

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r.content)

        Image.open(out_path).convert("RGBA")
        downloaded += 1
        print("Downloaded:", name)
    except Exception as e:
        print("Failed:", name, e)

print(f"\nDone. Downloaded {downloaded} headshots.")
