from __future__ import annotations

import config  # noqa: F401

from pipeline import run_from_local_file


def main() -> None:
    # Файл должен лежать рядом с этим main.py
    run_from_local_file("input.mp3", always_reseparate=False)


if __name__ == "__main__":
    main()
