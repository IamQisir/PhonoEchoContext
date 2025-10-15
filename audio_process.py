from datetime import datetime
import soundfile as sf
import os

def save_audio_to_file(audio_bytes_io, filename=None):
    """Save audio data from BytesIO to a WAV file."""
    if audio_bytes_io is None:
        raise ValueError("No audio data provided")
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"recorded_audio_{timestamp}.wav"
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Write the bytes directly to file
    with open(filename, 'wb') as f:
        f.write(audio_bytes_io.getvalue())