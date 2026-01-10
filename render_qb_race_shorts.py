import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import FancyBboxPatch
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib import font_manager
from PIL import Image
import requests

# =========================================================
# CONFIG (SHORTS)
# =========================================================
CSV_PATH = "nfl_qb_passing_weekly_2025_with_headshots.csv"
OUT_MP4  = "qb_passing_yards_race_2025_shorts.mp4"

TOP_N = 10
FPS = 60
DPI = 100
FIGSIZE = (10.8, 19.2)   # 1080x1920

INBETWEEN = 22
HOLD_END_FRAMES = 240

TEAM_LOGO_DIR = "assets/team_logos"
HEADSHOT_DIR  = "assets/headshots"
FONT_PATH = "Inter-VariableFont_opsz,wght.ttf"

# =========================================================
# SETUP
# =========================================================
os.makedirs("assets", exist_ok=True)
os.makedirs(TEAM_LOGO_DIR, exist_ok=True)
os.makedirs(HEADSHOT_DIR, exist_ok=True)

if os.path.exists(FONT_PATH):
    font_manager.fontManager.addfont(FONT_PATH)
    plt.rcParams["font.family"] = "Inter"
else:
    print(f"[WARN] Font not found: {FONT_PATH} — using default font.")

print("Font:", plt.rcParams["font.family"])

# Theme
BG   = "#0b0f14"
FG   = "#e8eef6"
SUB  = "#9fb2c7"
GRID = "#2a3340"

TEAM_COLORS = {
    "ARI":"#97233F","ATL":"#A71930","BAL":"#241773","BUF":"#00338D","CAR":"#0085CA",
    "CHI":"#0B162A","CIN":"#FB4F14","CLE":"#311D00","DAL":"#041E42","DEN":"#FB4F14",
    "DET":"#0076B6","GB":"#203731","HOU":"#03202F","IND":"#002C5F","JAX":"#006778",
    "KC":"#E31837","LAC":"#0080C6","LAR":"#003594","LV":"#000000","MIA":"#008E97",
    "MIN":"#4F2683","NE":"#002244","NO":"#D3BC8D","NYG":"#0B2265","NYJ":"#125740",
    "PHI":"#004C54","PIT":"#FFB612","SEA":"#002244","SF":"#AA0000","TB":"#D50A0A",
    "TEN":"#4B92DB","WAS":"#5A1414"
}

# =========================================================
# LAYOUT (SHORTS)
# =========================================================
BAR_H = 0.88

# Left lane (spacing tuned to avoid overlap)
RANK_X = 0.020
LOGO_X = 0.065
NAME_X = 0.125
RANK_COLOR = "#cbd5e1"
LOGO_PX = 34

# Right lane
VALUE_X = 0.86
HEADSHOT_X = 0.93
HEADSHOT_PX = 96

# Typography
TITLE_FS = 32
WEEK_BADGE_FS = 22
NAME_FS = 24
VALUE_FS = 24
AXIS_FS = 18          # ✅ bigger tick labels
SUBTITLE_FS = 18

WEEK_BADGE_FACE = "#1f2937"

# Podium emphasis
TOP3_BAR_H = BAR_H * 1.12
NON_TOP3_ALPHA = 0.55
TOP3_HEADSHOT_SCALE = 1.10

# Medal colors
MEDAL_COLORS = {
    1: "#facc15",  # gold
    2: "#e5e7eb",  # silver
    3: "#cd7f32",  # bronze
}

# =========================================================
# HELPERS
# =========================================================
def ease_in_out(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)

def safe_filename(name: str) -> str:
    return name.replace(" ", "_").replace(".", "").replace("'", "").replace("-", "_")

def load_png(path: str, max_px: int):
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    scale = max_px / max(w, h)
    img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    return np.asarray(img)

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
# BUILD INTERPOLATED FRAMES
# =========================================================
frames = []
frame_labels = []

def top_players(week):
    s = pivot.loc[week].sort_values(ascending=False)
    return s.head(TOP_N).index.tolist()

for w in weeks[:-1]:
    cohort = sorted(set(top_players(w)).union(set(top_players(w + 1))))
    a = pivot.loc[w][cohort]
    b = pivot.loc[w + 1][cohort]

    for j in range(INBETWEEN):
        t = ease_in_out(j / INBETWEEN)
        frames.append((a * (1 - t) + b * t, w, w + 1))
        frame_labels.append(f"Week {w} → {w + 1}")

final_cohort = top_players(final_week)
final_series = pivot.loc[final_week][final_cohort]
frames.append((final_series, final_week, final_week))
frame_labels.append(f"Week {final_week}")

for _ in range(HOLD_END_FRAMES):
    frames.append((final_series, final_week, final_week))
    frame_labels.append(f"Week {final_week}")

# =========================================================
# RENDER
# =========================================================
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.patch.set_facecolor(BG)

