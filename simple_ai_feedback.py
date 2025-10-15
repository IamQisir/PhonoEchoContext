"""
Simplified AI Feedback - No complex CAPT pipeline needed!
Just extract key info from Azure JSON and let AI do the heavy lifting.
"""
import streamlit as st


def extract_pronunciation_errors(azure_json):
    """
    Extract key pronunciation information from Azure Speech Assessment JSON.
    
    Args:
        azure_json: The pronunciation assessment result from Azure
        
    Returns:
        dict: Simplified error information
    """
    try:
        # Overall scores
        overall_score = azure_json.get("NBest", [{}])[0].get("PronunciationAssessment", {}).get("PronScore", 0)
        accuracy_score = azure_json.get("NBest", [{}])[0].get("PronunciationAssessment", {}).get("AccuracyScore", 0)
        fluency_score = azure_json.get("NBest", [{}])[0].get("PronunciationAssessment", {}).get("FluencyScore", 0)
        completeness_score = azure_json.get("NBest", [{}])[0].get("PronunciationAssessment", {}).get("CompletenessScore", 0)
        
        # Prosody
        prosody = azure_json.get("NBest", [{}])[0].get("PronunciationAssessment", {}).get("Prosody", {})
        
        # Extract problematic words (score < 70)
        words = azure_json.get("NBest", [{}])[0].get("Words", [])
        problem_words = []
        
        for word in words:
            word_text = word.get("Word", "")
            word_score = word.get("PronunciationAssessment", {}).get("AccuracyScore", 100)
            
            if word_score < 70:  # Threshold for "problematic"
                # Get phoneme errors
                phoneme_errors = []
                for phoneme in word.get("Phonemes", []):
                    phoneme_score = phoneme.get("PronunciationAssessment", {}).get("AccuracyScore", 100)
                    if phoneme_score < 70:
                        phoneme_errors.append({
                            "phoneme": phoneme.get("Phoneme", ""),
                            "score": phoneme_score
                        })
                
                problem_words.append({
                    "word": word_text,
                    "score": word_score,
                    "phoneme_errors": phoneme_errors
                })
        
        return {
            "overall_score": overall_score,
            "accuracy_score": accuracy_score,
            "fluency_score": fluency_score,
            "completeness_score": completeness_score,
            "prosody": prosody,
            "problem_words": problem_words
        }
    
    except Exception as e:
        st.error(f"データ抽出エラー: {e}")
        return None


def generate_simple_ai_feedback(client, azure_json, reference_text, attempt_number=1, previous_errors=None):
    """
    Generate AI feedback directly from Azure JSON - no complex pipeline!
    
    Args:
        client: OpenAI client
        azure_json: Azure pronunciation assessment result
        reference_text: The text the user should pronounce
        attempt_number: Current attempt number
        previous_errors: Previous errors for comparison (optional)
        
    Returns:
        str: AI-generated feedback in Japanese
    """
    
    # Extract key information
    info = extract_pronunciation_errors(azure_json)
    if not info:
        return "評価データの処理中にエラーが発生しました。"
    
    # Build prompt
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
    
    # Build user prompt
    user_prompt = f"""【練習 #{attempt_number} の発音評価】

参照テキスト: "{reference_text}"

**スコア:**
- 総合: {info['overall_score']:.0f}/100
- 正確さ: {info['accuracy_score']:.0f}/100
- 流暢さ: {info['fluency_score']:.0f}/100
- 完全性: {info['completeness_score']:.0f}/100

"""
    
    if info['problem_words']:
        # Has errors
        user_prompt += "**発音が難しかった単語:**\n"
        for pw in info['problem_words'][:5]:  # Top 5
            user_prompt += f"- '{pw['word']}' (スコア: {pw['score']:.0f}/100)\n"
            if pw['phoneme_errors']:
                phonemes = ", ".join([p['phoneme'] for p in pw['phoneme_errors'][:3]])
                user_prompt += f"  問題のある音素: {phonemes}\n"
        
        user_prompt += "\nこれらのミスがなぜ起きたのか、どう直せばいいか、優しく教えてください。"
    else:
        # No errors - praise!
        user_prompt += "**素晴らしい！発音ミスはありません。**\n\n"
        
        if previous_errors:
            user_prompt += f"前回は {len(previous_errors)} 個の単語で苦労していましたが、今回は完璧です！\n\n"
        
        user_prompt += "今回の発音の良かった点を具体的に褒めてください。\n"
        
        # Add prosody info if available
        if info['prosody']:
            user_prompt += f"韻律評価: {info['prosody']}\n"
        
        user_prompt += "可能であれば、韻律（イントネーション、リズム、強勢など）の面でさらに良くできる点があれば優しく提案してください。"
    
    user_prompt += "\n\n温かく励ましながら、次の練習へのモチベーションを高めてください。"
    
    # Get model name
    try:
        model_name = st.secrets["AzureGPT"].get("DEPLOYMENT_NAME", "gpt-5-mini")
    except:
        model_name = "gpt-5-mini"
    
    # Call AI
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        
        content = response.choices[0].message.content
        return content if content else "AIフィードバックの生成に失敗しました。もう一度お試しください。"
    
    except Exception as e:
        st.error(f"AI生成エラー: {type(e).__name__}: {str(e)}")
        
        # Fallback: Simple text feedback
        feedback = f"## 練習 #{attempt_number} の評価\n\n"
        feedback += f"**総合スコア:** {info['overall_score']:.0f}/100\n\n"
        
        if info['problem_words']:
            feedback += "**改善が必要な単語:**\n"
            for pw in info['problem_words'][:5]:
                feedback += f"- {pw['word']} ({pw['score']:.0f}点)\n"
        else:
            feedback += "**素晴らしい！全ての単語を正確に発音できました！** 🎉\n"
        
        return feedback


