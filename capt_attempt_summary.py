"""
Attempt Summary Generator for CAPT feedback pipeline.

This module parses subsequent pronunciation attempts and generates lightweight
summaries that capture only incremental changes (errors, improvements, regressions)
compared to the guidance card or previous attempt.

Key principle: Minimal parsing, focus on deltas.
"""

from typing import Dict, List, Optional
import json

from capt_models import (
    AttemptSummary,
    GuidanceCard,
    PhonemeError,
    WordError,
    ProsodyIssue,
    ErrorType,
    ProsodyErrorType,
)
from capt_config import FeedbackConfig, DEFAULT_CONFIG


def parse_attempt_summary(
    azure_result: Dict,
    attempt_number: int,
    guidance_card: GuidanceCard,
    previous_attempt: Optional[AttemptSummary] = None,
    config: Optional[FeedbackConfig] = None
) -> AttemptSummary:
    """
    Parse Azure Speech Assessment JSON to create an Attempt Summary.
    
    This function extracts only the incremental changes:
    - Current errors (phonemes, words, prosody)
    - Improvements compared to previous attempt or guidance card
    - Regressions compared to previous attempt
    - Omitted/inserted words
    
    Args:
        azure_result: Azure Speech Assessment JSON dict
        attempt_number: Sequential attempt number (1, 2, 3, ...)
        guidance_card: Reference guidance card from first attempt
        previous_attempt: Previous attempt summary for comparison (optional)
        config: Configuration object (uses DEFAULT_CONFIG if None)
        
    Returns:
        AttemptSummary object with incremental analysis
        
    Example:
        >>> guidance = parse_guidance_card(first_result)
        >>> attempt2 = parse_attempt_summary(second_result, 2, guidance)
        >>> print(attempt2.get_summary())
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Extract basic information
    nbest = azure_result.get("NBest", [])
    if not nbest:
        raise ValueError("No NBest results in Azure response")
    
    best_result = nbest[0]
    overall_assessment = best_result.get("PronunciationAssessment", {})
    words = best_result.get("Words", [])
    
    # Extract current scores
    accuracy = overall_assessment.get("AccuracyScore", 0.0)
    fluency = overall_assessment.get("FluencyScore", 0.0)
    prosody = overall_assessment.get("ProsodyScore", 0.0)
    completeness = overall_assessment.get("CompletenessScore", 0.0)
    overall = overall_assessment.get("PronScore", 0.0)
    
    # Create attempt summary
    summary = AttemptSummary(
        attempt_number=attempt_number,
        accuracy_score=accuracy,
        fluency_score=fluency,
        prosody_score=prosody,
        completeness_score=completeness,
        overall_score=overall,
    )
    
    # Extract current errors
    summary.current_phoneme_errors = _extract_current_phoneme_errors(words, config)
    summary.current_word_errors = _extract_current_word_errors(words, config)
    summary.current_prosody_issues = _extract_current_prosody_issues(words, config)
    
    # Identify omitted and inserted words
    summary.omitted_words = _extract_omitted_words(words)
    summary.inserted_words = _extract_inserted_words(words)
    
    # Compare with previous attempt or guidance card to find improvements/regressions
    if previous_attempt is not None:
        _compare_with_previous(summary, previous_attempt, guidance_card)
    else:
        _compare_with_guidance(summary, guidance_card)
    
    return summary


def _extract_current_phoneme_errors(
    words: List[Dict],
    config: FeedbackConfig
) -> List[PhonemeError]:
    """
    Extract phoneme errors from current attempt.
    
    Only returns the worst errors (up to config.max_attempt_errors).
    """
    all_errors: List[PhonemeError] = []
    
    for word in words:
        word_text = word.get("Word", "")
        phonemes = word.get("Phonemes", [])
        
        for idx, phoneme in enumerate(phonemes):
            phoneme_symbol = phoneme.get("Phoneme", "")
            assessment = phoneme.get("PronunciationAssessment", {})
            score = assessment.get("AccuracyScore", 100.0)
            
            if config.is_phoneme_error(score):
                all_errors.append(PhonemeError(
                    phoneme=phoneme_symbol,
                    score=score,
                    word=word_text,
                    position=idx
                ))
    
    # Sort by score (worst first), prioritize critical errors
    all_errors.sort(key=lambda e: (
        0 if config.is_critical_phoneme(e.score) else 1,
        e.score
    ))
    
    return all_errors[:config.max_attempt_errors]


def _extract_current_word_errors(
    words: List[Dict],
    config: FeedbackConfig
) -> List[WordError]:
    """
    Extract word errors from current attempt.
    
    Only returns the most significant errors (up to config.max_attempt_errors).
    """
    all_errors: List[WordError] = []
    
    for word in words:
        word_text = word.get("Word", "")
        assessment = word.get("PronunciationAssessment", {})
        
        # Parse error type
        error_type_str = assessment.get("ErrorType", "None")
        try:
            error_type = ErrorType(error_type_str)
        except ValueError:
            error_type = ErrorType.NONE
        
        # Get score
        score = assessment.get("AccuracyScore", None)
        if error_type == ErrorType.OMISSION:
            score = None
        
        # Check if this is an error
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
            
            offset_ms = word.get("Offset", 0) // 10000
            duration_ms = word.get("Duration", 0) // 10000
            
            all_errors.append(WordError(
                word=word_text,
                score=score,
                error_type=error_type,
                phoneme_errors=phoneme_errors,
                offset_ms=offset_ms,
                duration_ms=duration_ms
            ))
    
    # Sort by priority
    def word_priority(we: WordError) -> tuple:
        priority = config.error_type_priorities.get(we.error_type.value, 0)
        score_val = we.score if we.score is not None else -1
        return (-priority, score_val)
    
    all_errors.sort(key=word_priority)
    return all_errors[:config.max_attempt_errors]


def _extract_current_prosody_issues(
    words: List[Dict],
    config: FeedbackConfig
) -> List[ProsodyIssue]:
    """
    Extract prosody issues from current attempt.
    
    Only returns the most significant issues (up to config.max_attempt_errors).
    """
    all_issues: List[ProsodyIssue] = []
    
    for word in words:
        word_text = word.get("Word", "")
        assessment = word.get("PronunciationAssessment", {})
        feedback = assessment.get("Feedback", {})
        prosody_feedback = feedback.get("Prosody", {})
        
        # Check for break issues
        break_feedback = prosody_feedback.get("Break", {})
        
        # Unexpected break
        unexpected_break = break_feedback.get("UnexpectedBreak", {})
        if isinstance(unexpected_break, dict):
            confidence = unexpected_break.get("Confidence", 0.0)
            if confidence >= config.break_confidence_threshold:
                break_length = break_feedback.get("BreakLength", 0) // 10000
                all_issues.append(ProsodyIssue(
                    issue_type=ProsodyErrorType.UNEXPECTED_BREAK,
                    word=word_text,
                    confidence=confidence,
                    break_length_ms=break_length,
                    description=f"Unexpected pause before '{word_text}'"
                ))
        
        # Missing break
        missing_break = break_feedback.get("MissingBreak", {})
        if isinstance(missing_break, dict):
            confidence = missing_break.get("Confidence", 0.0)
            if confidence >= config.break_confidence_threshold:
                all_issues.append(ProsodyIssue(
                    issue_type=ProsodyErrorType.MISSING_BREAK,
                    word=word_text,
                    confidence=confidence,
                    description=f"Missing pause after '{word_text}'"
                ))
        
        # Monotone
        intonation_feedback = prosody_feedback.get("Intonation", {})
        monotone_feedback = intonation_feedback.get("Monotone", {})
        if isinstance(monotone_feedback, dict):
            confidence = monotone_feedback.get("SyllablePitchDeltaConfidence", 0.0)
            if confidence >= config.monotone_confidence_threshold:
                all_issues.append(ProsodyIssue(
                    issue_type=ProsodyErrorType.MONOTONE,
                    word=word_text,
                    confidence=confidence,
                    description=f"Monotone intonation around '{word_text}'"
                ))
    
    # Sort by confidence (highest first)
    all_issues.sort(key=lambda p: p.confidence, reverse=True)
    return all_issues[:config.max_attempt_errors]


def _extract_omitted_words(words: List[Dict]) -> List[str]:
    """Extract list of omitted words."""
    omitted = []
    for word in words:
        assessment = word.get("PronunciationAssessment", {})
        error_type = assessment.get("ErrorType", "None")
        if error_type == "Omission":
            omitted.append(word.get("Word", ""))
    return omitted


def _extract_inserted_words(words: List[Dict]) -> List[str]:
    """Extract list of inserted (unexpected) words."""
    inserted = []
    for word in words:
        assessment = word.get("PronunciationAssessment", {})
        error_type = assessment.get("ErrorType", "None")
        if error_type == "Insertion":
            inserted.append(word.get("Word", ""))
    return inserted


def _compare_with_guidance(
    summary: AttemptSummary,
    guidance: GuidanceCard
) -> None:
    """
    Compare current attempt with guidance card to identify improvements.
    
    Modifies summary in-place to add improved_phonemes and improved_words.
    """
    # Build set of currently problematic phonemes
    current_problem_phonemes = {
        f"{e.phoneme}_{e.word}" for e in summary.current_phoneme_errors
    }
    
    # Check which guidance phonemes are now fixed
    for guidance_error in guidance.challenging_phonemes:
        key = f"{guidance_error.phoneme}_{guidance_error.word}"
        if key not in current_problem_phonemes:
            summary.improved_phonemes.append(
                f"{guidance_error.phoneme} in '{guidance_error.word}'"
            )
    
    # Build set of currently problematic words
    current_problem_words = {e.word for e in summary.current_word_errors}
    
    # Check which guidance words are now fixed
    for guidance_error in guidance.challenging_words:
        if guidance_error.word not in current_problem_words:
            summary.improved_words.append(guidance_error.word)


def _compare_with_previous(
    summary: AttemptSummary,
    previous: AttemptSummary,
    guidance: GuidanceCard
) -> None:
    """
    Compare current attempt with previous attempt to identify improvements/regressions.
    
    Modifies summary in-place to add improvements and regressions.
    """
    # Build sets for comparison
    current_problem_phonemes = {
        f"{e.phoneme}_{e.word}" for e in summary.current_phoneme_errors
    }
    previous_problem_phonemes = {
        f"{e.phoneme}_{e.word}" for e in previous.current_phoneme_errors
    }
    
    # Improvements: phonemes that were problematic but now fixed
    improved_phonemes = previous_problem_phonemes - current_problem_phonemes
    summary.improved_phonemes = [
        key.replace("_", " in '") + "'" for key in improved_phonemes
    ]
    
    # Regressions: new phoneme problems
    regressed_phonemes = current_problem_phonemes - previous_problem_phonemes
    summary.regressed_phonemes = [
        key.replace("_", " in '") + "'" for key in regressed_phonemes
    ]
    
    # Word-level comparison
    current_problem_words = {e.word for e in summary.current_word_errors}
    previous_problem_words = {e.word for e in previous.current_word_errors}
    
    improved_words = previous_problem_words - current_problem_words
    summary.improved_words = list(improved_words)
    
    regressed_words = current_problem_words - previous_problem_words
    summary.regressed_words = list(regressed_words)


def save_attempt_summary(summary: AttemptSummary, filepath: str) -> None:
    """
    Save an attempt summary to JSON file.
    
    Args:
        summary: AttemptSummary object
        filepath: Output file path
    """
    import json
    from dataclasses import asdict
    
    # Convert to dict and handle Enum serialization
    data = asdict(summary)
    
    # Convert ErrorType enums to strings
    for word_error in data.get("current_word_errors", []):
        if "error_type" in word_error:
            word_error["error_type"] = word_error["error_type"].value if hasattr(word_error["error_type"], "value") else str(word_error["error_type"])
    
    # Convert ProsodyErrorType enums to strings
    for prosody_issue in data.get("current_prosody_issues", []):
        if "issue_type" in prosody_issue:
            prosody_issue["issue_type"] = prosody_issue["issue_type"].value if hasattr(prosody_issue["issue_type"], "value") else str(prosody_issue["issue_type"])
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_attempt_summary(filepath: str) -> AttemptSummary:
    """
    Load an attempt summary from JSON file.
    
    Args:
        filepath: Input file path
        
    Returns:
        AttemptSummary object
    """
    import json
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Reconstruct attempt summary
    summary = AttemptSummary(
        attempt_number=data["attempt_number"],
        accuracy_score=data["accuracy_score"],
        fluency_score=data["fluency_score"],
        prosody_score=data["prosody_score"],
        completeness_score=data["completeness_score"],
        overall_score=data["overall_score"],
        improved_phonemes=data.get("improved_phonemes", []),
        improved_words=data.get("improved_words", []),
        regressed_phonemes=data.get("regressed_phonemes", []),
        regressed_words=data.get("regressed_words", []),
        omitted_words=data.get("omitted_words", []),
        inserted_words=data.get("inserted_words", []),
    )
    
    # Reconstruct phoneme errors
    for ph_data in data.get("current_phoneme_errors", []):
        summary.current_phoneme_errors.append(PhonemeError(
            phoneme=ph_data["phoneme"],
            score=ph_data["score"],
            word=ph_data["word"],
            position=ph_data["position"]
        ))
    
    # Reconstruct word errors
    for word_data in data.get("current_word_errors", []):
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
        summary.current_word_errors.append(word_error)
    
    # Reconstruct prosody issues
    for pros_data in data.get("current_prosody_issues", []):
        summary.current_prosody_issues.append(ProsodyIssue(
            issue_type=ProsodyErrorType(pros_data["issue_type"]),
            word=pros_data["word"],
            confidence=pros_data["confidence"],
            break_length_ms=pros_data.get("break_length_ms", 0),
            description=pros_data.get("description", "")
        ))
    
    return summary
