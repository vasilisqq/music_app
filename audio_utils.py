from __future__ import annotations

import math
import wave
from pathlib import Path

import audioop
from pydub import AudioSegment

from config import ROOT


def convert_to_wav(mp3_path: str | Path, out_wav: str | Path = "output.wav") -> Path:
    mp3_path = Path(mp3_path)
    out_wav = (ROOT / out_wav).resolve()
    audio = AudioSegment.from_mp3(str(mp3_path))
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    audio.export(str(out_wav), format="wav")
    return out_wav


def wav_levels_dbfs(wav_path: str | Path, *, chunk_frames: int = 65536) -> tuple[float, float]:
    """Return (rms_dbfs, peak_dbfs) for a PCM WAV file.

    dBFS is computed relative to full-scale for the sample width.
    """
    wav_path = Path(wav_path).resolve()

    with wave.open(str(wav_path), "rb") as wf:
        n_channels = int(wf.getnchannels())
        sampwidth = int(wf.getsampwidth())
        if sampwidth <= 0:
            return -120.0, -120.0

        max_amp = float(2 ** (8 * sampwidth - 1))

        rms_max = 0.0
        peak_max = 0.0

        while True:
            frames = wf.readframes(chunk_frames)
            if not frames:
                break

            # Convert to mono to make thresholds stable across channel counts.
            if n_channels > 1:
                frames_mono = audioop.tomono(frames, sampwidth, 0.5, 0.5)
            else:
                frames_mono = frames

            rms = float(audioop.rms(frames_mono, sampwidth))
            peak = float(audioop.max(frames_mono, sampwidth))

            if rms > rms_max:
                rms_max = rms
            if peak > peak_max:
                peak_max = peak

    def to_dbfs(x: float) -> float:
        if x <= 0.0 or max_amp <= 0.0:
            return -120.0
        return float(20.0 * math.log10(max(1e-12, x / max_amp)))

    return to_dbfs(rms_max), to_dbfs(peak_max)


def is_wav_silent(
    wav_path: str | Path,
    *,
    rms_dbfs_threshold: float = -60.0,
    peak_dbfs_threshold: float = -50.0,
) -> bool:
    """Heuristic silence detector for demucs stems.

    Returns True if BOTH RMS and peak levels are below their thresholds.
    """
    rms_dbfs, peak_dbfs = wav_levels_dbfs(wav_path)
    return (rms_dbfs < float(rms_dbfs_threshold)) and (peak_dbfs < float(peak_dbfs_threshold))
