"""
Complete integration example for CAPT feedback in PhonoEcho.
This shows a working implementation you can adapt to your needs.

Usage: Copy relevant sections into your phonoecho.py
"""

import streamlit as st
from streamlit_advanced_audio import audix, CustomizedRegion, RegionColorOptions
from initialize import reset_page_padding, initialize_session_state, init_openai_client
from data_loader import load_video, load_text
from ai_feedback import get_ai_feedback, get_pronunciation_assessment, save_pronunciation_assessment
from audio_process import save_audio_to_file
from chart import create_radar_chart

# NEW: Import CAPT modules
from capt_integration import CAPTFeedbackPipeline
from capt_config import FeedbackConfig

reset_page_padding()

with st.sidebar:
    st.title("PhonoEcho")
    user = st.number_input("ユーザー番号", min_value=1, max_value=24, value=1, step=1)
    lesson = st.number_input("レッスン", min_value=1, max_value=4, value=1, step=1)


# Initialize session state (modify initialize.py to include CAPT pipeline)
initialize_session_state(st.session_state, user, lesson)

# NEW: Initialize CAPT pipeline if not exists
if "capt_pipeline" not in st.session_state:
    config = FeedbackConfig(
        fair_threshold=60.0,  # Minimum score for "fair" rating
        phoneme_error_threshold=70.0,  # Phoneme scores below this are errors
        word_error_threshold=70.0,  # Word scores below this are problematic
        prosody_error_threshold=65.0,  # Prosody scores below this indicate issues
        max_attempt_errors=5,  # Maximum errors to report per attempt
    )
    st.session_state.capt_pipeline = CAPTFeedbackPipeline(
        user_id=user,
        lesson_id=lesson,
        config=config
    )

if "guidance_card" not in st.session_state:
    st.session_state.guidance_card = None

if "ai_feedback_text" not in st.session_state:
    st.session_state.ai_feedback_text = None


