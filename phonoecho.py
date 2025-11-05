import streamlit as st
import pandas as pd
import json
from initialize import (
    reset_page_padding,
    initialize_session_state,
    refresh_page_to_remove_ghost,
    update_scores_history,
    update_errors_history
)
from data_loader import load_video, load_text, update_user_prompt, update_summary_prompt
from ai_feedback import (
    get_ai_feedback,
    get_pronunciation_assessment,
    save_pronunciation_assessment,
    parse_pronunciation_assessment,
)
from audio_process import save_audio_to_file
from chart import (
    create_radar_chart,
    create_syllable_table,
    create_waveform_plot,
    create_doughnut_chart,
    plot_overall_score,
    plot_detail_scores,
    create_metric_cards
)

from tools import delete_none_ai_history, has_pronunciation_errors

reset_page_padding()

with st.sidebar:
    st.title("PhonoEcho")
    with st.form("user_lesson_form"):
        user = st.number_input("ユーザー番号", min_value=1, max_value=24, value=1, step=1)
        lesson = st.number_input("レッスン番号", min_value=1, max_value=4, value=1, step=1)
        load_new_resources = st.form_submit_button("ロードする")
        if load_new_resources:
            for key in list(st.session_state.keys()):
                del st.session_state[key]

initialize_session_state(st.session_state, user, lesson)                

# Clean up any messages with None content (safety measure)
delete_none_ai_history(st.session_state, "ai_messages")
delete_none_ai_history(st.session_state, "ai_summary_messages")

tabs = st.tabs(["ラーニング", "発音の可視化", "まとめ"])

with tabs[0]:
    cols = st.columns([0.6, 0.4])

    with cols[0]:
        # load video and text and display
        load_video(st.session_state.sentence_order, user, lesson)
        reference_text = load_text(st.session_state.sentence_order, lesson)

        with st.form("audio_input"):
            audio_bytes_io = st.audio_input(f"音声を録音してみよう", sample_rate=48000)
            pronunciation_assessment_result = None

            submitted = st.form_submit_button("練習しよう！")
            if submitted:
                # Get pronunciation assessment
                st.session_state.practice_times += 1
                audio_file_path = f"assets/history_database/{user}/{lesson}-{st.session_state.practice_times}.wav"
                # save_audio_to_file will make sure the directory exists
                save_audio_to_file(audio_bytes_io, filename=audio_file_path)
                pronunciation_assessment_result = get_pronunciation_assessment(user, st.session_state.pronunciation_config, reference_text, audio_file_path)
                with open(f"assets/history_database/{user}/{lesson}-{st.session_state.practice_times}.json", "w", encoding="utf-8") as f:
                    json.dump(pronunciation_assessment_result, f, ensure_ascii=False, indent=4)
                scores_dict, errors_dict, lowest_word_phonemes_dict = parse_pronunciation_assessment(pronunciation_assessment_result)
                update_scores_history(st.session_state, scores_dict)
                update_errors_history(st.session_state, errors_dict)

                # For testing without re-recording audio
                # st.session_state.practice_times += 1
                # audio_file_path = f"assets/{user}/history/{lesson}-{1}.wav"
                # with open(f"assets/{user}/history/{lesson}-{1}.json", "r", encoding="utf-8") as f:
                #     pronunciation_assessment_result = json.load(f)
                # scores_dict, errors_dict, lowest_word_phonemes_dict = (
                #     parse_pronunciation_assessment(pronunciation_assessment_result)
                # )
                # update_scores_history(st.session_state, scores_dict)
                # update_errors_history(st.session_state, errors_dict)

                # Get AI feedback and write it streamingly later
                user_prompt = update_user_prompt(
                    reference_text, lowest_word_phonemes_dict
                )
                st.session_state.ai_messages.append(
                    {"role": "user", "content": user_prompt}
                )

                ai_feedback_generator = get_ai_feedback(
                    st.session_state.openai_client,
                    st.session_state.ai_messages,
                )

                # Get AI summary and write it streamingly later
                summary_prompt = update_summary_prompt(
                    st.session_state.scores_history, st.session_state.errors_history
                )
                st.session_state.ai_summary_messages.append(
                    {"role": "user", "content": summary_prompt}
                )
                ai_summary_generator = get_ai_feedback(
                    st.session_state.openai_client,
                    st.session_state.ai_summary_messages,
                )

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

        # 2. metric cards for scores
        with st.container(
            height=150, horizontal_alignment="center", vertical_alignment="center"):
            if pronunciation_assessment_result is not None:
                create_metric_cards(st.session_state.practice_times, st.session_state.scores_history)
            else:
                st.html("<h1 style='text-align: center;'>スコアカード</h1>")

        # 3. create and display current errors doughnut chart
        with st.container(
            height=350, horizontal_alignment="center", vertical_alignment="center"
        ):
            if pronunciation_assessment_result is not None:
                if has_pronunciation_errors(errors_dict):
                    current_errors_chart = create_doughnut_chart(errors_dict, "今回の練習")
                    st.altair_chart(current_errors_chart, use_container_width=True)
                else:
                    st.image("assets/Goodjob_stickman.gif")
            else:
                st.html("<h1 style='text-align: center;'>発音誤りの円グラフ</h1>")

