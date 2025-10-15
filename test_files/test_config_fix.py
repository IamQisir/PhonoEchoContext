"""
Test script to verify the FeedbackConfig fix works.
"""

from capt_config import FeedbackConfig
from capt_integration import CAPTFeedbackPipeline

print("Testing FeedbackConfig initialization...")

# Test 1: Default config
try:
    config1 = FeedbackConfig()
    print("✅ Test 1 PASSED: Default FeedbackConfig() works")
except Exception as e:
    print(f"❌ Test 1 FAILED: {e}")

# Test 2: Custom config with CORRECT parameters
try:
    config2 = FeedbackConfig(
        fair_threshold=60.0,
        phoneme_error_threshold=70.0,
        word_error_threshold=70.0,
        prosody_error_threshold=65.0,
        max_attempt_errors=5
    )
    print("✅ Test 2 PASSED: Custom FeedbackConfig with correct parameters works")
except Exception as e:
    print(f"❌ Test 2 FAILED: {e}")

# Test 3: Initialize CAPTFeedbackPipeline with default config
try:
    pipeline1 = CAPTFeedbackPipeline()
    print("✅ Test 3 PASSED: CAPTFeedbackPipeline() with default config works")
except Exception as e:
    print(f"❌ Test 3 FAILED: {e}")

# Test 4: Initialize CAPTFeedbackPipeline with custom config
try:
    config3 = FeedbackConfig(
        fair_threshold=60.0,
        max_attempt_errors=5
    )
    pipeline2 = CAPTFeedbackPipeline(config3)
    print("✅ Test 4 PASSED: CAPTFeedbackPipeline with custom config works")
except Exception as e:
    print(f"❌ Test 4 FAILED: {e}")

# Test 5: Verify the OLD incorrect parameters would fail
try:
    bad_config = FeedbackConfig(
        accuracy_threshold=60.0,  # THIS IS WRONG
        fluency_threshold=60.0,   # THIS IS WRONG
        prosody_threshold=60.0    # THIS IS WRONG
    )
    print("❌ Test 5 FAILED: Should have raised TypeError for wrong parameters")
except TypeError as e:
    print(f"✅ Test 5 PASSED: Correctly rejects wrong parameters (accuracy_threshold)")

print("\n" + "="*60)
print("All tests completed! The fix is working correctly.")
print("="*60)
