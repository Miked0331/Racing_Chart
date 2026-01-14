import os
from io import BytesIO

import requests
from PIL import Image

OUT_DIR = "assets/team_logos"
RAW_DIR = "assets/team_logos_raw"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

# ESPN team logo slugs (most are just lowercased abbreviations).
TEAM_SLUG = {
    "ARI": "ari",
    "ATL": "atl",
    "BAL": "bal",
    "BUF": "buf",
    "CAR": "car",
    "CHI": "chi",
    "CIN": "cin",
    "CLE": "cle",
    "DAL": "dal",
    "DEN": "den",
    "DET": "det",
    "GB": "gb",
    "HOU": "hou",
    "IND": "ind",
    "JAX": "jax",
    "KC": "kc",
    "LAC": "lac",
    "LAR": "lar",
    "LV": "lv",
    "MIA": "mia",
    "MIN": "min",
    "NE": "ne",
    "NO": "no",
    "NYG": "nyg",
    "NYJ": "nyj",
    "PHI": "phi",
    "PIT": "pit",
    "SEA": "sea",
    "SF": "sf",
    "TB": "tb",
    "TEN": "ten",
    "WAS": "was",
}

LOGO_SIZE = 512
FORCE = False
MIN_BYTES = 20000
BASE_URL = "https://a.espncdn.com/i/teamlogos/nfl/500/{slug}.png"

downloaded = 0
for team, slug in TEAM_SLUG.items():
    out_path = os.path.join(OUT_DIR, f"{team}.png")
    if os.path.exists(out_path) and not FORCE:
        if os.path.getsize(out_path) >= MIN_BYTES:
            continue

    url = BASE_URL.format(slug=slug)
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        raw_path = os.path.join(RAW_DIR, f"{team}.png")
        with open(raw_path, "wb") as f:
            f.write(r.content)

        img = Image.open(BytesIO(r.content)).convert("RGBA")
        img = img.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
        img.save(out_path, "PNG")
        downloaded += 1
        print("Downloaded:", team, url)
    except Exception as e:
        print("Failed:", team, url, e)

print(f"\nDone. Downloaded {downloaded} team logos.")
