import streamlit as st
from streamlit_advanced_audio import audix, CustomizedRegion, RegionColorOptions
from initialize import reset_page_padding, initialize_session_state
from data_loader import load_video, load_text
from ai_feedback import (
    get_pronunciation_assessment,
    save_pronunciation_assessment,
    generate_ai_feedback_streaming,
)
from audio_process import save_audio_to_file
from chart import create_radar_chart

# NEW: Use simple AI feedback - no complex pipeline!
from ai_feedback import generate_ai_feedback

reset_page_padding()

with st.sidebar:
    st.title("PhonoEcho")
    user = st.number_input("ユーザー番号", min_value=1, max_value=24, value=1, step=1)
    lesson = st.number_input("レッスン", min_value=1, max_value=4, value=1, step=1)

# Initialize session state
initialize_session_state(st.session_state, user, lesson)

tabs = st.tabs(["ラーニング", "発音の可視化", "まとめ"])

with tabs[0]:
    cols = st.columns([0.6, 0.4])

    with cols[0]:
        # Load video and text
        load_video(user, lesson)
        reference_text = load_text(user, lesson)

        with st.form("audio_input"):
            audio_bytes_io = st.audio_input(f"音声を録音してみよう", sample_rate=48000)

            submitted = st.form_submit_button("フィードバックをもらおう！")
            if submitted:
                st.session_state.practice_times += 1
                audio_file_path = f"asset/{user}/history/{lesson}-{st.session_state.practice_times}.wav"
                
                # TESTING: Use saved JSON for now
                import json
                with open("asset/1/history/test1.json", "r", encoding="utf-8") as f:
                    pronunciation_assessment_result = json.load(f)
                
                # Save assessment
                assessment_path = f"asset/{user}/history/{lesson}-{st.session_state.practice_times}.json"
                save_pronunciation_assessment(pronunciation_assessment_result, assessment_path)

                # Store for later use in streaming
                st.session_state.current_assessment_result = pronunciation_assessment_result

                # ========== STEP 1: CREATE RADAR CHART FIRST (FAST) ==========
                radar_chart = create_radar_chart(pronunciation_assessment_result)
                st.session_state["feedback"]["radar_chart"] = radar_chart
                st.success("✅ レーダーチャート作成完了！")
                # ========== END STEP 1 ==========

                # ========== STEP 2: GENERATE AI FEEDBACK WITH STREAMING ==========
                # Store attempt info for comparison
                from ai_feedback import extract_pronunciation_errors
                info = extract_pronunciation_errors(pronunciation_assessment_result)
                
                # Mark that AI feedback is being generated
                st.session_state.ai_feedback_generating = True
                st.session_state.ai_feedback_text = None  # Clear previous
                
                # Store info for later comparison
                if info:
                    st.session_state.previous_errors = info['problem_words']
                # ========== END STEP 2 ==========

    with cols[1]:
        # Radar Chart Container
        with st.container(height=400, horizontal_alignment="center", vertical_alignment="center"):
            if st.session_state["feedback"]["radar_chart"] is None:
                st.html("<h1 style='text-align: center;'>レーダーチャート</h1>")
            else:
                st.pyplot(st.session_state["feedback"]["radar_chart"], width=450)

        # ========== AI FEEDBACK CONTAINER WITH STREAMING ==========
        with st.container(height=450):
            if st.session_state.ai_feedback_text is None and not st.session_state.get("ai_feedback_generating", False):
                # Not started yet - centered text
                st.markdown("""
                    <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px;'>
                        <h2 style='text-align: center;'>AIフィードバック</h2>
                    </div>
                """, unsafe_allow_html=True)
                st.info("🎤 音声を録音してフィードバックを受け取りましょう！")
            elif st.session_state.get("ai_feedback_generating", False):
                # Currently generating - show streaming feedback
                st.markdown(f"### 🎯 AIフィードバック (練習 #{st.session_state.practice_times})")
                st.markdown("---")
                
                # Generate AI feedback with streaming
                
                # Use stored assessment result
                if st.session_state.current_assessment_result:
                    # Stream the feedback
                    st.write_stream(generate_ai_feedback_streaming(
                        client=st.session_state.openai_client,
                        azure_json=st.session_state.current_assessment_result,
                        reference_text=reference_text,
                        attempt_number=st.session_state.practice_times,
                        previous_errors=st.session_state.get("previous_errors", None)
                    ))
                    
                    # Mark as complete
                    st.session_state.ai_feedback_generating = False
                    st.session_state.ai_feedback_text = "完了"  # Mark as completed
                else:
                    st.error("評価データが見つかりません")
                    st.session_state.ai_feedback_generating = False
            else:
                # Already generated - show static content
                st.markdown(f"### 🎯 AIフィードバック (練習 #{st.session_state.practice_times})")
                st.markdown("---")
                st.info("✅ フィードバック表示完了（ページを更新すると再表示されます）")
        # ========== END AI FEEDBACK CONTAINER ==========

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
