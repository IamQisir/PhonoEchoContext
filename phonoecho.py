import streamlit as st
from streamlit_advanced_audio import audix, CustomizedRegion, RegionColorOptions
from initialize import reset_page_padding, initialize_session_state, init_openai_client
from data_loader import load_video, load_text
from ai_feedback import (
    get_ai_feedback,
    get_pronunciation_assessment,
    save_pronunciation_assessment,
)
from audio_process import save_audio_to_file
from chart import create_radar_chart, create_syllable_table

reset_page_padding()

with st.sidebar:
    st.title("PhonoEcho")
    user = st.number_input("ユーザー番号", min_value=1, max_value=24, value=1, step=1)
    lesson = st.number_input("レッスン", min_value=1, max_value=4, value=1, step=1)


initialize_session_state(st.session_state, user, lesson)


tabs = st.tabs(["ラーニング", "発音の可視化", "まとめ"])

with tabs[0]:
    cols = st.columns([0.6, 0.4])

    with cols[0]:
        # load video and text and display
        load_video(user, lesson)
        reference_text = load_text(user, lesson)

        with st.form("audio_input"):
            audio_bytes_io = st.audio_input(f"音声を録音してみよう", sample_rate=48000)
            pronunciation_assessment_result = None

            submitted = st.form_submit_button("フィードバックをもらおう！")
            if submitted:
                # Get pronunciation assessment
                st.session_state.practice_times += 1
                # audio_file_path = f"asset/{user}/history/{lesson}-{st.session_state.practice_times}.wav"
                audio_file_path = f"asset/{user}/history/{lesson}-{1}.wav"
                # save_audio_to_file(audio_bytes_io, filename=audio_file_path)
                # pronunciation_assessment_result = get_pronunciation_assessment(user, st.session_state.pronunciation_config, reference_text, audio_file_path)
                import json

                with open("asset/1/history/test1.json", "rb") as f:
                    pronunciation_assessment_result = json.load(f)
                # save_pronunciation_assessment(pronunciation_assessment_result, f"asset/{user}/history/{lesson}-{st.session_state.practice_times}.json")

                # Analyze the result and get AI feedback
                # 1. Radar chart
                radar_chart = create_radar_chart(pronunciation_assessment_result)
                st.session_state["feedback"]["radar_chart"] = radar_chart

    with cols[1]:
        # 1. createa and display radar chart
        with st.container(
            height=400, horizontal_alignment="center", vertical_alignment="center"
        ):
            if pronunciation_assessment_result is not None:
                radar_chart = create_radar_chart(pronunciation_assessment_result)
                st.session_state["feedback"]["radar_chart"] = radar_chart

                if st.session_state["feedback"]["radar_chart"] is None:
                    st.html("<h1 style='text-align: center;'>レーダーチャート</h1>")
                else:
                    st.pyplot(radar_chart, width=450)

        # 2. create and display AI feedback
        with st.container(height=450):
            
            st.html(
                "<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px;'><h1 style='text-align: center;'>AIフィードバック</h1></div>"
            )

with tabs[1]:
    st.header("発音の可視化")

    region_colors = RegionColorOptions(
        interactive_region_color="rgba(160, 211, 251, 0.4)",
        start_to_end_mask_region_color="rgba(160, 211, 251, 0.3)",
    )
    custom_regions = [
        CustomizedRegion(start=6, end=6.5, color="#00b89466"),
        CustomizedRegion(start=7, end=8, color="rgba(255, 255, 255, 0.6)"),
    ]
    audix("asset/1/history/9.wav", key="target")
    result = audix(
        "asset/1/history/9.wav",
        start_time=0.5,
        end_time=5.5,
        mask_start_to_end=True,
        region_color_options=region_colors,
        customized_regions=custom_regions,
        key="user",
    )
    with st.container(
        height=300, horizontal_alignment="center", vertical_alignment="center"
    ):
        if pronunciation_assessment_result is not None:
            syllable_table = create_syllable_table(pronunciation_assessment_result)
            st.html(syllable_table)
        else:
            st.html("<h2 style='text-align: center;'>音節的な発音の統計表</h2>")

with tabs[2]:
    st.header("まとめ")
    inner_cols3 = st.columns(2)

    with inner_cols3[0]:
        with st.container(
            height=400, horizontal_alignment="center", vertical_alignment="center"
        ):
            st.html("<h2 style='text-align: center;'>時系列データ1</h2>")
        with st.container(
            height=400, horizontal_alignment="center", vertical_alignment="center"
        ):
            st.html("<h2 style='text-align: center;'>円グラフ1</h2>")

    with inner_cols3[1]:
        with st.container(
            height=400, horizontal_alignment="center", vertical_alignment="center"
        ):
            st.html("<h2 style='text-align: center;'>時系列データ2</h2>")
        with st.container(
            height=400, horizontal_alignment="center", vertical_alignment="center"
        ):
            st.html("<h2 style='text-align: center;'>円グラフ2</h2>")
