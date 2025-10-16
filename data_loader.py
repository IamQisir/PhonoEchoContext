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