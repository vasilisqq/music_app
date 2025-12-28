from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal
import os
import sys
import math
import torch
from pydub import AudioSegment
import demucs.separate
import pretty_midi

# madmom
from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor

ROOT = Path(__file__).resolve().parent

project_hub_dir = ROOT / ".torch_hub"
project_hub_dir.mkdir(parents=True, exist_ok=True)
torch.hub.set_dir(str(project_hub_dir))

# basic-pitch-torch
BP_REPO_ROOT = ROOT / "third_party" / "basic_pitch_torch"
sys.path.insert(0, str(BP_REPO_ROOT))
from basic_pitch_torch.inference import predict


# -------------------------
# Step 0: audio utils
# -------------------------
def convert_to_wav(mp3_path: str | Path, out_wav: str | Path = "output.wav") -> Path:
    mp3_path = Path(mp3_path)
    out_wav = (ROOT / out_wav).resolve()
    audio = AudioSegment.from_mp3(str(mp3_path))
    audio.export(str(out_wav), format="wav")
    return out_wav


def separate_stems(wav_path: str | Path) -> None:
    wav_path = Path(wav_path)
    demucs.separate.main([str(wav_path)])


def stem_to_midi(stem_wav: str | Path, out_mid: str | Path) -> None:
    """
    If your basic_pitch_torch exposes onset_threshold/frame_threshold/minimum_note_length,
    these can reduce missed notes (at the cost of more noise). Basic Pitch uses such thresholds
    in note creation. [web:95][web:91]
    """
    stem_wav = Path(stem_wav).resolve()
    out_mid = Path(out_mid).resolve()
    out_mid.parent.mkdir(parents=True, exist_ok=True)

    old_cwd = Path.cwd()
    try:
        os.chdir(BP_REPO_ROOT)
        try:
            _, midi_data, _ = predict(
                str(stem_wav),
                onset_threshold=0.45,
                frame_threshold=0.25,
                minimum_note_length=60.0,
            )
        except TypeError:
            _, midi_data, _ = predict(str(stem_wav))
    finally:
        os.chdir(old_cwd)

    midi_data.write(str(out_mid))


# -------------------------
# Step 1: beats via madmom
# -------------------------
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


# -------------------------
# Step 2: beat grid + quantize + hard cleanup
# -------------------------
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
    drop_drums: bool = False,  # do not drop drums globally (we may keep them separately) [web:52]
    merge_gap: float = 0.03,
) -> pretty_midi.PrettyMIDI:
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
            name=inst.name
        )

        new_notes: list[pretty_midi.Note] = []
        for n in inst.notes:
            s0 = float(n.start)
            e0 = float(n.end)
            if e0 <= s0:
                continue

            s = _quantize_time(s0, grid, mode="nearest")
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
) -> Path:
    in_mid = Path(in_mid).resolve()
    out_mid = Path(out_mid).resolve()
    out_mid.parent.mkdir(parents=True, exist_ok=True)

    pm = pretty_midi.PrettyMIDI(str(in_mid))
    pm_q = quantize_pretty_midi_to_beats(pm, beat_times, subdivisions=subdivisions)
    pm_q.write(str(out_mid))
    return out_mid


# -------------------------
# Step 3: playable reduction (melody from OTHER)
# -------------------------
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


def _active_notes_at(notes_sorted_by_start: list[pretty_midi.Note], t: float, start_idx: int) -> tuple[list[pretty_midi.Note], int]:
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
    hand_span_limit: int | None = 12,   # stronger: octave
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


def _choose_one(active: list[pretty_midi.Note], rule: Literal["max_pitch", "min_pitch", "max_velocity"]) -> pretty_midi.Note | None:
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


def _remove_harmony_when_melody_active(melody: list[pretty_midi.Note], harmony: list[pretty_midi.Note]) -> list[pretty_midi.Note]:
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
    """
    In General MIDI, drums are typically on channel 10 and mapped by pitch; in pretty_midi use is_drum=True. [web:52]
    """
    inst = pretty_midi.Instrument(program=0, is_drum=True, name="Drums")
    for n in _iter_notes(pm, drop_drums=False):
        p = int(_clamp(int(n.pitch), 35, 81))
        inst.notes.append(pretty_midi.Note(int(n.velocity), p, float(n.start), float(n.end)))
    inst.notes.sort(key=lambda x: (float(x.start), int(x.pitch)))
    inst.notes = _merge_adjacent_same_pitch(inst.notes, gap_tol=1e-6)
    inst.notes = _remove_same_pitch_overlaps(inst.notes)
    return inst


