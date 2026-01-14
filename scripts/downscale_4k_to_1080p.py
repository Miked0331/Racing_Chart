import argparse
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Downscale a 4K master to 1080p using ffmpeg.")
    parser.add_argument(
        "--input",
        default="output/qb_passing_yards_race_2025_youtube_4k.mp4",
        help="Path to 4K input MP4",
    )
    parser.add_argument(
        "--output",
        default="output/qb_passing_yards_race_2025_youtube_1080p.mp4",
        help="Path to 1080p output MP4",
    )
    parser.add_argument("--crf", default="18", help="H.264 CRF value (lower = higher quality)")
    parser.add_argument("--preset", default="slow", help="H.264 preset")
    args = parser.parse_args()

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        args.input,
        "-vf",
        "scale=1920:1080:flags=lanczos",
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        args.preset,
        "-pix_fmt",
        "yuv420p",
        args.output,
    ]

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("ffmpeg not found on PATH. Install ffmpeg and retry.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"ffmpeg failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
