import os
import wave
import numpy as np


def generate_sine_wave(frequency, duration, amplitude=0.5, sample_rate=44100):
    """Generates a sine wave for the given frequency and duration."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave_data = (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
    return wave_data


def save_wave(file_path, wave_data, sample_rate=44100):
    """Saves the wave data to a .wav file."""
    with wave.open(file_path, 'w') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 2 bytes per sample
        wf.setframerate(sample_rate)
        wf.writeframes((wave_data * 32767).astype(np.int16).tobytes())


def generate_sounds(output_folder):
    """Generates predefined sounds and saves them in the output folder."""
    os.makedirs(output_folder, exist_ok=True)

    # Warning sound: Alternating high-pitched beeps
    warning_wave = np.concatenate([
        generate_sine_wave(1000, 0.2),
        np.zeros(int(44100 * 0.1)),  # Silence
        generate_sine_wave(1000, 0.2),
        np.zeros(int(44100 * 0.1))
    ])
    save_wave(os.path.join(output_folder, 'warning.wav'), warning_wave)

    # Error sound: Descending tone
    error_wave = np.concatenate([
        generate_sine_wave(1000, 0.3),
        generate_sine_wave(800, 0.3),
        generate_sine_wave(600, 0.3)
    ])
    save_wave(os.path.join(output_folder, 'error.wav'), error_wave)

    # Notification sound: Single short beep
    notification_wave = generate_sine_wave(1200, 0.2)
    save_wave(os.path.join(output_folder, 'notification.wav'), notification_wave)

    # Car horn sound: Dual-tone horn
    horn_wave = np.concatenate([
        generate_sine_wave(440, 0.5, amplitude=0.7),
        generate_sine_wave(550, 0.5, amplitude=0.7)
    ])
    save_wave(os.path.join(output_folder, 'car_horn.wav'), horn_wave)

    print(f"Sounds generated in folder: {output_folder}")


if __name__ == "__main__":
    sounds_folder = os.path.join(os.getcwd(), ".")
    generate_sounds(sounds_folder)
