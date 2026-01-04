from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from config import BP_REPO_ROOT

# imported after sys.path hack in config.py
from basic_pitch_torch.inference import predict


@dataclass(frozen=True)
class BasicPitchParams:
    onset_threshold: float = 0.45
    frame_threshold: float = 0.25
    minimum_note_length: float = 60.0  # frames (BP default is around 127.70 in spotify/basic-pitch) [web:8]


def stem_to_midi(
    stem_wav: str | Path,
    out_mid: str | Path,
    *,
    params: BasicPitchParams | None = None,
) -> None:
    stem_wav = Path(stem_wav).resolve()
    out_mid = Path(out_mid).resolve()
    out_mid.parent.mkdir(parents=True, exist_ok=True)

    params = params or BasicPitchParams()

    old_cwd = Path.cwd()
    try:
        os.chdir(BP_REPO_ROOT)
        try:
            _, midi_data, _ = predict(
                str(stem_wav),
                onset_threshold=params.onset_threshold,
                frame_threshold=params.frame_threshold,
                minimum_note_length=params.minimum_note_length,
            )
        except TypeError:
            # if the fork's signature differs
            _, midi_data, _ = predict(str(stem_wav))
    finally:
        os.chdir(old_cwd)

    midi_data.write(str(out_mid))
