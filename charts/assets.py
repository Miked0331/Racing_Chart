import os
from dataclasses import dataclass
from collections import deque
import numpy as np
from PIL import Image, ImageFilter
import requests


@dataclass(frozen=True)
class AssetsConfig:
    team_logo_dir: str
    headshot_source_dir: str
    headshot_dir: str
    use_cropped_headshots: bool
    headshot_target_px: int
    remove_black_bg: bool
    black_bg_threshold: int
    remove_white_bg: bool
    white_bg_threshold: int
    logo_outline_px: int
    logo_outline_color: tuple
    logo_outline_alpha: int
    logo_use_resize: bool
    logo_composite_on_bg: bool
    oversample_logo: int
    oversample_head: int


class AssetManager:
    def __init__(self, config: AssetsConfig, bg_color: str, team_aliases: dict):
        self.config = config
        self.bg_color = bg_color
        self.team_aliases = team_aliases
        self.logo_cache = {}
        self.headshot_cache = {}
        self.prepped_headshots = set()

    def crop_to_alpha(self, img: Image.Image) -> Image.Image:
        img = img.convert("RGBA")
        alpha = img.split()[-1]
        bbox = alpha.getbbox()
        if bbox is None:
            return img
        x0, y0, x1, y1 = bbox
        return img.crop((x0, y0, x1, y1))

    def make_square(self, img: Image.Image) -> Image.Image:
        w, h = img.size
        s = max(w, h)
        out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        out.paste(img, ((s - w) // 2, (s - h) // 2))
        return out

    def safe_filename(self, name: str) -> str:
        return name.replace(" ", "_").replace(".", "").replace("'", "").replace("-", "_")

    def prep_headshot(self, src_path: str, out_path: str, target_px: int) -> bool:
        try:
            img = Image.open(src_path).convert("RGBA")
            img = self.crop_to_alpha(img)
            img = self.make_square(img)
            img = img.resize((target_px, target_px), Image.LANCZOS)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.4, percent=120, threshold=3))
            img.save(out_path, "PNG")
            return True
        except Exception:
            return False

    def download_headshot(self, url: str, out_path: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        if os.path.exists(out_path):
            return True
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(r.content)
            Image.open(out_path).convert("RGBA")
            return True
        except Exception:
            return False

    def remove_near_black_bg(self, img: Image.Image, threshold: int) -> Image.Image:
        arr = np.asarray(img).copy()
        rgb = arr[:, :, :3]
        alpha = arr[:, :, 3]
        near_black = (
            (rgb[:, :, 0] < threshold)
            & (rgb[:, :, 1] < threshold)
            & (rgb[:, :, 2] < threshold)
            & (alpha > 0)
        )

        h, w = near_black.shape
        visited = np.zeros_like(near_black, dtype=bool)
        q = deque()

        for x in range(w):
            if near_black[0, x]:
                q.append((0, x))
            if near_black[h - 1, x]:
                q.append((h - 1, x))
        for y in range(h):
            if near_black[y, 0]:
                q.append((y, 0))
            if near_black[y, w - 1]:
                q.append((y, w - 1))

        while q:
            y, x = q.popleft()
            if visited[y, x] or not near_black[y, x]:
                continue
            visited[y, x] = True
            if y > 0:
                q.append((y - 1, x))
            if y + 1 < h:
                q.append((y + 1, x))
            if x > 0:
                q.append((y, x - 1))
            if x + 1 < w:
                q.append((y, x + 1))

        arr[visited, 3] = 0
        return Image.fromarray(arr)

    def remove_near_white_bg(self, img: Image.Image, threshold: int) -> Image.Image:
        arr = np.asarray(img).copy()
        rgb = arr[:, :, :3]
        alpha = arr[:, :, 3]
        near_white = (
            (rgb[:, :, 0] > threshold)
            & (rgb[:, :, 1] > threshold)
            & (rgb[:, :, 2] > threshold)
            & (alpha > 0)
        )

        h, w = near_white.shape
        visited = np.zeros_like(near_white, dtype=bool)
        q = deque()

        for x in range(w):
            if near_white[0, x]:
                q.append((0, x))
            if near_white[h - 1, x]:
                q.append((h - 1, x))
        for y in range(h):
            if near_white[y, 0]:
                q.append((y, 0))
            if near_white[y, w - 1]:
                q.append((y, w - 1))

        while q:
            y, x = q.popleft()
            if visited[y, x] or not near_white[y, x]:
                continue
            visited[y, x] = True
            if y > 0:
                q.append((y - 1, x))
            if y + 1 < h:
                q.append((y + 1, x))
            if x > 0:
                q.append((y, x - 1))
            if x + 1 < w:
                q.append((y, x + 1))

        arr[visited, 3] = 0
        return Image.fromarray(arr)

    def _load_png_array(self, path: str, display_px: int, oversample: int):
        if not os.path.exists(path):
            return None
        img = Image.open(path).convert("RGBA")
        w, h = img.size
        target_px = max(1, int(display_px * oversample))
        scale = target_px / max(w, h)
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
        if oversample > 1:
            img = img.resize((display_px, display_px), Image.LANCZOS)
        return np.asarray(img)

    def _load_png_raw(self, path: str, trim_alpha: bool, composite_on_bg: bool):
        if not os.path.exists(path):
            return None
        img = Image.open(path).convert("RGBA")
        if self.config.remove_black_bg:
            img = self.remove_near_black_bg(img, self.config.black_bg_threshold)
        if self.config.remove_white_bg:
            img = self.remove_near_white_bg(img, self.config.white_bg_threshold)
        if trim_alpha:
            alpha = img.split()[-1].filter(ImageFilter.MinFilter(3))
            img.putalpha(alpha)
            if self.config.logo_outline_px > 0:
                outline_alpha = img.split()[-1].filter(ImageFilter.MaxFilter(self.config.logo_outline_px * 2 + 1))
                outline_color = (
                    self.config.logo_outline_color[0],
                    self.config.logo_outline_color[1],
                    self.config.logo_outline_color[2],
                    self.config.logo_outline_alpha,
                )
                outline = Image.new("RGBA", img.size, outline_color)
                outline.putalpha(outline_alpha)
                img = Image.alpha_composite(outline, img)
        if trim_alpha:
            bbox = img.split()[-1].getbbox()
            if bbox:
                img = img.crop(bbox)
        if composite_on_bg:
            bg = Image.new("RGBA", img.size, self.bg_color)
            img = Image.alpha_composite(bg, img)
        return np.asarray(img)

    def get_cached_generic(self, cache, path: str, display_px: int, oversample: int):
        key = (path, display_px, oversample)
        if key in cache:
            return cache[key]
        arr = self._load_png_array(path, display_px, oversample)
        if arr is None:
            return None
        zoom = 1.0
        cache[key] = (arr, zoom)
        return cache[key]

    def get_cached_raw(self, cache, path: str, display_px: int, trim_alpha: bool, composite_on_bg: bool):
        key = (path, display_px, "raw", trim_alpha, composite_on_bg)
        if key in cache:
            return cache[key]
        arr = self._load_png_raw(path, trim_alpha, composite_on_bg)
        if arr is None:
            return None
        h, w = arr.shape[:2]
        zoom = float(display_px) / max(w, h)
        cache[key] = (arr, zoom)
        return cache[key]

    def get_team_logo(self, team: str, logo_px: int):
        team_key = self.team_aliases.get(team, team)
        p = os.path.join(self.config.team_logo_dir, f"{team_key}.png")
        if self.config.logo_use_resize:
            return self.get_cached_generic(self.logo_cache, p, logo_px, self.config.oversample_logo)
        return self.get_cached_raw(self.logo_cache, p, logo_px, True, self.config.logo_composite_on_bg)

    def get_headshot(self, player: str, head_px: int):
        base_dir = self.config.headshot_dir if self.config.use_cropped_headshots else self.config.headshot_source_dir
        p = os.path.join(base_dir, f"{self.safe_filename(player)}.png")
        if self.config.use_cropped_headshots:
            return self.get_cached_generic(self.headshot_cache, p, head_px, self.config.oversample_head)
        return self.get_cached_raw(self.headshot_cache, p, head_px, False, True)

    def ensure_headshot(self, player: str, headshot_map: dict[str, str]):
        if not self.config.use_cropped_headshots:
            return
        if not player or player in self.prepped_headshots:
            return
        self.prepped_headshots.add(player)
        name = f"{self.safe_filename(player)}.png"
        src_path = os.path.join(self.config.headshot_source_dir, name)
        out_path = os.path.join(self.config.headshot_dir, name)

        if os.path.exists(src_path):
            needs_prep = True
            if os.path.exists(out_path):
                try:
                    w, h = Image.open(out_path).size
                    if min(w, h) >= self.config.headshot_target_px:
                        needs_prep = False
                except Exception:
                    needs_prep = True
            if needs_prep:
                self.prep_headshot(src_path, out_path, self.config.headshot_target_px)
            return

        if (not os.path.exists(out_path)) and (player in headshot_map):
            self.download_headshot(headshot_map[player], out_path)
