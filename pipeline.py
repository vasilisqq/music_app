from __future__ import annotations

import shutil
from pathlib import Path

import pretty_midi

import config
from audio_utils import convert_to_wav, is_wav_silent
from beats_madmom import detect_beats_madmom
from midi_quantize import quantize_midi_file
from midi_reduce import complete_midi
from separation import separate_stems
from transcription_basic_pitch import BasicPitchParams, stem_to_midi


def _write_empty_midi(path: str | Path) -> None:
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    pretty_midi.PrettyMIDI().write(str(path))


def quantize_and_reduce_pipeline(
    stems_dir: str | Path,
    midi_dir: str | Path,
    *,
    subdivisions_quant: int = 4,
    include_drums: bool = False,
) -> None:
    stems_dir = Path(stems_dir).resolve()
    midi_dir = Path(midi_dir).resolve()
    midi_dir.mkdir(parents=True, exist_ok=True)

    # Use mixture/drums/other only for beat tracking, never for note transcription.
    beat_audio = None
    for name in ["mixture.wav", "drums.wav", "other.wav"]:
        p = stems_dir / name
        if p.exists():
            beat_audio = p
            break
    if beat_audio is None:
        raise FileNotFoundError(f"Не найдено drums.wav/other.wav/mixture.wav в {stems_dir}")

    beat_times = detect_beats_madmom(beat_audio)

    # Ensure required inputs exist (they can be empty MIDIs)
    if not (midi_dir / "vocals.mid").exists():
        _write_empty_midi(midi_dir / "vocals.mid")
    if not (midi_dir / "bass.mid").exists():
        _write_empty_midi(midi_dir / "bass.mid")

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

    other_used = None
    other_src = midi_dir / "other.mid"
    if other_src.exists():
        if config.OTHER_USE_QUANTIZATION:
            other_q = quantize_midi_file(
                other_src,
                midi_dir / "other_q.mid",
                beat_times,
                subdivisions=int(config.OTHER_Q_SUBDIVISIONS),
                merge_gap=float(config.OTHER_Q_MERGE_GAP),
                start_mode=str(config.OTHER_Q_START_MODE),
            )
            other_used = other_q
        else:
            # keep raw OTHER to avoid swallowing repeated notes
            other_used = other_src

    # NOTE: Drums are intentionally excluded from the playable piano reduction.
    drums_q = None
    if include_drums:
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
        other_mid=str(other_used) if other_used else None,
        drums_mid=str(drums_q) if drums_q else None,
        out_mid=str(midi_dir / "piano_reduction_playable.mid"),
        beat_times=beat_times,
        include_drums=include_drums,
    )


def stems_to_midi(
    stems_dir: str | Path,
    midi_dir: str | Path,
    *,
    transcribe_drums: bool = False,
) -> None:
    stems_dir = Path(stems_dir).resolve()
    midi_dir = Path(midi_dir).resolve()
    midi_dir.mkdir(parents=True, exist_ok=True)

    vocals_params = BasicPitchParams(
        onset_threshold=config.BP_VOCALS_ONSET_THRESHOLD,
        frame_threshold=config.BP_VOCALS_FRAME_THRESHOLD,
        minimum_note_length=config.BP_VOCALS_MIN_NOTE_LENGTH,
    )
    bass_params = BasicPitchParams(
        onset_threshold=config.BP_BASS_ONSET_THRESHOLD,
        frame_threshold=config.BP_BASS_FRAME_THRESHOLD,
        minimum_note_length=config.BP_BASS_MIN_NOTE_LENGTH,
    )
    other_params = BasicPitchParams(
        onset_threshold=config.BP_OTHER_ONSET_THRESHOLD,
        frame_threshold=config.BP_OTHER_FRAME_THRESHOLD,
        minimum_note_length=config.BP_OTHER_MIN_NOTE_LENGTH,
    )

    def transcribe_or_empty(stem_name: str, out_name: str, params: BasicPitchParams | None) -> None:
        stem_wav = stems_dir / stem_name
        out_mid = midi_dir / out_name

        if not stem_wav.exists():
            _write_empty_midi(out_mid)
            return

        if is_wav_silent(
            stem_wav,
            rms_dbfs_threshold=float(config.STEM_SILENCE_RMS_DBFS),
            peak_dbfs_threshold=float(config.STEM_SILENCE_PEAK_DBFS),
        ):
            _write_empty_midi(out_mid)
            return

        stem_to_midi(stem_wav, out_mid, params=params)

    if config.USE_ONLY_OTHER:
        _write_empty_midi(midi_dir / "vocals.mid")
        _write_empty_midi(midi_dir / "bass.mid")
        transcribe_or_empty("other.wav", "other.mid", other_params)
    else:
        transcribe_or_empty("vocals.wav", "vocals.mid", vocals_params)
        transcribe_or_empty("bass.wav", "bass.mid", bass_params)
        transcribe_or_empty("other.wav", "other.mid", other_params)

    if transcribe_drums:
        drums_wav = stems_dir / "drums.wav"
        if drums_wav.exists() and (not is_wav_silent(
            drums_wav,
            rms_dbfs_threshold=float(config.STEM_SILENCE_RMS_DBFS),
            peak_dbfs_threshold=float(config.STEM_SILENCE_PEAK_DBFS),
        )):
            stem_to_midi(drums_wav, midi_dir / "drums.mid")


def _materialize_input_as_output_wav(root: Path, input_name: str, out_wav_name: str = "output.wav") -> Path:
    input_path = (root / input_name).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Файл не найден рядом с кодом: {input_path}")

    out_wav = (root / out_wav_name).resolve()

    if input_path.suffix.lower() == ".mp3":
        convert_to_wav(input_path, out_wav=out_wav_name)
        return out_wav

    if input_path.suffix.lower() == ".wav":
        if input_path.resolve() != out_wav:
            shutil.copyfile(str(input_path), str(out_wav))
        return out_wav

    raise ValueError(f"Нужен .mp3 или .wav, получено: {input_path.suffix}")


def run_from_local_file(
    input_name: str = "input.mp3",
    *,
    always_reseparate: bool = False,
) -> None:
    root = Path(__file__).resolve().parent

    wav_path = _materialize_input_as_output_wav(root, input_name, out_wav_name="output.wav")

    stems_dir = root / "separated" / "htdemucs" / wav_path.stem
    if always_reseparate or (not stems_dir.exists()):
        separate_stems(wav_path)

    if not (stems_dir / "vocals.wav").exists():
        raise FileNotFoundError(f"После demucs не найден vocals.wav в {stems_dir}")

    midi_dir = root / "midi_out"
    stems_to_midi(stems_dir, midi_dir, transcribe_drums=False)
    quantize_and_reduce_pipeline(stems_dir, midi_dir, subdivisions_quant=4, include_drums=False)


def run_default_paths() -> None:
    root = Path(__file__).resolve().parent
    stems_dir = root / "separated" / "htdemucs" / "output"
    midi_dir = root / "midi_out"

    stems_to_midi(stems_dir, midi_dir, transcribe_drums=False)
    quantize_and_reduce_pipeline(stems_dir, midi_dir, subdivisions_quant=4, include_drums=False)
