from __future__ import annotations

from pathlib import Path
from pydub import AudioSegment

from config import ROOT


def convert_to_wav(mp3_path: str | Path, out_wav: str | Path = "output.wav") -> Path:
    mp3_path = Path(mp3_path)
    out_wav = (ROOT / out_wav).resolve()
    audio = AudioSegment.from_mp3(str(mp3_path))
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    audio.export(str(out_wav), format="wav")
    return out_wav
