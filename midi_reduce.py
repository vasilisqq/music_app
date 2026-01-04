from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

import pretty_midi

from midi_quantize import _build_subbeat_grid, _clamp, _merge_adjacent_same_pitch, _remove_same_pitch_overlaps


@dataclass(frozen=True)
class Range:
    lo: int
    hi: int


def _iter_notes(pm: pretty_midi.PrettyMIDI, *, drop_drums: bool = True) -> list[pretty_midi.Note]:
    notes: list[pretty_midi.Note] = []
    for inst in pm.instruments:
        if drop_drums and getattr(inst, "is_drum", False):
            continue
        notes.extend(inst.notes)
    return notes


def _clean_notes(
    notes: Iterable[pretty_midi.Note],
    *,
    pitch_range: Range | None,
    min_dur: float,
    min_vel: int,
) -> list[pretty_midi.Note]:
    out: list[pretty_midi.Note] = []
    for n in notes:
        dur = float(n.end) - float(n.start)
        if dur < min_dur:
            continue
        if int(n.velocity) < min_vel:
            continue
        if pitch_range is not None:
            p = int(n.pitch)
            if p < pitch_range.lo or p > pitch_range.hi:
                continue
        out.append(n)
    out.sort(key=lambda n: (float(n.start), int(n.pitch)))
    return out


def _time_boundaries(notes: list[pretty_midi.Note]) -> list[float]:
    tset = set()
    for n in notes:
        tset.add(float(n.start))
        tset.add(float(n.end))
    return sorted(tset)


def _active_notes_at(
    notes_sorted_by_start: list[pretty_midi.Note],
    t: float,
    start_idx: int,
) -> tuple[list[pretty_midi.Note], int]:
    active: list[pretty_midi.Note] = []
    i = start_idx
    while i < len(notes_sorted_by_start) and float(notes_sorted_by_start[i].start) <= t:
        i += 1
    for n in notes_sorted_by_start[:i]:
        if float(n.end) > t:
            active.append(n)
    return active, i


def _limit_polyphony_on_grid(
    notes: list[pretty_midi.Note],
    *,
    times: list[float],
    max_notes_per_slice: int,
    prefer: Literal["max_velocity", "max_pitch"] = "max_velocity",
    avoid_below_pitch: int | None = None,
    hand_span_limit: int | None = 12,
) -> list[pretty_midi.Note]:
    if not notes or len(times) < 2:
        return []

    notes_sorted = sorted(notes, key=lambda n: float(n.start))
    out: list[pretty_midi.Note] = []
    start_idx = 0

    for a, b in zip(times, times[1:]):
        probe_t = a + 1e-6
        active, start_idx = _active_notes_at(notes_sorted, probe_t, start_idx)

        if avoid_below_pitch is not None:
            active = [n for n in active if int(n.pitch) >= avoid_below_pitch]
        if not active:
            continue

        if prefer == "max_velocity":
            active.sort(key=lambda n: int(n.velocity), reverse=True)
        elif prefer == "max_pitch":
            active.sort(key=lambda n: int(n.pitch), reverse=True)
        else:
            raise ValueError(prefer)

        chosen = active[:max_notes_per_slice]

        if hand_span_limit is not None and chosen and len(chosen) >= 2:
            pitches = sorted(int(n.pitch) for n in chosen)
            if pitches[-1] - pitches[0] > hand_span_limit:
                top = max(chosen, key=lambda n: int(n.pitch))
                chosen = [top]

        for n in chosen:
            out.append(pretty_midi.Note(
                velocity=int(n.velocity),
                pitch=int(n.pitch),
                start=float(a),
                end=float(b),
            ))

    out = _merge_adjacent_same_pitch(out, gap_tol=1e-6)
    out = _remove_same_pitch_overlaps(out)
    return out


def _choose_one(
    active: list[pretty_midi.Note],
    rule: Literal["max_pitch", "min_pitch", "max_velocity"],
) -> pretty_midi.Note | None:
    if not active:
        return None
    if rule == "max_pitch":
        return max(active, key=lambda n: int(n.pitch))
    if rule == "min_pitch":
        return min(active, key=lambda n: int(n.pitch))
    if rule == "max_velocity":
        return max(active, key=lambda n: int(n.velocity))
    raise ValueError(rule)


