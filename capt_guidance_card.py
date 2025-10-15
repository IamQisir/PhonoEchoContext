"""
Guidance Card Generator for CAPT feedback pipeline.

This module parses the first pronunciation attempt to create a stable "Guidance Card"
that serves as a reference for all subsequent attempts. The guidance card identifies
challenging phonemes, words, and prosody patterns without overwhelming the user.

Key principle: Parse once, reuse many times.
"""

from typing import Dict, List, Optional
import json

from capt_models import (
    GuidanceCard,
    PhonemeError,
    WordError,
    ProsodyIssue,
    ErrorType,
    ProsodyErrorType,
)
from capt_config import FeedbackConfig, DEFAULT_CONFIG


def parse_guidance_card(
    azure_result: Dict,
    config: Optional[FeedbackConfig] = None
) -> GuidanceCard:
    """
    Parse Azure Speech Assessment JSON to create a Guidance Card.
    
    This function extracts:
    - Target sentence structure
    - Most challenging phonemes (worst scores)
    - Most challenging words (worst scores)
    - Prosody patterns (breaks, monotone issues)
    
    Args:
        azure_result: Azure Speech Assessment JSON dict
        config: Configuration object (uses DEFAULT_CONFIG if None)
        
    Returns:
        GuidanceCard object with stable reference data
        
    Example:
        >>> with open("first_attempt.json") as f:
        ...     result = json.load(f)
        >>> guidance = parse_guidance_card(result)
        >>> print(guidance.get_summary())
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Extract basic information
    display_text = azure_result.get("DisplayText", "")
    nbest = azure_result.get("NBest", [])
    
    if not nbest:
        raise ValueError("No NBest results in Azure response")
    
    best_result = nbest[0]
    lexical_text = best_result.get("Lexical", "")
    overall_assessment = best_result.get("PronunciationAssessment", {})
    words = best_result.get("Words", [])
    
    # Extract overall scores
    accuracy = overall_assessment.get("AccuracyScore", 0.0)
    fluency = overall_assessment.get("FluencyScore", 0.0)
    prosody = overall_assessment.get("ProsodyScore", 0.0)
    completeness = overall_assessment.get("CompletenessScore", 0.0)
    overall = overall_assessment.get("PronScore", 0.0)
    
    # Count total words and phonemes
    total_words = len(words)
    total_phonemes = sum(
        len(word.get("Phonemes", [])) for word in words
    )
    
    # Extract challenging phonemes
    challenging_phonemes = _extract_challenging_phonemes(
        words, config
    )
    
    # Extract challenging words
    challenging_words = _extract_challenging_words(
        words, config
    )
    
    # Extract prosody patterns
    prosody_patterns = _extract_prosody_patterns(
        words, config
    )
    
    # Create and return guidance card
    return GuidanceCard(
        target_text=lexical_text,
        target_display=display_text,
        total_words=total_words,
        total_phonemes=total_phonemes,
        challenging_phonemes=challenging_phonemes,
        challenging_words=challenging_words,
        prosody_patterns=prosody_patterns,
        reference_accuracy=accuracy,
        reference_fluency=fluency,
        reference_prosody=prosody,
        reference_completeness=completeness,
        reference_overall=overall,
    )


def _extract_challenging_phonemes(
    words: List[Dict],
    config: FeedbackConfig
) -> List[PhonemeError]:
    """
    Extract the most challenging phonemes from all words.
    
    Strategy:
    1. Collect all phoneme errors (score < threshold)
    2. Sort by score (worst first)
    3. Return top N unique phonemes
    
    Args:
        words: List of word dictionaries from Azure result
        config: Configuration object
        
    Returns:
        List of PhonemeError objects (up to config.max_guidance_phonemes)
    """
    all_phoneme_errors: List[PhonemeError] = []
    
    for word in words:
        word_text = word.get("Word", "")
        phonemes = word.get("Phonemes", [])
        
        for idx, phoneme in enumerate(phonemes):
            phoneme_symbol = phoneme.get("Phoneme", "")
            assessment = phoneme.get("PronunciationAssessment", {})
            score = assessment.get("AccuracyScore", 100.0)
            
            # Only include errors
            if config.is_phoneme_error(score):
                error = PhonemeError(
                    phoneme=phoneme_symbol,
                    score=score,
                    word=word_text,
                    position=idx
                )
                all_phoneme_errors.append(error)
    
    # Sort by score (worst first), then take top N
    all_phoneme_errors.sort(key=lambda e: e.score)
    return all_phoneme_errors[:config.max_guidance_phonemes]


def _extract_challenging_words(
    words: List[Dict],
    config: FeedbackConfig
) -> List[WordError]:
    """
    Extract the most challenging words.
    
    Strategy:
    1. Identify words with errors (score < threshold or omitted)
    2. Sort by priority: Omissions > Mispronunciations > Low scores
    3. Return top N words with their phoneme errors
    
    Args:
        words: List of word dictionaries from Azure result
        config: Configuration object
        
    Returns:
        List of WordError objects (up to config.max_guidance_words)
    """
    all_word_errors: List[WordError] = []
    
    for word in words:
        word_text = word.get("Word", "")
        assessment = word.get("PronunciationAssessment", {})
        
        # Parse error type
        error_type_str = assessment.get("ErrorType", "None")
        try:
            error_type = ErrorType(error_type_str)
        except ValueError:
            error_type = ErrorType.NONE
        
        # Get score (None for omissions)
        score = assessment.get("AccuracyScore", None)
        if error_type == ErrorType.OMISSION:
            score = None
        
        # Check if this word has issues
        is_error = (
            error_type != ErrorType.NONE or
            (score is not None and config.is_word_error(score))
        )
        
        if is_error:
            # Extract phoneme errors for this word
            phoneme_errors = []
            for idx, phoneme in enumerate(word.get("Phonemes", [])):
                phoneme_symbol = phoneme.get("Phoneme", "")
                phoneme_assessment = phoneme.get("PronunciationAssessment", {})
                phoneme_score = phoneme_assessment.get("AccuracyScore", 100.0)
                
                if config.is_phoneme_error(phoneme_score):
                    phoneme_errors.append(PhonemeError(
                        phoneme=phoneme_symbol,
                        score=phoneme_score,
                        word=word_text,
                        position=idx
                    ))
            
            # Get timing info
            offset_ms = word.get("Offset", 0) // 10000  # Convert from 100-nanosec to milliseconds
            duration_ms = word.get("Duration", 0) // 10000
            
            word_error = WordError(
                word=word_text,
                score=score,
                error_type=error_type,
                phoneme_errors=phoneme_errors,
                offset_ms=offset_ms,
                duration_ms=duration_ms
            )
            all_word_errors.append(word_error)
    
    # Sort by priority: Omissions first, then by error priority, then by score
    def word_priority(we: WordError) -> tuple:
        priority = config.error_type_priorities.get(we.error_type.value, 0)
        score_val = we.score if we.score is not None else -1
        return (-priority, score_val)  # Higher priority first, lower score first
    
    all_word_errors.sort(key=word_priority)
    return all_word_errors[:config.max_guidance_words]


def _extract_prosody_patterns(
    words: List[Dict],
    config: FeedbackConfig
) -> List[ProsodyIssue]:
    """
    Extract prosody patterns (pauses, intonation, monotone).
    
    Strategy:
    1. Check Feedback.Prosody for each word
    2. Identify unexpected breaks, missing breaks, monotone speech
    3. Filter by confidence thresholds
    4. Return top N issues
    
    Args:
        words: List of word dictionaries from Azure result
        config: Configuration object
        
    Returns:
        List of ProsodyIssue objects (up to config.guidance_prosody_issues)
    """
    all_prosody_issues: List[ProsodyIssue] = []
    
    for word in words:
        word_text = word.get("Word", "")
        assessment = word.get("PronunciationAssessment", {})
        feedback = assessment.get("Feedback", {})
        prosody_feedback = feedback.get("Prosody", {})
        
        # Check for break issues
        break_feedback = prosody_feedback.get("Break", {})
        error_types = break_feedback.get("ErrorTypes", [])
        
        # Unexpected break
        unexpected_break = break_feedback.get("UnexpectedBreak", {})
        if isinstance(unexpected_break, dict):
            confidence = unexpected_break.get("Confidence", 0.0)
            if confidence >= config.break_confidence_threshold:
                break_length = break_feedback.get("BreakLength", 0) // 10000  # Convert to ms
                all_prosody_issues.append(ProsodyIssue(
                    issue_type=ProsodyErrorType.UNEXPECTED_BREAK,
                    word=word_text,
                    confidence=confidence,
                    break_length_ms=break_length,
                    description=f"Unexpected pause before '{word_text}' ({break_length}ms)"
                ))
        
        # Missing break
        missing_break = break_feedback.get("MissingBreak", {})
        if isinstance(missing_break, dict):
            confidence = missing_break.get("Confidence", 0.0)
            if confidence >= config.break_confidence_threshold:
                all_prosody_issues.append(ProsodyIssue(
                    issue_type=ProsodyErrorType.MISSING_BREAK,
                    word=word_text,
                    confidence=confidence,
                    description=f"Missing pause after '{word_text}'"
                ))
        
        # Monotone intonation
        intonation_feedback = prosody_feedback.get("Intonation", {})
        monotone_feedback = intonation_feedback.get("Monotone", {})
        if isinstance(monotone_feedback, dict):
            confidence = monotone_feedback.get("SyllablePitchDeltaConfidence", 0.0)
            if confidence >= config.monotone_confidence_threshold:
                all_prosody_issues.append(ProsodyIssue(
                    issue_type=ProsodyErrorType.MONOTONE,
                    word=word_text,
                    confidence=confidence,
                    description=f"Monotone intonation around '{word_text}'"
                ))
    
    # Sort by confidence (highest first), take top N
    all_prosody_issues.sort(key=lambda p: p.confidence, reverse=True)
    return all_prosody_issues[:config.guidance_prosody_issues]


def save_guidance_card(guidance: GuidanceCard, filepath: str) -> None:
    """
    Save a guidance card to JSON file for persistence.
    
    Args:
        guidance: GuidanceCard object
        filepath: Output file path
    """
    import json
    from dataclasses import asdict
    
    # Convert to dict and handle Enum serialization
    data = asdict(guidance)
    
    # Convert ErrorType enums to strings
    for word_error in data.get("challenging_words", []):
        if "error_type" in word_error:
            word_error["error_type"] = word_error["error_type"].value if hasattr(word_error["error_type"], "value") else str(word_error["error_type"])
    
    # Convert ProsodyErrorType enums to strings
    for prosody_issue in data.get("prosody_patterns", []):
        if "issue_type" in prosody_issue:
            prosody_issue["issue_type"] = prosody_issue["issue_type"].value if hasattr(prosody_issue["issue_type"], "value") else str(prosody_issue["issue_type"])
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_guidance_card(filepath: str) -> GuidanceCard:
    """
    Load a guidance card from JSON file.
    
    Args:
        filepath: Input file path
        
    Returns:
        GuidanceCard object
    """
    import json
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Reconstruct nested objects
    guidance = GuidanceCard(
        target_text=data["target_text"],
        target_display=data["target_display"],
        total_words=data["total_words"],
        total_phonemes=data["total_phonemes"],
        reference_accuracy=data["reference_accuracy"],
        reference_fluency=data["reference_fluency"],
        reference_prosody=data["reference_prosody"],
        reference_completeness=data["reference_completeness"],
        reference_overall=data["reference_overall"],
    )
    
    # Reconstruct challenging phonemes
    for ph_data in data.get("challenging_phonemes", []):
        guidance.challenging_phonemes.append(PhonemeError(
            phoneme=ph_data["phoneme"],
            score=ph_data["score"],
            word=ph_data["word"],
            position=ph_data["position"],
            expected_phoneme=ph_data.get("expected_phoneme")
        ))
    
    # Reconstruct challenging words
    for word_data in data.get("challenging_words", []):
        word_error = WordError(
            word=word_data["word"],
            score=word_data["score"],
            error_type=ErrorType(word_data["error_type"]),
            offset_ms=word_data.get("offset_ms", 0),
            duration_ms=word_data.get("duration_ms", 0)
        )
        for ph_data in word_data.get("phoneme_errors", []):
            word_error.phoneme_errors.append(PhonemeError(
                phoneme=ph_data["phoneme"],
                score=ph_data["score"],
                word=ph_data["word"],
                position=ph_data["position"]
            ))
        guidance.challenging_words.append(word_error)
    
    # Reconstruct prosody patterns
    for pros_data in data.get("prosody_patterns", []):
        guidance.prosody_patterns.append(ProsodyIssue(
            issue_type=ProsodyErrorType(pros_data["issue_type"]),
            word=pros_data["word"],
            confidence=pros_data["confidence"],
            break_length_ms=pros_data.get("break_length_ms", 0),
            description=pros_data.get("description", "")
        ))
    
    return guidance
