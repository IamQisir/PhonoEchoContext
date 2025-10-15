import time
from openai import AzureOpenAI
import streamlit as st
from initialize import init_openai_client

def get_pronunciation_assessment(speech_config, audio_data):
    """Get pronunciation assessment from Azure Speech Service."""
    try:
        audio_input = speechsdk.AudioConfig(stream=speechsdk.AudioDataStream(audio_data))
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text="Good morning. Can you tell me who you are?",
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True
        )
        pronunciation_config.apply_to(recognizer)

        result = recognizer.recognize_once()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result
        else:
            st.error(f"Speech recognition failed: {result.reason}")
            return None
    except Exception as e:
        st.error(f"Error during pronunciation assessment: {e}")
        return None

def get_ai_feedback(client, user_input):
    prompt = f"ユーザーの発音に関するフィードバックを提供してください: {user_input}"
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "あなたは発音の専門家です。"},
                {"role": "user", "content": prompt},
            ],
            stream=True,
        )
        return response
    except Exception as e:
        st.error(f"Error getting AI feedback: {e}")
        return None
    
# test functions
def test_ai_feedback():
    client = init_openai_client()
    if client:
        user_input = "Good morning? Can you tell me who you are?"
        feedback = get_ai_feedback(client, user_input)
        if feedback:
            st.write("AI Feedback:")
            st.write_stream(feedback)
        else:
            st.write("No feedback received.")
    else:
        st.write("OpenAI client initialization failed.")
test_ai_feedback()