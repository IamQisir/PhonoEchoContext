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

def extract_timestamps_from_pronunciation_result(pronunciation_result):
    """
    Extract word-level timestamps from pronunciation assessment result.
    
    Args:
        pronunciation_result (dict): JSON result from Azure pronunciation assessment
        
    Returns:
        list: List of dictionaries containing word timestamps in the following format:
              [
                  {
                      "word": str,           # The word text (lowercase)
                      "start_time": float,   # Start time in seconds
                      "end_time": float,     # End time in seconds
                      "duration": float      # Duration in seconds
                  },
                  ...
              ]
              Returns empty list if extraction fails.
    
    Note:
        - Uses list structure to preserve word order and handle repeated words
        - Converts Azure ticks (10,000,000 ticks per second) to seconds
        - All word texts are converted to lowercase for consistency
    """
    timestamps = []  
    try:
        nbest = pronunciation_result.get("NBest", [])
        if not nbest:
            return timestamps
        
        words = nbest[0].get("Words", [])
        for word in words:
            start_time_ticks = word.get("Offset", 0)
            duration_ticks = word.get("Duration", 0)
            start_time_sec = start_time_ticks / 10000000  # Convert ticks to seconds
            duration_sec = duration_ticks / 10000000
            end_time_sec = start_time_sec + duration_sec
            
            timestamps.append({
                "word": word.get("Word", "").lower(),
                "start_time": round(start_time_sec, 3),
                "end_time": round(end_time_sec, 3),
                "duration": round(duration_sec, 3)
            })
    except Exception as e:
        print(f"Error extracting timestamps: {e}")
    
    return timestamps

import json
import streamlit as st
from streamlit_advanced_audio import audix, CustomizedRegion, RegionColorOptions

# with open("asset/1/video_text/2.json", "r", encoding="utf-8") as f:
#     pronunciation_result = json.load(f)
# timestamps = extract_timestamps_from_pronunciation_result(pronunciation_result)
# with open("timestamps.json", "w", encoding="utf-8") as f:
#     json.dump(timestamps, f, ensure_ascii=False, indent=4)


audix("asset/1/video_text/2.wav", sample_rate=48000, start_time=0.19, end_time=0.576)
audix("asset/1/video_text/3.wav", sample_rate=48000, start_time=1.52, end_time=2.05)
