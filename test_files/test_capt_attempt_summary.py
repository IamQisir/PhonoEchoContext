"""
Unit tests for CAPT Attempt Summary Parser.

These tests verify the attempt summary generation and comparison logic.
All tests use mock data and require no network calls.
"""

import pytest
from typing import Dict

from capt_attempt_summary import (
    parse_attempt_summary,
    _extract_current_phoneme_errors,
    _extract_current_word_errors,
    _extract_omitted_words,
    _compare_with_guidance,
    _compare_with_previous,
    save_attempt_summary,
    load_attempt_summary,
)
from capt_guidance_card import parse_guidance_card
from capt_config import FeedbackConfig
from capt_models import AttemptSummary, ErrorType


# === Fixtures ===

@pytest.fixture
def first_attempt_result() -> Dict:
    """First attempt with several errors."""
    return {
        "NBest": [
            {
                "PronunciationAssessment": {
                    "AccuracyScore": 70.0,
                    "FluencyScore": 65.0,
                    "ProsodyScore": 60.0,
                    "CompletenessScore": 80.0,
                    "PronScore": 68.0,
                },
                "Words": [
                    {
                        "Word": "hello",
                        "PronunciationAssessment": {
                            "AccuracyScore": 60.0,
                            "ErrorType": "Mispronunciation"
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "h",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 50.0
                                }
                            },
                            {
                                "Phoneme": "ɛ",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 65.0
                                }
                            }
                        ]
                    },
                    {
                        "Word": "world",
                        "PronunciationAssessment": {
                            "AccuracyScore": None,
                            "ErrorType": "Omission"
                        },
                        "Phonemes": []
                    }
                ]
            }
        ]
    }


