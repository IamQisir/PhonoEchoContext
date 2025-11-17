import streamlit as st
from uuid import uuid4

if "audio_io" not in st.session_state:
    st.session_state["audio_io"] = None

with st.form("audio_input_form"):
    audio_io = st.audio_input("録音ボタンを押して、発音練習を始めましょう！")
    prev_io = st.session_state.get("audio_io")
    st.session_state["audio_io"] = audio_io
    if submit := st.form_submit_button("保存"):
        if audio_io is not None and audio_io != prev_io:
            st.success("録音が保存されました！")
        else:
            st.warning("録音がありません。もう一度試してください。")

