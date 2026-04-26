import os
import re
import threading
import time
from typing import Optional

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject, Qt
from PyQt6.QtGui import QPen, QColor
from PyQt6.QtWidgets import QWidget
from scipy.io import wavfile
from scipy.ndimage import zoom
from scipy.signal import butter, lfilter

# Загружаем ОДИН реальный сэмпл пианино C4
SAMPLE_RATE, PIANO_C4 = wavfile.read('single-piano-note-c4_100bpm_C_major.wav')

if PIANO_C4.ndim == 2:
    base_note = PIANO_C4[:, 0].astype(np.float32) / 32768.0
else:
    base_note = PIANO_C4.astype(np.float32) / 32768.0

NOTE_FREQ = {
    'A0': 27.5, 'A0#': 29.14, 'B0b': 29.14, 'B0': 30.87, 'B0#': 30.87, 'C1b': 30.87,
    'C1': 32.7, 'C1#': 34.65, 'D1b': 34.65, 'D1': 36.71, 'D1#': 38.89, 'E1b': 38.89,
    'E1': 41.2, 'E1#': 43.65, 'F1b': 41.2, 'F1': 43.65, 'F1#': 46.25, 'G1b': 46.25,
    'G1': 49.0, 'G1#': 51.91, 'A1b': 51.91, 'A1': 55.0, 'A1#': 58.27, 'B1b': 58.27,
    'B1': 61.74, 'B1#': 61.74, 'C2b': 61.74, 'C2': 65.41, 'C2#': 69.3, 'D2b': 69.3,
    'D2': 73.42, 'D2#': 77.78, 'E2b': 77.78, 'E2': 82.41, 'E2#': 87.31, 'F2b': 82.41,
    'F2': 87.31, 'F2#': 92.5, 'G2b': 92.5, 'G2': 98.0, 'G2#': 103.83, 'A2b': 103.83,
    'A2': 110.0, 'A2#': 116.54, 'B2b': 116.54, 'B2': 123.47, 'B2#': 123.47, 'C3b': 123.47,
    'C3': 130.81, 'C3#': 138.59, 'D3b': 138.59, 'D3': 146.83, 'D3#': 155.56, 'E3b': 155.56,
    'E3': 164.81, 'E3#': 174.61, 'F3b': 164.81, 'F3': 174.61, 'F3#': 185.0, 'G3b': 185.0,
    'G3': 196.0, 'G3#': 207.65, 'A3b': 207.65, 'A3': 220.0, 'A3#': 233.08, 'B3b': 233.08,
    'B3': 246.94, 'B3#': 246.94, 'C4b': 246.94, 'C4': 261.63, 'C4#': 277.18, 'D4b': 277.18,
    'D4': 293.66, 'D4#': 311.13, 'E4b': 311.13, 'E4': 329.63, 'E4#': 349.23, 'F4b': 329.63,
    'F4': 349.23, 'F4#': 369.99, 'G4b': 369.99, 'G4': 392.0, 'G4#': 415.3, 'A4b': 415.3,
    'A4': 440.0, 'A4#': 466.16, 'B4b': 466.16, 'B4': 493.88, 'B4#': 493.88, 'C5b': 493.88,
    'C5': 523.25, 'C5#': 554.37, 'D5b': 554.37, 'D5': 587.33, 'D5#': 622.25, 'E5b': 622.25,
    'E5': 659.25, 'E5#': 698.46, 'F5b': 659.25, 'F5': 698.46, 'F5#': 739.99, 'G5b': 739.99,
    'G5': 783.99, 'G5#': 830.61, 'A5b': 830.61, 'A5': 880.0, 'A5#': 932.33, 'B5b': 932.33,
    'B5': 987.77, 'B5#': 987.77, 'C6b': 987.77, 'C6': 1046.5, 'C6#': 1108.73, 'D6b': 1108.73,
    'D6': 1174.66, 'D6#': 1244.51, 'E6b': 1244.51, 'E6': 1318.51, 'E6#': 1396.91, 'F6b': 1318.51,
    'F6': 1396.91, 'F6#': 1479.98, 'G6b': 1479.98, 'G6': 1567.98, 'G6#': 1661.22, 'A6b': 1661.22,
    'A6': 1760.0, 'A6#': 1864.66, 'B6b': 1864.66, 'B6': 1975.53, 'B6#': 1975.53, 'C7b': 1975.53,
    'C7': 2093.0, 'C7#': 2217.46, 'D7b': 2217.46, 'D7': 2349.32, 'D7#': 2489.02, 'E7b': 2489.02,
    'E7': 2637.02, 'E7#': 2793.83, 'F7b': 2637.02, 'F7': 2793.83, 'F7#': 2959.96, 'G7b': 2959.96,
    'G7': 3135.96, 'G7#': 3322.44, 'A7b': 3322.44, 'A7': 3520.0, 'A7#': 3729.31, 'B7b': 3729.31,
    'B7': 3951.07, 'B7#': 3951.07, 'C8b': 3951.07, 'C8': 4186.01
}