def _monophonic_reduce(
    notes: list[pretty_midi.Note],
    *,
    choose_rule: Literal["max_pitch", "min_pitch", "max_velocity"],
    min_segment: float = 0.03,
) -> list[pretty_midi.Note]:
    if not notes:
        return []
    notes_sorted = sorted(notes, key=lambda n: float(n.start))
    times = _time_boundaries(notes_sorted)
    if len(times) < 2:
        return []

    out: list[pretty_midi.Note] = []
    start_idx = 0

    cur_pitch: int | None = None
    cur_vel: int = 0
    cur_start: float | None = None
    cur_end: float | None = None

    for a, b in zip(times, times[1:]):
        if b - a < min_segment:
            continue

        probe_t = a + 1e-6
        active, start_idx = _active_notes_at(notes_sorted, probe_t, start_idx)
        chosen = _choose_one(active, choose_rule)

        if chosen is None:
            if cur_pitch is not None and cur_start is not None and cur_end is not None and (cur_end - cur_start) >= min_segment:
                out.append(pretty_midi.Note(velocity=cur_vel, pitch=cur_pitch, start=cur_start, end=cur_end))
            cur_pitch = None
            cur_start = None
            cur_end = None
            cur_vel = 0
            continue

        p = int(chosen.pitch)
        v = int(chosen.velocity)

        if cur_pitch is None:
            cur_pitch = p
            cur_vel = v
            cur_start = a
            cur_end = b
        elif p == cur_pitch:
            cur_end = b
            cur_vel = max(cur_vel, v)
        else:
            if cur_start is not None and cur_end is not None and (cur_end - cur_start) >= min_segment:
                out.append(pretty_midi.Note(velocity=cur_vel, pitch=cur_pitch, start=cur_start, end=cur_end))
            cur_pitch = p
            cur_vel = v
            cur_start = a
            cur_end = b

    if cur_pitch is not None and cur_start is not None and cur_end is not None and (cur_end - cur_start) >= min_segment:
        out.append(pretty_midi.Note(velocity=cur_vel, pitch=cur_pitch, start=cur_start, end=cur_end))

    return out


def _remove_harmony_when_melody_active(
    melody: list[pretty_midi.Note],
    harmony: list[pretty_midi.Note],
) -> list[pretty_midi.Note]:
    if not melody or not harmony:
        return harmony
    mel = sorted(melody, key=lambda n: float(n.start))
    out = []
    for h in harmony:
        t = float(h.start) + 1e-6
        ok = True
        for m in mel:
            if float(m.start) <= t < float(m.end):
                ok = False
                break
        if ok:
            out.append(h)
    return out


def _make_drums_instrument_from_any_notes(pm: pretty_midi.PrettyMIDI) -> pretty_midi.Instrument:
    inst = pretty_midi.Instrument(program=0, is_drum=True, name="Drums")
    for n in _iter_notes(pm, drop_drums=False):
        p = int(_clamp(int(n.pitch), 35, 81))
        inst.notes.append(pretty_midi.Note(int(n.velocity), p, float(n.start), float(n.end)))
    inst.notes.sort(key=lambda x: (float(x.start), int(x.pitch)))
    inst.notes = _merge_adjacent_same_pitch(inst.notes, gap_tol=1e-6)
    inst.notes = _remove_same_pitch_overlaps(inst.notes)
    return inst


def _pick_melody_skyline(
    notes: list[pretty_midi.Note],
    *,
    times: list[float],
) -> list[pretty_midi.Note]:
    if not notes or len(times) < 2:
        return []

    notes_sorted = sorted(notes, key=lambda n: float(n.start))
    out: list[pretty_midi.Note] = []
    start_idx = 0

    last_pitch = None
    for a, b in zip(times, times[1:]):
        probe_t = a + 1e-6
        active, start_idx = _active_notes_at(notes_sorted, probe_t, start_idx)
        if not active:
            last_pitch = None
            continue
        best = max(active, key=lambda n: (int(n.pitch), int(n.velocity)))
        p = int(best.pitch)
        v = int(best.velocity)
        if last_pitch == p and out:
            out[-1].end = float(b)
            out[-1].velocity = max(int(out[-1].velocity), v)
        else:
            out.append(pretty_midi.Note(v, p, float(a), float(b)))
            last_pitch = p

    out = _merge_adjacent_same_pitch(out, gap_tol=0.02)
    out = _remove_same_pitch_overlaps(out)
    return out


