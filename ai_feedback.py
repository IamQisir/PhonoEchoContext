import time
import json
from openai import AzureOpenAI
import streamlit as st
from initialize import init_openai_client
import azure.cognitiveservices.speech as speechsdk

def get_pronunciation_assessment(user, pronunciation_config, reference_text, audio_file_path):
    """Get pronunciation assessment from Azure Speech Service."""
    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=st.secrets["Azure_Speech"]["SPEECH_KEY"],
            region=st.secrets["Azure_Speech"]["SPEECH_REGION"]
        )
        audio_input = speechsdk.AudioConfig(filename=audio_file_path)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)
        pronunciation_config.reference_text = reference_text
        st.session_state.pronunciation_config = pronunciation_config

        pronunciation_config.apply_to(recognizer)

        result = recognizer.recognize_once_async().get()
        pronunciation_result = json.loads(result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult))

        return pronunciation_result
    except Exception as e:
        st.error(f"Error during pronunciation assessment: {e}")
        return None

def save_pronunciation_assessment(pronunciation_result, filepath):
    """Save pronunciation assessment result to a JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(pronunciation_result, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Error saving pronunciation assessment: {e}")

@DeprecationWarning
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


def test_pronunciation_assessment():
    from initialize import initialize_azure
    pronunciation_config = initialize_azure()
    user = 1
    reference_text = "Good morning! Can you tell me who you are?"
    audio_file_path = f"asset/1/history/9.wav"  # Replace with actual path to a test audio file

    result = get_pronunciation_assessment(user, pronunciation_config, reference_text, audio_file_path)
    if result:
        st.write("Pronunciation Assessment Result:")
        st.json(result)
    else:
        st.write("No pronunciation assessment result received.")
