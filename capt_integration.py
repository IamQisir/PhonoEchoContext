"""
CAPT Pipeline Integration Helper

This module provides a simple, high-level interface for integrating
the CAPT feedback pipeline into existing applications.

Usage:
    from capt_integration import CAPTFeedbackPipeline
    
    # Initialize
    pipeline = CAPTFeedbackPipeline(user_id=1, lesson_id=1)
    
    # Process first attempt
    feedback = pipeline.process_attempt(azure_result, attempt_number=1)
    
    # Process subsequent attempts
    feedback = pipeline.process_attempt(azure_result, attempt_number=2)
"""

from typing import Optional, Callable, Dict, Any
from pathlib import Path
import json

from capt_config import FeedbackConfig, DEFAULT_CONFIG
from capt_models import GuidanceCard, AttemptSummary
from capt_guidance_card import (
    parse_guidance_card,
    save_guidance_card,
    load_guidance_card,
)
from capt_attempt_summary import (
    parse_attempt_summary,
    save_attempt_summary,
)
from capt_feedback_generator import (
    generate_feedback,
    generate_structured_feedback,
    format_feedback_for_display,
)


class CAPTFeedbackPipeline:
    """
    High-level interface for CAPT feedback generation.
    
    This class manages guidance cards and attempt summaries automatically,
    providing a simple interface for feedback generation.
    
    Attributes:
        user_id: User identifier
        lesson_id: Lesson identifier
        config: Feedback configuration
        guidance_card: Current guidance card (loaded or created)
        last_attempt: Last attempt summary (for comparison)
        storage_dir: Directory for storing guidance cards and summaries
    """
    
    def __init__(
        self,
        user_id: int,
        lesson_id: int,
        config: Optional[FeedbackConfig] = None,
        storage_dir: Optional[str] = None,
    ):
        """
        Initialize the CAPT feedback pipeline.
        
        Args:
            user_id: User identifier
            lesson_id: Lesson identifier
            config: Configuration object (uses DEFAULT_CONFIG if None)
            storage_dir: Directory to store guidance cards/summaries
                        (defaults to "asset/{user_id}/history/")
        """
        self.user_id = user_id
        self.lesson_id = lesson_id
        self.config = config or DEFAULT_CONFIG
        
        # Set up storage directory
        if storage_dir is None:
            self.storage_dir = Path(f"asset/{user_id}/history")
        else:
            self.storage_dir = Path(storage_dir)
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # State
        self.guidance_card: Optional[GuidanceCard] = None
        self.last_attempt: Optional[AttemptSummary] = None
        
        # Try to load existing guidance card
        self._load_existing_guidance()
    
    def _load_existing_guidance(self) -> None:
        """Try to load existing guidance card for this lesson."""
        guidance_file = self.storage_dir / f"lesson_{self.lesson_id}_guidance.json"
        
        if guidance_file.exists():
            try:
                self.guidance_card = load_guidance_card(str(guidance_file))
            except Exception as e:
                print(f"Warning: Failed to load guidance card: {e}")
                self.guidance_card = None
    
    def _save_guidance(self) -> None:
        """Save current guidance card to disk."""
        if self.guidance_card is None:
            return
        
        guidance_file = self.storage_dir / f"lesson_{self.lesson_id}_guidance.json"
        save_guidance_card(self.guidance_card, str(guidance_file))
    
    def _save_attempt(self, attempt: AttemptSummary) -> None:
        """Save attempt summary to disk."""
        attempt_file = self.storage_dir / f"lesson_{self.lesson_id}_attempt_{attempt.attempt_number}.json"
        save_attempt_summary(attempt, str(attempt_file))
    
    def process_attempt(
        self,
        azure_result: Dict[str, Any],
        attempt_number: int,
        llm_function: Optional[Callable[[str], str]] = None,
        use_llm: bool = False,
    ) -> str:
        """
        Process a pronunciation attempt and generate feedback.
        
        This is the main entry point for the pipeline. It automatically:
        - Creates guidance card on first attempt
        - Generates incremental summaries for subsequent attempts
        - Produces formatted feedback
        
        Args:
            azure_result: Azure Speech Assessment JSON dict
            attempt_number: Sequential attempt number (1, 2, 3, ...)
            llm_function: Optional LLM function for feedback generation
            use_llm: Whether to use LLM (requires llm_function)
            
        Returns:
            Formatted feedback string
            
        Example:
            >>> pipeline = CAPTFeedbackPipeline(user_id=1, lesson_id=1)
            >>> feedback = pipeline.process_attempt(azure_result, attempt_number=1)
            >>> print(feedback)
        """
        # First attempt: create guidance card
        if attempt_number == 1 or self.guidance_card is None:
            self.guidance_card = parse_guidance_card(azure_result, self.config)
            self._save_guidance()
            
            # For first attempt, also create summary for future comparison
            self.last_attempt = parse_attempt_summary(
                azure_result,
                attempt_number=1,
                guidance_card=self.guidance_card,
                config=self.config
            )
            self._save_attempt(self.last_attempt)
            
            # Generate feedback for first attempt
            if use_llm and llm_function:
                return generate_feedback(
                    self.guidance_card,
                    self.last_attempt,
                    llm_function=llm_function,
                    config=self.config
                )
            else:
                structured = generate_structured_feedback(
                    self.guidance_card,
                    self.last_attempt,
                    config=self.config
                )
                return format_feedback_for_display(structured)
        
        # Subsequent attempts: generate incremental summary
        current_attempt = parse_attempt_summary(
            azure_result,
            attempt_number=attempt_number,
            guidance_card=self.guidance_card,
            previous_attempt=self.last_attempt,
            config=self.config
        )
        self._save_attempt(current_attempt)
        
        # Generate feedback
        if use_llm and llm_function:
            feedback = generate_feedback(
                self.guidance_card,
                current_attempt,
                llm_function=llm_function,
                config=self.config
            )
        else:
            structured = generate_structured_feedback(
                self.guidance_card,
                current_attempt,
                config=self.config
            )
            feedback = format_feedback_for_display(structured)
        
        # Update last attempt for next comparison
        self.last_attempt = current_attempt
        
        return feedback
    
    def get_structured_feedback(
        self,
        azure_result: Dict[str, Any],
        attempt_number: int,
    ) -> Dict[str, Any]:
        """
        Get structured feedback data (without formatting).
        
        Useful for custom UI display or further processing.
        
        Args:
            azure_result: Azure Speech Assessment JSON dict
            attempt_number: Sequential attempt number
            
        Returns:
            Dictionary with structured feedback components
        """
        # Create/update guidance if needed
        if attempt_number == 1 or self.guidance_card is None:
            self.guidance_card = parse_guidance_card(azure_result, self.config)
            self._save_guidance()
        
        # Parse attempt
        current_attempt = parse_attempt_summary(
            azure_result,
            attempt_number=attempt_number,
            guidance_card=self.guidance_card,
            previous_attempt=self.last_attempt,
            config=self.config
        )
        self._save_attempt(current_attempt)
        self.last_attempt = current_attempt
        
        # Generate structured feedback
        return generate_structured_feedback(
            self.guidance_card,
            current_attempt,
            config=self.config
        )
    
    def reset_lesson(self) -> None:
        """
        Reset guidance card and attempt history for current lesson.
        
        Call this when starting a new lesson or resetting practice.
        """
        self.guidance_card = None
        self.last_attempt = None
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get summary of learning progress.
        
        Returns:
            Dictionary with progress metrics
        """
        if self.guidance_card is None:
            return {"status": "no_data"}
        
        summary = {
            "lesson_id": self.lesson_id,
            "target_text": self.guidance_card.target_text,
            "initial_score": self.guidance_card.reference_overall,
        }
        
        if self.last_attempt:
            summary.update({
                "current_score": self.last_attempt.overall_score,
                "attempt_number": self.last_attempt.attempt_number,
                "improvement": self.last_attempt.overall_score - self.guidance_card.reference_overall,
                "improved_words": len(self.last_attempt.improved_words),
                "current_errors": len(self.last_attempt.current_word_errors),
            })
        
        return summary


# === Streamlit Integration Helper ===

def init_capt_pipeline_for_streamlit(
    session_state,
    user: int,
    lesson: int,
    config: Optional[FeedbackConfig] = None
) -> CAPTFeedbackPipeline:
    """
    Initialize CAPT pipeline in Streamlit session state.
    
    Usage in Streamlit:
        from capt_integration import init_capt_pipeline_for_streamlit
        
        pipeline = init_capt_pipeline_for_streamlit(
            st.session_state,
            user=user,
            lesson=lesson
        )
    
    Args:
        session_state: Streamlit session state object
        user: User ID
        lesson: Lesson ID
        config: Optional configuration
        
    Returns:
        CAPTFeedbackPipeline instance
    """
    key = f"capt_pipeline_{user}_{lesson}"
    
    if key not in session_state:
        session_state[key] = CAPTFeedbackPipeline(
            user_id=user,
            lesson_id=lesson,
            config=config
        )
    
    return session_state[key]


# === Example Usage ===

def example_usage():
    """Example of using the pipeline."""
    import json
    
    # Initialize pipeline
    pipeline = CAPTFeedbackPipeline(user_id=1, lesson_id=1)
    
    # Load test data
    with open("asset/1/history/test1.json", 'r', encoding='utf-8') as f:
        azure_result = json.load(f)
    
    # Process first attempt
    print("Processing Attempt #1...")
    feedback1 = pipeline.process_attempt(azure_result, attempt_number=1)
    print(feedback1)
    print()
    
    # Process second attempt (simulated)
    print("Processing Attempt #2...")
    feedback2 = pipeline.process_attempt(azure_result, attempt_number=2)
    print(feedback2)
    print()
    
    # Get progress summary
    print("Progress Summary:")
    progress = pipeline.get_progress_summary()
    for key, value in progress.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    example_usage()
