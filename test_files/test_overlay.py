import streamlit as st

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


reset_page_padding()
tabs =  st.tabs(["Tab1", "Tab2", "Tab3"])

with tabs[0]:
    st.markdown("## AIフィードバック")
    st.video("assets/1/resources/1.mp4")
    audio_io = st.audio_input("音声を録音してみよう", sample_rate=48000)
    if audio_io:
        st.audio(audio_io, format="audio/wav")
with tabs[1]:
    st.markdown("## AIフィードバック")

with tabs[2]:
    st.markdown("### 全体スコアの推移")
    st.markdown("### 詳細スコアの推移")
    st.markdown("### 今回の練習")
    st.markdown("### 総合エラー数")
