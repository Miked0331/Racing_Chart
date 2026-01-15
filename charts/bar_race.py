import os
import math
import time
from dataclasses import dataclass
from typing import Any, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib import font_manager
from PIL import Image

from charts.assets import AssetManager, AssetsConfig
from charts.layout import Layout, Theme, ease_in_out


@dataclass(frozen=True)
class ChartConfig:
    title: str
    final_subtitle: str
    metric_label: str
    name_template: str
    layout_mode: str
    top_n: int
    fps: int
    dpi: int
    figsize: tuple[float, float]
    inbetween: int
    intro_hold_frames: int
    hold_end_frames: int
    hold_end_fade_frames: int
    show_safe_zones: bool
    camera_pan_x: tuple[float, float]
    camera_zoom: tuple[float, float]
    leader_pulse_frames: int
    new_top10_fade_frames: int
    big_game_boost: float
    big_game_threshold: float
    save_still: bool
    still_frame_idx: int
    still_path: Optional[str]
    still_downscale_max: Optional[tuple[int, int]]
    still_downscale_path: Optional[str]
    save_video: bool
    video_codec: str
    video_crf: str
    video_preset: str
    video_pixel_format: str
    font_path: Optional[str]
    columns: dict


def normalize_team(team: str) -> str:
    if not team or not isinstance(team, str):
        return ""
    return team.strip().upper()


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


def get_big_game_weeks(source_df: pd.DataFrame, yard_threshold: float, col_week: str, col_player: str, col_weekly: str):
    big = {}
    if col_weekly not in source_df.columns:
        return big
    for _, row in source_df.iterrows():
        if row.get(col_weekly, 0) > yard_threshold:
            big[(int(row[col_week]), row[col_player])] = float(row[col_weekly])
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


def draw_rounded_bar(ax, y_center, width, height, color, alpha=1.0):
    rounding = height * 0.45
    patch = FancyBboxPatch(
        (0, y_center - height / 2),
        float(width),
        float(height),
        boxstyle=f"round,pad=0,rounding_size={rounding}",
        linewidth=0,
        facecolor=color,
    )
    patch.set_alpha(alpha)
    ax.add_patch(patch)
    return patch


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


def build_frames(pivot: pd.DataFrame, top_n: int, inbetween: int, intro_hold_frames: int, hold_end_frames: int):
    frames = []
    weeks = pivot.index.to_list()
    final_week = weeks[-1]

    def top_players(week):
        s = pivot.loc[week].sort_values(ascending=False)
        return s.head(top_n).index.tolist()

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
    for _ in range(intro_hold_frames):
        add_frame(intro_cohort, first_week, first_week, 0.0, "intro", f"Week {first_week}", first_week)

    for w in weeks[:-1]:
        cohort = sorted(set(top_players(w)).union(set(top_players(w + 1))))
        for j in range(inbetween):
            t = ease_in_out(j / inbetween)
            add_frame(cohort, w, w + 1, t, "transition", f"Week {w} -> {w + 1}", w + 1)

    final_cohort = top_players(final_week)
    add_frame(final_cohort, final_week, final_week, 0.0, "final", f"Week {final_week}", final_week)

    effective_hold = max(0, hold_end_frames - intro_hold_frames)
    hold_end_start_idx = len(frames)
    for _ in range(effective_hold):
        add_frame(final_cohort, final_week, final_week, 0.0, "hold_end", f"Week {final_week}", final_week)

    week_start_frames = {}
    for i, f in enumerate(frames):
        w = f["week"]
        if w not in week_start_frames:
            week_start_frames[w] = i

    return frames, hold_end_start_idx, week_start_frames


