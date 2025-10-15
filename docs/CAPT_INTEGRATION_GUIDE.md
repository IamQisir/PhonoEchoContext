# CAPT Feedback Integration Guide for PhonoEcho

## Overview
This guide shows how to integrate the CAPT (Computer-Assisted Pronunciation Training) feedback pipeline into your `phonoecho.py` Streamlit app, specifically displaying results in the "AIフィードバック" container.

## Integration Strategy

The CAPT pipeline reduces token usage from ~8000 to ~800 (90% reduction) by:
1. **First attempt**: Parse full Azure JSON → create stable **Guidance Card** (saved once)
2. **Subsequent attempts**: Parse incrementally → create **Attempt Summary** (lighter payload)
3. **Generate feedback**: Use GPT with the compact data structures

---

## 🎯 Implementation Ideas

### Idea 1: **Progressive Feedback Display** (Recommended)
Show different feedback types based on practice attempt number:
- **First attempt**: Comprehensive guidance with all error types and patterns
- **Subsequent attempts**: Focused feedback on specific improvements

### Idea 2: **Tabbed Feedback Interface**
Display multiple feedback views in tabs within the AIフィードバック container:
- 📊 Overview
- 🎯 Focus Areas
- 💡 Practice Tips
- 📈 Progress

### Idea 3: **Interactive Feedback Cards**
Show expandable cards for each error category with examples and tips.

### Idea 4: **Comparative Feedback**
Compare current attempt with previous attempt to show improvement.

---

## 📝 Step-by-Step Integration

### Step 1: Import CAPT Modules
Add to the top of `phonoecho.py`:

```python
from capt_integration import CAPTFeedbackPipeline
from capt_config import FeedbackConfig
```

### Step 2: Initialize CAPT Pipeline
Add to `initialize_session_state()` in `initialize.py`:

```python
if "capt_pipeline" not in session_state:
    config = FeedbackConfig(
        fair_threshold=60.0,  # Minimum score for "fair" rating
        phoneme_error_threshold=70.0,  # Phoneme scores below this are errors
        word_error_threshold=70.0,  # Word scores below this are problematic
        prosody_error_threshold=65.0,  # Prosody scores below this indicate issues
        max_attempt_errors=5  # Maximum errors to report per attempt
    )
    session_state.capt_pipeline = CAPTFeedbackPipeline(config)

if "guidance_card" not in session_state:
    session_state.guidance_card = None  # First attempt creates this

if "ai_feedback_text" not in session_state:
    session_state.ai_feedback_text = None  # Store generated feedback
```

### Step 3: Process Pronunciation Results
Replace the section after getting `pronunciation_assessment_result` in `phonoecho.py`:

```python
if submitted:
    # Get pronunciation assessment
    st.session_state.practice_times += 1
    audio_file_path = f"asset/{user}/history/{lesson}-{st.session_state.practice_times}.wav"
    save_audio_to_file(audio_bytes_io, filename=audio_file_path)
    pronunciation_assessment_result = get_pronunciation_assessment(
        user, 
        st.session_state.pronunciation_config, 
        reference_text, 
        audio_file_path
    )
    save_pronunciation_assessment(
        pronunciation_assessment_result, 
        f"asset/{user}/history/{lesson}-{st.session_state.practice_times}.json"
    )

    # CAPT Processing
    if st.session_state.practice_times == 1:
        # First attempt: Create guidance card
        guidance_card = st.session_state.capt_pipeline.parse_guidance_card(
            pronunciation_assessment_result
        )
        st.session_state.guidance_card = guidance_card
        
        # Save guidance card for reuse
        guidance_path = f"asset/{user}/history/{lesson}_guidance.json"
        st.session_state.capt_pipeline.save_guidance_card(guidance_card, guidance_path)
        
        # Generate comprehensive feedback
        feedback_prompt = st.session_state.capt_pipeline.generate_feedback(
            guidance_card=guidance_card,
            attempt_summary=None,
            reference_text=reference_text,
            is_first_attempt=True
        )
    else:
        # Subsequent attempts: Create attempt summary
        attempt_summary = st.session_state.capt_pipeline.parse_attempt_summary(
            pronunciation_assessment_result
        )
        
        # Save attempt summary
        attempt_path = f"asset/{user}/history/{lesson}-{st.session_state.practice_times}_summary.json"
        st.session_state.capt_pipeline.save_attempt_summary(attempt_summary, attempt_path)
        
        # Generate focused feedback
        feedback_prompt = st.session_state.capt_pipeline.generate_feedback(
            guidance_card=st.session_state.guidance_card,
            attempt_summary=attempt_summary,
            reference_text=reference_text,
            is_first_attempt=False
        )
    
    # Generate AI feedback using OpenAI
    st.session_state.ai_feedback_text = generate_ai_feedback_from_prompt(
        st.session_state.openai_client,
        feedback_prompt
    )
    
    # Create visualization (radar chart)
    radar_chart = create_radar_chart(pronunciation_assessment_result)
    st.session_state["feedback"]["radar_chart"] = radar_chart
```

