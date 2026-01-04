from __future__ import annotations

from pathlib import Path
import demucs.separate


def separate_stems(wav_path: str | Path) -> None:
    wav_path = Path(wav_path)
    demucs.separate.main([str(wav_path)])