def generate_simple_ai_feedback_streaming(client, azure_json, reference_text, attempt_number=1, previous_errors=None):
    """
    Generate AI feedback with streaming - for better UX!
    
    Args:
        client: OpenAI client
        azure_json: Azure pronunciation assessment result
        reference_text: The text the user should pronounce
        attempt_number: Current attempt number
        previous_errors: Previous errors for comparison (optional)
        
    Yields:
        str: Chunks of AI-generated feedback
    """
    
    # Extract key information
    info = extract_pronunciation_errors(azure_json)
    if not info:
        yield "評価データの処理中にエラーが発生しました。"
        return
    
    # Build prompt (same as non-streaming version)
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
    
    # Build user prompt based on whether there are errors or not
    has_errors = info['problem_words'] and len(info['problem_words']) > 0
    
    user_prompt = f"""【練習 #{attempt_number} の発音評価】

参照テキスト: "{reference_text}"

**スコア:**
- 総合: {info['overall_score']:.0f}/100
- 正確さ: {info['accuracy_score']:.0f}/100
- 流暢さ: {info['fluency_score']:.0f}/100
- 完全性: {info['completeness_score']:.0f}/100

"""
    
    if has_errors:
        # Has errors
        user_prompt += "**発音が難しかった単語:**\n"
        for pw in info['problem_words'][:5]:
            user_prompt += f"- '{pw['word']}' (スコア: {pw['score']:.0f}/100)\n"
            if pw['phoneme_errors']:
                phonemes = ", ".join([p['phoneme'] for p in pw['phoneme_errors'][:3]])
                user_prompt += f"  問題のある音素: {phonemes}\n"
        
        user_prompt += "\nこれらのミスがなぜ起きたのか、どう直せばいいか、優しく教えてください。"
    else:
        # No errors - praise!
        user_prompt += "**素晴らしい！発音ミスはありません。**\n\n"
        
        if previous_errors:
            user_prompt += f"前回は {len(previous_errors)} 個の単語で苦労していましたが、今回は完璧です！\n\n"
        
        user_prompt += "今回の発音の良かった点を具体的に褒めてください。\n"
        
        if info['prosody']:
            user_prompt += f"韻律評価: {info['prosody']}\n"
        
        user_prompt += "可能であれば、韻律（イントネーション、リズム、強勢など）の面でさらに良くできる点があれば優しく提案してください。"
    
    user_prompt += "\n\n温かく励ましながら、次の練習へのモチベーションを高めてください。"
    
    # Get model name
    try:
        model_name = st.secrets["AzureGPT"].get("DEPLOYMENT_NAME", "gpt-5-mini")
    except:
        model_name = "gpt-5-mini"
    
    # Call AI with streaming
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True  # Enable streaming!
        )
        
        # Yield chunks as they arrive
        for chunk in response:
            # Check if chunk has choices and content
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    yield delta.content
    
    except Exception as e:
        # Fallback on error
        yield f"\n\n⚠️ AI生成エラー: {type(e).__name__}: {str(e)}\n\n"
        yield f"## 練習 #{attempt_number} の評価\n\n"
        yield f"**総合スコア:** {info['overall_score']:.0f}/100\n\n"
        
        if info['problem_words']:
            yield "**改善が必要な単語:**\n"
            for pw in info['problem_words'][:5]:
                yield f"- {pw['word']} ({pw['score']:.0f}点)\n"
        else:
            yield "**素晴らしい！全ての単語を正確に発音できました！** 🎉\n"
