from __future__ import annotations

import shutil
from pathlib import Path

from audio_utils import convert_to_wav
from beats_madmom import detect_beats_madmom
from midi_quantize import quantize_midi_file
from midi_reduce import complete_midi
from separation import separate_stems
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
    for name in ["mixture.wav", "drums.wav", "other.wav"]:
        p = stems_dir / name
        if p.exists():
            beat_audio = p
            break
    if beat_audio is None:
        raise FileNotFoundError(f"Не найдено drums.wav/other.wav/mixture.wav в {stems_dir}")

    beat_times = detect_beats_madmom(beat_audio)

    vocals_q = quantize_midi_file(
        midi_dir / "vocals.mid",
        midi_dir / "vocals_q.mid",
        beat_times,
        subdivisions=subdivisions_quant,
    )
    bass_q = quantize_midi_file(
        midi_dir / "bass.mid",
        midi_dir / "bass_q.mid",
        beat_times,
        subdivisions=subdivisions_quant,
    )

    other_q = None
    other_src = midi_dir / "other.mid"
    if other_src.exists():
        other_q = quantize_midi_file(
            other_src,
            midi_dir / "other_q.mid",
            beat_times,
            subdivisions=subdivisions_quant,
        )

    drums_q = None
    drums_src = midi_dir / "drums.mid"
    if drums_src.exists():
        drums_q = quantize_midi_file(
            drums_src,
            midi_dir / "drums_q.mid",
            beat_times,
            subdivisions=2,
        )

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
    stem_to_midi(stems_dir / "bass.wav", midi_dir / "bass.mid")
    stem_to_midi(stems_dir / "other.wav", midi_dir / "other.mid")

    drums_wav = stems_dir / "drums.wav"
    if drums_wav.exists():
        stem_to_midi(drums_wav, midi_dir / "drums.mid")


def _materialize_input_as_output_wav(root: Path, input_name: str, out_wav_name: str = "output.wav") -> Path:
    """
    Берёт input_name из папки проекта и гарантирует, что появится WAV с фиксированным именем out_wav_name.
    Так stems от demucs будут в separated/htdemucs/<out_wav_name without ext>/, т.е. .../output/ (как у тебя раньше).
    """
    input_path = (root / input_name).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Файл не найден рядом с кодом: {input_path}")

    out_wav = (root / out_wav_name).resolve()

    if input_path.suffix.lower() == ".mp3":
        # mp3 -> output.wav
        convert_to_wav(input_path, out_wav=out_wav_name)
        return out_wav

    if input_path.suffix.lower() == ".wav":
        # wav -> output.wav (копируем, чтобы имя было стабильным)
        if input_path.resolve() != out_wav:
            shutil.copyfile(str(input_path), str(out_wav))
        return out_wav

    raise ValueError(f"Нужен .mp3 или .wav, получено: {input_path.suffix}")


def run_from_local_file(
    input_name: str = "input.mp3",
    *,
    always_reseparate: bool = False,
) -> None:
    """
    Вариант "как раньше":
    - файл лежит рядом с кодом
    - ты указываешь только имя
    - demucs пишет в separated/htdemucs/output/
    """
    root = Path(__file__).resolve().parent

    wav_path = _materialize_input_as_output_wav(root, input_name, out_wav_name="output.wav")

    stems_dir = root / "separated" / "htdemucs" / wav_path.stem  # => .../output
    if always_reseparate or (not stems_dir.exists()):
        separate_stems(wav_path)

    # sanity-check: убеждаемся, что separation реально произошёл
    if not (stems_dir / "vocals.wav").exists():
        raise FileNotFoundError(f"После demucs не найден vocals.wav в {stems_dir}")

    midi_dir = root / "midi_out"
    stems_to_midi(stems_dir, midi_dir)
    quantize_and_reduce_pipeline(stems_dir, midi_dir, subdivisions_quant=4)


def run_default_paths() -> None:
    """
    Старый режим: ты уже заранее сделал separation, и stems лежат в separated/htdemucs/output/
    """
    root = Path(__file__).resolve().parent
    stems_dir = root / "separated" / "htdemucs" / "output"
    midi_dir = root / "midi_out"

    stems_to_midi(stems_dir, midi_dir)
    quantize_and_reduce_pipeline(stems_dir, midi_dir, subdivisions_quant=4)
