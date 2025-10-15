"""
Configuration module for CAPT (Computer-Assisted Pronunciation Training) feedback pipeline.

This module defines tunable thresholds and parameters for pronunciation assessment
analysis, error classification, and feedback generation.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class FeedbackConfig:
    """
    Configuration for CAPT feedback generation with tunable thresholds.
    
    All score thresholds are on a 0-100 scale as returned by Azure Speech API.
    """
    
    # === Accuracy Score Thresholds ===
    excellent_threshold: float = 90.0
    """Scores >= this are considered excellent (minimal issues)"""
    
    good_threshold: float = 75.0
    """Scores >= this are considered good (minor issues)"""
    
    fair_threshold: float = 60.0
    """Scores >= this are considered fair (noticeable issues)"""
    
    poor_threshold: float = 40.0
    """Scores < this are considered poor (significant issues)"""
    
    # === Phoneme-Level Thresholds ===
    phoneme_error_threshold: float = 70.0
    """Phoneme scores < this are flagged as errors"""
    
    phoneme_critical_threshold: float = 40.0
    """Phoneme scores < this are critical errors (prioritized in feedback)"""
    
    # === Word-Level Thresholds ===
    word_error_threshold: float = 70.0
    """Word scores < this are flagged as problematic"""
    
    word_critical_threshold: float = 50.0
    """Word scores < this need immediate attention"""
    
    # === Prosody Thresholds ===
    prosody_error_threshold: float = 65.0
    """Prosody scores < this indicate rhythm/intonation issues"""
    
    break_confidence_threshold: float = 0.7
    """Confidence >= this indicates pause issues (unexpected/missing breaks)"""
    
    monotone_confidence_threshold: float = 0.5
    """Confidence >= this indicates monotone speech"""
    
    # === Fluency & Completeness ===
    fluency_min_acceptable: float = 70.0
    """Minimum acceptable fluency score"""
    
    completeness_min_acceptable: float = 80.0
    """Minimum acceptable completeness score (too low = omissions)"""
    
    # === Guidance Card Configuration ===
    max_guidance_phonemes: int = 5
    """Maximum number of challenging phonemes to track in guidance card"""
    
    max_guidance_words: int = 3
    """Maximum number of challenging words to track in guidance card"""
    
    guidance_prosody_issues: int = 3
    """Maximum number of prosody patterns to track"""
    
    # === Attempt Summary Configuration ===
    max_attempt_errors: int = 5
    """Maximum number of errors to report per attempt"""
    
    max_attempt_improvements: int = 3
    """Maximum number of improvements to highlight"""
    
    # === Feedback Generation ===
    feedback_max_tokens: int = 150
    """Maximum tokens for LLM-generated feedback"""
    
    feedback_temperature: float = 0.7
    """LLM temperature for feedback generation (0.0-1.0)"""
    
    feedback_language: str = "ja"
    """Language code for feedback ('ja' for Japanese, 'en' for English)"""
    
    # === Error Type Classifications ===
    error_type_priorities: Dict[str, int] = field(default_factory=lambda: {
        "Mispronunciation": 3,  # Highest priority
        "Omission": 2,
        "Insertion": 1,
        "None": 0
    })
    """Priority weights for different error types (higher = more important)"""
    
    # === Score Category Labels ===
    score_labels: Dict[str, str] = field(default_factory=lambda: {
        "excellent": "優秀 (Excellent)",
        "good": "良好 (Good)", 
        "fair": "普通 (Fair)",
        "poor": "要改善 (Needs Improvement)"
    })
    """Human-readable labels for score categories"""
    
    def classify_score(self, score: float) -> str:
        """
        Classify a score into a category.
        
        Args:
            score: Score value (0-100)
            
        Returns:
            Category label: 'excellent', 'good', 'fair', or 'poor'
        """
        if score >= self.excellent_threshold:
            return "excellent"
        elif score >= self.good_threshold:
            return "good"
        elif score >= self.fair_threshold:
            return "fair"
        else:
            return "poor"
    
    def is_phoneme_error(self, score: float) -> bool:
        """Check if a phoneme score indicates an error."""
        return score < self.phoneme_error_threshold
    
    def is_critical_phoneme(self, score: float) -> bool:
        """Check if a phoneme score is critically low."""
        return score < self.phoneme_critical_threshold
    
    def is_word_error(self, score: float) -> bool:
        """Check if a word score indicates an error."""
        return score < self.word_error_threshold
    
    def is_prosody_issue(self, score: float) -> bool:
        """Check if a prosody score indicates an issue."""
        return score < self.prosody_error_threshold


# Default configuration instance
DEFAULT_CONFIG = FeedbackConfig()
