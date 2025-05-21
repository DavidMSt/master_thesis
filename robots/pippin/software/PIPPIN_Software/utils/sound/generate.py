import os

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine
from scipy.io.wavfile import write


# wave_obj = sa.WaveObject.from_wave_file(filename)
# play_obj = wave_obj.play()
# play_obj.wait_done()

def get_library_path():
    """
    Returns the absolute path to the 'library' folder, relative to the script's location.
    Creates the folder if it doesn't exist.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the script's directory
    library_path = os.path.join(script_dir, "library")  # Path to 'library' folder
    os.makedirs(library_path, exist_ok=True)  # Create the folder if it doesn't exist
    return library_path


def generate_robot_connected_sound():
    """Generates a sound to represent a new robot_old connection and saves it in the library folder."""
    library_path = get_library_path()
    filename = os.path.join(library_path, "robot_connected.wav")

    # Create a short rising tone
    tone1 = Sine(440).to_audio_segment(duration=200)  # A4 for 200 ms
    tone2 = Sine(660).to_audio_segment(duration=200)  # E5 for 200 ms
    tone3 = Sine(880).to_audio_segment(duration=200)  # A5 for 200 ms
    sound = tone1 + tone2 + tone3

    sound.export(filename, format="wav")
    print(f"Robot connected sound saved to '{filename}'.")


def generate_robot_disconnected_sound():
    """Generates a sound to represent a robot_old disconnection and saves it in the library folder."""
    library_path = get_library_path()
    filename = os.path.join(library_path, "robot_disconnected.wav")

    # Create a short descending tone
    tone1 = Sine(880).to_audio_segment(duration=200)  # A5 for 200 ms
    tone2 = Sine(660).to_audio_segment(duration=200)  # E5 for 200 ms
    tone3 = Sine(440).to_audio_segment(duration=200)  # A4 for 200 ms
    sound = tone1 + tone2 + tone3

    sound.export(filename, format="wav")
    print(f"Robot disconnected sound saved to '{filename}'.")


def generate_warning_sound():
    """Generates a warning sound and saves it in the library folder."""
    library_path = get_library_path()
    filename = os.path.join(library_path, "warning.wav")

    # Create a pulsing tone for warning
    tone1 = Sine(600).to_audio_segment(duration=150)  # High-pitched tone
    silence = Sine(0).to_audio_segment(duration=150)  # Silence
    tone2 = Sine(600).to_audio_segment(duration=150)
    sound = tone1 + silence + tone2 + silence + tone1

    sound.export(filename, format="wav")
    print(f"Warning sound saved to '{filename}'.")


def generate_error_sound():
    """Generates a distinctive error sound with a buzzer effect and saves it in the library folder."""
    library_path = get_library_path()
    filename = os.path.join(library_path, "error.wav")

    # Parameters for the sound
    sample_rate = 44100  # 44.1 kHz sample rate
    duration = 1.0  # 1 second duration
    freq1 = 880  # First frequency (Hz)
    freq2 = 440  # Second frequency (Hz)

    # Generate the time axis
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    # Create a buzzer-like effect by switching between two frequencies
    wave = 0.5 * (np.sin(2 * np.pi * freq1 * t[:len(t) // 2]) + np.sin(2 * np.pi * freq2 * t[len(t) // 2:]))

    # Add a harsh overdrive effect by clamping the values
    wave = np.clip(wave * 5, -1, 1)

    # Convert to 16-bit PCM format
    audio_data = (wave * 32767).astype(np.int16)

    # Save to file
    write(filename, sample_rate, audio_data)
    print(f"Error sound saved to '{filename}'.")


from pydub import AudioSegment


def generate_empty_mp3(duration_ms=500, output_filename="empty.mp3"):
    """
    Generates an empty MP3 file with the specified duration.

    Parameters:
    duration_ms (int): The duration of the silent MP3 file in milliseconds. Default is 500ms.
    output_filename (str): The name of the output MP3 file. Default is 'empty_sound.mp3'.

    Returns:
    None
    """
    # Create a silent audio segment
    silent_audio = AudioSegment.silent(duration=duration_ms)

    # Export the silent audio as an MP3 file
    silent_audio.export(output_filename, format="mp3")
    print(f"Empty MP3 file generated: {output_filename}")


if __name__ == '__main__':
    generate_empty_mp3()
