import os
import math
import time
from collections import deque
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib import font_manager
from PIL import Image, ImageFilter
import requests

# =========================================================
# CONFIG
# =========================================================
CSV_PATH = "nfl_qb_passing_weekly_2025_with_headshots.csv"
OUTPUT_DIR = "output"
OUTPUT_BASENAME = "qb_passing_yards_race_2025_youtube"
RENDER_4K = True
DPI_1080 = 100
DPI_4K = 200
PIXEL_SCALE_4K = 2.0
DPI = DPI_4K if RENDER_4K else DPI_1080
PIXEL_SCALE = PIXEL_SCALE_4K if RENDER_4K else 1.0
OUT_MP4 = os.path.join(
    OUTPUT_DIR,
    f"{OUTPUT_BASENAME}{'_4k' if RENDER_4K else ''}.mp4"
)
STILL_FRAME_IDX = 0
SAVE_STILL = True
STILL_PATH = os.path.join(
    OUTPUT_DIR,
    f"frame_0000{'_4k' if RENDER_4K else ''}.png"
)
SAVE_VIDEO = True

TOP_N = 10
FPS = 60
# DPI configured above
FIGSIZE = (19.2, 10.8)   # 1920x1080

INBETWEEN = 24
HOLD_END_FRAMES = 300
INTRO_HOLD_FRAMES = 60
HOLD_END_FADE_FRAMES = 60

TEAM_LOGO_DIR = "assets/team_logos"
HEADSHOT_SOURCE_DIR = "assets/headshots"
HEADSHOT_DIR = "assets/headshots_cropped"
USE_CROPPED_HEADSHOTS = False
FONT_PATH = "Inter-VariableFont_opsz,wght.ttf"
HEADSHOT_TARGET_PX = 1024
REMOVE_BLACK_BG = True
BLACK_BG_THRESHOLD = 12
REMOVE_WHITE_BG = False
WHITE_BG_THRESHOLD = 245
LOGO_OUTLINE_PX = 0
LOGO_OUTLINE_COLOR = (255, 255, 255, 255)
LOGO_OUTLINE_ALPHA = 140
LOGO_USE_RESIZE = False
LOGO_COMPOSITE_ON_BG = True
SAVE_STILL_1080 = True
STILL_DOWNSCALE_MAX = (1920, 1080)
SHOW_SAFE_ZONES = False

CAMERA_PAN_X = (0.0, 0.04)
CAMERA_ZOOM = (1.02, 1.00)

LEADER_PULSE_FRAMES = 10
NEW_TOP10_FADE_FRAMES = 12
BIG_GAME_BOOST = 1.12

VIDEO_CODEC = "libx264"
VIDEO_CRF = "18"
VIDEO_PRESET = "slow"
VIDEO_PIXEL_FORMAT = "yuv420p"

