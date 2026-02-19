import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from scipy.ndimage import zoom
import os
import threading
import time
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
# precompute_all()
# save_cache()

def _get_note_audio(note_name, duration, apply_envelope=True):
    """
    Возвращает массив (моно) для заданной ноты и длительности.
    Если apply_envelope=True и массив повторяется, накладывается затухающая огибающая.
    """
    if note_name not in note_cache:
        return np.zeros(0, dtype=np.float32)
    
    base = note_cache[note_name]
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

def play_note(note_name, duration, volume=0.7):
    """Воспроизводит одну ноту заданной длительности."""
    audio = _get_note_audio(note_name, duration, apply_envelope=True)
    if len(audio) == 0:
        return
    
    # Нормализация
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * volume
    
    # Стерео
    stereo = np.stack([audio, audio], axis=1)
    sd.play(stereo, SAMPLE_RATE, blocking=True)

def play_chord(notes, duration, volumes=None):
    """
    Воспроизводит аккорд из списка нот.
    notes: список названий нот (например, ['C4', 'E4', 'G4'])
    duration: длительность в секундах
    volumes: список громкостей для каждой ноты (0..1), если None, то все 0.7
    """
    if volumes is None:
        volumes = [0.7] * len(notes)
    
    # Собираем массивы для всех нот
    arrays = []
    for note, vol in zip(notes, volumes):
        audio = _get_note_audio(note, duration, apply_envelope=True)
        if len(audio) > 0:
            arrays.append(audio * vol)
    
    if not arrays:
        return
    
    # Суммируем (все массивы одной длины, т.к. _get_note_audio возвращает ровно target_len)
    mixed = np.sum(arrays, axis=0)
    
    # Нормализация
    max_val = np.max(np.abs(mixed))
    if max_val > 0:
        mixed = mixed / max_val * 0.9  # небольшой запас
    
    # Стерео
    stereo = np.stack([mixed, mixed], axis=1)
    sd.play(stereo, SAMPLE_RATE, blocking=True)





class PianoPlayer:
    def __init__(self, note_cache, sample_rate):
        self.note_cache = note_cache
        self.sample_rate = sample_rate
        self.active_notes = []          # список активных нот
        self.lock = threading.Lock()    # для потокобезопасности
        self.stream = sd.OutputStream(
            samplerate=sample_rate,
            channels=1,                  # моно (потом можно сделать стерео)
            callback=self.audio_callback,
            blocksize=512,
            dtype='float32'
        )
        self.stream.start()

    def audio_callback(self, outdata, frames, time_info, status):
        outdata.fill(0)
        with self.lock:
            to_remove = []
            for note in self.active_notes:
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
            # Удаляем по индексу, чтобы избежать сравнения массивов
            for note in to_remove:
                try:
                    idx = self.active_notes.index(note)  # index тоже сравнивает, но мы можем использовать is
                    # Но index тоже использует ==. Поэтому лучше использовать удаление по ссылке:
                    self.active_notes = [n for n in self.active_notes if n is not note]
                except ValueError:
                    pass

    def play_note(self, note_name, duration, volume=0.7):
        """
        Запускает ноту с заданной длительностью (в секундах) и громкостью.
        """
        if note_name not in self.note_cache:
            print(f"Нота {note_name} не найдена")
            return
        base = self.note_cache[note_name]
        base = base.ravel()
        print(f"play_note: {note_name}, base shape {base.shape}, ndim {base.ndim}")
        target_len = int(self.sample_rate * duration)

        # Формируем аудиоданные нужной длины
        if target_len <= len(base):
            note_data = base[:target_len].copy()
        else:
            repeats = target_len // len(base) + 1
            note_data = np.tile(base, repeats)[:target_len]
            # Добавляем затухание, чтобы скрыть повторы
            t = np.arange(target_len)
            envelope = np.exp(-t / (self.sample_rate * duration * 0.3))
            note_data *= envelope

        # Нормализуем с учётом громкости
        max_val = np.max(np.abs(note_data))
        if max_val > 0:
            note_data = note_data / max_val * volume

        with self.lock:
            self.active_notes.append({
                'data': note_data,
                'pos': 0,
                'vel': 1.0   # громкость уже встроена в данные
            })

    def stop(self):
        self.stream.stop()
        self.stream.close()








# Пример использования
if __name__ == "__main__":
    player = PianoPlayer(note_cache, SAMPLE_RATE)

    # Играем длинную ноту C4 (1 секунда)
    player.play_note('C4', 1.0, volume=0.7)
    # time.sleep(0.3)          # через 0.3 секунды добавляем E4 на 0.5 секунд
    player.play_note('E4', 0.5, volume=0.6)
    time.sleep(0.5)          # ещё через 0.2 секунды добавляем G4 на 0.5 секунд
    player.play_note('G4', 0.5, volume=0.6)

    # Ждём окончания всех нот
    time.sleep(1.0)
    player.stop()