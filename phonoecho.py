import streamlit as st
from initialize import reset_page_padding, initialize_session_state, init_openai_client
from data_loader import load_video, load_text, update_user_prompt
from ai_feedback import (
    get_ai_feedback,
    get_pronunciation_assessment,
    save_pronunciation_assessment,
    parse_pronunciation_assessment,
)
from audio_process import save_audio_to_file
from chart import create_radar_chart, create_syllable_table, create_waveform_plot

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

                with open("asset/1/history/1-2.json", "rb") as f:
                    pronunciation_assessment_result = json.load(f)
                # save_pronunciation_assessment(pronunciation_assessment_result, f"asset/{user}/history/{lesson}-{st.session_state.practice_times}.json")

    with cols[1]:
        # 1. create and display radar chart
        with st.container(
            height=400, horizontal_alignment="center", vertical_alignment="center"
        ):
            if pronunciation_assessment_result is not None:
                radar_chart = create_radar_chart(pronunciation_assessment_result)
                st.session_state["feedback"]["radar_chart"] = radar_chart
                st.pyplot(radar_chart, width=450)
            else:
                st.html("<h1 style='text-align: center;'>レーダーチャート</h1>")

        # 2. create and display AI feedback
        with st.container(height=450):
            if pronunciation_assessment_result is not None:
                scores_dict, errors_dict, lowest_word_phonemes_dict = parse_pronunciation_assessment(pronunciation_assessment_result)
                
                # user_prompt = update_user_prompt(lowest_word_phonemes_dict)
                # st.session_state.ai_messages.append(
                #     {"role": "user", "content": user_prompt}
                # )
                # ai_response = get_ai_feedback(
                #     st.session_state.openai_client,
                #     st.session_state.ai_messages,
                # )
                # st.session_state.ai_messages.append(
                #     {"role": "assistant", "content": ai_response}
                # )
                # st.write(ai_response)

            else:
                st.html(
                    "<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px;'><h1 style='text-align: center;'>AIフィードバック</h1></div>"
                )

with tabs[1]:
    with st.container(height=500):
        if pronunciation_assessment_result is not None:
            create_waveform_plot()
        else:
            st.html(
                "<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px;'><h1 style='text-align: center;'>AIフィードバック</h1></div>"
            )
    with st.container(
        height=300, horizontal_alignment="center", vertical_alignment="center"
    ):
        if pronunciation_assessment_result is not None:
            syllable_table = create_syllable_table(pronunciation_assessment_result)
            st.html(syllable_table)
        else:
            st.html("<h2 style='text-align: center;'>音節的な発音の統計表</h2>")

# with tabs[2]:
#     st.header("まとめ")
#     inner_cols3 = st.columns(2)

#     with inner_cols3[0]:
#         with st.container(
#             height=400, horizontal_alignment="center", vertical_alignment="center"
#         ):
#             st.html("<h2 style='text-align: center;'>時系列データ1</h2>")
#         with st.container(
#             height=400, horizontal_alignment="center", vertical_alignment="center"
#         ):
#             st.html("<h2 style='text-align: center;'>円グラフ1</h2>")

#     with inner_cols3[1]:
#         with st.container(
#             height=400, horizontal_alignment="center", vertical_alignment="center"
#         ):
#             st.html("<h2 style='text-align: center;'>時系列データ2</h2>")
#         with st.container(
#             height=400, horizontal_alignment="center", vertical_alignment="center"
#         ):
#             st.html("<h2 style='text-align: center;'>円グラフ2</h2>")