def _pick_melody_skyline_from_other(
    other_notes: list[pretty_midi.Note],
    *,
    times: list[float],
) -> list[pretty_midi.Note]:
    """
    Simple, stable melody extraction: for each slice pick highest pitch (Skyline idea). [web:42]
    """
    if not other_notes or len(times) < 2:
        return []

    notes_sorted = sorted(other_notes, key=lambda n: float(n.start))
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
    vocals_mid: str | Path,
    bass_mid: str | Path,
    other_mid: str | Path | None,
    drums_mid: str | Path | None,
    out_mid: str | Path,
    *,
    beat_times: list[float],
) -> None:
    vocals_mid = Path(vocals_mid).resolve()
    bass_mid = Path(bass_mid).resolve()
    other_mid = Path(other_mid).resolve() if other_mid is not None else None
    drums_mid = Path(drums_mid).resolve() if drums_mid is not None else None
    out_mid = Path(out_mid).resolve()
    out_mid.parent.mkdir(parents=True, exist_ok=True)

    # tighter ranges reduce junk
    right_range = Range(lo=52, hi=92)  # E3..G6
    left_range = Range(lo=28, hi=55)   # E1..G3
    harmony_range = Range(lo=55, hi=88)

    # stricter filters for playability (tune if becomes too empty)
    min_note_duration = 0.08
    min_vel_v = 35
    min_vel_b = 30
    min_vel_o = 45

    pm_v = pretty_midi.PrettyMIDI(str(vocals_mid))
    pm_b = pretty_midi.PrettyMIDI(str(bass_mid))
    pm_o = pretty_midi.PrettyMIDI(str(other_mid)) if other_mid else None
    pm_d = pretty_midi.PrettyMIDI(str(drums_mid)) if drums_mid and drums_mid.exists() else None

    v_notes = _clean_notes(_iter_notes(pm_v, drop_drums=True), pitch_range=right_range, min_dur=min_note_duration, min_vel=min_vel_v)
    b_notes = _clean_notes(_iter_notes(pm_b, drop_drums=True), pitch_range=left_range,  min_dur=min_note_duration, min_vel=min_vel_b)

    o_notes: list[pretty_midi.Note] = []
    if pm_o is not None:
        o_notes = _clean_notes(_iter_notes(pm_o, drop_drums=True), pitch_range=harmony_range, min_dur=min_note_duration, min_vel=min_vel_o)

    # grids: coarse for musical decisions
    grid_mel = _build_subbeat_grid(beat_times, subdivisions=2)  # 1/8
    grid_har = _build_subbeat_grid(beat_times, subdivisions=1)  # 1/4

    # Bass: 1 note per 1/8 slice
    b_notes = _limit_polyphony_on_grid(b_notes, times=grid_mel, max_notes_per_slice=1, prefer="max_velocity", hand_span_limit=None)
    bassline = _monophonic_reduce(b_notes, choose_rule="min_pitch")

    # MAIN MELODY: from OTHER (stable skyline), then RH will be truly sparse
    melody = _pick_melody_skyline_from_other(o_notes, times=grid_mel) if o_notes else _pick_melody_skyline_from_other(v_notes, times=grid_mel)

    # Harmony: optional and very light (max 1 note per 1/4, no overlap with melody)
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

    # Drums track (optional)
    if pm_d is not None:
        drum_inst = _make_drums_instrument_from_any_notes(pm_d)
        if drum_inst.notes:
            out_pm.instruments.append(drum_inst)

    out_pm.write(str(out_mid))


# -------------------------
# Pipeline: madmom -> quantize -> reduction
# -------------------------
def quantize_and_reduce_pipeline(
    stems_dir: str | Path,
    midi_dir: str | Path,
    *,
    subdivisions_quant: int = 4,
) -> None:
    stems_dir = Path(stems_dir).resolve()
    midi_dir = Path(midi_dir).resolve()
    midi_dir.mkdir(parents=True, exist_ok=True)

    beat_audio = None
    for name in ["drums.wav", "other.wav", "mixture.wav"]:
        p = stems_dir / name
        if p.exists():
            beat_audio = p
            break
    if beat_audio is None:
        raise FileNotFoundError(f"Не найдено drums.wav/other.wav/mixture.wav в {stems_dir}")

    beat_times = detect_beats_madmom(beat_audio)

    vocals_q = quantize_midi_file(midi_dir / "vocals.mid", midi_dir / "vocals_q.mid", beat_times, subdivisions=subdivisions_quant)
    bass_q   = quantize_midi_file(midi_dir / "bass.mid",   midi_dir / "bass_q.mid",   beat_times, subdivisions=subdivisions_quant)

    other_q = None
    other_src = midi_dir / "other.mid"
    if other_src.exists():
        other_q = quantize_midi_file(other_src, midi_dir / "other_q.mid", beat_times, subdivisions=subdivisions_quant)

    drums_q = None
    drums_src = midi_dir / "drums.mid"
    if drums_src.exists():
        drums_q = quantize_midi_file(drums_src, midi_dir / "drums_q.mid", beat_times, subdivisions=2)

    complete_midi(
        vocals_mid=vocals_q,
        bass_mid=bass_q,
        other_mid=other_q,
        drums_mid=drums_q,
        out_mid=midi_dir / "piano_reduction_playable.mid",
        beat_times=beat_times,
    )


def main():
    stems_dir = ROOT / "separated" / "htdemucs" / "output"
    midi_dir = ROOT / "midi_out"

    # Stems to MIDI
    stem_to_midi(stems_dir / "vocals.wav", midi_dir / "vocals.mid")
    stem_to_midi(stems_dir / "bass.wav",   midi_dir / "bass.mid")
    stem_to_midi(stems_dir / "other.wav",  midi_dir / "other.mid")

    # Demucs htdemucs provides drums stem (drums/bass/vocals/other). [web:118]
    drums_wav = stems_dir / "drums.wav"
    if drums_wav.exists():
        stem_to_midi(drums_wav, midi_dir / "drums.mid")

    quantize_and_reduce_pipeline(stems_dir, midi_dir, subdivisions_quant=4)


if __name__ == "__main__":
    main()
