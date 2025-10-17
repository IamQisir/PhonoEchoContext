import streamlit as st
from openai import AzureOpenAI
import azure.cognitiveservices.speech as speechsdk
from data_loader import load_system_prompt


def reset_page_padding():
    """Reset the default padding of the Streamlit page and set layout to wide."""
    st.set_page_config(layout="wide")
    # NEED Discussion: is it the best practice to set padding using st.markdown?
    st.markdown(
        """
        <style>
               .block-container {
                    padding-top: 2rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """,
        unsafe_allow_html=True,
    )

@st.cache_resource
def init_openai_client():
    try:
        client = AzureOpenAI(
            azure_endpoint=st.secrets["AzureGPT"]["AZURE_OPENAI_ENDPOINT"],
            api_key=st.secrets["AzureGPT"]["AZURE_OPENAI_API_KEY"],
            api_version="2024-12-01-preview",
        )
    except Exception as e:
        st.error(f"Error initializing OpenAI client: {e}")
    return client

def initialize_azure():
    """Initialize Azure Speech client."""
    speech_key, service_region = (
        st.secrets["Azure_Speech"]["SPEECH_KEY"],
        st.secrets["Azure_Speech"]["SPEECH_REGION"],
    )

    pronunciation_config = speechsdk.PronunciationAssessmentConfig(
        reference_text="",
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=False)
    pronunciation_config.enable_prosody_assessment()
    pronunciation_config.phoneme_alphabet = "IPA"
    return pronunciation_config


def initialize_session_state(session_state, user:int, lesson: int):
    """Initialize session state variables."""
    if "user" not in session_state:
        session_state.user = user
    if "lesson" not in session_state:
        session_state.lesson = lesson
    if "openai_client" not in session_state:
        session_state.openai_client = init_openai_client()
    if "pronunciation_config" not in session_state:
        session_state.pronunciation_config = initialize_azure()
    if "ai_messages" not in session_state:
        session_state.ai_messages = [
            {"role": "system", "content": load_system_prompt()}
        ]
    if "practice_times" not in session_state:
        session_state.practice_times = 0
    if "feedback" not in session_state:
        session_state.feedback = {
            "result_json": None,
            "radar_chart": None,
            "errors_table": None,
            "example_waveform_plot": None,
            "waveform_plot": None,
            "syllable_table": None,
            "pron_score": None,
        }
