import streamlit as st

@st.cache_resource
def load_video(user:int, lesson:int):
    """Load video file path based on user and lesson."""
    st.video(f"asset/{user}/video_text/{lesson}.mp4")

@st.cache_data
def load_text(user:int, lesson:int):
    """Load text file content based on user and lesson."""
    txt = ""
    with open(f"asset/{user}/video_text/{lesson}.txt", "r", encoding="utf-8") as f:
        txt = f.read()
    st.html(f"<h2 style='text-align: center; color: white;'>{txt}</h2>")
    return txt

def load_ai_history(user:int, lesson:int):
    """Load AI feedback history for the user."""
    history = []
    try:
        with open(f"asset/{user}/ai_feedback/history.txt", "r", encoding="utf-8") as f:
            history = f.readlines()
    except FileNotFoundError:
        st.warning("No AI feedback history found.")
    return history

@st.cache_data
def load_system_prompt():
    """Load system prompt from file."""
    with open("asset/system_prompt.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read()
    
    return system_prompt

def update_user_prompt(lowest_word_phonemes: dict):
    """Update user prompt based on lowest scoring words and phonemes."""
    user_prompt = """
    あなたは system prompt で定義された「英語発音改善アシスタント」として、前回までの傾向も踏まえ、学習者に最適なフィードバックを日本語で返してください。
    返答では、単語の再提示・具体的アドバイス・簡潔な練習指示を含め、自然で励ましのある口調を保ってください。
    """
    user_prompt += str(lowest_word_phonemes)
    return user_prompt