# =========================================================
# SETUP
# =========================================================
os.makedirs("assets", exist_ok=True)
os.makedirs(TEAM_LOGO_DIR, exist_ok=True)
os.makedirs(HEADSHOT_SOURCE_DIR, exist_ok=True)
os.makedirs(HEADSHOT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

if os.path.exists(FONT_PATH):
    font_manager.fontManager.addfont(FONT_PATH)
    plt.rcParams["font.family"] = "Inter"
else:
    print(f"[WARN] Font not found: {FONT_PATH} using default font.")

print("Font:", plt.rcParams["font.family"])

# Theme
BG = "#0b0f14"
FG = "#e8eef6"
SUB = "#9fb2c7"
GRID = "#2a3340"

TEAM_COLORS = {
    "ARI": "#97233F", "ATL": "#A71930", "BAL": "#241773", "BUF": "#00338D", "CAR": "#0085CA",
    "CHI": "#0B162A", "CIN": "#FB4F14", "CLE": "#311D00", "DAL": "#041E42", "DEN": "#FB4F14",
    "DET": "#0076B6", "GB": "#203731", "HOU": "#03202F", "IND": "#002C5F", "JAX": "#006778",
    "KC": "#E31837", "LAC": "#0080C6", "LAR": "#003594", "LV": "#000000", "MIA": "#008E97",
    "MIN": "#4F2683", "NE": "#002244", "NO": "#D3BC8D", "NYG": "#0B2265", "NYJ": "#125740",
    "PHI": "#004C54", "PIT": "#FFB612", "SEA": "#002244", "SF": "#AA0000", "TB": "#D50A0A",
    "TEN": "#4B92DB", "WAS": "#5A1414"
}

TEAM_LOGO_ALIAS = {
    "LA": "LAR",
}

# =========================================================
# LAYOUT
# =========================================================
BAR_H = 0.62
ROW_SPACING = 1.25
TOP_PAD = 1.15

RANK_X = 0.006
LOGO_X = 0.042
NAME_X = 0.120
RANK_COLOR = "#cbd5e1"
RANK_Z = 5
LOGO_Z = 2
LOGO_PX = int(32 * PIXEL_SCALE)

VALUE_X = 0.915
HEADSHOT_X = 0.965
HEADSHOT_PX = int(40 * PIXEL_SCALE)

TITLE_FS = 26
SUBTITLE_FS = 14
NAME_FS = 15
RANK_FS = 24
VALUE_FS = 16
AXIS_FS = 12

WEEK_BADGE_FS = 18
WEEK_BADGE_FACE = "#1f2937"

TOP3_BAR_H = BAR_H * 1.15
NON_TOP3_ALPHA = 0.55
TOP3_HEADSHOT_SCALE = 1.0

MEDAL_COLORS = {
    1: "#facc15",
    2: "#e5e7eb",
    3: "#cd7f32",
}

# =========================================================
# HELPERS
# =========================================================
def ease_in_out(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


def normalize_team(team: str) -> str:
    if not team or not isinstance(team, str):
        return ""
    return team.strip().upper()


def safe_filename(name: str) -> str:
    return name.replace(" ", "_").replace(".", "").replace("'", "").replace("-", "_")


def crop_to_alpha(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    if bbox is None:
        return img
    x0, y0, x1, y1 = bbox
    return img.crop((x0, y0, x1, y1))


def make_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    s = max(w, h)
    out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    out.paste(img, ((s - w) // 2, (s - h) // 2))
    return out


def resize_and_optimize_png(input_path: str, output_path: str, max_dimensions: tuple[int, int]) -> bool:
    try:
        img = Image.open(input_path).convert("RGBA")
        if hasattr(Image, "Resampling"):
            resample = Image.Resampling.LANCZOS
        else:
            resample = getattr(Image, "LANCZOS", Image.BICUBIC)
        img.thumbnail(max_dimensions, resample)
        img.save(output_path, "PNG", optimize=True)
        print(f"Successfully resized and optimized image: {output_path}")
        print(f"Original size: {os.path.getsize(input_path)} bytes")
        print(f"New size: {os.path.getsize(output_path)} bytes")
        return True
    except IOError as e:
        print(f"Error processing image: {e}")
        return False


def prep_headshot(src_path: str, out_path: str, target_px: int) -> bool:
    try:
        img = Image.open(src_path).convert("RGBA")
        img = crop_to_alpha(img)
        img = make_square(img)
        img = img.resize((target_px, target_px), Image.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.4, percent=120, threshold=3))
        img.save(out_path, "PNG")
        return True
    except Exception:
        return False


def download_headshot(url: str, out_path: str) -> bool:
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


def _load_png_array(path: str, display_px: int, oversample: int):
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


def _load_png_raw(path: str, trim_alpha: bool, composite_on_bg: bool):
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA")
    if REMOVE_BLACK_BG:
        img = remove_near_black_bg(img, BLACK_BG_THRESHOLD)
    if REMOVE_WHITE_BG:
        img = remove_near_white_bg(img, WHITE_BG_THRESHOLD)
    if trim_alpha:
        # Slightly contract alpha to remove fringe artifacts on logos.
        alpha = img.split()[-1].filter(ImageFilter.MinFilter(3))
        img.putalpha(alpha)
        if LOGO_OUTLINE_PX > 0:
            outline_alpha = img.split()[-1].filter(ImageFilter.MaxFilter(LOGO_OUTLINE_PX * 2 + 1))
            outline_color = (
                LOGO_OUTLINE_COLOR[0],
                LOGO_OUTLINE_COLOR[1],
                LOGO_OUTLINE_COLOR[2],
                LOGO_OUTLINE_ALPHA,
            )
            outline = Image.new("RGBA", img.size, outline_color)
            outline.putalpha(outline_alpha)
            img = Image.alpha_composite(outline, img)
    if trim_alpha:
        bbox = img.split()[-1].getbbox()
        if bbox:
            img = img.crop(bbox)
    if composite_on_bg:
        # Composite on BG to avoid dark fringes from straight alpha edges.
        bg = Image.new("RGBA", img.size, BG)
        img = Image.alpha_composite(bg, img)
    return np.asarray(img)


def remove_near_black_bg(img: Image.Image, threshold: int) -> Image.Image:
    arr = np.asarray(img).copy()
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    near_black = (rgb[:, :, 0] < threshold) & (rgb[:, :, 1] < threshold) & (rgb[:, :, 2] < threshold) & (alpha > 0)

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


def remove_near_white_bg(img: Image.Image, threshold: int) -> Image.Image:
    arr = np.asarray(img).copy()
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    near_white = (rgb[:, :, 0] > threshold) & (rgb[:, :, 1] > threshold) & (rgb[:, :, 2] > threshold) & (alpha > 0)

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


# --- caches ---
LOGO_CACHE = {}
HEADSHOT_CACHE = {}
BRAND_CACHE = None
PREPPED_HEADSHOTS = set()

# Use higher oversample for sharper small icons
OVERSAMPLE_LOGO = 2
OVERSAMPLE_HEAD = 1
OVERSAMPLE_BRAND = 2


def get_cached_generic(cache, path: str, display_px: int, oversample: int):
    key = (path, display_px, oversample)
    if key in cache:
        return cache[key]
    arr = _load_png_array(path, display_px, oversample)
    if arr is None:
        return None
    zoom = 1.0
    cache[key] = (arr, zoom)
    return cache[key]


def get_cached_raw(cache, path: str, display_px: int, trim_alpha: bool, composite_on_bg: bool):
    key = (path, display_px, "raw", trim_alpha, composite_on_bg)
    if key in cache:
        return cache[key]
    arr = _load_png_raw(path, trim_alpha, composite_on_bg)
    if arr is None:
        return None
    h, w = arr.shape[:2]
    zoom = float(display_px) / max(w, h)
    cache[key] = (arr, zoom)
    return cache[key]


def get_team_logo(team: str):
    team_norm = normalize_team(team)
    if not team_norm:
        return None
    team_key = TEAM_LOGO_ALIAS.get(team_norm, team_norm)
    p = os.path.join(TEAM_LOGO_DIR, f"{team_key}.png")
    if LOGO_USE_RESIZE:
        return get_cached_generic(LOGO_CACHE, p, LOGO_PX, OVERSAMPLE_LOGO)
    return get_cached_raw(LOGO_CACHE, p, LOGO_PX, True, LOGO_COMPOSITE_ON_BG)


def get_headshot(player: str, head_px: int):
    base_dir = HEADSHOT_DIR if USE_CROPPED_HEADSHOTS else HEADSHOT_SOURCE_DIR
    p = os.path.join(base_dir, safe_filename(player) + ".png")
    if USE_CROPPED_HEADSHOTS:
        return get_cached_generic(HEADSHOT_CACHE, p, head_px, OVERSAMPLE_HEAD)
    return get_cached_raw(HEADSHOT_CACHE, p, head_px, False, True)


def ensure_headshot(player: str):
    if not USE_CROPPED_HEADSHOTS:
        return
    if not player or player in PREPPED_HEADSHOTS:
        return
    PREPPED_HEADSHOTS.add(player)
    name = safe_filename(player) + ".png"
    src_path = os.path.join(HEADSHOT_SOURCE_DIR, name)
    out_path = os.path.join(HEADSHOT_DIR, name)

    if os.path.exists(src_path):
        needs_prep = True
        if os.path.exists(out_path):
            try:
                w, h = Image.open(out_path).size
                if min(w, h) >= HEADSHOT_TARGET_PX:
                    needs_prep = False
            except Exception:
                needs_prep = True
        if needs_prep:
            prep_headshot(src_path, out_path, HEADSHOT_TARGET_PX)
        return

    if (not os.path.exists(out_path)) and (player in headshot_map):
        download_headshot(headshot_map[player], out_path)


def draw_rounded_bar(ax, y_center, width, height, color, alpha=1.0):
    rounding = height * 0.45
    patch = FancyBboxPatch(
        (0, y_center - height / 2),
        float(width),
        float(height),
        boxstyle=f"round,pad=0,rounding_size={rounding}",
        linewidth=0,
        facecolor=color
    )
    patch.set_alpha(alpha)
    ax.add_patch(patch)
    return patch


# =========================================================
# LOAD DATA
# =========================================================
df = pd.read_csv(CSV_PATH)
needed = {"week", "player", "team", "weekly_yards", "cumulative_yards"}
missing = needed - set(df.columns)
if missing:
    raise RuntimeError(f"CSV missing columns: {missing}")

headshot_map = {}
if "headshot_url" in df.columns:
    headshot_map = (
        df.dropna(subset=["headshot_url"])
          .groupby("player")["headshot_url"]
          .last()
          .to_dict()
    )

team_by_player_week = df.set_index(["player", "week"])["team"].to_dict()

pivot = (
    df.pivot_table(index="week", columns="player", values="cumulative_yards", aggfunc="max")
      .fillna(0)
      .sort_index()
)
weeks = pivot.index.to_list()
final_week = weeks[-1]
GLOBAL_XMAX = float(pivot.max().max()) * 1.12

# =========================================================
# EVENT DETECTION
# =========================================================
def get_new_leader_weeks(pivot_df: pd.DataFrame) -> dict[int, str]:
    weeks_local = pivot_df.index.to_list()
    leaders = {}
    prev_leader = None
    for week in weeks_local:
        leader = pivot_df.loc[week].idxmax()
        if prev_leader is not None and leader != prev_leader:
            leaders[int(week)] = leader
        prev_leader = leader
    return leaders


def get_big_game_weeks(source_df: pd.DataFrame, yard_threshold: int = 350) -> dict[tuple[int, str], float]:
    big = {}
    for _, row in source_df.iterrows():
        if row.get("weekly_yards", 0) > yard_threshold:
            big[(int(row["week"]), row["player"])] = float(row["weekly_yards"])
    return big


def get_new_top10_entries(pivot_df: pd.DataFrame, top_n: int = 10) -> dict[int, list[str]]:
    weeks_local = pivot_df.index.to_list()
    new_entries = {}
    prev_top = set()
    for week in weeks_local:
        current_top = set(pivot_df.loc[week].sort_values(ascending=False).head(top_n).index.to_list())
        if prev_top:
            entered = sorted(current_top - prev_top)
            if entered:
                new_entries[int(week)] = entered
        prev_top = current_top
    return new_entries


NEW_LEADERS = get_new_leader_weeks(pivot)
BIG_GAMES = get_big_game_weeks(df)
NEW_TOP10 = get_new_top10_entries(pivot, top_n=TOP_N)

# =========================================================
# BUILD FRAMES
# =========================================================
frames = []


def top_players(week):
    s = pivot.loc[week].sort_values(ascending=False)
    return s.head(TOP_N).index.tolist()


def add_frame(cohort, w_from, w_to, t, phase, label, week):
    frames.append(
        {
            "cohort": cohort,
            "w_from": int(w_from),
            "w_to": int(w_to),
            "t": float(t),
            "phase": phase,
            "label": label,
            "week": int(week),
        }
    )


first_week = int(weeks[0])
intro_cohort = top_players(first_week)
for i in range(INTRO_HOLD_FRAMES):
    add_frame(intro_cohort, first_week, first_week, 0.0, "intro", f"Week {first_week}", first_week)

for w in weeks[:-1]:
    cohort = sorted(set(top_players(w)).union(set(top_players(w + 1))))
    for j in range(INBETWEEN):
        t = ease_in_out(j / INBETWEEN)
        add_frame(cohort, w, w + 1, t, "transition", f"Week {w} -> {w + 1}", w + 1)

final_cohort = top_players(final_week)
add_frame(final_cohort, final_week, final_week, 0.0, "final", f"Week {final_week}", final_week)

effective_hold_end_frames = max(0, HOLD_END_FRAMES - INTRO_HOLD_FRAMES)
hold_end_start_idx = len(frames)
for _ in range(effective_hold_end_frames):
    add_frame(final_cohort, final_week, final_week, 0.0, "hold_end", f"Week {final_week}", final_week)


def frame_to_week(idx: int) -> int:
    return frames[idx]["week"]


WEEK_START_FRAMES = {}
for i, f in enumerate(frames):
    w = f["week"]
    if w not in WEEK_START_FRAMES:
        WEEK_START_FRAMES[w] = i

# =========================================================
# RENDER
# =========================================================
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.patch.set_facecolor(BG)


def update(idx):
    ax.clear()
    ax.set_facecolor(BG)

    frame = frames[idx]
    cohort = frame["cohort"]
    w_from = frame["w_from"]
    w_to = frame["w_to"]
    t = frame["t"]
    phase = frame["phase"]
    frame_week = frame_to_week(idx)
    label = frame["label"]

    a = pivot.loc[w_from][cohort]
    b = pivot.loc[w_to][cohort]
    series = a * (1 - t) + b * t
    if phase == "transition":
        for player in cohort:
            if (frame_week, player) in BIG_GAMES:
                t_boost = min(1.0, t * BIG_GAME_BOOST)
                series[player] = a[player] * (1 - t_boost) + b[player] * t_boost

    s = series.sort_values(ascending=True).tail(TOP_N)
    names = list(s.index)
    vals = s.values
    y = np.arange(len(names)) * ROW_SPACING

    progress = w_to / final_week
    xmax = GLOBAL_XMAX * (0.70 + 0.30 * progress)

    p = idx / max(1, len(frames) - 1)
    pan = CAMERA_PAN_X[0] + (CAMERA_PAN_X[1] - CAMERA_PAN_X[0]) * p
    zoom = CAMERA_ZOOM[0] + (CAMERA_ZOOM[1] - CAMERA_ZOOM[0]) * p
    xmax_zoom = xmax * zoom
    x0 = pan * xmax
    ax.set_xlim(x0, x0 + xmax_zoom)
    ax.set_ylim(-0.85, (len(names) - 1) * ROW_SPACING + TOP_PAD)

    xticks = np.arange(0, int((x0 + xmax_zoom) // 500 + 1) * 500 + 1, 500)
    ax.set_xticks(xticks)
    ax.set_xticklabels([f"{int(v):,}" if v else "0" for v in xticks], color=SUB, fontsize=AXIS_FS)

    ax.xaxis.grid(True, color=GRID, alpha=0.18, linewidth=1)
    ax.yaxis.grid(False)
    ax.tick_params(colors=SUB)
    for spine in ax.spines.values():
        spine.set_visible(False)

    title_alpha = 1.0
    badge_alpha = 1.0
    if phase == "intro":
        intro_p = (idx + 1) / max(1, INTRO_HOLD_FRAMES)
        title_alpha = ease_in_out(min(1.0, intro_p))
        badge_alpha = title_alpha

    # Larger title, lower for mobile readability
    ax.text(
        0.02, 1.005,
        "Top 10 NFL QBs - Cumulative Passing Yards (2025 Regular Season)",
        transform=ax.transAxes,
        color=FG,
        fontsize=TITLE_FS,
        weight="bold",
        ha="left",
        va="bottom",
        alpha=title_alpha
    )

    # Week badge top-right
    ax.text(
        0.98, 0.99,
        label.replace("Week", "WEEK"),
        transform=ax.transAxes,
        va="bottom",
        ha="right",
        color=FG,
        fontsize=WEEK_BADGE_FS,
        weight="bold",
        bbox=dict(
            boxstyle="round,pad=0.40,rounding_size=0.45",
            facecolor=WEEK_BADGE_FACE,
            edgecolor="none",
            alpha=0.95
        ),
        alpha=badge_alpha
    )

    is_final_hold = phase == "hold_end"

    if SHOW_SAFE_ZONES:
        crop_w = (9 / 16) / (16 / 9)
        crop_x = 0.5 - crop_w / 2
        safe_color = "#1b2330"
        ax.add_patch(Rectangle(
            (crop_x, 0.0),
            crop_w,
            1.0,
            transform=ax.transAxes,
            fill=False,
            edgecolor=safe_color,
            linewidth=1.0,
            alpha=0.35,
            zorder=0.1,
        ))
        band_h = 0.15
        ax.add_patch(Rectangle(
            (0.0, 1.0 - band_h),
            1.0,
            band_h,
            transform=ax.transAxes,
            facecolor=safe_color,
            edgecolor="none",
            alpha=0.20,
            zorder=0.1,
        ))
        ax.add_patch(Rectangle(
            (0.0, 0.0),
            1.0,
            band_h,
            transform=ax.transAxes,
            facecolor=safe_color,
            edgecolor="none",
            alpha=0.20,
            zorder=0.1,
        ))


    current_leader = series.idxmax()
    leader_for_week = NEW_LEADERS.get(frame_week)
    week_start_idx = WEEK_START_FRAMES.get(frame_week, 0)
    new_top10_players = set(NEW_TOP10.get(frame_week, []))

    for i, (player, val) in enumerate(zip(names, vals)):
        y_pos = y[i]
        team_raw = team_by_player_week.get((player, w_to), team_by_player_week.get((player, w_from), ""))
        team = normalize_team(team_raw)
        team_logo = TEAM_LOGO_ALIAS.get(team, team)
        color = TEAM_COLORS.get(team_logo, "#5b6470")

        rank = TOP_N - i
        is_top3 = rank <= 3

        bar_h = TOP3_BAR_H if (is_final_hold and is_top3) else BAR_H
        alpha = 1.0
        if is_final_hold and not is_top3:
            hold_idx = max(0, idx - hold_end_start_idx)
            if hold_idx < HOLD_END_FADE_FRAMES:
                fade_p = hold_idx / max(1, HOLD_END_FADE_FRAMES)
                alpha = 1.0 - (1.0 - NON_TOP3_ALPHA) * fade_p
            else:
                alpha = NON_TOP3_ALPHA

        if player in new_top10_players:
            fade_in = min(1.0, max(0.0, (idx - week_start_idx + 1) / max(1, NEW_TOP10_FADE_FRAMES)))
            alpha *= fade_in

        leader_pulse = 1.0
        if leader_for_week == current_leader and player == current_leader:
            pulse_idx = idx - week_start_idx
            if 0 <= pulse_idx < LEADER_PULSE_FRAMES:
                bar_h *= 1.15
                alpha = 1.0
                pulse_t = pulse_idx / max(1, LEADER_PULSE_FRAMES)
                leader_pulse = 1.0 + 0.1 * math.sin(math.pi * min(1.0, pulse_t))

        draw_rounded_bar(ax, y_pos, val, bar_h, color, alpha=alpha).set_zorder(1)

        rank_color = MEDAL_COLORS.get(rank, RANK_COLOR)

        ax.text(
            RANK_X * xmax, y_pos, f"#{rank}",
            va="center", ha="left",
            color=rank_color,
            fontsize=RANK_FS,
            weight="bold",
            alpha=alpha,
            zorder=RANK_Z
        )

        # Team logo (sharper)
        cached_logo = get_team_logo(team_logo)
        if cached_logo is not None:
            arr, zoom = cached_logo
            ab = AnnotationBbox(
                OffsetImage(arr, zoom=zoom, resample=True, interpolation="lanczos"),
                (LOGO_X * xmax, y_pos),
                frameon=False,
                box_alignment=(0, 0.5),
                alpha=alpha
            )
            ab.set_zorder(LOGO_Z)
            ax.add_artist(ab)

        ax.text(
            NAME_X * xmax, y_pos, f"{player}  |  {team_raw or team_logo}",
            va="center", ha="left",
            color=FG,
            fontsize=NAME_FS,
            weight="semibold",
            alpha=alpha
        )

        ax.text(
            VALUE_X * xmax, y_pos, f"{val:,.0f}",
            va="center", ha="right",
            color=FG,
            fontsize=VALUE_FS,
            alpha=alpha
        )

        # Headshot (sharper)
        base_head_px = int(HEADSHOT_PX * TOP3_HEADSHOT_SCALE) if (is_final_hold and is_top3) else HEADSHOT_PX
        head_px = max(1, int(base_head_px * leader_pulse))
        ensure_headshot(player)

        cached_h = get_headshot(player, head_px)
        if cached_h is not None:
            arr, zoom = cached_h
            ax.add_artist(AnnotationBbox(
                OffsetImage(arr, zoom=zoom, resample=True, interpolation="lanczos"),
                (HEADSHOT_X * xmax, y_pos),
                frameon=False,
                box_alignment=(0.5, 0.5),
                alpha=alpha
            ))

    if is_final_hold:
        ax.text(
            0.0, -0.08,
            "FINAL STANDINGS - PASSING YARDS",
            transform=ax.transAxes,
            color=SUB,
            fontsize=SUBTITLE_FS,
            va="top"
        )

    ax.set_yticks(y)
    ax.set_yticklabels([""] * len(names))
    ax.set_xlabel("Yards", color=SUB, fontsize=AXIS_FS, labelpad=10)


def save_still_frame():
    start = time.perf_counter()
    print("Rendering still frame...")
    update(STILL_FRAME_IDX)
    fig.savefig(STILL_PATH, facecolor=BG, dpi=DPI)
    print("Saved still:", STILL_PATH)
    if RENDER_4K and SAVE_STILL_1080:
        still_1080_path = os.path.join(OUTPUT_DIR, "frame_0000_1080.png")
        resize_and_optimize_png(STILL_PATH, still_1080_path, STILL_DOWNSCALE_MAX)
    elapsed = time.perf_counter() - start
    print(f"Still render complete in {elapsed:.2f}s")


def render_video():
    start = time.perf_counter()
    print("Rendering MP4 (requires ffmpeg on PATH)...")
    ani = FuncAnimation(fig, update, frames=len(frames), interval=1000 / FPS)
    ani.save(
        OUT_MP4,
        fps=FPS,
        dpi=DPI,
        codec=VIDEO_CODEC,
        extra_args=[
            "-pix_fmt",
            VIDEO_PIXEL_FORMAT,
            "-crf",
            str(VIDEO_CRF),
            "-preset",
            VIDEO_PRESET,
        ],
    )
    elapsed = time.perf_counter() - start
    print("Saved:", OUT_MP4)
    print(f"Video render complete in {elapsed:.2f}s")


if SAVE_STILL:
    save_still_frame()

if SAVE_VIDEO:
    render_video()
