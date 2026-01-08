from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

import pretty_midi

import config
from midi_quantize import _build_subbeat_grid, _clamp, _merge_adjacent_same_pitch, _remove_same_pitch_overlaps


@dataclass(frozen=True)
class Range:
    lo: int
    hi: int


@dataclass(frozen=True)
class KeyEstimate:
    tonic_pc: int
    mode: Literal["major", "minor"]
    confidence: float


_MAJOR_PROFILE = [
    6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88,
]
_MINOR_PROFILE = [
    6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17,
]


def _pc(pitch: int) -> int:
    return int(pitch) % 12


def _rotate(v: list[float], k: int) -> list[float]:
    k = k % len(v)
    return v[-k:] + v[:-k]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(a: list[float]) -> float:
    import math
    return math.sqrt(_dot(a, a))


def _estimate_key_ks(notes: list[pretty_midi.Note]) -> KeyEstimate:
    if not notes:
        return KeyEstimate(tonic_pc=0, mode="major", confidence=0.0)

    hist = [0.0] * 12
    for n in notes:
        dur = max(0.0, float(n.end) - float(n.start))
        w = dur * (max(1, int(n.velocity)) / 127.0)
        hist[_pc(int(n.pitch))] += w

    s = sum(hist)
    if s <= 1e-9:
        return KeyEstimate(tonic_pc=0, mode="major", confidence=0.0)

    hist = [x / s for x in hist]

    maj_norm = _norm(_MAJOR_PROFILE)
    min_norm = _norm(_MINOR_PROFILE)

    best = (-1e9, 0, "major")
    second = -1e9

    for tonic in range(12):
        maj = _rotate(_MAJOR_PROFILE, tonic)
        minr = _rotate(_MINOR_PROFILE, tonic)

        maj_score = _dot(hist, maj) / (maj_norm + 1e-9)
        min_score = _dot(hist, minr) / (min_norm + 1e-9)

        for score, mode in [(maj_score, "major"), (min_score, "minor")]:
            if score > best[0]:
                second = best[0]
                best = (score, tonic, mode)
            elif score > second:
                second = score

    confidence = float(best[0] - second) if second > -1e8 else float(best[0])
    return KeyEstimate(tonic_pc=int(best[1]), mode=best[2], confidence=confidence)


def _scale_pcs(tonic_pc: int, mode: Literal["major", "minor"]) -> set[int]:
    degrees = {0, 2, 4, 5, 7, 9, 11} if mode == "major" else {0, 2, 3, 5, 7, 8, 10}
    return {(_pc(tonic_pc) + d) % 12 for d in degrees}


def _soft_snap_pitch_to_scale(pitch: int, *, allowed_pcs: set[int], max_shift: int = 1) -> int:
    p = int(_clamp(int(pitch), 21, 108))
    if _pc(p) in allowed_pcs:
        return p

    for d in range(1, max_shift + 1):
        up = p + d
        dn = p - d
        up_ok = 21 <= up <= 108 and (_pc(up) in allowed_pcs)
        dn_ok = 21 <= dn <= 108 and (_pc(dn) in allowed_pcs)

        if dn_ok and up_ok:
            return dn
        if dn_ok:
            return dn
        if up_ok:
            return up

    return p


def _soft_snap_notes_to_key(
    notes: list[pretty_midi.Note],
    *,
    key: KeyEstimate,
    max_shift: int = 1,
) -> list[pretty_midi.Note]:
    allowed = _scale_pcs(key.tonic_pc, key.mode)
    out: list[pretty_midi.Note] = []

    for n in notes:
        new_pitch = _soft_snap_pitch_to_scale(int(n.pitch), allowed_pcs=allowed, max_shift=max_shift)
        out.append(pretty_midi.Note(
            velocity=int(n.velocity),
            pitch=int(new_pitch),
            start=float(n.start),
            end=float(n.end),
        ))

    out.sort(key=lambda x: (float(x.start), int(x.pitch)))
    out = _merge_adjacent_same_pitch(out, gap_tol=1e-6)
    out = _remove_same_pitch_overlaps(out)
    return out


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


def _add_hold(notes: list[pretty_midi.Note], hold_sec: float) -> list[pretty_midi.Note]:
    if hold_sec <= 1e-9:
        return notes
    out: list[pretty_midi.Note] = []
    for n in notes:
        out.append(pretty_midi.Note(
            velocity=int(n.velocity),
            pitch=int(n.pitch),
            start=float(n.start),
            end=float(n.end) + float(hold_sec),
        ))
    out.sort(key=lambda n: (float(n.start), int(n.pitch)))
    return out


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


