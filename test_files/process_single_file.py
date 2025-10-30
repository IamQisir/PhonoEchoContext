"""
Single file pronunciation assessment script.
"""

import os
import json
import azure.cognitiveservices.speech as speechsdk


def get_pronunciation_assessment_batch(speech_key, speech_region, reference_text, audio_file_path):
    """Get pronunciation assessment from Azure Speech Service."""
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
            enable_miscue=False
        )
        pronunciation_config.enable_prosody_assessment()
        pronunciation_config.phoneme_alphabet = "IPA"
        
        pronunciation_config.apply_to(recognizer)

        print("Processing audio file...")
        result = recognizer.recognize_once_async().get()
        pronunciation_result = json.loads(
            result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
        )

        return pronunciation_result
    except Exception as e:
        print(f"Error during pronunciation assessment: {e}")
        return None


def main():
    """Process only the 4th file."""
    
    # Load from Streamlit secrets
    try:
        import streamlit as st
        SPEECH_KEY = st.secrets["Azure_Speech"]["SPEECH_KEY"]
        SPEECH_REGION = st.secrets["Azure_Speech"]["SPEECH_REGION"]
        print("✓ Loaded credentials from Streamlit secrets")
    except:
        print("✗ Could not load credentials")
        return
    
    base_path = r"c:\Users\Chyis\Documents\Code\PhonoEchoContext\assets\1\resources"
    
    audio_file = os.path.join(base_path, '4.wav')
    text_file = os.path.join(base_path, '4.txt')
    output_file = os.path.join(base_path, '4.json')
    
    # Read reference text
    with open(text_file, 'r', encoding='utf-8') as f:
        reference_text = f.read().strip()
    
    print(f"Audio: {audio_file}")
    print(f"Reference text: {reference_text}")
    
    # Get pronunciation assessment
    result = get_pronunciation_assessment_batch(
        SPEECH_KEY, 
        SPEECH_REGION, 
        reference_text, 
        audio_file
    )
    
    if result:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"✓ Saved: {output_file}")
    else:
        print(f"✗ Failed to get assessment")


if __name__ == "__main__":
    main()
