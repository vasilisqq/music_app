from __future__ import annotations

from pathlib import Path

from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor


def detect_beats_madmom(
    audio_path: str | Path,
    *,
    beats_per_bar: list[int] = [3, 4],
    fps: int = 100,
    min_bpm: float = 55.0,
    max_bpm: float = 215.0,
) -> list[float]:
    audio_path = Path(audio_path).resolve()
    act = RNNDownBeatProcessor()(str(audio_path))
    tracker = DBNDownBeatTrackingProcessor(
        beats_per_bar=beats_per_bar,
        fps=fps,
        min_bpm=min_bpm,
        max_bpm=max_bpm,
    )
    beats = tracker(act)
    times = sorted(set(float(t) for t, _ in beats))
    return times
