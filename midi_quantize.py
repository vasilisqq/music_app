from __future__ import annotations

from pathlib import Path
from typing import Literal

import pretty_midi


def _build_subbeat_grid(beat_times: list[float], subdivisions: int) -> list[float]:
    if len(beat_times) < 2:
        raise ValueError("Need at least 2 beat times to build a grid")

    diffs = [beat_times[i + 1] - beat_times[i] for i in range(len(beat_times) - 1)]
    diffs = [d for d in diffs if d > 1e-6]
    if not diffs:
        raise ValueError("Invalid beat times (no positive diffs)")

    diffs_sorted = sorted(diffs)
    median_dt = diffs_sorted[len(diffs_sorted) // 2]
    extended = beat_times + [beat_times[-1] + median_dt]

    grid: list[float] = []
    for i in range(len(extended) - 1):
        a = extended[i]
        b = extended[i + 1]
        step = (b - a) / subdivisions
        for k in range(subdivisions):
            grid.append(a + k * step)
    grid.append(extended[-1])
    return grid


def _quantize_time(t: float, grid: list[float], mode: Literal["nearest", "floor", "ceil"]) -> float:
    import bisect
    idx = bisect.bisect_left(grid, t)

    if mode == "floor":
        if idx <= 0:
            return grid[0]
        return grid[idx - 1]

    if mode == "ceil":
        if idx >= len(grid):
            return grid[-1]
        return grid[idx]

    # nearest
    if idx <= 0:
        return grid[0]
    if idx >= len(grid):
        return grid[-1]
    a = grid[idx - 1]
    b = grid[idx]
    return a if abs(t - a) <= abs(t - b) else b


def _clamp(x: float, a: float, b: float) -> float:
    return a if x < a else (b if x > b else x)


def _merge_adjacent_same_pitch(
    notes: list[pretty_midi.Note],
    *,
    gap_tol: float = 0.03,
    overlap_tol: float = 1e-6,
) -> list[pretty_midi.Note]:
    if not notes:
        return []
    by_pitch: dict[int, list[pretty_midi.Note]] = {}
    for n in notes:
        by_pitch.setdefault(int(n.pitch), []).append(n)

    out: list[pretty_midi.Note] = []
    for _, arr in by_pitch.items():
        arr.sort(key=lambda n: float(n.start))
        cur = arr[0]
        for n in arr[1:]:
            if float(n.start) <= float(cur.end) + overlap_tol or (float(n.start) - float(cur.end)) <= gap_tol:
                cur.end = max(float(cur.end), float(n.end))
                cur.velocity = max(int(cur.velocity), int(n.velocity))
            else:
                out.append(cur)
                cur = n
        out.append(cur)

    out.sort(key=lambda n: (float(n.start), int(n.pitch)))
    return out


def _remove_same_pitch_overlaps(notes: list[pretty_midi.Note]) -> list[pretty_midi.Note]:
    if not notes:
        return []
    notes = sorted(notes, key=lambda n: (int(n.pitch), float(n.start), float(n.end)))
    out: list[pretty_midi.Note] = []
    last_by_pitch: dict[int, pretty_midi.Note] = {}

    for n in notes:
        p = int(n.pitch)
        if p in last_by_pitch:
            prev = last_by_pitch[p]
            if float(n.start) < float(prev.end):
                prev.end = float(n.start)
        out.append(n)
        last_by_pitch[p] = n

    out = [n for n in out if float(n.end) - float(n.start) > 1e-6]
    out.sort(key=lambda n: (float(n.start), int(n.pitch)))
    return out


def quantize_pretty_midi_to_beats(
    pm: pretty_midi.PrettyMIDI,
    beat_times: list[float],
    *,
    subdivisions: int = 4,
    min_note_steps: int = 1,
    drop_drums: bool = False,
    merge_gap: float = 0.03,
    start_mode: Literal["nearest", "floor", "ceil"] = "nearest",
) -> pretty_midi.PrettyMIDI:
    """Quantize note starts to a beat grid.

    Note: merge_gap can "swallow" repeated same-pitch notes if too large.
    For lead lines, setting merge_gap=0 and start_mode="floor" is often safer.
    """
    grid = _build_subbeat_grid(beat_times, subdivisions=subdivisions)
    if len(grid) < 2:
        raise ValueError("Quantization grid too small")

    min_step_sec = min(
        grid[i + 1] - grid[i]
        for i in range(len(grid) - 1)
        if (grid[i + 1] - grid[i]) > 1e-9
    )
    min_dur_sec = min_step_sec * max(1, min_note_steps)

    out = pretty_midi.PrettyMIDI()

    for inst in pm.instruments:
        if drop_drums and getattr(inst, "is_drum", False):
            continue

        new_inst = pretty_midi.Instrument(
            program=inst.program,
            is_drum=getattr(inst, "is_drum", False),
            name=inst.name,
        )

        new_notes: list[pretty_midi.Note] = []
        for n in inst.notes:
            s0 = float(n.start)
            e0 = float(n.end)
            if e0 <= s0:
                continue

            s = _quantize_time(s0, grid, mode=start_mode)
            dur0 = e0 - s0

            steps = max(1, int(round(dur0 / min_step_sec)))
            steps = max(steps, min_note_steps)
            e = s + steps * min_step_sec

            e = _clamp(e, s + min_dur_sec, grid[-1])
            if e <= s:
                continue

            new_notes.append(pretty_midi.Note(
                velocity=int(n.velocity),
                pitch=int(n.pitch),
                start=float(s),
                end=float(e),
            ))

        new_notes.sort(key=lambda x: (float(x.start), int(x.pitch)))
        new_notes = _merge_adjacent_same_pitch(new_notes, gap_tol=merge_gap)
        new_notes = _remove_same_pitch_overlaps(new_notes)

        new_inst.notes = new_notes
        if new_inst.notes:
            out.instruments.append(new_inst)

    return out


def quantize_midi_file(
    in_mid: str | Path,
    out_mid: str | Path,
    beat_times: list[float],
    *,
    subdivisions: int = 4,
    merge_gap: float = 0.03,
    start_mode: Literal["nearest", "floor", "ceil"] = "nearest",
) -> Path:
    in_mid = Path(in_mid).resolve()
    out_mid = Path(out_mid).resolve()
    out_mid.parent.mkdir(parents=True, exist_ok=True)

    pm = pretty_midi.PrettyMIDI(str(in_mid))
    pm_q = quantize_pretty_midi_to_beats(
        pm,
        beat_times,
        subdivisions=subdivisions,
        merge_gap=merge_gap,
        start_mode=start_mode,
    )
    pm_q.write(str(out_mid))
    return out_mid
