import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from scipy.ndimage import zoom
import os
import threading
import time
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject, Qt
from PyQt6.QtGui import QPen, QColor
from PyQt6.QtWidgets import QWidget
import time
import threading
from typing import Optional


# Загружаем ОДИН реальный сэмпл пианино C4
SAMPLE_RATE, PIANO_C4 = wavfile.read('single-piano-note-c4_100bpm_C_major.wav')

if PIANO_C4.ndim == 2:
    base_note = PIANO_C4[:, 0].astype(np.float32) / 32768.0
else:
    base_note = PIANO_C4.astype(np.float32) / 32768.0

NOTE_FREQ = {
    'A0': 27.50, 'A#0': 29.14, 'B0': 30.87,
    'C1': 32.70, 'C#1': 34.65, 'D1': 36.71, 'D#1': 38.89,
    'E1': 41.20, 'F1': 43.65, 'F#1': 46.25, 'G1': 49.00, 'G#1': 51.91,
    'A1': 55.00, 'A#1': 58.27, 'B1': 61.74,
    'C2': 65.41, 'C#2': 69.30, 'D2': 73.42, 'D#2': 77.78,
    'E2': 82.41, 'F2': 87.31, 'F#2': 92.50, 'G2': 98.00, 'G#2': 103.83,
    'A2': 110.00, 'A#2': 116.54, 'B2': 123.47,
    'C3': 130.81, 'C#3': 138.59, 'D3': 146.83, 'D#3': 155.56,
    'E3': 164.81, 'F3': 174.61, 'F#3': 185.00, 'G3': 196.00, 'G#3': 207.65,
    'A3': 220.00, 'A#3': 233.08, 'B3': 246.94,
    'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13,
    'E4': 329.63, 'F4': 349.23, 'F#4': 369.99, 'G4': 392.00, 'G#4': 415.30,
    'A4': 440.00, 'A#4': 466.16, 'B4': 493.88,
    'C5': 523.25, 'C#5': 554.37, 'D5': 587.33, 'D#5': 622.25,
    'E5': 659.25, 'F5': 698.46, 'F#5': 739.99, 'G5': 783.99, 'G#5': 830.61,
    'A5': 880.00, 'A#5': 932.33, 'B5': 987.77,
    'C6': 1046.50, 'C#6': 1108.73, 'D6': 1174.66, 'D#6': 1244.51,
    'E6': 1318.51, 'F6': 1396.91, 'F#6': 1479.98, 'G6': 1567.98, 'G#6': 1661.22,
    'A6': 1760.00, 'A#6': 1864.66, 'B6': 1975.53,
    'C7': 2093.00, 'C#7': 2217.46, 'D7': 2349.32, 'D#7': 2489.02,
    'E7': 2637.02, 'F7': 2793.83, 'F#7': 2959.96, 'G7': 3135.96, 'G#7': 3322.44,
    'A7': 3520.00, 'A#7': 3729.31, 'B7': 3951.07,
    'C8': 4186.01
}

# Кеш для всех нот (предвычисляется при старте)
note_cache = {}

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


def precompute_all():
    for name, freq in NOTE_FREQ.items():
        ratio = freq / 261.63  # частота относительно C4
        new_len = int(len(base_note) / ratio)
        if new_len < 1:
            new_len = 1
        # Кубическая интерполяция (хорошее качество)
        arr = zoom(base_note, new_len / len(base_note), order=3).astype(np.float32)
        note_cache[name] = arr.ravel()
    print(f'Предвычислено {len(note_cache)} нот')
precompute_all()
# save_cache()


class PianoPlayer(QObject):

    note_correct = pyqtSignal(object, str)   # передаёт объект ноты и её имя
    note_wrong = pyqtSignal(object, str, bool)

    def __init__(self, note_cache, sample_rate):
        super().__init__()
        self.note_cache = note_cache
        self.sample_rate = sample_rate
        self.active_audio_notes = []
        self.lock = threading.Lock()
        self.current_note_plays = None
        self.current_note_await = None         
        self.current_note_await_time = None    # время старта ожидания
        self.hit_window = 0.8
        self.pre_start_active = False
        self.current_note_item = None 
        self.on_note_correct = None
        self.on_note_wrong = None

        self.space_pressed_in_window = False   # флаг: был ли пробел в окне

        self.stream = sd.OutputStream(
            samplerate=sample_rate,
            channels=1,
            callback=self.audio_callback,
            blocksize=512,
            dtype='float32'
        )
        self.stream.start()


    def play_click(self, duration=0.05, freq=1000, volume=1):
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

    def _get_note_audio(self, note_name, duration, apply_envelope=True):
        base = self.note_cache[note_name]
        target_len = int(SAMPLE_RATE * duration)
        
        if target_len <= len(base):
            audio = base[:target_len].copy()
        else:
            repeats = target_len // len(base) + 1
            audio = np.tile(base, repeats)[:target_len]
            if apply_envelope:
                t = np.arange(target_len)
                envelope = np.exp(-t / (SAMPLE_RATE * duration * 0.3))
                audio *= envelope
        
        return audio


    def play_chord(self, notes, duration, volumes=None):
        if volumes is None:
            volumes = [0.7] * len(notes)
        # Собираем массивы для всех нот
        active_notes = []
        for note, vol in zip(notes, volumes):
            audio = self._get_note_audio(note, duration, apply_envelope=True)  # используем глобальную функцию
            if len(audio) > 0:
                max_val = np.max(np.abs(audio))
                if max_val > 0:
                    audio = audio / max_val * vol
                # Добавляем в активные ноты для одновременного воспроизведения
                active_notes.append({
                    'data': audio,
                    'pos': 0,
                    'vel': 1.0,
                    'note_name': note
                })
        # Добавляем все ноты аккорда одновременно
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


    def check_space_press(self):
        """Вызывается при нажатии пробела извне"""
        if self.current_note_await_time is None:
            print(self.current_note_item, "test")
            self.note_wrong.emit(self.current_note_item, self.current_note_await, False)
            return False
        now = time.time()
        dt = now - self.current_note_await_time
        if dt <= self.hit_window and not self.space_pressed_in_window:
            self.space_pressed_in_window = True
            self.note_correct.emit(self.current_note_item, self.current_note_await)
            return True
        self.note_wrong.emit(self.current_note_item, self.current_note_await, False)
        return False


    def _check_window_timeout(self):
        time.sleep(self.hit_window)
        with self.lock:
            if not self.space_pressed_in_window:
                # Если пробел не был нажат, генерируем сигнал wrong
                self.note_wrong.emit(self.current_note_item, self.current_note_await, True)
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
