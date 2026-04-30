import time

import numpy as np
import sounddevice as sd
from scipy.signal import butter, filtfilt


class GentlePiano:
    def __init__(self, sample_rate=44100):
        self.sr = sample_rate
        # Предварительный фильтр для всех нот (срез низких частот)
        # Фильтр Баттерворта 2-го порядка, частота среза 80 Гц
        self.b_hpf, self.a_hpf = butter(2, 80 / (self.sr / 2), btype="high")

    def _freq(self, midi):
        return 440.0 * 2.0 ** ((midi - 69) / 12.0)

    def _get_harmonics_amps(self, midi_note):
        # Уменьшаем амплитуды для басов
        if midi_note < 48:  # ниже C3
            factor = 0.4  # басы тише
        elif midi_note > 72:
            factor = 0.8
        else:
            factor = 0.9
        base = [1.0, 0.65, 0.45, 0.30, 0.20, 0.15, 0.12, 0.09, 0.07, 0.05]
        return [a * factor for a in base]

    def _get_decay_rates(self, midi_note):
        # Для басов затухание быстрее, чтобы не гудели
        if midi_note < 48:
            t60_base = 1.0  # было 2.5 -> уменьшили
        elif midi_note > 72:
            t60_base = 0.6
        else:
            t60_base = 1.2
        rates = []
        for i in range(10):
            # высокие гармоники затухают быстрее
            t60 = t60_base / (1 + 0.5 * i)
            tau = t60 / np.log(2)
            rates.append(1.0 / tau)
        return rates

    def generate_note(self, midi_note, duration, velocity=0.6):
        freq = self._freq(midi_note)
        t = np.linspace(0, duration, int(self.sr * duration), endpoint=False)

        harmonics_amps = self._get_harmonics_amps(midi_note)
        decay_rates = self._get_decay_rates(midi_note)

        signal = np.zeros_like(t)
        for i, amp in enumerate(harmonics_amps):
            if amp == 0:
                continue
            harmonic_freq = freq * (i + 1)
            osc = np.sin(2 * np.pi * harmonic_freq * t)
            env = np.exp(-decay_rates[i] * t)
            signal += amp * osc * env

        # Шум атаки (короткий, чтобы не добавлять басов)
        noise = np.random.randn(len(signal)) * 0.2
        noise_env = np.exp(-t / 0.008)
        noise = noise * noise_env
        signal += noise * 0.2

        # ADSR
        attack = 0.003
        decay = 0.05
        sustain = 0.35
        release = 0.08

        attack_s = int(attack * self.sr)
        decay_s = int(decay * self.sr)
        release_s = int(release * self.sr)
        total = len(t)

        envelope = np.ones(total)
        if attack_s > 0:
            envelope[:attack_s] = np.linspace(0, 1, attack_s)
        start = attack_s
        end = min(attack_s + decay_s, total)
        if end > start:
            envelope[start:end] = np.linspace(1, sustain, end - start)
        release_start = max(0, total - release_s)
        if release_start < total:
            envelope[release_start:] = np.linspace(
                envelope[release_start], 0, total - release_start
            )

        signal = signal * envelope * velocity

        # Применяем HPF (убираем излишний бас)
        signal = filtfilt(self.b_hpf, self.a_hpf, signal)

        # Нормализация и мягкое ограничение
        peak = np.max(np.abs(signal))
        if peak > 0:
            signal = signal / peak * 0.95
        signal = np.tanh(signal * 1.1)  # лёгкое насыщение

        return signal.astype(np.float32)

    def play_note(self, midi_note, duration=1, velocity=0.6):
        audio = self.generate_note(midi_note, duration, velocity)
        sd.play(audio, self.sr)
        sd.wait()

    def play_chord(self, notes, duration=1, velocities=None):
        if velocities is None:
            velocities = [0.5] * len(notes)
        total_samples = int(self.sr * duration)
        mix = np.zeros(total_samples)
        for note, vel in zip(notes, velocities):
            audio = self.generate_note(note, duration, vel)
            if len(audio) > total_samples:
                audio = audio[:total_samples]
            else:
                audio = np.pad(audio, (0, total_samples - len(audio)))
            mix += audio
        # Общий лимитер
        peak = np.max(np.abs(mix))
        if peak > 0.95:
            mix = mix / peak * 0.95
        sd.play(mix, self.sr)
        sd.wait()


# Тест
if __name__ == "__main__":
    piano = GentlePiano()
    print("Играем C4 (средняя октава)")
    piano.play_note(60, 1.5)
    time.sleep(0.5)
    print("Играем C2 (бас) - должно быть тише и короче")
    piano.play_note(36, 1.5)
    time.sleep(0.5)
    print("Аккорд C2-E2-G2 (басовый аккорд)")
    piano.play_chord([36, 40, 43], 2)
