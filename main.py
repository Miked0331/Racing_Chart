import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Optional
import pandas as pd

from charts.assets import AssetManager, AssetsConfig
from charts.bar_race import ChartConfig, render_bar_race
from charts.layout import get_layout, get_theme


@dataclass(frozen=True)
class Paths:
    project_name: str
    data_csv: str
    team_logo_dir: str
    headshot_dir: str
    output_dir: str


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        import yaml  # type: ignore
        return yaml.safe_load(raw)
    except Exception:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Config parsing failed. Install PyYAML or use JSON-compatible YAML."
            ) from exc


def resolve_path(root: str, path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(root, path))


def build_paths(cfg: dict, repo_root: str) -> Paths:
    paths_cfg = cfg.get("paths", {}) or {}
    project_name = str(cfg.get("project_name") or "")

    data_csv = paths_cfg.get("data_csv") or cfg.get("csv_path")
    if not data_csv:
        raise RuntimeError("Config is missing paths.data_csv (or legacy csv_path).")

    team_logo_dir = paths_cfg.get("team_logo_dir") or cfg.get("assets", {}).get("team_logo_dir")
    headshot_dir = paths_cfg.get("headshot_dir") or cfg.get("assets", {}).get("headshot_source_dir")
    if not team_logo_dir or not headshot_dir:
        raise RuntimeError("Config is missing paths.team_logo_dir or paths.headshot_dir.")

    output_dir = paths_cfg.get("output_dir") or cfg.get("output_dir")
    if not output_dir:
        output_dir = os.path.join("output", project_name) if project_name else "output"

    return Paths(
        project_name=project_name,
        data_csv=resolve_path(repo_root, data_csv) or "",
        team_logo_dir=resolve_path(repo_root, team_logo_dir) or "",
        headshot_dir=resolve_path(repo_root, headshot_dir) or "",
        output_dir=resolve_path(repo_root, output_dir) or "",
    )


def build_chart_config(cfg: dict, repo_root: str) -> ChartConfig:
    return ChartConfig(
        title=cfg["title"],
        final_subtitle=cfg.get("final_subtitle", ""),
        metric_label=cfg.get("metric_label", ""),
        name_template=cfg.get("name_template", "{player}"),
        layout_mode=cfg["layout_mode"],
        top_n=int(cfg.get("top_n", 10)),
        fps=int(cfg.get("fps", 60)),
        dpi=int(cfg.get("dpi", 100)),
        figsize=tuple(cfg.get("figsize", [19.2, 10.8])),
        inbetween=int(cfg.get("inbetween", 24)),
        intro_hold_frames=int(cfg.get("intro_hold_frames", 60)),
        hold_end_frames=int(cfg.get("hold_end_frames", 300)),
        hold_end_fade_frames=int(cfg.get("hold_end_fade_frames", 60)),
        show_safe_zones=bool(cfg.get("show_safe_zones", False)),
        camera_pan_x=tuple(cfg.get("camera_pan_x", [0.0, 0.04])),
        camera_zoom=tuple(cfg.get("camera_zoom", [1.02, 1.00])),
        leader_pulse_frames=int(cfg.get("leader_pulse_frames", 10)),
        new_top10_fade_frames=int(cfg.get("new_top10_fade_frames", 12)),
        big_game_boost=float(cfg.get("big_game_boost", 1.12)),
        big_game_threshold=float(cfg.get("big_game_threshold", 350)),
        save_still=bool(cfg.get("save_still", False)),
        still_frame_idx=int(cfg.get("still_frame_idx", 0)),
        still_path=resolve_path(repo_root, cfg.get("still_path")),
        still_downscale_max=tuple(cfg.get("still_downscale_max", [])) or None,
        still_downscale_path=resolve_path(repo_root, cfg.get("still_downscale_path")),
        save_video=bool(cfg.get("save_video", True)),
        video_codec=str(cfg.get("video_codec", "libx264")),
        video_crf=str(cfg.get("video_crf", "18")),
        video_preset=str(cfg.get("video_preset", "slow")),
        video_pixel_format=str(cfg.get("video_pixel_format", "yuv420p")),
        font_path=resolve_path(repo_root, cfg.get("font_path")),
        columns=cfg["columns"],
    )


def build_assets_config(cfg: dict, paths: Paths, repo_root: str) -> AssetsConfig:
    headshot_dir = cfg.get("headshot_dir")
    if not headshot_dir:
        if paths.project_name:
            headshot_dir = os.path.join("assets", "headshots_cropped", paths.project_name)
        else:
            headshot_dir = os.path.join("assets", "headshots_cropped")
    return AssetsConfig(
        team_logo_dir=paths.team_logo_dir,
        headshot_source_dir=paths.headshot_dir,
        headshot_dir=resolve_path(repo_root, headshot_dir) or "",
        use_cropped_headshots=bool(cfg.get("use_cropped_headshots", False)),
        headshot_target_px=int(cfg.get("headshot_target_px", 1024)),
        remove_black_bg=bool(cfg.get("remove_black_bg", True)),
        black_bg_threshold=int(cfg.get("black_bg_threshold", 12)),
        remove_white_bg=bool(cfg.get("remove_white_bg", False)),
        white_bg_threshold=int(cfg.get("white_bg_threshold", 245)),
        logo_outline_px=int(cfg.get("logo_outline_px", 0)),
        logo_outline_color=tuple(cfg.get("logo_outline_color", [255, 255, 255, 255])),
        logo_outline_alpha=int(cfg.get("logo_outline_alpha", 140)),
        logo_use_resize=bool(cfg.get("logo_use_resize", False)),
        logo_composite_on_bg=bool(cfg.get("logo_composite_on_bg", True)),
        oversample_logo=int(cfg.get("oversample_logo", 2)),
        oversample_head=int(cfg.get("oversample_head", 1)),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to config YAML/JSON")
    args = parser.parse_args()

    cfg = load_config(args.config)
    repo_root = os.path.dirname(os.path.abspath(__file__))
    paths = build_paths(cfg, repo_root)

    data = pd.read_csv(paths.data_csv)

    theme = get_theme(cfg.get("theme", "dark_nfl"))
    chart_config = build_chart_config(cfg, repo_root)
    layout = get_layout(chart_config.layout_mode, cfg.get("pixel_scale", 1.0))
    assets_cfg = build_assets_config(cfg.get("assets", {}), paths, repo_root)
    assets = AssetManager(assets_cfg, theme.bg, theme.team_aliases)

    output_path = cfg.get("output_path")
    if not output_path:
        output_basename = cfg.get("output_basename") or paths.project_name or "chart"
        output_path = os.path.join(paths.output_dir, f"{output_basename}.mp4")
    output_path = resolve_path(repo_root, output_path) or output_path

    render_bar_race(
        data=data,
        config=chart_config,
        theme=theme,
        layout=layout,
        assets=assets,
        output_path=output_path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
