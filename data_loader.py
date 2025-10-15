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


