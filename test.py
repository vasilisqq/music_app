import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from scipy import signal
from time import sleep

# Загружаем ОДИН реальный сэмпл пианино C4
SAMPLE_RATE, PIANO_C4 = wavfile.read('C4.wav')  # твой файл

NOTE_FREQ = {
    'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13,
    'E4': 329.63, 'F4': 349.23, 'F#4': 369.99, 'G4': 392.00,
    'G#4': 415.30, 'A4': 440.00, 'A#4': 466.16, 'B4': 493.88
}

NOTE_PARAMS = {note: (SAMPLE_RATE * (freq / 261.63), int(SAMPLE_RATE * 0.5))
               for note, freq in NOTE_FREQ.items()}

def play_piano_note(note_name, duration):
    if note_name not in NOTE_PARAMS:
        print(f"❌ Нет сэмплов для {note_name}")
        return
        
    shifted_rate, samples_needed = NOTE_PARAMS[note_name]
    
    source = PIANO_C4[:, 0] if PIANO_C4.ndim == 2 else PIANO_C4
    sample = np.tile(source, (samples_needed // len(source)) + 1)[:samples_needed]
    
    envelope = np.ones_like(sample, dtype=np.float32)
    fade_out = min(int(len(sample) * 0.15), len(sample)//4)
    envelope[-fade_out:] = np.linspace(1, 0, fade_out)
    
    sample = sample * envelope
    stereo = np.stack([sample * 0.65, sample * 0.58], axis=1)
    stereo /= np.max(np.abs(stereo)) * 1.1
    
    print(f"🎹 {note_name}: {len(stereo)}spl @ {shifted_rate:.0f}Hz")
    
    # ✅ БЛОКИРУЮЩЕЕ воспроизведение!
    sd.play(stereo, shifted_rate, blocking=True)









import sounddevice as sd
from scipy.io import wavfile

# SAMPLE_RATE, PIANO_C4 = wavfile.read('./C4.wav')
# audio_normalized = PIANO_C4.astype(np.float32) / 32768.0  # Ключевой фикс!

# print(f"✅ Сэмпл загружен: {PIANO_C4.shape} сэмплов @ {SAMPLE_RATE}Hz")
# print(f"Амплитуда после нормализации: min={np.min(audio_normalized):.3f}, max={np.max(audio_normalized):.3f}")

# print("🎹 ИГРАЮ C4 нормализованный...")
# sd.play(audio_normalized, samplerate=SAMPLE_RATE)
# sd.wait()
# print("✅ C4 чистый звук!")
