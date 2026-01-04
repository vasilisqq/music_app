from __future__ import annotations

from pathlib import Path

from beats_madmom import detect_beats_madmom
from midi_quantize import quantize_midi_file
from midi_reduce import complete_midi
from transcription_basic_pitch import stem_to_midi


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
        vocals_mid=str(vocals_q),
        bass_mid=str(bass_q),
        other_mid=str(other_q) if other_q else None,
        drums_mid=str(drums_q) if drums_q else None,
        out_mid=str(midi_dir / "piano_reduction_playable.mid"),
        beat_times=beat_times,
    )


def stems_to_midi(stems_dir: str | Path, midi_dir: str | Path) -> None:
    stems_dir = Path(stems_dir).resolve()
    midi_dir = Path(midi_dir).resolve()
    midi_dir.mkdir(parents=True, exist_ok=True)

    stem_to_midi(stems_dir / "vocals.wav", midi_dir / "vocals.mid")
    stem_to_midi(stems_dir / "bass.wav",   midi_dir / "bass.mid")
    stem_to_midi(stems_dir / "other.wav",  midi_dir / "other.mid")

    drums_wav = stems_dir / "drums.wav"
    if drums_wav.exists():
        stem_to_midi(drums_wav, midi_dir / "drums.mid")


def run_default_paths() -> None:
    root = Path(__file__).resolve().parent
    stems_dir = root / "separated" / "htdemucs" / "output"
    midi_dir = root / "midi_out"

    stems_to_midi(stems_dir, midi_dir)
    quantize_and_reduce_pipeline(stems_dir, midi_dir, subdivisions_quant=4)
