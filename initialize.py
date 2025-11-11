import streamlit as st
from openai import AzureOpenAI
import azure.cognitiveservices.speech as speechsdk
from data_loader import load_system_prompt, load_participant_sentence_order


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
        enable_miscue=True)
    pronunciation_config.enable_prosody_assessment()
    pronunciation_config.phoneme_alphabet = "IPA"
    return pronunciation_config

def initialize_session_state(session_state, user:int, lesson: int):
    """Initialize session state variables."""
    if "user" not in session_state:
        session_state.user = user
    if "lesson" not in session_state:
        session_state.lesson = lesson   
    if "sentence_order" not in session_state:
        session_state.sentence_order = load_participant_sentence_order(session_state.user)
    if "openai_client" not in session_state:
        session_state.openai_client = init_openai_client()
    if "pronunciation_config" not in session_state:
        session_state.pronunciation_config = initialize_azure()
    if "ai_messages" not in session_state:
        session_state.ai_messages = [
            {"role": "system", "content": load_system_prompt("assets/system_prompt/feedback_system_prompt.txt")}
        ]
    if "practice_times" not in session_state:
        session_state.practice_times = 0
    if "scores_history" not in session_state:
        session_state.scores_history = {
            "PronScore": [],
            "AccuracyScore": [],
            "FluencyScore": [],
            "CompletenessScore": [],
            "ProsodyScore": []
        }
    if "errors_history" not in session_state:
        session_state.errors_history = {}
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
    if "ai_summary_messages" not in session_state:
        session_state.ai_summary_messages = [
            {
                "role": "system",
                "content": load_system_prompt(
                    "assets/system_prompt/feedback_system_prompt.txt"
                ),
            }
        ]

def refresh_page_to_remove_ghost(session_state):
    if "refreshed" not in session_state:
        session_state.refreshed = True
        st.rerun()


def update_scores_history(session_state, scores_dict):
    """Update scores history in session state."""
    for key, value in scores_dict.items():
        if key in session_state.scores_history:
            session_state.scores_history[key].append(value)
        else:
            session_state.scores_history[key] = [value]


def update_errors_history(session_state, errors_dict):
    """Update errors history in session state.

    Args:
        session_state: Streamlit session state object
        errors_dict: Dictionary with error types as keys and lists of words as values
                    Format: {"Omission": ["word1", "word2"], ...}
    """
    for key, value in errors_dict.items():
        # Convert list to count
        count = len(value) if isinstance(value, list) else value

        if key in session_state.errors_history:
            session_state.errors_history[key] += count
        else:
            session_state.errors_history[key] = count
