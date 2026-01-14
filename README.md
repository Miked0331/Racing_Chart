# Charts Template

This repo is a reusable bar-chart-race template with config-driven rendering for 16:9 and 9:16 layouts.

## Layout

- `charts/` core renderer and shared utilities
- `configs/` chart configs (JSON-compatible YAML)
- `assets/` per-project logos/headshots
- `output/` per-project renders
- `scripts/` helper scripts (downloads, preprocessing)

## Run

```
python main.py --config configs/qb_passing_2025_16x9.yml
python main.py --config configs/qb_passing_2025_shorts.yml
```

## New chart

1) Drop your CSV under the repo root (or a `data/` subfolder).
2) Create per-project icon folders:
   - `assets/team_logos/<project_name>`
   - `assets/headshots/<project_name>`
3) Copy an existing config in `configs/` and update `project_name`, `paths`, and `columns`.
4) Outputs will land in `output/<project_name>` via `paths.output_dir`.
5) Adjust `title`, `metric_label`, and layout settings as needed.

## Notes

- Config files are JSON-compatible YAML. If you want full YAML, install `PyYAML`.
- All paths in `paths` are resolved relative to the repo root.
- `main.py` only needs `--config`; no per-project code changes.

## Config schema (core)

```
project_name: "qb_passing_2025"
paths:
  data_csv: "nfl_qb_passing_weekly_2025_with_headshots.csv"
  team_logo_dir: "assets/team_logos/qb_passing_2025"
  headshot_dir: "assets/headshots/qb_passing_2025"
  output_dir: "output/qb_passing_2025"
```

If you enable cropped headshots, set `assets.headshot_dir` to a per-project folder
like `assets/headshots_cropped/<project_name>`.