def update(idx):
    ax.clear()
    ax.set_facecolor(BG)

    series, w_from, w_to = frames[idx]

    s = series.sort_values(ascending=True).tail(TOP_N)
    names = list(s.index)
    vals = s.values
    y = np.arange(len(names))

    progress = w_to / final_week
    xmax = GLOBAL_XMAX * (0.78 + 0.22 * progress)

    # Reduce left empty space
    ax.set_xlim(0.05 * xmax, xmax)

    # Headroom for title + week badge
    ax.set_ylim(-1.35, len(names) + 1.15)

    ax.xaxis.grid(True, color=GRID, alpha=0.35, linewidth=1)
    ax.yaxis.grid(False)

    # ✅ Make x-axis ticks readable + fewer ticks
    ax.tick_params(axis="x", labelsize=AXIS_FS, colors=SUB)
    ax.tick_params(axis="y", colors=SUB)
    ax.locator_params(axis="x", nbins=5)

    for spine in ax.spines.values():
        spine.set_visible(False)

    # ✅ Centered title (true center)
    ax.text(
        0.5 * xmax,
        len(names) + 0.78,
        "Top 10 NFL QBs — Passing Yards Race (2025)",
        color=FG,
        fontsize=TITLE_FS,
        weight="bold",
        va="bottom",
        ha="center"
    )

    # Week badge centered
    ax.text(
        0.5 * xmax,
        len(names) + 0.25,
        frame_labels[idx].replace("Week", "WEEK"),
        va="bottom",
        ha="center",
        color=FG,
        fontsize=WEEK_BADGE_FS,
        weight="bold",
        bbox=dict(
            boxstyle="round,pad=0.50,rounding_size=0.60",
            facecolor=WEEK_BADGE_FACE,
            edgecolor="none",
            alpha=0.98
        )
    )

    is_final_hold = (
        w_from == final_week
        and w_to == final_week
        and idx >= len(frames) - HOLD_END_FRAMES
    )

    for i, (player, val) in enumerate(zip(names, vals)):
        team = team_by_player_week.get((player, w_to), team_by_player_week.get((player, w_from), ""))
        color = TEAM_COLORS.get(team, "#5b6470")

        rank = TOP_N - i
        is_top3 = rank <= 3

        bar_h = TOP3_BAR_H if (is_final_hold and is_top3) else BAR_H
        alpha = 1.0 if (not is_final_hold or is_top3) else NON_TOP3_ALPHA

        draw_rounded_bar(ax, i, val, bar_h, color, alpha=alpha)

        # Rank (top 3 pop at end)
        rank_color = MEDAL_COLORS.get(rank, RANK_COLOR)
        rank_fs = NAME_FS + 4 if (is_final_hold and is_top3) else NAME_FS

        ax.text(
            RANK_X * xmax, i, f"#{rank}",
            va="center", ha="left",
            color=rank_color,
            fontsize=rank_fs,
            weight="bold",
            alpha=alpha
        )

        # Logo
        logo = load_png(os.path.join(TEAM_LOGO_DIR, f"{team}.png"), max_px=LOGO_PX) if team else None
        if logo is not None:
            ax.add_artist(AnnotationBbox(
                OffsetImage(logo, zoom=1),
                (LOGO_X * xmax, i),
                frameon=False,
                box_alignment=(0, 0.5),
                alpha=alpha
            ))

        # Name
        ax.text(
            NAME_X * xmax, i, f"{player}  •  {team}",
            va="center", ha="left",
            color=FG,
            fontsize=NAME_FS,
            weight="semibold",
            alpha=alpha
        )

        # Value
        ax.text(
            VALUE_X * xmax, i, f"{val:,.0f}",
            va="center", ha="right",
            color=FG,
            fontsize=VALUE_FS,
            alpha=alpha
        )

        # Headshot
        head_px = int(HEADSHOT_PX * TOP3_HEADSHOT_SCALE) if (is_final_hold and is_top3) else HEADSHOT_PX
        headshot_path = os.path.join(HEADSHOT_DIR, safe_filename(player) + ".png")
        if (not os.path.exists(headshot_path)) and (player in headshot_map):
            download_headshot(headshot_map[player], headshot_path)

        head = load_png(headshot_path, max_px=head_px)
        if head is not None:
            ax.add_artist(AnnotationBbox(
                OffsetImage(head, zoom=1),
                (HEADSHOT_X * xmax, i),
                frameon=False,
                box_alignment=(0.5, 0.5),
                alpha=alpha
            ))

    if is_final_hold:
        ax.text(
            0.05 * xmax,
            -1.05,
            "FINAL PASSING YARDS LEADERS",
            color=SUB,
            fontsize=SUBTITLE_FS,
            va="top"
        )

    ax.set_yticks(y)
    ax.set_yticklabels([""] * len(names))
    ax.set_xlabel("Yards", color=SUB, fontsize=AXIS_FS, labelpad=10)

ani = FuncAnimation(fig, update, frames=len(frames), interval=1000 / FPS)

print("Rendering MP4… (requires ffmpeg on PATH)")
ani.save(OUT_MP4, fps=FPS, dpi=DPI)
print("Saved:", OUT_MP4)
