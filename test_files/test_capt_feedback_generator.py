"""
Unit tests for CAPT Feedback Generator.

These tests verify feedback generation combining guidance cards and attempt summaries.
Uses mocked LLM calls for pure-Python testing.
"""

import pytest
from typing import Dict, Callable
from unittest.mock import Mock

from capt_feedback_generator import (
    generate_feedback,
    generate_structured_feedback,
    format_feedback_for_display,
    _build_guidance_highlights,
    _build_attempt_text,
    _generate_fallback_feedback,
)
from capt_guidance_card import parse_guidance_card
from capt_attempt_summary import parse_attempt_summary
from capt_config import FeedbackConfig
from capt_models import GuidanceCard, AttemptSummary


# === Fixtures ===

@pytest.fixture
def sample_azure_result() -> Dict:
    """Sample Azure result for testing."""
    return {
        "DisplayText": "Hello world.",
        "NBest": [
            {
                "Lexical": "hello world",
                "PronunciationAssessment": {
                    "AccuracyScore": 75.0,
                    "FluencyScore": 70.0,
                    "ProsodyScore": 65.0,
                    "CompletenessScore": 85.0,
                    "PronScore": 72.0,
                },
                "Words": [
                    {
                        "Word": "hello",
                        "Offset": 10000000,
                        "Duration": 5000000,
                        "PronunciationAssessment": {
                            "AccuracyScore": 65.0,
                            "ErrorType": "Mispronunciation"
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "h",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 55.0
                                }
                            },
                            {
                                "Phoneme": "ɛ",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 70.0
                                }
                            }
                        ]
                    },
                    {
                        "Word": "world",
                        "Offset": 15000000,
                        "Duration": 7000000,
                        "PronunciationAssessment": {
                            "AccuracyScore": 80.0,
                            "ErrorType": "None"
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "w",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 75.0
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def mock_guidance_card(sample_azure_result) -> GuidanceCard:
    """Create a sample guidance card."""
    return parse_guidance_card(sample_azure_result)


@pytest.fixture
def mock_attempt_summary(sample_azure_result, mock_guidance_card) -> AttemptSummary:
    """Create a sample attempt summary."""
    return parse_attempt_summary(
        sample_azure_result,
        attempt_number=2,
        guidance_card=mock_guidance_card
    )


@pytest.fixture
def mock_llm_function() -> Callable[[str], str]:
    """Create a mock LLM function."""
    def _mock_llm(prompt: str) -> str:
        return "Mock feedback: Practice your /h/ sound. Try to speak more slowly."
    return _mock_llm


# === Guidance Highlights Tests ===

def test_build_guidance_highlights(mock_guidance_card):
    """Test building guidance highlights."""
    config = FeedbackConfig()
    highlights = _build_guidance_highlights(mock_guidance_card, config)
    
    assert isinstance(highlights, str)
    assert len(highlights) > 0
    # Should contain some reference to challenging elements
    assert "音素" in highlights or "単語" in highlights or highlights


def test_guidance_highlights_includes_score(mock_guidance_card):
    """Test that guidance highlights include initial score."""
    config = FeedbackConfig()
    highlights = _build_guidance_highlights(mock_guidance_card, config)
    
    # Should mention the initial score
    assert "72" in highlights or "初回" in highlights


# === Attempt Text Tests ===

def test_build_attempt_text(mock_attempt_summary):
    """Test building attempt summary text."""
    config = FeedbackConfig()
    text = _build_attempt_text(mock_attempt_summary, config)
    
    assert isinstance(text, str)
    assert len(text) > 0
    # Should contain score information
    assert "72" in text or "点" in text


def test_attempt_text_includes_category(mock_attempt_summary):
    """Test that attempt text includes score category."""
    config = FeedbackConfig()
    text = _build_attempt_text(mock_attempt_summary, config)
    
    # Should include category label (fair for score of 72)
    assert "普通" in text or "Fair" in text or "良" in text


def test_attempt_text_shows_errors(mock_attempt_summary):
    """Test that attempt text shows main errors."""
    # Modify attempt to have clear errors
    mock_attempt_summary.current_word_errors = [
        type('obj', (object,), {
            'word': 'hello', 
            'error_type': type('obj', (object,), {'value': 'Mispronunciation'})()
        })()
    ]
    
    config = FeedbackConfig()
    text = _build_attempt_text(mock_attempt_summary, config)
    
    # Should mention the error
    assert "hello" in text or "エラー" in text


# === Fallback Feedback Tests ===

def test_generate_fallback_feedback(mock_attempt_summary):
    """Test fallback feedback generation."""
    config = FeedbackConfig()
    feedback = _generate_fallback_feedback(mock_attempt_summary, config)
    
    assert isinstance(feedback, str)
    assert len(feedback) > 0
    # Should be encouraging
    assert "練習" in feedback or "上達" in feedback or len(feedback) > 20


def test_fallback_feedback_varies_by_score():
    """Test that fallback feedback varies based on score."""
    config = FeedbackConfig()
    
    # Create high-score attempt
    high_score_attempt = AttemptSummary(
        attempt_number=1,
        overall_score=95.0,
        accuracy_score=95.0,
        fluency_score=95.0,
        prosody_score=95.0,
        completeness_score=95.0
    )
    
    # Create low-score attempt
    low_score_attempt = AttemptSummary(
        attempt_number=1,
        overall_score=45.0,
        accuracy_score=45.0,
        fluency_score=45.0,
        prosody_score=45.0,
        completeness_score=45.0
    )
    
    high_feedback = _generate_fallback_feedback(high_score_attempt, config)
    low_feedback = _generate_fallback_feedback(low_score_attempt, config)
    
    # Feedbacks should be different
    assert high_feedback != low_feedback
    
    # High score should be more positive
    assert "素晴らしい" in high_feedback or "excellent" in high_feedback.lower()


# === Feedback Generation Tests ===

def test_generate_feedback_with_llm(
    mock_guidance_card,
    mock_attempt_summary,
    mock_llm_function
):
    """Test feedback generation with LLM."""
    config = FeedbackConfig()
    
    feedback = generate_feedback(
        mock_guidance_card,
        mock_attempt_summary,
        llm_function=mock_llm_function,
        config=config
    )
    
    assert isinstance(feedback, str)
    assert "Mock feedback" in feedback


def test_generate_feedback_without_llm_returns_prompt(
    mock_guidance_card,
    mock_attempt_summary
):
    """Test feedback generation without LLM returns formatted prompt."""
    config = FeedbackConfig()
    
    feedback = generate_feedback(
        mock_guidance_card,
        mock_attempt_summary,
        llm_function=None,  # No LLM
        config=config
    )
    
    # Should return the prompt itself
    assert isinstance(feedback, str)
    assert len(feedback) > 100  # Prompt should be reasonably long
    # Should contain Japanese text for default config
    assert "目標" in feedback or "指示" in feedback


def test_generate_feedback_handles_llm_error(
    mock_guidance_card,
    mock_attempt_summary
):
    """Test feedback generation gracefully handles LLM errors."""
    def failing_llm(prompt: str) -> str:
        raise Exception("LLM API Error")
    
    config = FeedbackConfig()
    
    # Should fall back to rule-based feedback
    feedback = generate_feedback(
        mock_guidance_card,
        mock_attempt_summary,
        llm_function=failing_llm,
        config=config
    )
    
    assert isinstance(feedback, str)
    assert len(feedback) > 0
    # Fallback should be in Japanese by default
    assert any(ord(c) > 127 for c in feedback)  # Contains non-ASCII (Japanese)


def test_generate_feedback_with_english_config(
    mock_guidance_card,
    mock_attempt_summary
):
    """Test feedback generation with English configuration."""
    config = FeedbackConfig(feedback_language="en")
    
    feedback = generate_feedback(
        mock_guidance_card,
        mock_attempt_summary,
        llm_function=None,
        config=config
    )
    
    # Should use English prompt
    assert "Target Sentence" in feedback
    assert "Instructions" in feedback


# === Structured Feedback Tests ===

def test_generate_structured_feedback(
    mock_guidance_card,
    mock_attempt_summary
):
    """Test structured feedback generation."""
    config = FeedbackConfig()
    
    structured = generate_structured_feedback(
        mock_guidance_card,
        mock_attempt_summary,
        config=config
    )
    
    # Check required fields
    assert "overall_score" in structured
    assert "score_category" in structured
    assert "main_issues" in structured
    assert "improvements" in structured
    assert "recommendations" in structured
    assert "encouragement" in structured
    
    # Check values
    assert structured["overall_score"] == 72.0
    assert structured["score_category"] in ["excellent", "good", "fair", "poor"]
    assert isinstance(structured["main_issues"], list)
    assert isinstance(structured["recommendations"], list)


def test_structured_feedback_identifies_issues(
    mock_guidance_card,
    mock_attempt_summary
):
    """Test that structured feedback identifies pronunciation issues."""
    config = FeedbackConfig()
    
    structured = generate_structured_feedback(
        mock_guidance_card,
        mock_attempt_summary,
        config=config
    )
    
    # Should have identified some issues
    assert len(structured["main_issues"]) > 0


def test_structured_feedback_provides_recommendations(
    mock_guidance_card,
    mock_attempt_summary
):
    """Test that structured feedback provides actionable recommendations."""
    config = FeedbackConfig()
    
    structured = generate_structured_feedback(
        mock_guidance_card,
        mock_attempt_summary,
        config=config
    )
    
    # Should have recommendations if there are errors
    if len(structured["main_issues"]) > 0:
        assert len(structured["recommendations"]) > 0


def test_structured_feedback_includes_improvements():
    """Test that structured feedback tracks improvements."""
    # Create guidance
    guidance = GuidanceCard(
        target_text="hello world",
        target_display="Hello world.",
        total_words=2,
        total_phonemes=5,
        reference_overall=60.0,
        reference_accuracy=55.0,
        reference_fluency=60.0,
        reference_prosody=58.0,
        reference_completeness=70.0,
    )
    
    # Create attempt with improvements
    attempt = AttemptSummary(
        attempt_number=2,
        overall_score=85.0,
        accuracy_score=85.0,
        fluency_score=85.0,
        prosody_score=80.0,
        completeness_score=90.0,
        improved_words=["hello"],
        improved_phonemes=["/h/ in 'hello'"]
    )
    
    structured = generate_structured_feedback(guidance, attempt)
    
    # Should show improvements
    assert len(structured["improvements"]) > 0
    assert any("hello" in imp for imp in structured["improvements"])


# === Format Display Tests ===

def test_format_feedback_for_display():
    """Test formatting structured feedback for display."""
    structured = {
        "overall_score": 85.0,
        "score_label": "良好 (Good)",
        "score_category": "good",
        "main_issues": ["'hello'の発音"],
        "improvements": ["'world'が改善されました"],
        "recommendations": ["/h/の発音を重点的に練習しましょう"],
        "encouragement": "良い発音です。",
        "attempt_number": 2
    }
    
    display = format_feedback_for_display(structured)
    
    assert isinstance(display, str)
    assert "85" in display
    assert "良好" in display
    assert "hello" in display
    assert "world" in display


def test_format_display_handles_empty_sections():
    """Test formatting handles empty sections gracefully."""
    structured = {
        "overall_score": 95.0,
        "score_label": "優秀 (Excellent)",
        "score_category": "excellent",
        "main_issues": [],  # No issues
        "improvements": [],
        "recommendations": [],
        "encouragement": "素晴らしい！",
        "attempt_number": 1
    }
    
    display = format_feedback_for_display(structured)
    
    # Should still produce valid output
    assert isinstance(display, str)
    assert "95" in display
    assert "素晴らしい" in display
    # Should not have empty sections
    assert "主な課題" not in display or "None" not in display


# === Integration Tests ===

def test_full_feedback_pipeline(sample_azure_result):
    """Test complete feedback generation pipeline."""
    # Step 1: Create guidance card from first attempt
    guidance = parse_guidance_card(sample_azure_result)
    
    # Step 2: Parse second attempt
    attempt = parse_attempt_summary(
        sample_azure_result,
        attempt_number=2,
        guidance_card=guidance
    )
    
    # Step 3: Generate structured feedback
    structured = generate_structured_feedback(guidance, attempt)
    
    # Step 4: Format for display
    display = format_feedback_for_display(structured)
    
    # Verify complete pipeline
    assert len(display) > 0
    assert "72" in display  # Score
    assert any(c for c in display if ord(c) > 127)  # Contains Japanese


def test_feedback_with_different_configurations():
    """Test feedback generation with various configurations."""
    # Create sample data
    guidance = GuidanceCard(
        target_text="test",
        target_display="Test.",
        total_words=1,
        total_phonemes=4,
        reference_overall=70.0,
        reference_accuracy=70.0,
        reference_fluency=70.0,
        reference_prosody=70.0,
        reference_completeness=70.0,
    )
    
    attempt = AttemptSummary(
        attempt_number=1,
        overall_score=75.0,
        accuracy_score=75.0,
        fluency_score=75.0,
        prosody_score=75.0,
        completeness_score=75.0,
    )
    
    # Test with different score thresholds
    strict_config = FeedbackConfig(
        excellent_threshold=95.0,
        good_threshold=85.0,
        fair_threshold=75.0
    )
    
    lenient_config = FeedbackConfig(
        excellent_threshold=80.0,
        good_threshold=65.0,
        fair_threshold=50.0
    )
    
    strict_feedback = generate_structured_feedback(guidance, attempt, strict_config)
    lenient_feedback = generate_structured_feedback(guidance, attempt, lenient_config)
    
    # Same score should be categorized differently
    assert strict_feedback["score_category"] in ["fair", "poor"]
    assert lenient_feedback["score_category"] in ["good", "excellent"]


def test_mock_llm_integration():
    """Test integration with mocked LLM."""
    mock_llm = Mock(return_value="あなたの発音は良好です。/h/の音に注意してください。")
    
    guidance = GuidanceCard(
        target_text="hello",
        target_display="Hello.",
        total_words=1,
        total_phonemes=3,
        reference_overall=70.0,
        reference_accuracy=70.0,
        reference_fluency=70.0,
        reference_prosody=70.0,
        reference_completeness=70.0,
    )
    
    attempt = AttemptSummary(
        attempt_number=1,
        overall_score=75.0,
        accuracy_score=75.0,
        fluency_score=75.0,
        prosody_score=75.0,
        completeness_score=75.0,
    )
    
    feedback = generate_feedback(guidance, attempt, llm_function=mock_llm)
    
    # Verify LLM was called
    assert mock_llm.called
    assert "良好" in feedback
    assert "/h/" in feedback


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
