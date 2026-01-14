import math
from dataclasses import dataclass

from charts.themes import nfl_theme


@dataclass(frozen=True)
class Theme:
    bg: str
    fg: str
    sub: str
    grid: str
    week_badge_face: str
    rank_color: str
    medal_colors: dict
    team_colors: dict
    team_aliases: dict


@dataclass(frozen=True)
class Layout:
    bar_h: float
    row_spacing: float
    top_pad: float
    rank_x: float
    logo_x: float
    name_x: float
    value_x: float
    headshot_x: float
    logo_px: int
    headshot_px: int
    title_fs: int
    week_badge_fs: int
    name_fs: int
    value_fs: int
    axis_fs: int
    subtitle_fs: int
    rank_fs: int
    rank_fs_top3: int
    title_pos: tuple[float, float]
    title_ha: str
    title_va: str
    badge_pos: tuple[float, float]
    badge_ha: str
    badge_va: str
    final_subtitle_pos: tuple[float, float]
    use_axes_text: bool
    top3_bar_h: float
    non_top3_alpha: float
    top3_headshot_scale: float
    base_x0_ratio: float
    xmax_progress_min: float
    xmax_progress_max: float


def ease_in_out(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


def get_theme(name: str) -> Theme:
    if name != "dark_nfl":
        raise ValueError(f"Unknown theme: {name}")

    return Theme(
        bg="#0b0f14",
        fg="#e8eef6",
        sub="#9fb2c7",
        grid="#2a3340",
        week_badge_face="#1f2937",
        rank_color="#cbd5e1",
        medal_colors={1: "#facc15", 2: "#e5e7eb", 3: "#cd7f32"},
        team_colors=nfl_theme.TEAM_COLORS,
        team_aliases=nfl_theme.TEAM_ALIASES,
    )


def get_layout(mode: str, pixel_scale: float) -> Layout:
    if mode == "horizontal_16x9":
        return Layout(
            bar_h=0.62,
            row_spacing=1.25,
            top_pad=1.15,
            rank_x=0.006,
            logo_x=0.042,
            name_x=0.120,
            value_x=0.915,
            headshot_x=0.965,
            logo_px=int(32 * pixel_scale),
            headshot_px=int(40 * pixel_scale),
            title_fs=26,
            week_badge_fs=18,
            name_fs=15,
            value_fs=16,
            axis_fs=12,
            subtitle_fs=14,
            rank_fs=24,
            rank_fs_top3=24,
            title_pos=(0.02, 1.005),
            title_ha="left",
            title_va="bottom",
            badge_pos=(0.98, 0.99),
            badge_ha="right",
            badge_va="bottom",
            final_subtitle_pos=(0.0, -0.08),
            use_axes_text=True,
            top3_bar_h=0.62 * 1.15,
            non_top3_alpha=0.55,
            top3_headshot_scale=1.0,
            base_x0_ratio=0.0,
            xmax_progress_min=0.70,
            xmax_progress_max=0.30,
        )

    if mode == "vertical_9x16":
        return Layout(
            bar_h=0.72,
            row_spacing=1.05,
            top_pad=1.6,
            rank_x=0.020,
            logo_x=0.085,
            name_x=0.170,
            value_x=0.80,
            headshot_x=0.92,
            logo_px=int(44 * pixel_scale),
            headshot_px=int(96 * pixel_scale),
            title_fs=32,
            week_badge_fs=22,
            name_fs=24,
            value_fs=22,
            axis_fs=18,
            subtitle_fs=18,
            rank_fs=24,
            rank_fs_top3=28,
            title_pos=(0.5, 0.985),
            title_ha="center",
            title_va="top",
            badge_pos=(0.5, 0.94),
            badge_ha="center",
            badge_va="top",
            final_subtitle_pos=(0.5, 0.03),
            use_axes_text=True,
            top3_bar_h=0.72 * 1.12,
            non_top3_alpha=0.55,
            top3_headshot_scale=1.10,
            base_x0_ratio=0.05,
            xmax_progress_min=0.78,
            xmax_progress_max=0.22,
        )

    raise ValueError(f"Unknown layout mode: {mode}")
