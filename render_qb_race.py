import sys
from main import main


if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--config", "configs/qb_passing_2025_16x9.yml"]
    raise SystemExit(main())