def render_bar_race(
    data: pd.DataFrame,
    config: ChartConfig,
    theme: Theme,
    layout: Layout,
    assets: AssetManager,
    output_path: str,
):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if config.font_path and os.path.exists(config.font_path):
        font_manager.fontManager.addfont(config.font_path)
        plt.rcParams["font.family"] = "Inter"

    col_time = config.columns["time"]
    col_entity = config.columns["entity"]
    col_group = config.columns.get("group")
    col_value = config.columns["value"]
    col_weekly = config.columns.get("weekly_value", "")
    col_headshot = config.columns.get("headshot_url", "")

    headshot_map = {}
    if col_headshot and col_headshot in data.columns:
        headshot_map = (
            data.dropna(subset=[col_headshot])
                .groupby(col_entity)[col_headshot]
                .last()
                .to_dict()
        )

    team_by_entity_week = {}
    if col_group:
        team_by_entity_week = data.set_index([col_entity, col_time])[col_group].to_dict()

    pivot = (
        data.pivot_table(index=col_time, columns=col_entity, values=col_value, aggfunc="max")
            .fillna(0)
            .sort_index()
    )

    weeks = pivot.index.to_list()
    final_week = weeks[-1]
    global_xmax = float(pivot.max().max()) * 1.12

    new_leaders = get_new_leader_weeks(pivot)
    big_games = get_big_game_weeks(data, config.big_game_threshold, col_time, col_entity, col_weekly)
    new_top10 = get_new_top10_entries(pivot, top_n=config.top_n)

    frames, hold_end_start_idx, week_start_frames = build_frames(
        pivot,
        config.top_n,
        config.inbetween,
        config.intro_hold_frames,
        config.hold_end_frames,
    )

    def frame_to_week(idx: int) -> int:
        return frames[idx]["week"]

    fig, ax = plt.subplots(figsize=config.figsize, dpi=config.dpi)
    fig.subplots_adjust(bottom=0.16)
    fig.patch.set_facecolor(theme.bg)

    def update(idx):
        ax.clear()
        ax.set_facecolor(theme.bg)

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
                if (frame_week, player) in big_games:
                    t_boost = min(1.0, t * config.big_game_boost)
                    series[player] = a[player] * (1 - t_boost) + b[player] * t_boost

        s = series.sort_values(ascending=True).tail(config.top_n)
        names = list(s.index)
        vals = s.values
        def y_for_rank(rank_idx: int) -> float:
            return rank_idx * layout.row_spacing

        y = np.array([y_for_rank(i) for i in range(len(names))])

        progress = w_to / final_week
        xmax = global_xmax * (layout.xmax_progress_min + layout.xmax_progress_max * progress)
        base_x0 = layout.base_x0_ratio * xmax
        base_width = xmax - base_x0

        p = idx / max(1, len(frames) - 1)
        pan = config.camera_pan_x[0] + (config.camera_pan_x[1] - config.camera_pan_x[0]) * p
        zoom = config.camera_zoom[0] + (config.camera_zoom[1] - config.camera_zoom[0]) * p
        x0 = base_x0 + pan * xmax
        x1 = x0 + base_width * zoom

        ax.set_xlim(x0, x1)
        ax.set_ylim(-0.85, (len(names) - 1) * layout.row_spacing + layout.top_pad)

        major_step = 10000
        max_tick = int(x1 // major_step + 1) * major_step
        xticks = np.arange(0, max_tick + 1, major_step)
        ax.set_xticks(xticks)
        ax.set_xticklabels(
            ["0" if v == 0 else f"{int(v / 1000)}k" for v in xticks],
            color=theme.sub,
            fontsize=layout.axis_fs + 2,
        )

        ax.xaxis.grid(True, color=theme.grid, alpha=0.35, linewidth=1)
        ax.yaxis.grid(False)
        ax.tick_params(axis="x", labelsize=layout.axis_fs + 2, colors=theme.sub, pad=-12)
        ax.tick_params(axis="y", colors=theme.sub)

        for spine in ax.spines.values():
            spine.set_visible(False)

        title_alpha = 1.0
        badge_alpha = 1.0
        if phase == "intro":
            intro_p = (idx + 1) / max(1, config.intro_hold_frames)
            title_alpha = ease_in_out(min(1.0, intro_p))
            badge_alpha = title_alpha

        ax.text(
            layout.title_pos[0],
            layout.title_pos[1],
            config.title,
            transform=ax.transAxes if layout.use_axes_text else None,
            color=theme.fg,
            fontsize=layout.title_fs,
            weight="bold",
            ha=layout.title_ha,
            va=layout.title_va,
            alpha=title_alpha,
        )

        ax.text(
            layout.badge_pos[0],
            layout.badge_pos[1],
            f"YEAR {frame_week}",
            transform=ax.transAxes if layout.use_axes_text else None,
            va=layout.badge_va,
            ha=layout.badge_ha,
            color=theme.fg,
            fontsize=layout.week_badge_fs,
            weight="bold",
            bbox=dict(
                boxstyle="round,pad=0.50,rounding_size=0.60",
                facecolor=theme.week_badge_face,
                edgecolor="none",
                alpha=0.98,
            ),
            alpha=badge_alpha,
        )

        is_final_hold = phase == "hold_end"

        if config.show_safe_zones:
            crop_w = 0.90
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
        leader_for_week = new_leaders.get(frame_week)
        week_start_idx = week_start_frames.get(frame_week, 0)
        new_top10_players = set(new_top10.get(frame_week, []))

        for i, (player, val) in enumerate(zip(names, vals)):
            y_pos = y[i]
            team_raw = team_by_entity_week.get((player, w_to), team_by_entity_week.get((player, w_from), "")) if col_group else ""
            team = normalize_team(team_raw)
            team_logo = theme.team_aliases.get(team, team)
            color = theme.team_colors.get(team_logo, "#5b6470")

            rank = config.top_n - i
            is_top3 = rank <= 3

            bar_h = layout.top3_bar_h if (is_final_hold and is_top3) else layout.bar_h
            alpha = 1.0
            if is_final_hold and not is_top3:
                hold_idx = max(0, idx - hold_end_start_idx)
                if hold_idx < config.hold_end_fade_frames:
                    fade_p = hold_idx / max(1, config.hold_end_fade_frames)
                    alpha = 1.0 - (1.0 - layout.non_top3_alpha) * fade_p
                else:
                    alpha = layout.non_top3_alpha

            if player in new_top10_players:
                fade_in = min(1.0, max(0.0, (idx - week_start_idx + 1) / max(1, config.new_top10_fade_frames)))
                alpha *= fade_in

            leader_pulse = 1.0
            if leader_for_week == current_leader and player == current_leader:
                pulse_idx = idx - week_start_idx
                if 0 <= pulse_idx < config.leader_pulse_frames:
                    bar_h *= 1.15
                    alpha = 1.0
                    pulse_t = pulse_idx / max(1, config.leader_pulse_frames)
                    leader_pulse = 1.0 + 0.1 * math.sin(math.pi * min(1.0, pulse_t))

            draw_rounded_bar(ax, y_pos, val, bar_h, color, alpha=alpha).set_zorder(1)

            rank_color = theme.medal_colors.get(rank, theme.rank_color)
            rank_fs = layout.rank_fs_top3 if (is_final_hold and is_top3) else layout.rank_fs

            ax.text(
                layout.rank_x * xmax, y_pos, f"#{rank}",
                va="center", ha="left",
                color=rank_color,
                fontsize=rank_fs,
                weight="bold",
                alpha=alpha,
                zorder=5,
            )

            cached_logo = assets.get_team_logo(team_logo, layout.logo_px)
            if cached_logo is not None:
                arr, zoom = cached_logo
                ab = AnnotationBbox(
                    OffsetImage(arr, zoom=zoom, resample=True, interpolation="lanczos"),
                    (layout.logo_x * xmax, y_pos),
                    frameon=False,
                    box_alignment=(0, 0.5),
                    alpha=alpha,
                )
                ab.set_zorder(2)
                ax.add_artist(ab)

            name_pad = 0.01 * xmax
            max_name_x = (layout.value_x - 0.03) * xmax
            name_x = min(val + name_pad, max_name_x)

            ax.text(
                name_x, y_pos,
                config.name_template.format(player=player, team=team_raw or team_logo),
                va="center", ha="left",
                color=theme.fg,
                fontsize=layout.name_fs,
                weight="semibold",
                alpha=alpha,
            )

            ax.text(
                layout.value_x * xmax, y_pos, f"{val:,.0f}",
                va="center", ha="right",
                color=theme.fg,
                fontsize=layout.value_fs,
                alpha=alpha,
            )

            base_head_px = int(layout.headshot_px * layout.top3_headshot_scale) if (is_final_hold and is_top3) else layout.headshot_px
            head_px = max(1, int(base_head_px * leader_pulse))
            assets.ensure_headshot(player, headshot_map)

            cached_h = assets.get_headshot(player, head_px)
            if cached_h is None:
                cached_h = assets.get_team_logo(team_logo, head_px)
            if cached_h is not None:
                arr, zoom = cached_h
                ax.add_artist(AnnotationBbox(
                    OffsetImage(arr, zoom=zoom, resample=True, interpolation="lanczos"),
                    (layout.headshot_x * xmax, y_pos),
                    frameon=False,
                    box_alignment=(0.5, 0.5),
                    alpha=alpha,
                ))

        if is_final_hold and config.final_subtitle:
            ax.text(
                layout.final_subtitle_pos[0],
                layout.final_subtitle_pos[1],
                config.final_subtitle,
                transform=ax.transAxes if layout.use_axes_text else None,
                color=theme.sub,
                fontsize=layout.subtitle_fs,
                va="top",
                ha="center" if layout.final_subtitle_pos[0] == 0.5 else "left",
            )

        ax.set_yticks(y)
        ax.set_yticklabels([""] * len(names))
        ax.set_xlabel(config.metric_label, color=theme.sub, fontsize=layout.axis_fs + 2, labelpad=-6)

    def save_still_frame():
        if not config.still_path:
            return
        start = time.perf_counter()
        print("Rendering still frame...")
        update(config.still_frame_idx)
        fig.savefig(config.still_path, facecolor=theme.bg, dpi=config.dpi)
        if config.still_downscale_max and config.still_downscale_path:
            resize_and_optimize_png(config.still_path, config.still_downscale_path, config.still_downscale_max)
        elapsed = time.perf_counter() - start
        print("Saved still:", config.still_path)
        print(f"Still render complete in {elapsed:.2f}s")

    def render_video():
        start = time.perf_counter()
        print("Rendering MP4 (requires ffmpeg on PATH)...")
        ani = FuncAnimation(fig, update, frames=len(frames), interval=1000 / config.fps)
        ani.save(
            output_path,
            fps=config.fps,
            dpi=config.dpi,
            codec=config.video_codec,
            extra_args=[
                "-pix_fmt", config.video_pixel_format,
                "-crf", str(config.video_crf),
                "-preset", config.video_preset,
            ],
        )
        elapsed = time.perf_counter() - start
        print("Saved:", output_path)
        print(f"Video render complete in {elapsed:.2f}s")

    if config.save_still:
        save_still_frame()
    if config.save_video:
        render_video()
