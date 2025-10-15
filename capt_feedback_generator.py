"""
Feedback Generator for CAPT feedback pipeline.

This module generates concise, actionable feedback by combining:
1. Guidance Card (stable reference)
2. Attempt Summary (incremental changes)
3. LLM prompting (with token optimization)

The goal is to produce short, consistent, encouraging feedback that focuses
on the most important pronunciation issues without overwhelming the learner.
"""

from typing import Optional, Callable
import json

from capt_models import (
    GuidanceCard,
    AttemptSummary,
    FeedbackPrompt,
)
from capt_config import FeedbackConfig, DEFAULT_CONFIG


def generate_feedback(
    guidance_card: GuidanceCard,
    attempt_summary: AttemptSummary,
    llm_function: Optional[Callable[[str], str]] = None,
    config: Optional[FeedbackConfig] = None
) -> str:
    """
    Generate concise feedback for a pronunciation attempt.
    
    This function:
    1. Creates a compact prompt combining guidance highlights + attempt delta
    2. Calls LLM with optimized prompt
    3. Returns short, actionable feedback
    
    Args:
        guidance_card: Stable reference guidance card
        attempt_summary: Current attempt analysis
        llm_function: Function to call LLM (takes prompt str, returns response str)
                      If None, returns structured prompt without LLM call
        config: Configuration object (uses DEFAULT_CONFIG if None)
        
    Returns:
        Generated feedback string (or prompt if llm_function is None)
        
    Example:
        >>> def my_llm(prompt: str) -> str:
        ...     return openai_client.chat.completions.create(...)
        >>> feedback = generate_feedback(guidance, attempt, my_llm)
        >>> print(feedback)
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Build compact guidance highlights
    guidance_highlights = _build_guidance_highlights(guidance_card, config)
    
    # Build compact attempt summary
    attempt_text = _build_attempt_text(attempt_summary, config)
    
    # Create feedback prompt
    prompt = FeedbackPrompt(
        target_text=guidance_card.target_display,
        guidance_highlights=guidance_highlights,
        attempt_summary=attempt_text,
        language=config.feedback_language,
        max_tokens=config.feedback_max_tokens,
        temperature=config.feedback_temperature,
    )
    
    formatted_prompt = prompt.format_prompt()
    
    # If no LLM function provided, return the prompt itself
    if llm_function is None:
        return formatted_prompt
    
    # Call LLM
    try:
        feedback = llm_function(formatted_prompt)
        return feedback
    except Exception as e:
        # Fallback to rule-based feedback if LLM fails
        return _generate_fallback_feedback(attempt_summary, config)


def _build_guidance_highlights(
    guidance: GuidanceCard,
    config: FeedbackConfig
) -> str:
    """
    Build compact guidance highlights (≈50-100 tokens).
    
    Focus on the most challenging elements from the guidance card.
    """
    lines = []
    
    # Add challenging phonemes (top 3)
    if guidance.challenging_phonemes:
        phonemes = guidance.challenging_phonemes[:3]
        phoneme_str = ", ".join([
            f"/{p.phoneme}/ in '{p.word}' ({p.score:.0f})" 
            for p in phonemes
        ])
        lines.append(f"難しい音素: {phoneme_str}")
    
    # Add challenging words (top 2)
    if guidance.challenging_words:
        words = guidance.challenging_words[:2]
        word_str = ", ".join([
            f"'{w.word}' ({w.score:.0f})" if w.score else f"'{w.word}' (省略)"
            for w in words
        ])
        lines.append(f"難しい単語: {word_str}")
    
    # Add prosody pattern (top 1)
    if guidance.prosody_patterns:
        prosody = guidance.prosody_patterns[0]
        lines.append(f"リズム: {prosody.description}")
    
    # Add reference score
    lines.append(f"初回スコア: {guidance.reference_overall:.0f}点")
    
    return "\n".join(lines)


def _build_attempt_text(
    attempt: AttemptSummary,
    config: FeedbackConfig
) -> str:
    """
    Build compact attempt summary (≈50-100 tokens).
    
    Focus on:
    - Current score
    - Most critical errors
    - Improvements (if any)
    """
    lines = []
    
    # Current score with category
    category = config.classify_score(attempt.overall_score)
    category_label = config.score_labels.get(category, "")
    lines.append(
        f"第{attempt.attempt_number}回: {attempt.overall_score:.0f}点 ({category_label})"
    )
    
    # Score breakdown
    lines.append(
        f"正確性: {attempt.accuracy_score:.0f}, "
        f"流暢性: {attempt.fluency_score:.0f}, "
        f"韻律: {attempt.prosody_score:.0f}"
    )
    
    # Critical errors (top 2)
    if attempt.current_word_errors:
        errors = attempt.current_word_errors[:2]
        error_str = ", ".join([
            f"'{e.word}' ({e.error_type.value})" 
            for e in errors
        ])
        lines.append(f"エラー: {error_str}")
    
    if attempt.current_phoneme_errors:
        errors = attempt.current_phoneme_errors[:2]
        phoneme_str = ", ".join([
            f"/{e.phoneme}/ in '{e.word}'" 
            for e in errors
        ])
        lines.append(f"音素エラー: {phoneme_str}")
    
    # Improvements
    if attempt.improved_words:
        improved_str = ", ".join(attempt.improved_words[:2])
        lines.append(f"✅ 改善: {improved_str}")
    
    # Omissions
    if attempt.omitted_words:
        omitted_str = ", ".join(attempt.omitted_words[:2])
        lines.append(f"⚠️ 省略: {omitted_str}")
    
    return "\n".join(lines)


def _generate_fallback_feedback(
    attempt: AttemptSummary,
    config: FeedbackConfig
) -> str:
    """
    Generate rule-based feedback if LLM is unavailable.
    
    Simple template-based feedback focusing on scores and main issues.
    """
    category = config.classify_score(attempt.overall_score)
    
    # Start with score assessment
    if category == "excellent":
        feedback = f"素晴らしい発音です！スコア: {attempt.overall_score:.0f}点\n"
    elif category == "good":
        feedback = f"良い発音です。スコア: {attempt.overall_score:.0f}点\n"
    elif category == "fair":
        feedback = f"まずまずの発音です。スコア: {attempt.overall_score:.0f}点\n"
    else:
        feedback = f"もう少し練習しましょう。スコア: {attempt.overall_score:.0f}点\n"
    
    # Add main issue
    if attempt.current_word_errors:
        word = attempt.current_word_errors[0]
        feedback += f"'{word.word}'の発音に注目してください。\n"
    elif attempt.current_phoneme_errors:
        phoneme = attempt.current_phoneme_errors[0]
        feedback += f"/{phoneme.phoneme}/の音に注意しましょう。\n"
    
    # Add improvement note
    if attempt.improved_words:
        feedback += f"'{attempt.improved_words[0]}'が改善されました！\n"
    
    # Encouragement
    if attempt.attempt_number > 1:
        feedback += "継続して練習することで、さらに上達します！"
    else:
        feedback += "次回はもっと良くなるはずです！"
    
    return feedback


def generate_structured_feedback(
    guidance_card: GuidanceCard,
    attempt_summary: AttemptSummary,
    config: Optional[FeedbackConfig] = None
) -> dict:
    """
    Generate structured feedback data (without LLM).
    
    Returns a dictionary with organized feedback components for UI display.
    
    Args:
        guidance_card: Stable reference guidance card
        attempt_summary: Current attempt analysis
        config: Configuration object (uses DEFAULT_CONFIG if None)
        
    Returns:
        Dictionary with feedback components:
        - overall_score: Overall pronunciation score
        - score_category: Category label (excellent, good, fair, poor)
        - main_issues: List of main pronunciation issues
        - improvements: List of improvements from previous attempts
        - recommendations: List of actionable recommendations
        - encouragement: Encouraging message
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    category = config.classify_score(attempt_summary.overall_score)
    
    # Identify main issues (top 3)
    main_issues = []
    for word_error in attempt_summary.current_word_errors[:3]:
        if word_error.error_type.value == "Omission":
            main_issues.append(f"'{word_error.word}'が省略されました")
        else:
            score_str = f"{word_error.score:.0f}点" if word_error.score else "N/A"
            main_issues.append(f"'{word_error.word}'の発音 ({score_str})")
    
    for phoneme_error in attempt_summary.current_phoneme_errors[:2]:
        main_issues.append(
            f"/{phoneme_error.phoneme}/の音 in '{phoneme_error.word}' ({phoneme_error.score:.0f}点)"
        )
    
    # Identify improvements
    improvements = []
    if attempt_summary.improved_words:
        improvements.extend([
            f"'{word}'が改善されました" for word in attempt_summary.improved_words[:2]
        ])
    if attempt_summary.improved_phonemes:
        improvements.extend([
            f"{phoneme}が改善されました" for phoneme in attempt_summary.improved_phonemes[:2]
        ])
    
    # Generate recommendations
    recommendations = []
    if attempt_summary.current_phoneme_errors:
        top_phoneme = attempt_summary.current_phoneme_errors[0]
        recommendations.append(
            f"/{top_phoneme.phoneme}/の発音を重点的に練習しましょう"
        )
    if attempt_summary.current_prosody_issues:
        top_prosody = attempt_summary.current_prosody_issues[0]
        recommendations.append(top_prosody.description)
    if attempt_summary.fluency_score < config.fluency_min_acceptable:
        recommendations.append("もう少しゆっくり、はっきりと話してみましょう")
    
    # Generate encouragement
    if category == "excellent":
        encouragement = "素晴らしい発音です！この調子で続けてください。"
    elif category == "good":
        encouragement = "良い発音です。あと少しでパーフェクトです！"
    elif category == "fair":
        encouragement = "着実に進歩しています。練習を続けましょう。"
    else:
        encouragement = "諦めずに練習すれば、必ず上達します！"
    
    return {
        "overall_score": attempt_summary.overall_score,
        "score_category": category,
        "score_label": config.score_labels.get(category, ""),
        "main_issues": main_issues,
        "improvements": improvements,
        "recommendations": recommendations,
        "encouragement": encouragement,
        "attempt_number": attempt_summary.attempt_number,
    }


def format_feedback_for_display(structured_feedback: dict) -> str:
    """
    Format structured feedback into a readable string for display.
    
    Args:
        structured_feedback: Dictionary from generate_structured_feedback()
        
    Returns:
        Formatted feedback string
    """
    lines = []
    
    # Header with score
    lines.append(f"📊 総合スコア: {structured_feedback['overall_score']:.0f}点")
    lines.append(f"   評価: {structured_feedback['score_label']}")
    lines.append("")
    
    # Main issues
    if structured_feedback['main_issues']:
        lines.append("🎯 主な課題:")
        for issue in structured_feedback['main_issues']:
            lines.append(f"   • {issue}")
        lines.append("")
    
    # Improvements
    if structured_feedback['improvements']:
        lines.append("✅ 改善点:")
        for improvement in structured_feedback['improvements']:
            lines.append(f"   • {improvement}")
        lines.append("")
    
    # Recommendations
    if structured_feedback['recommendations']:
        lines.append("💡 アドバイス:")
        for rec in structured_feedback['recommendations']:
            lines.append(f"   • {rec}")
        lines.append("")
    
    # Encouragement
    lines.append(f"💪 {structured_feedback['encouragement']}")
    
    return "\n".join(lines)