with tabs[1]:
    waveform_plot_col, ai_col = st.columns([0.6, 0.4])
    with waveform_plot_col:
        with st.container(height=500):
            if pronunciation_assessment_result is not None:
                # this function is under fragment decorator in chart.py
                create_waveform_plot(st.session_state.sentence_order, user, lesson, st.session_state.practice_times, lowest_word_phonemes_dict, pronunciation_assessment_result)
            else:
                st.html(
                    "<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px;'><h1 style='text-align: center;'>AIフィードバック</h1></div>"
                )
    with ai_col:
        with st.container(height=500):
            if pronunciation_assessment_result is not None:

                ai_response = st.write_stream(ai_feedback_generator)
                # write ai feedback in streaming mode
                st.session_state.ai_messages.append(
                    {"role": "assistant", "content": ai_response}
                )
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
            st.html("<h1 style='text-align: center;'>音節的な発音の統計表</h1>")

with tabs[2]:
    inner_cols = st.columns(2)

    with inner_cols[0]:
        with st.container(
            height=350, horizontal_alignment="center", vertical_alignment="center"
        ):
            if pronunciation_assessment_result is not None:
                overall_score_chart = plot_overall_score(st.session_state.scores_history)
                st.altair_chart(overall_score_chart, use_container_width=True)
            else:
                st.html("<h1 style='text-align: center;'>全体スコアの推移</h1>")
        with st.container(
            height=400, horizontal_alignment="center", vertical_alignment="center"
        ):
            # errors_history is always available from session_state
            if pronunciation_assessment_result is not None:
                if has_pronunciation_errors(st.session_state.errors_history):
                    total_errors_chart = create_doughnut_chart(
                        st.session_state.errors_history, "総合"
                    )
                    st.altair_chart(total_errors_chart, use_container_width=True)
                else:
                    st.image("assets/Goodjob_stickman.gif")
            else:
                st.html("<h1 style='text-align: center;'>総合エラー数</h1>")

    with inner_cols[1]:
        with st.container(
            height=350, horizontal_alignment="center", vertical_alignment="center"
        ):
            if pronunciation_assessment_result is not None:
                detail_scores_chart = plot_detail_scores(st.session_state.scores_history)
                st.altair_chart(detail_scores_chart, use_container_width=True)
            else:
                st.html("<h1 style='text-align: center;'>詳細スコアの推移</h1>")

        with st.container(
            height=400, horizontal_alignment="center", vertical_alignment="center"
        ):
            if pronunciation_assessment_result is not None:
                ai_summary_response = st.write_stream(ai_summary_generator)
                # write ai feedback in streaming mode
                st.session_state.ai_summary_messages.append(
                    {"role": "assistant", "content": ai_summary_response}
                )
            else:
                st.html(
                    "<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px;'><h1 style='text-align: center;'>AIフィードバック</h1></div>"
                )

refresh_page_to_remove_ghost(st.session_state)
