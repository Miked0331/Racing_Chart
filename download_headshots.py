import os
import pandas as pd
import requests
from io import BytesIO
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

def upgrade_headshot_url(url: str) -> str:
    if "/image/upload/" not in url:
        return url
    base, remainder = url.split("/image/upload/", 1)
    if "/" in remainder:
        _, remainder = remainder.split("/", 1)
    transform = "f_png,q_100,w_1024,c_fit"
    return f"{base}/image/upload/{transform}/{remainder}"

downloaded = 0
for _, row in players.iterrows():
    name = safe_name(row["player"])
    url = upgrade_headshot_url(row["headshot_url"])
    out_path = os.path.join(OUT_DIR, f"{name}.png")

    if os.path.exists(out_path):
        continue

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        img.save(out_path, "PNG")
        downloaded += 1
        print("Downloaded:", name)
    except Exception as e:
        print("Failed:", name, e)

print(f"\nDone. Downloaded {downloaded} headshots.")
