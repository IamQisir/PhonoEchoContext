"""
Unit tests for CAPT Guidance Card Parser.

These tests verify the guidance card generation from Azure Speech Assessment JSON.
All tests use mock data and require no network calls.
"""

import pytest
import json
from typing import Dict

from capt_guidance_card import (
    parse_guidance_card,
    _extract_challenging_phonemes,
    _extract_challenging_words,
    _extract_prosody_patterns,
    save_guidance_card,
    load_guidance_card,
)
from capt_config import FeedbackConfig
from capt_models import ErrorType, ProsodyErrorType


# === Fixtures ===

@pytest.fixture
def minimal_azure_result() -> Dict:
    """Minimal valid Azure Speech Assessment result."""
    return {
        "DisplayText": "Hello world.",
        "NBest": [
            {
                "Lexical": "hello world",
                "PronunciationAssessment": {
                    "AccuracyScore": 85.0,
                    "FluencyScore": 80.0,
                    "ProsodyScore": 75.0,
                    "CompletenessScore": 90.0,
                    "PronScore": 82.5,
                },
                "Words": [
                    {
                        "Word": "hello",
                        "PronunciationAssessment": {
                            "AccuracyScore": 90.0,
                            "ErrorType": "None"
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "h",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 95.0
                                }
                            },
                            {
                                "Phoneme": "ɛ",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 85.0
                                }
                            }
                        ]
                    },
                    {
                        "Word": "world",
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
                            },
                            {
                                "Phoneme": "ɔ",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 65.0  # Error (< 70)
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def complex_azure_result() -> Dict:
    """Complex Azure result with various error types."""
    return {
        "DisplayText": "A rocket roared into the sky.",
        "NBest": [
            {
                "Lexical": "a rocket roared into the sky",
                "PronunciationAssessment": {
                    "AccuracyScore": 75.0,
                    "FluencyScore": 70.0,
                    "ProsodyScore": 65.0,
                    "CompletenessScore": 85.0,
                    "PronScore": 72.0,
                },
                "Words": [
                    {
                        "Word": "a",
                        "Offset": 10000000,
                        "Duration": 5000000,
                        "PronunciationAssessment": {
                            "AccuracyScore": 100.0,
                            "ErrorType": "None"
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "ə",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 100.0
                                }
                            }
                        ]
                    },
                    {
                        "Word": "rocket",
                        "Offset": 15000000,
                        "Duration": 10000000,
                        "PronunciationAssessment": {
                            "AccuracyScore": 55.0,  # Error
                            "ErrorType": "Mispronunciation",
                            "Feedback": {
                                "Prosody": {
                                    "Break": {
                                        "ErrorTypes": ["None"],
                                        "UnexpectedBreak": {
                                            "Confidence": 0.8
                                        },
                                        "BreakLength": 5000000
                                    }
                                }
                            }
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "r",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 35.0  # Critical error
                                }
                            },
                            {
                                "Phoneme": "ɑ",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 80.0
                                }
                            }
                        ]
                    },
                    {
                        "Word": "roared",
                        "Offset": 25000000,
                        "Duration": 8000000,
                        "PronunciationAssessment": {
                            "AccuracyScore": 60.0,  # Error
                            "ErrorType": "None"
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "r",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 50.0  # Error
                                }
                            },
                            {
                                "Phoneme": "ɔ",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 65.0  # Error
                                }
                            }
                        ]
                    },
                    {
                        "Word": "sky",
                        "Offset": 50000000,
                        "Duration": 7000000,
                        "PronunciationAssessment": {
                            "AccuracyScore": None,
                            "ErrorType": "Omission"  # Omitted word
                        },
                        "Phonemes": []
                    }
                ]
            }
        ]
    }


@pytest.fixture
def custom_config() -> FeedbackConfig:
    """Custom configuration for testing."""
    return FeedbackConfig(
        phoneme_error_threshold=75.0,
        word_error_threshold=75.0,
        max_guidance_phonemes=3,
        max_guidance_words=2,
    )


# === Basic Parsing Tests ===

def test_parse_minimal_guidance_card(minimal_azure_result):
    """Test parsing minimal valid Azure result."""
    guidance = parse_guidance_card(minimal_azure_result)
    
    assert guidance.target_text == "hello world"
    assert guidance.target_display == "Hello world."
    assert guidance.total_words == 2
    assert guidance.total_phonemes == 4
    assert guidance.reference_accuracy == 85.0
    assert guidance.reference_fluency == 80.0
    assert guidance.reference_overall == 82.5