# Кеш для всех нот (предвычисляется при старте)
note_cache = {}

_MIDI_NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_FLAT_TO_SHARP = {
    "Db": "C#",
    "Eb": "D#",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
}
_NOTE_NAME_PATTERN = re.compile(r"^([A-G])([#b]?)(-?\d+)$")


def normalize_note_name(note_name: str | None) -> str | None:
    if not note_name:
        return None
    normalized = (note_name or "").strip()
    match = _NOTE_NAME_PATTERN.match(normalized)
    if not match:
        return normalized
    letter, accidental, octave = match.groups()
    accidental_pair = f"{letter}{accidental}"
    canonical = _FLAT_TO_SHARP.get(accidental_pair, accidental_pair)
    return f"{canonical}{octave}"


def midi_note_to_name(note_number: int) -> str:
    octave = (int(note_number) // 12) - 1
    note_name = _MIDI_NOTE_NAMES[int(note_number) % 12]
    return f"{note_name}{octave}"


def save_cache(filename='piano_cache.npz'):
    """Сохраняет note_cache в сжатый .npz файл."""
    np.savez_compressed(filename, **note_cache)
    print(f"Кеш сохранён в {filename}")


def load_cache(filename="piano_cache.npz"):
    if not os.path.exists(filename):
        return None
    loaded = np.load(filename, allow_pickle=True)
    cache = {}
    for key in loaded.files:
        arr = loaded[key]
        print(f"Загружаю {key}: форма {arr.shape}, ndim {arr.ndim}")
        cache[key] = arr.ravel().copy()
    return cache


def lowpass_filter(data, cutoff, sr, order=5):
    nyquist = 0.5 * sr
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return lfilter(b, a, data)

def precompute_all():
    for name, freq in NOTE_FREQ.items():
        ratio = freq / 261.63
        new_len = int(len(base_note) / ratio)
        if new_len < 1:
            new_len = 1
        arr = zoom(base_note, new_len / len(base_note), order=3).astype(np.float32)

        # Anti-aliasing фильтр для высоких нот (ratio > 1)
        if ratio > 1:
            cutoff = 20000 / ratio   # пропорциональное снижение частоты среза
            cutoff = min(cutoff, 20000)  # не выше 20 кГц
            if cutoff > 50:
                arr = lowpass_filter(arr, cutoff, SAMPLE_RATE, order=5)

        note_cache[name] = arr.ravel()
precompute_all()
# save_cache()


class PianoPlayer(QObject):

    note_correct = pyqtSignal(object, str)   # передаёт объект ноты и её имя
    note_wrong = pyqtSignal(object, str, str, bool)
    note_ignored = pyqtSignal()

    def __init__(self, note_cache, sample_rate):
        super().__init__()
        self.note_cache = note_cache
        self.sample_rate = sample_rate
        self.active_audio_notes = []
        self.lock = threading.Lock()
        self.current_note_plays = None
        self.current_note_await = None         
        self.current_note_await_time = None    # время старта ожидания
        self.hit_window = 0.1
        self.pre_start_active = False
        self.current_note_item = None 
        self.on_note_correct = None
        self.on_note_wrong = None

        self.space_pressed_in_window = False   # флаг: было ли попадание в окне

        self.stream = sd.OutputStream(
            samplerate=sample_rate,
            channels=1,
            callback=self.audio_callback,
            blocksize=512,
            dtype='float32'
        )
        self.stream.start()


    def play_click(self, duration=0.05, freq=1000, volume=0.25):
        """Воспроизводит короткий щелчок для метронома"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        click = np.sin(2 * np.pi * freq * t) * volume
        click = click.astype(np.float32)
        with self.lock:
            self.active_audio_notes.append({
                'data': click,
                'pos': 0,
                'vel': 1.0,
                'note_name': 'click'
            })

    def _get_note_audio(self, note_name, duration, volume=0.7):
        base = self.note_cache[note_name]
        target_len = int(self.sample_rate * duration)
        
        if target_len <= len(base):
            audio = base[:target_len].copy()
        else:
            repeats = target_len // len(base) + 1
            audio = np.tile(base, repeats)[:target_len]

        # Простая ADSR
        attack = int(0.01 * self.sample_rate)      # 10 мс
        decay = int(0.05 * self.sample_rate)       # 50 мс
        release = int(0.1 * self.sample_rate)      # 100 мс
        sustain = 0.7

        envelope = np.ones(target_len)
        # Attack
        if attack > 0:
            envelope[:attack] = np.linspace(0, 1, attack)
        # Decay
        start = attack
        end = min(attack + decay, target_len)
        envelope[start:end] = np.linspace(1, sustain, end - start)
        # Release
        start_release = max(0, target_len - release)
        envelope[start_release:] = np.linspace(envelope[start_release], 0, target_len - start_release)

        audio = audio * envelope
        # Нормализация по пику
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val * volume
        return audio.astype(np.float32)


    def play_chord(self, notes, duration, volumes=None):
        if volumes is None:
            n = len(notes)
            base_vol = 0.5
            vol = base_vol / (n ** 0.5)
            volumes = [vol] * n

        active_notes = []
        for note, vol in zip(notes, volumes):
            audio = self._get_note_audio(note, duration, vol)
            active_notes.append({
                'data': audio,
                'pos': 0,
                'vel': 1.0,
                'note_name': note
            })
        with self.lock:
            self.active_audio_notes.extend(active_notes)
        print(f"🎸 Аккорд: {notes}")


    def set_note_handlers(self, on_correct, on_wrong):
        """🔥 НОВОЕ: Устанавливает колбэки для проверки нот"""
        self.on_note_correct = on_correct
        self.on_note_wrong = on_wrong


    def audio_callback(self, outdata, frames, time_info, status):
        outdata.fill(0)
        with self.lock:
            to_remove = []
            for note in self.active_audio_notes:
                data = note['data']
                if data.ndim != 1:
                    data = data.ravel()
                    note['data'] = data
                pos = note['pos']
                vel = note['vel']
                remaining = len(data) - pos
                if remaining > 0:
                    take = min(frames, remaining)
                    outdata[:take, 0] += data[pos:pos+take] * vel
                    note['pos'] += take
                if note['pos'] >= len(data):
                    to_remove.append(note)
            for note in to_remove:
                self.active_audio_notes = [n for n in self.active_audio_notes if n is not note]

        # ---- Лимитер ----
        # Если сигнал превышает порог, применяем мягкое ограничение
        peak = np.max(np.abs(outdata))
        if peak > 0.95:
            gain = 0.95 / peak
            outdata[:] *= gain


    def check_note_press(self, note_name: str):
        if self.current_note_await_time is None:
            self.note_ignored.emit()
            return False
        now = time.time()
        dt = now - self.current_note_await_time
        expected_note = normalize_note_name(self.current_note_await)
        played_note = normalize_note_name(note_name)
        if dt <= self.hit_window and not self.space_pressed_in_window and played_note == expected_note:
            self.space_pressed_in_window = True
            self.note_correct.emit(self.current_note_item, self.current_note_await)
            return True
        self.note_wrong.emit(self.current_note_item, self.current_note_await, played_note or note_name, False)
        return False

    def check_midi_note_number(self, note_number: int):
        return self.check_note_press(midi_note_to_name(note_number))

    def check_space_press(self):
        self.note_ignored.emit()
        return False


    def _check_window_timeout(self):
        time.sleep(self.hit_window)
        with self.lock:
            if not self.space_pressed_in_window:
                self.note_wrong.emit(self.current_note_item, self.current_note_await, None, True)
            self.current_note_await_time = None
            self.space_pressed_in_window = False
            self.current_note_item = None


    def play_note(self, note_name, duration, volume=0.7):
        if note_name not in self.note_cache:
            print(f"Нота {note_name} не найдена")
            return
        
        base = self.note_cache[note_name].ravel()
        target_len = int(self.sample_rate * duration)

        if target_len <= len(base):
            note_data = base[:target_len].copy()
        else:
            repeats = target_len // len(base) + 1
            note_data = np.tile(base, repeats)[:target_len]
            t = np.arange(target_len)
            envelope = np.exp(-t / (self.sample_rate * duration * 0.3))
            note_data *= envelope

        max_val = np.max(np.abs(note_data))
        if max_val > 0:
            note_data = note_data / max_val * volume


        self.active_audio_notes.append({
                'data': note_data,
                'pos': 0,
                'vel': 1.0,
                'note_name': note_name
            })

            # 🔥 устанавливаем ожидание нажатия
        self.current_note_name = note_name
        self.current_note_start_time = time.time()
        self.space_pressed_in_window = False
        self.pre_start_active = True  # 🔥 НОВОЕ: ж
        
        print(f"🎵 Ожидаем ноту: {note_name} (окно 3 с)")
        # 🔥 запускаем проверку по истечении окна
        threading.Thread(
            target=self._check_window_timeout,
            daemon=True
        ).start()


    def start_waiting_for_note(self, note_name, note_item=None):
        """Запускает ожидание нажатия для конкретной ноты"""
        self.current_note_await = note_name
        self.current_note_item = note_item      # сохраняем объект ноты
        self.current_note_await_time = time.time()
        self.space_pressed_in_window = False
        threading.Thread(target=self._check_window_timeout, daemon=True).start()

    def stop(self):
        with self.lock:
            self.active_audio_notes.clear()
            self.current_note_name = None
        self.stream.stop()
        self.stream.close()


player = PianoPlayer(note_cache, SAMPLE_RATE)
