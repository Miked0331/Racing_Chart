import os
from PIL import Image

IN_DIR = "assets/headshots"
OUT_DIR = "assets/headshots_cropped"
os.makedirs(OUT_DIR, exist_ok=True)

MARGIN = 20          # pixels padding around detected non-transparent area
TARGET = 512         # final square size (higher = sharper)

def crop_to_alpha(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    if bbox is None:
        return img
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - MARGIN)
    y0 = max(0, y0 - MARGIN)
    x1 = min(img.width, x1 + MARGIN)
    y1 = min(img.height, y1 + MARGIN)
    return img.crop((x0, y0, x1, y1))

def make_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    s = max(w, h)
    out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    out.paste(img, ((s - w)//2, (s - h)//2))
    return out

for fn in os.listdir(IN_DIR):
    if not fn.lower().endswith(".png"):
        continue
    p = os.path.join(IN_DIR, fn)
    img = Image.open(p)
    img = crop_to_alpha(img)
    img = make_square(img)
    img = img.resize((TARGET, TARGET), Image.LANCZOS)
    img.save(os.path.join(OUT_DIR, fn), "PNG")

print("Done. Cropped headshots saved to:", OUT_DIR)
