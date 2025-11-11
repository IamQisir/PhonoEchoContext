"""
Batch pronunciation assessment script for audio files.
This script processes multiple audio files and generates pronunciation assessment JSON files.
"""

import os
import json
import azure.cognitiveservices.speech as speechsdk


def get_pronunciation_assessment_batch(speech_key, speech_region, reference_text, audio_file_path):
    """Get pronunciation assessment from Azure Speech Service (without Streamlit dependency).
    
    Args:
        speech_key (str): Azure Speech API key
        speech_region (str): Azure Speech region
        reference_text (str): Reference text for pronunciation assessment
        audio_file_path (str): Path to the audio file
        
    Returns:
        dict: Pronunciation assessment result as JSON
    """
    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key,
            region=speech_region,
        )
        audio_input = speechsdk.AudioConfig(filename=audio_file_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_input
        )
        
        # Configure pronunciation assessment
        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True
        )
        pronunciation_config.enable_prosody_assessment()
        pronunciation_config.phoneme_alphabet = "IPA"
        
        pronunciation_config.apply_to(recognizer)

        result = recognizer.recognize_once_async().get()
        pronunciation_result = json.loads(
            result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
        )

        return pronunciation_result
    except Exception as e:
        print(f"Error during pronunciation assessment for {audio_file_path}: {e}")
        return None


def save_pronunciation_assessment(pronunciation_result, filepath):
    """Save pronunciation assessment result to a JSON file.
    
    Args:
        pronunciation_result (dict): Pronunciation assessment result
        filepath (str): Path to save the JSON file
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(pronunciation_result, f, ensure_ascii=False, indent=4)
        print(f"✓ Saved: {filepath}")
    except Exception as e:
        print(f"✗ Error saving {filepath}: {e}")


def process_audio_files(speech_key, speech_region, base_path, file_configs):
    """Process multiple audio files and generate pronunciation assessments.
    
    Args:
        speech_key (str): Azure Speech API key
        speech_region (str): Azure Speech region
        base_path (str): Base path for resources
        file_configs (list): List of dicts with 'audio_file', 'text_file', 'output_file'
    """
    print("=" * 60)
    print("Starting Batch Pronunciation Assessment")
    print("=" * 60)
    
    for idx, config in enumerate(file_configs, 1):
        audio_file = os.path.join(base_path, config['audio_file'])
        text_file = os.path.join(base_path, config['text_file'])
        output_file = os.path.join(base_path, config['output_file'])
        
        print(f"\n[{idx}/{len(file_configs)}] Processing: {config['audio_file']}")
        
        # Check if audio file exists
        if not os.path.exists(audio_file):
            print(f"✗ Audio file not found: {audio_file}")
            continue
        
        # Read reference text
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                reference_text = f.read().strip()
            print(f"Reference text: {reference_text}")
        except Exception as e:
            print(f"✗ Error reading text file {text_file}: {e}")
            continue
        
        # Get pronunciation assessment
        result = get_pronunciation_assessment_batch(
            speech_key, 
            speech_region, 
            reference_text, 
            audio_file
        )
        
        if result:
            save_pronunciation_assessment(result, output_file)
        else:
            print(f"✗ Failed to get assessment for {audio_file}")
    
    print("\n" + "=" * 60)
    print("Batch Processing Completed")
    print("=" * 60)


def main():
    """Main function to run batch pronunciation assessment."""

    # You need to set your Azure credentials here or load from environment/config
    # Option 1: Set directly (NOT recommended for production)
    SPEECH_KEY = "YOUR_SPEECH_KEY_HERE"
    SPEECH_REGION = "YOUR_SPEECH_REGION_HERE"

    # Option 2: Load from environment variables (recommended)
    # import os
    # SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
    # SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

    # Option 3: Load from Streamlit secrets (if available)
    try:
        import streamlit as st
        SPEECH_KEY = st.secrets["Azure_Speech"]["SPEECH_KEY"]
        SPEECH_REGION = st.secrets["Azure_Speech"]["SPEECH_REGION"]
        print("✓ Loaded credentials from Streamlit secrets")
    except:
        print("⚠ Could not load from Streamlit secrets, using manual config")
        if SPEECH_KEY == "YOUR_SPEECH_KEY_HERE":
            print("✗ ERROR: Please configure your Azure Speech credentials in the script!")
            return

    # Base path for resources
    # base_path = r"c:\Users\Chyis\Documents\Code\PhonoEchoContext\assets\learning_database"
    base_path = (
        r"c:\Users\Chyis\Documents\Code\PhonoEchoContext\assets\history_database\0"
    )

    # Configure files to process
    file_configs = [
        {"audio_file": "1-1.wav", "text_file": "s0.txt", "output_file": "s0.json"},
        # {"audio_file": "1.wav", "text_file": "1.txt", "output_file": "1.json"},
        # {"audio_file": "2.wav", "text_file": "2.txt", "output_file": "2.json"},
        # {"audio_file": "3.wav", "text_file": "3.txt", "output_file": "3.json"},
        # {"audio_file": "4.wav", "text_file": "4.txt", "output_file": "4.json"},
    ]

    # Process all files
    process_audio_files(SPEECH_KEY, SPEECH_REGION, base_path, file_configs)


if __name__ == "__main__":
    main()