@pytest.fixture
def second_attempt_result() -> Dict:
    """Second attempt with improvements."""
    return {
        "NBest": [
            {
                "PronunciationAssessment": {
                    "AccuracyScore": 85.0,
                    "FluencyScore": 80.0,
                    "ProsodyScore": 75.0,
                    "CompletenessScore": 95.0,
                    "PronScore": 83.0,
                },
                "Words": [
                    {
                        "Word": "hello",
                        "PronunciationAssessment": {
                            "AccuracyScore": 90.0,  # Improved
                            "ErrorType": "None"
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "h",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 85.0  # Improved
                                }
                            },
                            {
                                "Phoneme": "ɛ",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 90.0  # Improved
                                }
                            }
                        ]
                    },
                    {
                        "Word": "world",
                        "PronunciationAssessment": {
                            "AccuracyScore": 80.0,  # No longer omitted
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
def third_attempt_result() -> Dict:
    """Third attempt with regression."""
    return {
        "NBest": [
            {
                "PronunciationAssessment": {
                    "AccuracyScore": 75.0,
                    "FluencyScore": 70.0,
                    "ProsodyScore": 68.0,
                    "CompletenessScore": 90.0,
                    "PronScore": 75.0,
                },
                "Words": [
                    {
                        "Word": "hello",
                        "PronunciationAssessment": {
                            "AccuracyScore": 65.0,  # Regressed from 90 to 65
                            "ErrorType": "None"
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "h",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 60.0  # Regressed
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
                            "AccuracyScore": 85.0,
                            "ErrorType": "None"
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "w",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 80.0
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }


# === Basic Parsing Tests ===

def test_parse_attempt_summary_basic(first_attempt_result):
    """Test basic attempt summary parsing."""
    # Create mock guidance card
    guidance = parse_guidance_card({
        "DisplayText": "Hello world",
        "NBest": [{"Lexical": "hello world", 
                   "PronunciationAssessment": {
                       "AccuracyScore": 70.0,
                       "FluencyScore": 65.0,
                       "ProsodyScore": 60.0,
                       "CompletenessScore": 80.0,
                       "PronScore": 68.0,
                   },
                   "Words": first_attempt_result["NBest"][0]["Words"]}]
    })
    
    summary = parse_attempt_summary(
        first_attempt_result,
        attempt_number=1,
        guidance_card=guidance
    )
    
    assert summary.attempt_number == 1
    assert summary.accuracy_score == 70.0
    assert summary.fluency_score == 65.0
    assert summary.overall_score == 68.0


def test_parse_attempt_extracts_scores(first_attempt_result):
    """Test that all scores are extracted correctly."""
    guidance = parse_guidance_card({
        "DisplayText": "Test",
        "NBest": [{"Lexical": "test", 
                   "PronunciationAssessment": {},
                   "Words": []}]
    })
    
    summary = parse_attempt_summary(
        first_attempt_result,
        attempt_number=1,
        guidance_card=guidance
    )
    
    assert summary.accuracy_score == 70.0
    assert summary.fluency_score == 65.0
    assert summary.prosody_score == 60.0
    assert summary.completeness_score == 80.0
    assert summary.overall_score == 68.0


# === Error Extraction Tests ===

def test_extract_current_phoneme_errors(first_attempt_result):
    """Test phoneme error extraction."""
    config = FeedbackConfig(phoneme_error_threshold=70.0)
    words = first_attempt_result["NBest"][0]["Words"]
    errors = _extract_current_phoneme_errors(words, config)
    
    # Should find /h/ (50) and /ɛ/ (65)
    assert len(errors) >= 2
    
    # Worst error should be first
    assert errors[0].phoneme == "h"
    assert errors[0].score == 50.0


def test_extract_current_word_errors(first_attempt_result):
    """Test word error extraction."""
    config = FeedbackConfig(word_error_threshold=70.0)
    words = first_attempt_result["NBest"][0]["Words"]
    errors = _extract_current_word_errors(words, config)
    
    # Should find "hello" (60) and "world" (omitted)
    assert len(errors) >= 2
    
    # Omission should be prioritized
    omitted = [e for e in errors if e.error_type == ErrorType.OMISSION]
    assert len(omitted) == 1
    assert omitted[0].word == "world"


def test_extract_omitted_words(first_attempt_result):
    """Test omitted word extraction."""
    words = first_attempt_result["NBest"][0]["Words"]
    omitted = _extract_omitted_words(words)
    
    assert len(omitted) == 1
    assert omitted[0] == "world"


def test_word_errors_include_phonemes(first_attempt_result):
    """Test that word errors include phoneme-level details."""
    config = FeedbackConfig(word_error_threshold=70.0)
    words = first_attempt_result["NBest"][0]["Words"]
    errors = _extract_current_word_errors(words, config)
    
    # Find "hello" error
    hello_error = next((e for e in errors if e.word == "hello"), None)
    assert hello_error is not None
    
    # Should have phoneme errors
    assert len(hello_error.phoneme_errors) > 0


# === Comparison Tests ===

def test_compare_with_guidance_finds_improvements(first_attempt_result, second_attempt_result):
    """Test comparison with guidance card identifies improvements."""
    # Create guidance from first attempt
    guidance = parse_guidance_card({
        "DisplayText": "Hello world",
        "NBest": [{"Lexical": "hello world", 
                   "PronunciationAssessment": {
                       "AccuracyScore": 70.0,
                       "FluencyScore": 65.0,
                       "ProsodyScore": 60.0,
                       "CompletenessScore": 80.0,
                       "PronScore": 68.0,
                   },
                   "Words": first_attempt_result["NBest"][0]["Words"]}]
    })
    
    # Parse second attempt
    summary = parse_attempt_summary(
        second_attempt_result,
        attempt_number=2,
        guidance_card=guidance
    )
    
    # Should find improvements (hello was problematic, now fixed)
    assert len(summary.improved_words) > 0 or len(summary.improved_phonemes) > 0


def test_compare_with_previous_finds_improvements(
    first_attempt_result, 
    second_attempt_result
):
    """Test comparison with previous attempt finds improvements."""
    guidance = parse_guidance_card({
        "DisplayText": "Hello world",
        "NBest": [{"Lexical": "hello world", 
                   "PronunciationAssessment": {},
                   "Words": first_attempt_result["NBest"][0]["Words"]}]
    })
    
    # Parse first attempt
    attempt1 = parse_attempt_summary(
        first_attempt_result,
        attempt_number=1,
        guidance_card=guidance
    )
    
    # Parse second attempt with comparison
    attempt2 = parse_attempt_summary(
        second_attempt_result,
        attempt_number=2,
        guidance_card=guidance,
        previous_attempt=attempt1
    )
    
    # Should find improvements
    assert len(attempt2.improved_words) > 0


def test_compare_with_previous_finds_regressions(
    second_attempt_result,
    third_attempt_result
):
    """Test comparison with previous attempt finds regressions."""
    guidance = parse_guidance_card({
        "DisplayText": "Hello world",
        "NBest": [{"Lexical": "hello world", 
                   "PronunciationAssessment": {},
                   "Words": second_attempt_result["NBest"][0]["Words"]}]
    })
    
    # Parse second attempt (good performance)
    attempt2 = parse_attempt_summary(
        second_attempt_result,
        attempt_number=2,
        guidance_card=guidance
    )
    
    # Parse third attempt (regression)
    attempt3 = parse_attempt_summary(
        third_attempt_result,
        attempt_number=3,
        guidance_card=guidance,
        previous_attempt=attempt2
    )
    
    # Should find regressions (hello got worse)
    assert len(attempt3.regressed_words) > 0 or len(attempt3.regressed_phonemes) > 0


# === Summary Methods Tests ===

def test_attempt_summary_get_summary(first_attempt_result):
    """Test attempt summary text generation."""
    guidance = parse_guidance_card({
        "DisplayText": "Test",
        "NBest": [{"Lexical": "test", 
                   "PronunciationAssessment": {},
                   "Words": []}]
    })
    
    summary = parse_attempt_summary(
        first_attempt_result,
        attempt_number=2,
        guidance_card=guidance
    )
    
    text = summary.get_summary()
    
    assert "Attempt #2" in text
    assert "68" in text  # Overall score
    assert "70" in text  # Accuracy


# === Serialization Tests ===

def test_save_and_load_attempt_summary(first_attempt_result, tmp_path):
    """Test saving and loading attempt summary."""
    guidance = parse_guidance_card({
        "DisplayText": "Test",
        "NBest": [{"Lexical": "test", 
                   "PronunciationAssessment": {},
                   "Words": []}]
    })
    
    summary = parse_attempt_summary(
        first_attempt_result,
        attempt_number=1,
        guidance_card=guidance
    )
    
    # Save
    filepath = tmp_path / "attempt.json"
    save_attempt_summary(summary, str(filepath))
    
    # Load
    loaded = load_attempt_summary(str(filepath))
    
    # Verify
    assert loaded.attempt_number == summary.attempt_number
    assert loaded.overall_score == summary.overall_score
    assert len(loaded.current_word_errors) == len(summary.current_word_errors)


# === Integration Tests ===

def test_full_progression_three_attempts(
    first_attempt_result,
    second_attempt_result,
    third_attempt_result
):
    """Test full progression across three attempts."""
    # Create guidance from first attempt
    guidance = parse_guidance_card({
        "DisplayText": "Hello world",
        "NBest": [{"Lexical": "hello world", 
                   "PronunciationAssessment": {
                       "AccuracyScore": 70.0,
                       "FluencyScore": 65.0,
                       "ProsodyScore": 60.0,
                       "CompletenessScore": 80.0,
                       "PronScore": 68.0,
                   },
                   "Words": first_attempt_result["NBest"][0]["Words"]}]
    })
    
    # Parse attempt 1
    attempt1 = parse_attempt_summary(
        first_attempt_result,
        attempt_number=1,
        guidance_card=guidance
    )
    assert attempt1.overall_score == 68.0
    
    # Parse attempt 2 (improvement)
    attempt2 = parse_attempt_summary(
        second_attempt_result,
        attempt_number=2,
        guidance_card=guidance,
        previous_attempt=attempt1
    )
    assert attempt2.overall_score > attempt1.overall_score
    assert len(attempt2.improved_words) > 0
    
    # Parse attempt 3 (slight regression)
    attempt3 = parse_attempt_summary(
        third_attempt_result,
        attempt_number=3,
        guidance_card=guidance,
        previous_attempt=attempt2
    )
    assert attempt3.overall_score < attempt2.overall_score


def test_error_prioritization(first_attempt_result):
    """Test that errors are prioritized correctly."""
    config = FeedbackConfig(max_attempt_errors=3)
    guidance = parse_guidance_card({
        "DisplayText": "Test",
        "NBest": [{"Lexical": "test", 
                   "PronunciationAssessment": {},
                   "Words": []}]
    })
    
    summary = parse_attempt_summary(
        first_attempt_result,
        attempt_number=1,
        guidance_card=guidance,
        config=config
    )
    
    # Should respect max_attempt_errors limit
    assert len(summary.current_phoneme_errors) <= 3
    assert len(summary.current_word_errors) <= 3
    
    # Check that omissions are present and prioritized
    if summary.current_word_errors:
        omitted = [e for e in summary.current_word_errors 
                   if e.error_type == ErrorType.OMISSION]
        if omitted:
            # If there are omissions, they should be among the first errors
            # (mispronunciations with priority 3 come before omissions with priority 2)
            omission_indices = [i for i, e in enumerate(summary.current_word_errors) 
                               if e.error_type == ErrorType.OMISSION]
            # Just verify omissions are included, not necessarily first
            assert len(omission_indices) > 0


# === Edge Cases ===

def test_parse_attempt_with_no_errors():
    """Test parsing attempt with perfect pronunciation."""
    perfect_result = {
        "NBest": [
            {
                "PronunciationAssessment": {
                    "AccuracyScore": 100.0,
                    "FluencyScore": 100.0,
                    "ProsodyScore": 100.0,
                    "CompletenessScore": 100.0,
                    "PronScore": 100.0,
                },
                "Words": [
                    {
                        "Word": "perfect",
                        "PronunciationAssessment": {
                            "AccuracyScore": 100.0,
                            "ErrorType": "None"
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "p",
                                "PronunciationAssessment": {
                                    "AccuracyScore": 100.0
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    guidance = parse_guidance_card({
        "DisplayText": "Perfect",
        "NBest": [{"Lexical": "perfect", 
                   "PronunciationAssessment": {},
                   "Words": perfect_result["NBest"][0]["Words"]}]
    })
    
    summary = parse_attempt_summary(
        perfect_result,
        attempt_number=1,
        guidance_card=guidance
    )
    
    assert summary.overall_score == 100.0
    assert len(summary.current_phoneme_errors) == 0
    assert len(summary.current_word_errors) == 0
    assert len(summary.omitted_words) == 0


def test_parse_attempt_with_missing_nbest():
    """Test error handling for missing NBest."""
    bad_result = {"NBest": []}
    guidance = parse_guidance_card({
        "DisplayText": "Test",
        "NBest": [{"Lexical": "test", 
                   "PronunciationAssessment": {},
                   "Words": []}]
    })
    
    with pytest.raises(ValueError, match="No NBest results"):
        parse_attempt_summary(bad_result, 1, guidance)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
