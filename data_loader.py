import streamlit as st
import json

@st.cache_data
def load_participant_sentence_order(user: int) -> list:
    """Load participant sentence order from JSON file."""
    with open("assets/participant_sentence_order.json", "r", encoding="utf-8") as f:
        participant_sentence_order = json.load(f)
    return participant_sentence_order.get(str(user), [])

def determine_avatar_order(user: int) -> list:
    """Determine avatar order based on user ID."""
    if user % 2 == 1:
        return [1, 2, 3, 4]
    return [1, 3, 2, 4]

@st.cache_data
def load_video(sentence_order: list, user: int, lesson: int):
    """Load video file path based on user and lesson."""
    avatar_order = determine_avatar_order(user)
    video_path = f"assets/learning_database/{sentence_order[lesson-1]}-{avatar_order[lesson-1]}.mp4"
    st.video(video_path)

@st.cache_data
def load_text(sentence_order: list, lesson: int):
    """Load text file content based on user and lesson."""
    txt = ""
    with open(f"assets/learning_database/{sentence_order[lesson-1]}.txt", "r", encoding="utf-8") as f:
        txt = f.read()
    st.html(f"<h2 style='text-align: center; color: white;'>{txt}</h2>")
    return txt

@DeprecationWarning
def load_ai_history(user:int, lesson:int):
    """Load AI feedback history for the user."""
    history = []
    try:
        with open(f"assets/{user}/ai_feedback/history.txt", "r", encoding="utf-8") as f:
            history = f.readlines()
    except FileNotFoundError:
        st.warning("No AI feedback history found.")
    return history

@st.cache_data
def load_system_prompt(file_path: str = "system_prompt.txt"):
    """Load system prompt from file."""
    with open(file_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()
    
    return system_prompt

def update_user_prompt(sentence, lowest_word_phonemes: dict):
    """Update user prompt based on lowest scoring words and phonemes."""
    user_prompt = f"""
    練習の文：{sentence}
    あなたは system prompt で定義された「英語発音改善アシスタント」として、前回までの傾向も踏まえ、学習者に最適なフィードバックを日本語で返してください。
    返答では、単語の再提示・具体的アドバイス・簡潔な練習指示を含め、自然で励ましのある口調を保ってください。
    """
    user_prompt += str(lowest_word_phonemes)
    return user_prompt

def update_summary_prompt(scores_history, errors_history):
    """Create a summary prompt for AI Summary."""
    summary_prompt = f"""
    あなたは system prompt で定義された「学習者の発音成績サマライザー」として、日本語で返してください。
    3段落構成：①成果ハイライト ②推移の要約 ③停滞・ばらつきの観測
    発音スコアの歴史データ{scores_history}
    発音エラーの歴史データ{errors_history}
    """
    return summary_prompt