def complete_midi(
    vocals_mid: str,
    bass_mid: str,
    other_mid: str | None,
    drums_mid: str | None,
    out_mid: str,
    *,
    beat_times: list[float],
) -> None:
    # tighter ranges reduce junk
    right_range = Range(lo=52, hi=92)  # E3..G6
    left_range = Range(lo=28, hi=55)   # E1..G3
    harmony_range = Range(lo=55, hi=88)

    # strict filters for playability (tune if becomes too empty)
    min_note_duration = 0.08
    min_vel_v = 35
    min_vel_b = 30
    min_vel_o = 45

    pm_v = pretty_midi.PrettyMIDI(vocals_mid)
    pm_b = pretty_midi.PrettyMIDI(bass_mid)
    pm_o = pretty_midi.PrettyMIDI(other_mid) if other_mid else None
    pm_d = pretty_midi.PrettyMIDI(drums_mid) if drums_mid else None

    v_notes = _clean_notes(_iter_notes(pm_v, drop_drums=True), pitch_range=right_range, min_dur=min_note_duration, min_vel=min_vel_v)
    b_notes = _clean_notes(_iter_notes(pm_b, drop_drums=True), pitch_range=left_range,  min_dur=min_note_duration, min_vel=min_vel_b)

    o_notes: list[pretty_midi.Note] = []
    if pm_o is not None:
        o_notes = _clean_notes(_iter_notes(pm_o, drop_drums=True), pitch_range=harmony_range, min_dur=min_note_duration, min_vel=min_vel_o)

    grid_mel = _build_subbeat_grid(beat_times, subdivisions=2)  # 1/8
    grid_har = _build_subbeat_grid(beat_times, subdivisions=1)  # 1/4

    # Bass
    b_notes = _limit_polyphony_on_grid(b_notes, times=grid_mel, max_notes_per_slice=1, prefer="max_velocity", hand_span_limit=None)
    bassline = _monophonic_reduce(b_notes, choose_rule="min_pitch")

    # Melody (prefer OTHER if present else VOCALS)
    melody_src = o_notes if o_notes else v_notes
    melody = _pick_melody_skyline(melody_src, times=grid_mel)

    # Harmony: very light
    harmony: list[pretty_midi.Note] = []
    if o_notes:
        harmony = _limit_polyphony_on_grid(
            o_notes,
            times=grid_har,
            max_notes_per_slice=1,
            prefer="max_velocity",
            avoid_below_pitch=left_range.hi,
            hand_span_limit=12,
        )
        harmony = _remove_harmony_when_melody_active(melody, harmony)

    out_pm = pretty_midi.PrettyMIDI()
    piano_program = 0

    right = pretty_midi.Instrument(program=piano_program, is_drum=False, name="Piano RH")
    left = pretty_midi.Instrument(program=piano_program, is_drum=False, name="Piano LH")

    right.notes.extend(melody)
    right.notes.extend(harmony)
    left.notes.extend(bassline)

    right.notes.sort(key=lambda n: (float(n.start), int(n.pitch)))
    left.notes.sort(key=lambda n: (float(n.start), int(n.pitch)))

    right.notes = _merge_adjacent_same_pitch(right.notes, gap_tol=0.02)
    right.notes = _remove_same_pitch_overlaps(right.notes)
    left.notes = _merge_adjacent_same_pitch(left.notes, gap_tol=0.03)
    left.notes = _remove_same_pitch_overlaps(left.notes)

    out_pm.instruments.append(right)
    out_pm.instruments.append(left)

    if pm_d is not None:
        drum_inst = _make_drums_instrument_from_any_notes(pm_d)
        if drum_inst.notes:
            out_pm.instruments.append(drum_inst)

    out_pm.write(out_mid)
