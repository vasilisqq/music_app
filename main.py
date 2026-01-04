from __future__ import annotations

import config  # noqa: F401  (side effects: torch hub dir + sys.path for basic_pitch_torch)

from pipeline import run_default_paths


def main() -> None:
    run_default_paths()


if __name__ == "__main__":
    main()