### Step 4: Create AI Feedback Generator Function
Add this function to `ai_feedback.py`:

```python
def generate_ai_feedback_from_prompt(client, feedback_prompt):
    """
    Generate AI feedback using the structured CAPT feedback prompt.
    
    Args:
        client: OpenAI client instance
        feedback_prompt: FeedbackPrompt dataclass from CAPT pipeline
    
    Returns:
        str: Generated feedback text
    """
    # Build system prompt
    system_prompt = """あなたは発音指導の専門家です。
学習者の発音評価データに基づいて、具体的で実行可能なフィードバックを日本語で提供してください。

フィードバックには以下を含めてください：
1. 全体的な評価（肯定的なフィードバックから始める）
2. 改善が必要な主要なポイント（優先順位順）
3. 具体的な練習方法
4. 励ましの言葉

簡潔で分かりやすい言葉を使い、学習者が次のステップを理解できるようにしてください。"""
    
    # Build user prompt from FeedbackPrompt
    user_prompt = f"""
【発音評価フィードバック】

参照テキスト: {feedback_prompt.reference_text}

スコア:
- 発音スコア: {feedback_prompt.overall_scores.pronunciation_score}/100
- 正確さ: {feedback_prompt.overall_scores.accuracy_score}/100
- 流暢さ: {feedback_prompt.overall_scores.fluency_score}/100
- 完全性: {feedback_prompt.overall_scores.completeness_score}/100

"""
    
    # Add prosody issues
    if feedback_prompt.prosody_issues:
        user_prompt += "韻律の問題:\n"
        for issue in feedback_prompt.prosody_issues:
            user_prompt += f"- {issue.error_type.value}: 単語「{issue.word}」(深刻度: {issue.severity})\n"
        user_prompt += "\n"
    
    # Add word errors
    if feedback_prompt.word_errors:
        user_prompt += "単語レベルのエラー:\n"
        for error in feedback_prompt.word_errors:
            user_prompt += f"- {error.error_type.value}: 単語「{error.word}」"
            if error.phoneme_errors:
                phonemes = ", ".join([f"{p.phoneme}({p.accuracy_score}点)" 
                                     for p in error.phoneme_errors])
                user_prompt += f" [音素: {phonemes}]"
            user_prompt += "\n"
        user_prompt += "\n"
    
    # Add practice recommendations
    if feedback_prompt.practice_recommendations:
        user_prompt += "推奨される練習:\n"
        for i, rec in enumerate(feedback_prompt.practice_recommendations, 1):
            user_prompt += f"{i}. {rec}\n"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",  # or "gpt-5-mini" if available
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=800
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating AI feedback: {e}")
        return "フィードバックの生成中にエラーが発生しました。"
```

### Step 5: Display Feedback in AIフィードバック Container

Replace the AIフィードバック container section in `phonoecho.py`:

```python
with st.container(height=450, horizontal_alignment="center", vertical_alignment="center"):
    if st.session_state.ai_feedback_text is None:
        st.html("<h2 style='text-align: center;'>AIフィードバック</h2>")
        st.info("音声を録音してフィードバックを取得してください")
    else:
        st.markdown("### 🎯 AIフィードバック")
        
        # Display practice attempt number
        st.caption(f"練習回数: {st.session_state.practice_times}")
        
        # Display feedback with nice formatting
        st.markdown(st.session_state.ai_feedback_text)
        
        # Add a divider
        st.divider()
        
        # Show token savings info (optional)
        with st.expander("📊 技術情報", expanded=False):
            if st.session_state.practice_times == 1:
                st.write("✅ 初回: ガイダンスカードを作成しました")
                st.write("📝 フルJSON解析（約8000トークン）")
            else:
                st.write("✅ 2回目以降: 差分データを使用")
                st.write("📝 軽量サマリー（約800トークン）")
                st.write("💡 トークン使用量を90%削減")
```

---

## 🎨 Enhanced Display Ideas

### Option A: Tabbed Feedback Display
```python
with st.container(height=450):
    if st.session_state.ai_feedback_text is not None:
        feedback_tabs = st.tabs(["📊 総評", "🎯 改善点", "💡 練習方法"])
        
        with feedback_tabs[0]:
            # Overall feedback and scores
            st.markdown(st.session_state.ai_feedback_text)
        
        with feedback_tabs[1]:
            # Show specific errors from guidance card or attempt summary
            if st.session_state.guidance_card:
                st.write("主な改善点:")
                for error in st.session_state.guidance_card.word_errors[:3]:
                    st.error(f"**{error.word}**: {error.error_type.value}")
        
        with feedback_tabs[2]:
            # Practice recommendations
            st.write("推奨される練習:")
            recs = [
                "遅いスピードで繰り返し練習してください",
                "問題のある音素に焦点を当ててください",
                "ネイティブスピーカーの音声を聞いて模倣してください"
            ]
            for rec in recs:
                st.write(f"• {rec}")
```

