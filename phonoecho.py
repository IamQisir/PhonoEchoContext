import streamlit as st
from streamlit_advanced_audio import audix, CustomizedRegion, RegionColorOptions
from initialize import reset_page_padding, initialize_session_state, init_openai_client
from data_loader import load_video, load_text
from ai_feedback import get_ai_feedback

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
        load_text(user, lesson)

        with st.form("audio_input"):
            audio_bytes_io = st.audio_input(f"音声を録音してみよう", sample_rate=48000)

            submitted = st.form_submit_button("フィードバックをもらおう！")
            if submitted:
                # TODO: Analysis
                st.write("音声を送信しました")

    with cols[1]:
        with st.container(height=400, horizontal_alignment="center", vertical_alignment="center"):
            st.html("<h1 style='text-align: center;'>レーダーチャート</h1>")

        inner_cols1 = st.columns(2)
        with inner_cols1[0]:
            with st.container(height=150, horizontal_alignment="center", vertical_alignment="center"):
                st.html("<h2 style='text-align: center;'>発音誤りの統計表</h2>")
        with inner_cols1[1]:
            with st.container(height=150, horizontal_alignment="center", vertical_alignment="center"):
                st.html("<h2 style='text-align: center;'>発音スコアのバッジ</h2>")
        
        with st.container(height=350, horizontal_alignment="center", vertical_alignment="center"):
            st.html("<h2 style='text-align: center;'>AIフィードバック</h2>")

with tabs[1]:
    st.header("発音の可視化")
    
    region_colors = RegionColorOptions(
        interactive_region_color="rgba(160, 211, 251, 0.4)",
        start_to_end_mask_region_color="rgba(160, 211, 251, 0.3)"
    )
    custom_regions = [
        CustomizedRegion(start=6, end=6.5, color="#00b89466"),
        CustomizedRegion(start=7, end=8, color="rgba(255, 255, 255, 0.6)")
    ]
    audix("asset/1/history/9.wav", key="target")
    result = audix(
        "asset/1/history/9.wav",
        start_time=0.5,
        end_time=5.5,
        mask_start_to_end=True,
        region_color_options=region_colors,
        customized_regions=custom_regions,
        key="user"
    )
    with st.container(height=300, horizontal_alignment="center", vertical_alignment="center"):
        st.html("<h2 style='text-align: center;'>音節的な発音の統計表</h2>")

with tabs[2]:
    st.header("まとめ")
    inner_cols3 = st.columns(2)
    
    with inner_cols3[0]:
        with st.container(height=400, horizontal_alignment="center", vertical_alignment="center"):
            st.html("<h2 style='text-align: center;'>時系列データ1</h2>")
        with st.container(height=400, horizontal_alignment="center", vertical_alignment="center"):
            st.html("<h2 style='text-align: center;'>円グラフ1</h2>")

    with inner_cols3[1]:
        with st.container(height=400, horizontal_alignment="center", vertical_alignment="center"):
            st.html("<h2 style='text-align: center;'>時系列データ2</h2>")
        with st.container(
            height=400, horizontal_alignment="center", vertical_alignment="center"
        ):
            st.html("<h2 style='text-align: center;'>円グラフ2</h2>")