def test_parse_with_custom_config(minimal_azure_result, custom_config):
    """Test parsing with custom configuration."""
    guidance = parse_guidance_card(minimal_azure_result, config=custom_config)
    
    # With lower threshold, should detect more errors
    assert len(guidance.challenging_phonemes) > 0
    

def test_guidance_card_summary(minimal_azure_result):
    """Test guidance card summary generation."""
    guidance = parse_guidance_card(minimal_azure_result)
    summary = guidance.get_summary()
    
    assert "hello world" in summary
    assert "Words: 2" in summary
    assert "Overall: 82" in summary or "Overall: 83" in summary


# === Phoneme Extraction Tests ===

def test_extract_challenging_phonemes(complex_azure_result, custom_config):
    """Test extraction of challenging phonemes."""
    words = complex_azure_result["NBest"][0]["Words"]
    phonemes = _extract_challenging_phonemes(words, custom_config)
    
    # Should find at least the critical /r/ phoneme
    assert len(phonemes) > 0
    
    # Verify worst phoneme is first (score = 35)
    assert phonemes[0].score == 35.0
    assert phonemes[0].phoneme == "r"
    assert phonemes[0].word == "rocket"


def test_phoneme_extraction_respects_max_limit(complex_azure_result):
    """Test that phoneme extraction respects max limit."""
    config = FeedbackConfig(max_guidance_phonemes=2)
    words = complex_azure_result["NBest"][0]["Words"]
    phonemes = _extract_challenging_phonemes(words, config)
    
    assert len(phonemes) <= 2


def test_phoneme_extraction_filters_by_threshold(minimal_azure_result):
    """Test that phoneme extraction filters by threshold."""
    # High threshold should find more errors
    config = FeedbackConfig(phoneme_error_threshold=90.0)
    words = minimal_azure_result["NBest"][0]["Words"]
    phonemes = _extract_challenging_phonemes(words, config)
    
    # Should find phonemes with score < 90
    assert len(phonemes) > 0
    for phoneme in phonemes:
        assert phoneme.score < 90.0


# === Word Extraction Tests ===

def test_extract_challenging_words(complex_azure_result, custom_config):
    """Test extraction of challenging words."""
    words = complex_azure_result["NBest"][0]["Words"]
    word_errors = _extract_challenging_words(words, custom_config)
    
    # Should find problematic words
    assert len(word_errors) > 0
    
    # Should prioritize omissions
    omitted = [w for w in word_errors if w.error_type == ErrorType.OMISSION]
    assert len(omitted) > 0
    assert omitted[0].word == "sky"


def test_word_extraction_includes_phoneme_errors(complex_azure_result, custom_config):
    """Test that word extraction includes phoneme-level errors."""
    words = complex_azure_result["NBest"][0]["Words"]
    word_errors = _extract_challenging_words(words, custom_config)
    
    # Find "rocket" word error
    rocket_error = next((w for w in word_errors if w.word == "rocket"), None)
    assert rocket_error is not None
    
    # Should have phoneme errors attached
    assert len(rocket_error.phoneme_errors) > 0
    
    # Should include the /r/ phoneme error
    r_error = next((p for p in rocket_error.phoneme_errors if p.phoneme == "r"), None)
    assert r_error is not None
    assert r_error.score == 35.0


def test_word_extraction_timing_info(complex_azure_result):
    """Test that word extraction preserves timing information."""
    words = complex_azure_result["NBest"][0]["Words"]
    word_errors = _extract_challenging_words(words, FeedbackConfig())
    
    # Check that timing info is converted correctly (100-nanosec to ms)
    for word_error in word_errors:
        if word_error.word == "rocket":
            assert word_error.offset_ms == 1500  # 15000000 / 10000
            assert word_error.duration_ms == 1000  # 10000000 / 10000


# === Prosody Extraction Tests ===

def test_extract_prosody_patterns(complex_azure_result):
    """Test extraction of prosody patterns."""
    config = FeedbackConfig(break_confidence_threshold=0.7)
    words = complex_azure_result["NBest"][0]["Words"]
    prosody_issues = _extract_prosody_patterns(words, config)
    
    # Should find unexpected break before "rocket"
    assert len(prosody_issues) > 0
    
    unexpected = [p for p in prosody_issues 
                  if p.issue_type == ProsodyErrorType.UNEXPECTED_BREAK]
    assert len(unexpected) > 0
    assert unexpected[0].word == "rocket"
    assert unexpected[0].confidence == 0.8


def test_prosody_extraction_respects_confidence_threshold(complex_azure_result):
    """Test that prosody extraction filters by confidence."""
    # High confidence threshold should find fewer issues
    config = FeedbackConfig(break_confidence_threshold=0.9)
    words = complex_azure_result["NBest"][0]["Words"]
    prosody_issues = _extract_prosody_patterns(words, config)
    
    # All issues should have high confidence
    for issue in prosody_issues:
        assert issue.confidence >= 0.9