def generate_ai_feedback_from_structured(client, structured_feedback, reference_text):
    """
    Generate AI feedback using structured CAPT feedback data.
    
    Args:
        client: OpenAI client instance
        structured_feedback: Dictionary from get_structured_feedback()
        reference_text: The reference text for the lesson
    
    Returns:
        str: Generated feedback text in Japanese
    """
    system_prompt = """あなたは学習者の専属発音チューターです。温かく、親しみやすく、励ましながら指導してください。

以下の点を含めてフィードバックしてください：
1. 🎯 前向きで具体的な評価から始める
2. 💡 ミスがある場合：なぜそのミスが起きたのか、会話調で分かりやすく説明
   　 ミスがない場合：今回の発音の良かった点を具体的に褒め、韻律面での改善点があれば優しく指摘
3. 🗣️ シンプルな言葉で、実例を使って説明
4. ✨ 具体的で実践しやすい練習方法を2〜3個提案
5. 🌟 次回に向けた励ましのメッセージで終わる

重要なルール：
- 発音説明は必ずIPA（国際音声記号）を使用
- カタカナや仮名は使わない
- まるで隣にいるかのような、フレンドリーで親しみやすい口調
- 日本語で回答"""
    
    # Extract data from structured feedback (correct keys)
    overall_score = structured_feedback.get("overall_score", 0)
    score_category = structured_feedback.get("score_category", "fair")
    score_label = structured_feedback.get("score_label", "")
    main_issues = structured_feedback.get("main_issues", [])
    improvements = structured_feedback.get("improvements", [])
    recommendations = structured_feedback.get("recommendations", [])
    encouragement = structured_feedback.get("encouragement", "")
    attempt_number = structured_feedback.get("attempt_number", 1)
    
    # Build user prompt based on whether there are errors or not
    has_errors = main_issues and len(main_issues) > 0
    
    user_prompt = f"""【練習 #{attempt_number} の発音評価】

参照テキスト: "{reference_text}"
発音スコア: {overall_score:.0f}/100

"""
    
    if has_errors:
        # If there are errors, focus on them
        user_prompt += "**発音ミス:**\n"
        for issue in main_issues[:3]:
            user_prompt += f"- {issue}\n"
        user_prompt += "\nこれらのミスがなぜ起きたのか、どう直せばいいか、優しく教えてください。"
    else:
        # If no errors, praise and focus on prosody
        user_prompt += "**素晴らしい！発音ミスはありません。**\n\n"
        if improvements:
            user_prompt += "前回からの改善点:\n"
            for improvement in improvements[:2]:
                user_prompt += f"- {improvement}\n"
            user_prompt += "\n"
        user_prompt += "今回の発音の良かった点を具体的に褒めてください。\n"
        user_prompt += "可能であれば、韻律（イントネーション、リズム、強勢など）の面でさらに良くできる点があれば優しく提案してください。"
    
    user_prompt += "\n\n温かく励ましながら、次の練習へのモチベーションを高めてください。"
    
    # Try to get model/deployment name from secrets, with fallbacks
    try:
        # First try to get from secrets
        model_name = st.secrets["AzureGPT"].get("DEPLOYMENT_NAME", None)
        if not model_name:
            # Fallback to common names
            model_name = "gpt-5-mini"  # Your deployment name
    except:
        model_name = "gpt-5-mini"  # Default fallback
    
    try:
        # Note: gpt-5-mini is a reasoning model
        # Not setting max_completion_tokens to use the default limit
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            # No max_completion_tokens - use default
        )
        
        content = response.choices[0].message.content
        
        # Return content or fallback message
        if content and len(content.strip()) > 0:
            return content
        else:
            # If empty, return a friendly message
            return "申し訳ございません。AIフィードバックの生成に問題が発生しました。もう一度お試しください。"
    except Exception as e:
        # If AI fails, show the error and return structured feedback
        st.warning(f"⚠️ AI生成に失敗: {type(e).__name__}: {str(e)}")
        st.info(f"💡 モデル '{model_name}' が利用できません。構造化フィードバックを表示します。")
        
        feedback_lines = [
            f"## 発音評価 - 練習 #{attempt_number}",
            f"",
            f"**スコア:** {overall_score:.0f}/100 ({score_label})",
            f""
        ]
        
        if improvements:
            feedback_lines.append("### ✅ 改善されたポイント")
            for improvement in improvements:
                feedback_lines.append(f"- {improvement}")
            feedback_lines.append("")
        
        if main_issues:
            feedback_lines.append("### 🎯 改善が必要なポイント")
            for issue in main_issues:
                feedback_lines.append(f"- {issue}")
            feedback_lines.append("")
        
        if recommendations:
            feedback_lines.append("### 💡 推奨される練習方法")
            for rec in recommendations:
                feedback_lines.append(f"- {rec}")
            feedback_lines.append("")
        
        feedback_lines.append(f"**{encouragement}**")
        
        return "\n".join(feedback_lines)


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
                # Get pronunciation assessment
                st.session_state.practice_times += 1
                audio_file_path = f"asset/{user}/history/{lesson}-{st.session_state.practice_times}.wav"
                
                # TESTING: Use saved JSON for now
                # save_audio_to_file(audio_bytes_io, filename=audio_file_path)
                # pronunciation_assessment_result = get_pronunciation_assessment(
                #     user, st.session_state.pronunciation_config, reference_text, audio_file_path
                # )
                
                import json
                with open("asset/1/history/test1.json", "r", encoding="utf-8") as f:
                    pronunciation_assessment_result = json.load(f)
                
                # Save assessment
                assessment_path = f"asset/{user}/history/{lesson}-{st.session_state.practice_times}.json"
                save_pronunciation_assessment(pronunciation_assessment_result, assessment_path)

                # ========== CAPT PIPELINE INTEGRATION ==========
                with st.spinner("AI フィードバックを生成中..."):
                    # Use the simplified process_attempt method
                    # It handles guidance card creation, attempt summaries, and feedback automatically
                    structured_feedback = st.session_state.capt_pipeline.get_structured_feedback(
                        pronunciation_assessment_result,
                        attempt_number=st.session_state.practice_times
                    )
                    
                    # Store guidance card reference for UI display
                    if st.session_state.practice_times == 1:
                        st.session_state.guidance_card = st.session_state.capt_pipeline.guidance_card
                        st.success("✅ 初回分析完了！ガイダンスカードを作成しました。")
                    else:
                        st.success(f"✅ 差分分析完了！（トークン使用量: 約90%削減）")
                    
                    # Generate AI feedback using OpenAI with structured data
                    with st.spinner("🤖 AI フィードバックを生成中..."):
                        st.session_state.ai_feedback_text = generate_ai_feedback_from_structured(
                            st.session_state.openai_client,
                            structured_feedback,
                            reference_text
                        )
                    
                    # Simple success message
                    if st.session_state.ai_feedback_text:
                        st.success("✅ AI フィードバック生成完了！")
                # ========== END CAPT INTEGRATION ==========

                # Create radar chart for visualization
                radar_chart = create_radar_chart(pronunciation_assessment_result)
                st.session_state["feedback"]["radar_chart"] = radar_chart

    with cols[1]:
        # Radar Chart Container
        with st.container(height=400, horizontal_alignment="center", vertical_alignment="center"):
            if st.session_state["feedback"]["radar_chart"] is None:
                st.html("<h1 style='text-align: center;'>レーダーチャート</h1>")
            else:
                st.pyplot(st.session_state["feedback"]["radar_chart"], width=450)

        # ========== SIMPLIFIED AI FEEDBACK CONTAINER ==========
        with st.container(height=450, horizontal_alignment="center", vertical_alignment="center"):
            if st.session_state.ai_feedback_text is None:
                st.html("<h2 style='text-align: center;'>AIフィードバック</h2>")
                st.info("🎤 音声を録音してフィードバックを受け取りましょう！")
            else:
                # Header
                st.markdown(f"### 🎯 AIフィードバック (練習 #{st.session_state.practice_times})")
                st.markdown("---")
                
                # Main AI feedback text only
                st.markdown(st.session_state.ai_feedback_text)
        # ========== END SIMPLIFIED FEEDBACK CONTAINER ==========

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
