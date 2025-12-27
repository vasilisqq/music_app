from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

from pydub import AudioSegment
import demucs.separate
import sys
import torch
import os
import pretty_midi  # pretty_midi умеет читать/писать MIDI [web:497]


ROOT = Path(__file__).resolve().parent

# (Опционально) torch hub cache в папке проекта
project_hub_dir = ROOT / ".torch_hub"
project_hub_dir.mkdir(parents=True, exist_ok=True)
torch.hub.set_dir(str(project_hub_dir))

# basic-pitch-torch (third_party)
BP_REPO_ROOT = ROOT / "third_party" / "basic_pitch_torch"
sys.path.insert(0, str(BP_REPO_ROOT))
from basic_pitch_torch.inference import predict


# -------------------------
# Шаг 1: mp3 -> wav
# -------------------------
def convert_to_wav(mp3_path: str | Path, out_wav: str | Path = "output.wav") -> Path:
    mp3_path = Path(mp3_path)
    out_wav = (ROOT / out_wav).resolve()
    audio = AudioSegment.from_mp3(str(mp3_path))
    audio.export(str(out_wav), format="wav")
    return out_wav


# -------------------------
# Шаг 2: separation -> stems
# -------------------------
def separate_stems(wav_path: str | Path) -> None:
    wav_path = Path(wav_path)
    demucs.separate.main([str(wav_path)])


# -------------------------
# Шаг 3: stem wav -> midi
# -------------------------
def stem_to_midi(stem_wav: str | Path, out_mid: str | Path) -> None:
    stem_wav = Path(stem_wav).resolve()
    out_mid = Path(out_mid).resolve()
    out_mid.parent.mkdir(parents=True, exist_ok=True)

    # basic-pitch-torch ищет веса по относительному пути assets/...,
    # поэтому временно делаем cwd = корень репозитория.
    old_cwd = Path.cwd()
    try:
        os.chdir(BP_REPO_ROOT)
        model_output, midi_data, note_events = predict(str(stem_wav))
    finally:
        os.chdir(old_cwd)

    midi_data.write(str(out_mid))


# -------------------------
# Шаг 4: собрать "пианистичный" MIDI (правилами)
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


def _polyphonic_limit(
    notes: list[pretty_midi.Note],
    *,
    max_notes_per_slice: int,
    prefer_rule: Literal["max_velocity", "max_pitch"],
    min_segment: float = 0.03,
    avoid_below_pitch: int | None = None,
) -> list[pretty_midi.Note]:
    if not notes:
        return []

    notes_sorted = sorted(notes, key=lambda n: float(n.start))
    times = _time_boundaries(notes_sorted)
    if len(times) < 2:
        return []

    out: list[pretty_midi.Note] = []
    start_idx = 0

    for a, b in zip(times, times[1:]):
        if b - a < min_segment:
            continue

        probe_t = a + 1e-6
        active, start_idx = _active_notes_at(notes_sorted, probe_t, start_idx)

        if avoid_below_pitch is not None:
            active = [n for n in active if int(n.pitch) >= avoid_below_pitch]

        if not active:
            continue

        if prefer_rule == "max_velocity":
            active.sort(key=lambda n: int(n.velocity), reverse=True)
        elif prefer_rule == "max_pitch":
            active.sort(key=lambda n: int(n.pitch), reverse=True)
        else:
            raise ValueError(prefer_rule)

        chosen = active[:max_notes_per_slice]
        for n in chosen:
            out.append(pretty_midi.Note(
                velocity=int(n.velocity),
                pitch=int(n.pitch),
                start=a,
                end=b,
            ))

    out.sort(key=lambda n: (int(n.pitch), float(n.start)))
    merged: list[pretty_midi.Note] = []
    for n in out:
        if not merged:
            merged.append(n)
            continue
        prev = merged[-1]
        if int(prev.pitch) == int(n.pitch) and abs(float(prev.end) - float(n.start)) < 1e-6:
            prev.end = n.end
            prev.velocity = max(int(prev.velocity), int(n.velocity))
        else:
            merged.append(n)
    return merged