# === Serialization Tests ===

def test_save_and_load_guidance_card(minimal_azure_result, tmp_path):
    """Test saving and loading guidance card to/from JSON."""
    guidance = parse_guidance_card(minimal_azure_result)
    
    # Save to temporary file
    filepath = tmp_path / "guidance.json"
    save_guidance_card(guidance, str(filepath))
    
    # Load back
    loaded = load_guidance_card(str(filepath))
    
    # Verify key attributes
    assert loaded.target_text == guidance.target_text
    assert loaded.target_display == guidance.target_display
    assert loaded.total_words == guidance.total_words
    assert loaded.reference_overall == guidance.reference_overall


def test_save_guidance_card_with_complex_data(complex_azure_result, tmp_path):
    """Test saving/loading guidance card with complex nested data."""
    guidance = parse_guidance_card(complex_azure_result)
    
    filepath = tmp_path / "complex_guidance.json"
    save_guidance_card(guidance, str(filepath))
    loaded = load_guidance_card(str(filepath))
    
    # Verify phoneme errors
    assert len(loaded.challenging_phonemes) == len(guidance.challenging_phonemes)
    if len(loaded.challenging_phonemes) > 0:
        assert loaded.challenging_phonemes[0].phoneme == guidance.challenging_phonemes[0].phoneme
    
    # Verify word errors
    assert len(loaded.challenging_words) == len(guidance.challenging_words)
    
    # Verify prosody patterns
    assert len(loaded.prosody_patterns) == len(guidance.prosody_patterns)


# === Error Handling Tests ===

def test_parse_empty_nbest():
    """Test parsing Azure result with empty NBest array."""
    result = {"DisplayText": "Test", "NBest": []}
    
    with pytest.raises(ValueError, match="No NBest results"):
        parse_guidance_card(result)


def test_parse_missing_fields():
    """Test parsing Azure result with missing optional fields."""
    result = {
        "DisplayText": "Test",
        "NBest": [
            {
                "Lexical": "test",
                "PronunciationAssessment": {},  # Missing scores
                "Words": []
            }
        ]
    }
    
    # Should not raise, but use default values
    guidance = parse_guidance_card(result)
    assert guidance.reference_accuracy == 0.0
    assert guidance.reference_overall == 0.0


# === Integration Tests ===

def test_full_pipeline_with_real_structure(complex_azure_result):
    """Test full guidance card generation with realistic data."""
    guidance = parse_guidance_card(complex_azure_result)
    
    # Verify all components
    assert guidance.target_text
    assert guidance.total_words == 4
    assert guidance.reference_overall > 0
    
    # Should have identified errors
    assert len(guidance.challenging_phonemes) > 0
    assert len(guidance.challenging_words) > 0
    assert len(guidance.prosody_patterns) > 0
    
    # Verify prioritization (worst errors first)
    if len(guidance.challenging_phonemes) > 1:
        assert guidance.challenging_phonemes[0].score <= guidance.challenging_phonemes[1].score


def test_guidance_card_repr(complex_azure_result):
    """Test that guidance card components have readable representations."""
    guidance = parse_guidance_card(complex_azure_result)
    
    # Test PhonemeError repr
    if guidance.challenging_phonemes:
        repr_str = repr(guidance.challenging_phonemes[0])
        assert "PhonemeError" in repr_str
        assert "score=" in repr_str
    
    # Test WordError repr
    if guidance.challenging_words:
        repr_str = repr(guidance.challenging_words[0])
        assert "WordError" in repr_str
    
    # Test ProsodyIssue repr
    if guidance.prosody_patterns:
        repr_str = repr(guidance.prosody_patterns[0])
        assert "ProsodyIssue" in repr_str


# === Configuration Tests ===

def test_config_classify_score():
    """Test score classification."""
    config = FeedbackConfig()
    
    assert config.classify_score(95) == "excellent"
    assert config.classify_score(80) == "good"
    assert config.classify_score(65) == "fair"
    assert config.classify_score(35) == "poor"


def test_config_threshold_checks():
    """Test configuration threshold helper methods."""
    config = FeedbackConfig(
        phoneme_error_threshold=70.0,
        phoneme_critical_threshold=40.0
    )
    
    assert config.is_phoneme_error(65.0) is True
    assert config.is_phoneme_error(75.0) is False
    assert config.is_critical_phoneme(35.0) is True
    assert config.is_critical_phoneme(50.0) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
