from datetime import datetime
import soundfile as sf

def save_audio_from_mic(audio_bytes_io, user, lesson):
    if audio_bytes_io:
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{user}/history/{lesson}-{current_time}.wav"
        audio_data, sr = sf.read(audio_bytes_io, dtype="int16")
        sf.write(
            filename, audio_data, sample_rate=48000, format="WAV", subtype="PCM_16"
        )
        return filename
