import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from scipy import signal

# Загружаем ОДИН реальный сэмпл пианино C4
SAMPLE_RATE, PIANO_C4 = wavfile.read('piano_C4.wav')  # твой файл

NOTE_FREQ = {'C4':261.63,'D4':293.66,'E4':329.63,'F4':349.23,'G4':392.00,'A4':440.00,'B4':493.88,'C5':523.25}

def play_piano_note(note_name, duration):
    """ИГРАЕТ ЛЮБУЮ НОТУ ИЗ ОДНОГО СЭМПЛА"""
    target_freq = NOTE_FREQ[note_name]
    pitch_ratio = target_freq / 261.63  # C4 = 261.63Hz
    
    # Pitch shift с сохранением формы волны
    shifted_rate = int(SAMPLE_RATE / pitch_ratio)
    samples_needed = int(shifted_rate * duration)
    
    # Берём сэмпл и растягиваем/сжимаем
    sample = PIANO_C4[:min(len(PIANO_C4), samples_needed)]
    
    # Интерполяция для плавности
    if len(sample) < samples_needed:
        sample = np.interp(np.linspace(0, len(sample)-1, samples_needed), 
                          np.arange(len(sample)), sample)
    
    # Огибающая длительности
    envelope = np.ones_like(sample)
    fade_out = int(len(sample) * 0.1)
    envelope[-fade_out:] = np.linspace(1, 0, fade_out)
    
    stereo = np.stack([sample * envelope * 0.6, sample * envelope * 0.55], axis=1)
    sd.play(stereo.astype(np.float32), shifted_rate, device=3)

def on_start_clicked(self):
    for tact in self.lay.tacts:
        for notes in tact.notes:
            duration = 60/self.lay.bpm * notes.note_lenght
            play_piano_note(notes.note_name, duration)