### Option B: Progress Comparison
```python
with st.container(height=450):
    if st.session_state.practice_times > 1 and st.session_state.ai_feedback_text:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                label="発音スコア",
                value=f"{st.session_state.guidance_card.overall_scores.pronunciation_score}",
                delta="+5"  # Calculate from previous attempt
            )
        
        with col2:
            st.metric(
                label="エラー数",
                value=len(st.session_state.guidance_card.word_errors),
                delta="-2"  # Calculate from previous attempt
            )
        
        st.divider()
        st.markdown(st.session_state.ai_feedback_text)
```

### Option C: Interactive Error Cards
```python
with st.container(height=450):
    if st.session_state.guidance_card and st.session_state.ai_feedback_text:
        st.markdown("### 🎯 AIフィードバック")
        st.markdown(st.session_state.ai_feedback_text)
        
        st.divider()
        
        # Show expandable error details
        if st.session_state.guidance_card.word_errors:
            st.write("**詳細なエラー分析:**")
            for error in st.session_state.guidance_card.word_errors[:3]:
                with st.expander(f"❌ {error.word} - {error.error_type.value}"):
                    st.write(f"**スコア**: {error.accuracy_score}/100")
                    if error.phoneme_errors:
                        st.write("**問題のある音素:**")
                        for phoneme in error.phoneme_errors:
                            st.write(f"- /{phoneme.phoneme}/ → スコア: {phoneme.accuracy_score}")
```

---

## 📊 Complete Example Integration

Here's a complete modified section for `phonoecho.py`:

```python
with cols[1]:
    # Radar Chart Container
    with st.container(height=400, horizontal_alignment="center", vertical_alignment="center"):
        if st.session_state["feedback"]["radar_chart"] is None:
            st.html("<h1 style='text-align: center;'>レーダーチャート</h1>")
        else:
            st.pyplot(st.session_state["feedback"]["radar_chart"], width=450)

    # AI Feedback Container (ENHANCED)
    with st.container(height=450, horizontal_alignment="center", vertical_alignment="center"):
        if st.session_state.ai_feedback_text is None:
            st.html("<h2 style='text-align: center;'>AIフィードバック</h2>")
            st.info("🎤 音声を録音してフィードバックを受け取りましょう！")
        else:
            # Header with practice count
            st.markdown(f"### 🎯 AIフィードバック (練習 #{st.session_state.practice_times})")
            
            # Main feedback text
            st.markdown(st.session_state.ai_feedback_text)
            
            # Visual separator
            st.divider()
            
            # Additional insights
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.session_state.guidance_card:
                    score = st.session_state.guidance_card.overall_scores.pronunciation_score
                    st.metric("発音スコア", f"{score}/100")
            
            with col2:
                if st.session_state.guidance_card:
                    errors = len(st.session_state.guidance_card.word_errors)
                    st.metric("エラー数", errors)
            
            with col3:
                st.metric("練習回数", st.session_state.practice_times)
```

---

## 🔧 Additional Features

### Feature 1: Feedback History
Store and display feedback history:

```python
# In initialize.py
if "feedback_history" not in session_state:
    session_state.feedback_history = []

# After generating feedback
st.session_state.feedback_history.append({
    "attempt": st.session_state.practice_times,
    "feedback": st.session_state.ai_feedback_text,
    "score": guidance_card.overall_scores.pronunciation_score,
    "timestamp": datetime.now()
})
```

### Feature 2: Download Feedback Report
```python
if st.session_state.ai_feedback_text:
    st.download_button(
        label="📥 フィードバックをダウンロード",
        data=st.session_state.ai_feedback_text,
        file_name=f"feedback_{user}_{lesson}_{st.session_state.practice_times}.txt",
        mime="text/plain"
    )
```

---

## 🎯 Token Savings Demonstration

Show users the efficiency gains:

```python
with st.expander("💡 トークン効率について"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**従来の方法**")
        st.write("❌ 毎回フルJSON送信")
        st.write("📊 ~8000トークン/回")
        st.write("💰 高コスト")
    
    with col2:
        st.write("**CAPTパイプライン**")
        st.write("✅ 初回のみフル解析")
        st.write("📊 ~800トークン/回（2回目以降）")
        st.write("💰 90%削減")
```

---

## 📚 Next Steps

1. **Test with real audio**: Use actual pronunciation assessments
2. **Tune prompts**: Adjust `generate_ai_feedback_from_prompt()` for better Japanese feedback
3. **Add visualization**: Show error locations on waveform
4. **Track progress**: Store feedback history across sessions
5. **Gamification**: Add badges for improvements

---

## 🐛 Troubleshooting

**Issue**: Feedback not displaying
- Check `st.session_state.ai_feedback_text` is not None
- Verify OpenAI client is initialized
- Check console for errors

**Issue**: Token usage still high
- Ensure using `attempt_summary` for subsequent attempts
- Verify `guidance_card` is saved and reused
- Check `is_first_attempt` flag is correct

**Issue**: Japanese feedback quality poor
- Adjust temperature (0.7 recommended)
- Use GPT-4 instead of GPT-3.5
- Refine system prompt