def complete_midi(
    vocals_mid: str | Path,
    bass_mid: str | Path,
    other_mid: str | Path | None,
    out_mid: str | Path,
) -> None:
    vocals_mid = Path(vocals_mid).resolve()
    bass_mid = Path(bass_mid).resolve()
    other_mid = Path(other_mid).resolve() if other_mid is not None else None
    out_mid = Path(out_mid).resolve()
    out_mid.parent.mkdir(parents=True, exist_ok=True)

    # Диапазоны под "2 руки"
    right_range = Range(lo=48, hi=96)  # C3..C7
    left_range = Range(lo=24, hi=60)   # C1..C4

    # Пороговые фильтры
    min_note_duration = 0.06
    min_velocity = 12

    pm_v = pretty_midi.PrettyMIDI(str(vocals_mid))
    pm_b = pretty_midi.PrettyMIDI(str(bass_mid))
    pm_o = pretty_midi.PrettyMIDI(str(other_mid)) if other_mid else None

    v_notes = _clean_notes(_iter_notes(pm_v, drop_drums=True),
                           pitch_range=right_range, min_dur=min_note_duration, min_vel=min_velocity)
    b_notes = _clean_notes(_iter_notes(pm_b, drop_drums=True),
                           pitch_range=left_range, min_dur=min_note_duration, min_vel=min_velocity)

    o_notes: list[pretty_midi.Note] = []
    if pm_o is not None:
        harmony_range = Range(lo=52, hi=92)
        o_notes = _clean_notes(_iter_notes(pm_o, drop_drums=True),
                               pitch_range=harmony_range, min_dur=min_note_duration, min_vel=min_velocity)

    melody = _monophonic_reduce(v_notes, choose_rule="max_velocity")
    bassline = _monophonic_reduce(b_notes, choose_rule="min_pitch")

    harmony: list[pretty_midi.Note] = []
    if o_notes:
        harmony = _polyphonic_limit(
            o_notes,
            max_notes_per_slice=3,
            prefer_rule="max_velocity",
            avoid_below_pitch=left_range.hi,
        )

    out_pm = pretty_midi.PrettyMIDI()
    piano_program = 0  # acoustic grand piano (GM) [web:497]

    right = pretty_midi.Instrument(program=piano_program, is_drum=False, name="Piano RH")
    left = pretty_midi.Instrument(program=piano_program, is_drum=False, name="Piano LH")

    right.notes.extend(melody)
    right.notes.extend(harmony)
    left.notes.extend(bassline)

    right.notes.sort(key=lambda n: (float(n.start), int(n.pitch)))
    left.notes.sort(key=lambda n: (float(n.start), int(n.pitch)))

    out_pm.instruments.append(right)
    out_pm.instruments.append(left)

    out_pm.write(str(out_mid))


# -------------------------
# Точка входа (пример пайплайна)
# -------------------------
def main():
    # 1) Пример: конвертация + separation (если нужно)
    # wav = convert_to_wav("input.mp3")
    # separate_stems(wav)

    # 2) Пример: stems -> MIDI (пути подстрой под свои имена)
    stems_dir = ROOT / "separated" / "htdemucs" / "output"
    midi_dir = ROOT / "midi_out"
    midi_dir.mkdir(parents=True, exist_ok=True)

    #stem_to_midi(stems_dir / "vocals.wav", midi_dir / "vocals.mid")
    #stem_to_midi(stems_dir / "bass.wav", midi_dir / "bass.mid")
    #stem_to_midi(stems_dir / "other.wav", midi_dir / "other.mid")

    # 3) Сборка "пианистичной" партии
    complete_midi(
        vocals_mid=midi_dir / "vocals.mid",
        bass_mid=midi_dir / "bass.mid",
        other_mid=midi_dir / "other.mid",  # поставь None, если other даёт кашу
        out_mid=midi_dir / "piano_reduction.mid",
    )


if __name__ == "__main__":
    main()