def complete_midi(
    vocals_mid: str,
    bass_mid: str,
    other_mid: str | None,
    drums_mid: str | None,
    out_mid: str,
    *,
    beat_times: list[float],
    include_drums: bool = False,
) -> None:
    right_range = Range(lo=52, hi=96)
    left_range = Range(lo=28, hi=60)
    harmony_range = Range(lo=45, hi=96)

    min_note_duration = 0.05
    min_vel_v = 25
    min_vel_b = 20

    pm_v = pretty_midi.PrettyMIDI(vocals_mid)
    pm_b = pretty_midi.PrettyMIDI(bass_mid)
    pm_o = pretty_midi.PrettyMIDI(other_mid) if other_mid else None

    v_notes = _clean_notes(_iter_notes(pm_v, drop_drums=True), pitch_range=right_range, min_dur=min_note_duration, min_vel=min_vel_v)
    b_notes = _clean_notes(_iter_notes(pm_b, drop_drums=True), pitch_range=left_range, min_dur=min_note_duration, min_vel=min_vel_b)

    raw_o: list[pretty_midi.Note] = []
    o_notes_harmony: list[pretty_midi.Note] = []
    if pm_o is not None:
        raw_o = _iter_notes(pm_o, drop_drums=True)
        o_notes_harmony = _clean_notes(
            raw_o,
            pitch_range=harmony_range,
            min_dur=float(config.OTHER_HARMONY_MIN_DUR),
            min_vel=int(config.OTHER_HARMONY_MIN_VEL),
        )

    # Left texture stays as-is
    total_bass_dur = sum(float(n.end) - float(n.start) for n in b_notes)
    if total_bass_dur < 0.6 or len(b_notes) < 6:
        b_notes = []

    left_texture: list[pretty_midi.Note] = []
    if b_notes:
        grid_mel = _build_subbeat_grid(beat_times, subdivisions=max(1, int(config.MELODY_GRID_SUBDIV)))
        left_texture = _limit_polyphony_on_grid(
            b_notes,
            times=grid_mel,
            max_notes_per_slice=max(1, int(config.LH_MAX_NOTES)),
            prefer="max_velocity",
            hand_span_limit=int(config.LH_SPAN_LIMIT),
        )

    # Dense OTHER
    if bool(getattr(config, "OTHER_DENSE_MODE", False)) and raw_o:
        dense_grid = _build_subbeat_grid(beat_times, subdivisions=max(2, int(getattr(config, "OTHER_DENSE_GRID_SUBDIV", 12))))

        src = o_notes_harmony if o_notes_harmony else raw_o
        src = _add_hold(src, float(getattr(config, "OTHER_DENSE_HOLD_SEC", 0.18)))

        # minimal filtering here; rely on max_notes_per_slice
        src = _clean_notes(
            src,
            pitch_range=harmony_range,
            min_dur=0.0,
            min_vel=int(getattr(config, "OTHER_DENSE_MIN_VEL", 1)),
        )

        right_dense = _limit_polyphony_on_grid(
            src,
            times=dense_grid,
            max_notes_per_slice=max(2, int(getattr(config, "OTHER_DENSE_MAX_NOTES", 12))),
            prefer="max_velocity",
            avoid_below_pitch=left_range.hi,
            hand_span_limit=getattr(config, "OTHER_DENSE_HAND_SPAN", None),
        )

        # Keep key-lock off by default for dense mode
        if config.ENABLE_KEY_LOCK:
            key_basis = right_dense + left_texture
            key = _estimate_key_ks(key_basis)
            right_dense = _soft_snap_notes_to_key(right_dense, key=key, max_shift=config.KEY_LOCK_MAX_SHIFT)
            left_texture = _soft_snap_notes_to_key(left_texture, key=key, max_shift=config.KEY_LOCK_MAX_SHIFT)

        out_pm = pretty_midi.PrettyMIDI()
        right = pretty_midi.Instrument(program=0, is_drum=False, name="Piano RH")
        left = pretty_midi.Instrument(program=0, is_drum=False, name="Piano LH")

        right.notes.extend(right_dense)
        left.notes.extend(left_texture)

        right.notes.sort(key=lambda n: (float(n.start), int(n.pitch)))
        left.notes.sort(key=lambda n: (float(n.start), int(n.pitch)))

        right.notes = _merge_adjacent_same_pitch(right.notes, gap_tol=0.02)
        right.notes = _remove_same_pitch_overlaps(right.notes)
        left.notes = _merge_adjacent_same_pitch(left.notes, gap_tol=0.03)
        left.notes = _remove_same_pitch_overlaps(left.notes)

        if right.notes:
            out_pm.instruments.append(right)
        if left.notes:
            out_pm.instruments.append(left)

        out_pm.write(out_mid)
        return

    # fallback: empty
    pretty_midi.PrettyMIDI().write(out_mid)
