"""
Data models for CAPT (Computer-Assisted Pronunciation Training) feedback pipeline.

This module defines dataclasses for structured pronunciation assessment data:
- GuidanceCard: Stable reference created from first attempt
- AttemptSummary: Incremental changes from subsequent attempts
- PhonemeError, WordError, ProsodyIssue: Fine-grained error information
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class ErrorType(Enum):
    """Error classification from Azure Speech Assessment."""
    NONE = "None"
    MISPRONUNCIATION = "Mispronunciation"
    OMISSION = "Omission"
    INSERTION = "Insertion"


class ProsodyErrorType(Enum):
    """Prosody-specific error types."""
    UNEXPECTED_BREAK = "UnexpectedBreak"
    MISSING_BREAK = "MissingBreak"
    MONOTONE = "Monotone"


@dataclass
class PhonemeError:
    """
    Represents a single phoneme-level pronunciation error.
    
    Attributes:
        phoneme: IPA phoneme symbol (e.g., 'r', 'ɔ', 'ð')
        score: Accuracy score (0-100)
        word: Parent word containing this phoneme
        position: Position in word (0-indexed)
        expected_phoneme: Optional expected phoneme if substitution occurred
    """
    phoneme: str
    score: float
    word: str
    position: int
    expected_phoneme: Optional[str] = None
    
    def __repr__(self) -> str:
        return f"PhonemeError(/{self.phoneme}/ in '{self.word}', score={self.score:.0f})"


@dataclass
class WordError:
    """
    Represents a word-level pronunciation error.
    
    Attributes:
        word: The word text
        score: Word accuracy score (0-100), None if omitted
        error_type: Classification (Mispronunciation, Omission, etc.)
        phoneme_errors: List of problematic phonemes within this word
        offset_ms: Timing offset in milliseconds
        duration_ms: Word duration in milliseconds
    """
    word: str
    score: Optional[float]
    error_type: ErrorType
    phoneme_errors: List[PhonemeError] = field(default_factory=list)
    offset_ms: int = 0
    duration_ms: int = 0
    
    def __repr__(self) -> str:
        error_str = self.error_type.value
        score_str = f"{self.score:.0f}" if self.score is not None else "N/A"
        return f"WordError('{self.word}', {error_str}, score={score_str})"


@dataclass
class ProsodyIssue:
    """
    Represents a prosody-related issue (rhythm, intonation, pauses).
    
    Attributes:
        issue_type: Type of prosody error
        word: Word where issue occurs
        confidence: Confidence score (0-1) that this is an issue
        break_length_ms: Length of unexpected/missing pause in milliseconds
        description: Human-readable description
    """
    issue_type: ProsodyErrorType
    word: str
    confidence: float
    break_length_ms: int = 0
    description: str = ""
    
    def __repr__(self) -> str:
        return f"ProsodyIssue({self.issue_type.value} at '{self.word}', confidence={self.confidence:.2f})"


@dataclass
class GuidanceCard:
    """
    Stable guidance card generated from the first pronunciation attempt.
    
    This card captures the "target" pronunciation profile and serves as a reference
    for all subsequent attempts. It should remain constant across practice sessions.
    
    Attributes:
        target_text: The reference sentence/phrase
        target_display: Formatted display text (with punctuation)
        total_words: Number of words in target
        total_phonemes: Number of phonemes in target
        
        # Challenging elements (from first attempt analysis)
        challenging_phonemes: List of phonemes that were difficult initially
        challenging_words: List of words that were difficult initially
        prosody_patterns: Expected prosody patterns (pauses, intonation)
        
        # Reference scores (from first attempt)
        reference_accuracy: Initial accuracy score
        reference_fluency: Initial fluency score
        reference_prosody: Initial prosody score
        reference_completeness: Initial completeness score
        reference_overall: Initial overall pronunciation score
    """
    target_text: str
    target_display: str
    total_words: int
    total_phonemes: int
    
    # Challenging elements
    challenging_phonemes: List[PhonemeError] = field(default_factory=list)
    challenging_words: List[WordError] = field(default_factory=list)
    prosody_patterns: List[ProsodyIssue] = field(default_factory=list)
    
    # Reference scores
    reference_accuracy: float = 0.0
    reference_fluency: float = 0.0
    reference_prosody: float = 0.0
    reference_completeness: float = 0.0
    reference_overall: float = 0.0
    
    def get_summary(self) -> str:
        """Get a concise text summary of the guidance card."""
        return (
            f"Target: '{self.target_text}'\n"
            f"Words: {self.total_words}, Phonemes: {self.total_phonemes}\n"
            f"Challenging phonemes: {len(self.challenging_phonemes)}\n"
            f"Challenging words: {len(self.challenging_words)}\n"
            f"Prosody patterns: {len(self.prosody_patterns)}\n"
            f"Initial scores - Overall: {self.reference_overall:.0f}, "
            f"Accuracy: {self.reference_accuracy:.0f}, "
            f"Fluency: {self.reference_fluency:.0f}, "
            f"Prosody: {self.reference_prosody:.0f}"
        )


@dataclass
class AttemptSummary:
    """
    Summary of a single pronunciation attempt (incremental analysis).
    
    This captures only the changes/issues in the current attempt, designed to
    be lightweight compared to the full guidance card.
    
    Attributes:
        attempt_number: Sequential attempt number (1, 2, 3, ...)
        
        # Current scores
        accuracy_score: Current accuracy
        fluency_score: Current fluency
        prosody_score: Current prosody
        completeness_score: Current completeness
        overall_score: Current overall pronunciation score
        
        # Current errors (only significant ones)
        current_phoneme_errors: Phoneme errors in this attempt
        current_word_errors: Word errors in this attempt
        current_prosody_issues: Prosody issues in this attempt
        
        # Improvements (comparison with previous attempt or guidance card)
        improved_phonemes: List of phonemes that improved
        improved_words: List of words that improved
        
        # Regressions (comparison with previous attempt)
        regressed_phonemes: List of phonemes that got worse
        regressed_words: List of words that got worse
        
        # Metadata
        omitted_words: List of words that were omitted
        inserted_words: List of words that were incorrectly inserted
    """
    attempt_number: int
    
    # Current scores
    accuracy_score: float = 0.0
    fluency_score: float = 0.0
    prosody_score: float = 0.0
    completeness_score: float = 0.0
    overall_score: float = 0.0
    
    # Current errors
    current_phoneme_errors: List[PhonemeError] = field(default_factory=list)
    current_word_errors: List[WordError] = field(default_factory=list)
    current_prosody_issues: List[ProsodyIssue] = field(default_factory=list)
    
    # Improvements
    improved_phonemes: List[str] = field(default_factory=list)
    improved_words: List[str] = field(default_factory=list)
    
    # Regressions
    regressed_phonemes: List[str] = field(default_factory=list)
    regressed_words: List[str] = field(default_factory=list)
    
    # Metadata
    omitted_words: List[str] = field(default_factory=list)
    inserted_words: List[str] = field(default_factory=list)
    
    def get_summary(self) -> str:
        """Get a concise text summary of this attempt."""
        return (
            f"Attempt #{self.attempt_number}\n"
            f"Scores - Overall: {self.overall_score:.0f}, "
            f"Accuracy: {self.accuracy_score:.0f}, "
            f"Fluency: {self.fluency_score:.0f}, "
            f"Prosody: {self.prosody_score:.0f}\n"
            f"Errors - Phonemes: {len(self.current_phoneme_errors)}, "
            f"Words: {len(self.current_word_errors)}, "
            f"Prosody: {len(self.current_prosody_issues)}\n"
            f"Improvements: {len(self.improved_words)} words, {len(self.improved_phonemes)} phonemes\n"
            f"Omitted: {len(self.omitted_words)}, Inserted: {len(self.inserted_words)}"
        )


@dataclass
class FeedbackPrompt:
    """
    Structured prompt for LLM feedback generation.
    
    Combines guidance card context with attempt summary for efficient token usage.
    
    Attributes:
        target_text: The target sentence
        guidance_highlights: Key challenging elements from guidance card
        attempt_summary: Current attempt analysis
        language: Language code for feedback ('ja', 'en')
        max_tokens: Maximum tokens for LLM response
        temperature: LLM sampling temperature
    """
    target_text: str
    guidance_highlights: str
    attempt_summary: str
    language: str = "ja"
    max_tokens: int = 150
    temperature: float = 0.7
    
    def format_prompt(self) -> str:
        """
        Format the prompt for LLM input.
        
        Returns:
            Formatted prompt string optimized for concise feedback.
        """
        if self.language == "ja":
            return self._format_japanese_prompt()
        else:
            return self._format_english_prompt()
    
    def _format_japanese_prompt(self) -> str:
        """Format prompt in Japanese."""
        return f"""あなたは発音トレーニングの専門家です。以下の情報に基づいて、簡潔で具体的なフィードバックを提供してください。

【目標文】
{self.target_text}

【重点ポイント】
{self.guidance_highlights}

【今回の結果】
{self.attempt_summary}

**指示:**
- フィードバックは3-4文で簡潔に
- 具体的な改善点を1-2つに絞る
- ポジティブな言葉遣いで励ます
- 専門用語は最小限に"""
    
    def _format_english_prompt(self) -> str:
        """Format prompt in English."""
        return f"""You are a pronunciation training expert. Provide concise, specific feedback based on the following information.

【Target Sentence】
{self.target_text}

【Key Focus Areas】
{self.guidance_highlights}

【Current Attempt】
{self.attempt_summary}

**Instructions:**
- Keep feedback to 3-4 sentences
- Focus on 1-2 specific improvement areas
- Use encouraging, positive language
- Minimize technical jargon"""
