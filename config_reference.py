"""
Quick reference for FeedbackConfig parameters.
Use this as a reference when initializing the CAPT pipeline.
"""

from capt_config import FeedbackConfig

# ============================================================
# CORRECT WAY TO INITIALIZE FeedbackConfig
# ============================================================

# Option 1: Use default values (recommended for quick start)
config_default = FeedbackConfig()

print("✅ Default Configuration:")
print(f"  - Fair threshold: {config_default.fair_threshold}")
print(f"  - Phoneme error threshold: {config_default.phoneme_error_threshold}")
print(f"  - Word error threshold: {config_default.word_error_threshold}")
print(f"  - Prosody error threshold: {config_default.prosody_error_threshold}")
print(f"  - Max attempt errors: {config_default.max_attempt_errors}")
print()

# Option 2: Customize specific thresholds
config_custom = FeedbackConfig(
    fair_threshold=60.0,  # Scores >= 60 are "fair"
    good_threshold=75.0,  # Scores >= 75 are "good"
    excellent_threshold=90.0,  # Scores >= 90 are "excellent"
    
    phoneme_error_threshold=70.0,  # Phonemes < 70 are errors
    phoneme_critical_threshold=40.0,  # Phonemes < 40 are critical
    
    word_error_threshold=70.0,  # Words < 70 are problematic
    word_critical_threshold=50.0,  # Words < 50 need immediate attention
    
    prosody_error_threshold=65.0,  # Prosody < 65 indicates issues
    
    fluency_min_acceptable=70.0,  # Minimum acceptable fluency
    completeness_min_acceptable=80.0,  # Minimum acceptable completeness
    
    max_attempt_errors=5,  # Report max 5 errors per attempt
    max_guidance_phonemes=5,  # Track max 5 challenging phonemes
    max_guidance_words=3,  # Track max 3 challenging words
    
    feedback_temperature=0.7,  # LLM temperature for feedback
    feedback_language="ja"  # Feedback language (ja/en)
)

print("✅ Custom Configuration:")
print(f"  - Fair threshold: {config_custom.fair_threshold}")
print(f"  - Good threshold: {config_custom.good_threshold}")
print(f"  - Excellent threshold: {config_custom.excellent_threshold}")
print(f"  - Max attempt errors: {config_custom.max_attempt_errors}")
print()

# ============================================================
# AVAILABLE PARAMETERS (Complete List)
# ============================================================

print("📋 All Available FeedbackConfig Parameters:")
print("""
Score Thresholds (0-100 scale):
  - excellent_threshold: float = 90.0
  - good_threshold: float = 75.0
  - fair_threshold: float = 60.0
  - poor_threshold: float = 40.0

Phoneme-Level:
  - phoneme_error_threshold: float = 70.0
  - phoneme_critical_threshold: float = 40.0

Word-Level:
  - word_error_threshold: float = 70.0
  - word_critical_threshold: float = 50.0

Prosody:
  - prosody_error_threshold: float = 65.0
  - break_confidence_threshold: float = 0.7
  - monotone_confidence_threshold: float = 0.5

Fluency & Completeness:
  - fluency_min_acceptable: float = 70.0
  - completeness_min_acceptable: float = 80.0

Guidance Card Limits:
  - max_guidance_phonemes: int = 5
  - max_guidance_words: int = 3
  - guidance_prosody_issues: int = 3

Attempt Summary Limits:
  - max_attempt_errors: int = 5
  - max_attempt_improvements: int = 3

Feedback Generation:
  - feedback_max_tokens: int = 150
  - feedback_temperature: float = 0.7
  - feedback_language: str = "ja"
""")

# ============================================================
# HELPER METHODS
# ============================================================

print("🔧 Helper Methods:")
score = 75
print(f"  Score {score} is classified as: {config_custom.classify_score(score)}")
print(f"  Is phoneme error (score={score})? {config_custom.is_phoneme_error(score)}")
print(f"  Is word error (score={score})? {config_custom.is_word_error(score)}")
print(f"  Is prosody issue (score={score})? {config_custom.is_prosody_issue(score)}")
print()

# ============================================================
# INTEGRATION EXAMPLE
# ============================================================

print("💡 Integration Example:")
print("""
# In your initialize.py or phonoecho.py:

from capt_integration import CAPTFeedbackPipeline
from capt_config import FeedbackConfig

# Option 1: Use defaults (quickest)
if "capt_pipeline" not in st.session_state:
    st.session_state.capt_pipeline = CAPTFeedbackPipeline()

# Option 2: Customize thresholds
if "capt_pipeline" not in st.session_state:
    config = FeedbackConfig(
        fair_threshold=60.0,
        phoneme_error_threshold=70.0,
        word_error_threshold=70.0,
        prosody_error_threshold=65.0,
        max_attempt_errors=5
    )
    st.session_state.capt_pipeline = CAPTFeedbackPipeline(config)
""")
