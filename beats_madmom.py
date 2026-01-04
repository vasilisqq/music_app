from __future__ import annotations

from pathlib import Path

from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor
from madmom.features.beats import RNNBeatProcessor, DBNBeatTrackingProcessor


def _wav_duration_sec(wav_path: Path) -> float:
    # без внешних зависимостей: читаем WAV через стандартный модуль wave
    import wave

    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        sr = wf.getframerate()
    return float(frames) / float(sr) if sr else 0.0


def detect_beats_madmom(
    audio_path: str | Path,
    *,
    beats_per_bar: list[int] = [3, 4],
    fps: int = 100,
    min_bpm: float = 55.0,
    max_bpm: float = 215.0,
) -> list[float]:
    audio_path = Path(audio_path).resolve()

    # 1) downbeats (как было)
    act = RNNDownBeatProcessor()(str(audio_path))
    tracker = DBNDownBeatTrackingProcessor(
        beats_per_bar=beats_per_bar,
        fps=fps,
        min_bpm=min_bpm,
        max_bpm=max_bpm,
    )
    beats = tracker(act)
    times = sorted(set(float(t) for t, _ in beats))

    if len(times) >= 2:
        return times

    # 2) fallback: обычные beats (без downbeat-классификации)
    act_b = RNNBeatProcessor()(str(audio_path))
    tracker_b = DBNBeatTrackingProcessor(
        fps=fps,
        min_bpm=min_bpm,
        max_bpm=max_bpm,
    )
    beat_times = tracker_b(act_b)
    times = sorted(set(float(t) for t in beat_times))

    if len(times) >= 2:
        return times

    # 3) последний fallback: равномерная сетка по длительности файла
    dur = _wav_duration_sec(audio_path)
    bpm = 120.0
    step = 60.0 / bpm

    if dur <= 0.0:
        # совсем аварийно: минимально возможная сетка
        return [0.0, 1.0]

    n = max(2, int(dur / step) + 1)
    times = [i * step for i in range(n)]
    if times[-1] < dur:
        times.append(dur)

    # гарантируем минимум 2 значения
    if len(times) < 2:
        times = [0.0, dur]

    return times
