"""
Example usage of the CAPT Feedback Pipeline.

This script demonstrates:
1. Creating a guidance card from the first attempt
2. Analyzing subsequent attempts with incremental summaries
3. Generating feedback (both structured and LLM-based)

Run this script to see the complete pipeline in action.
"""

import json
from pathlib import Path

from capt_guidance_card import parse_guidance_card, save_guidance_card
from capt_attempt_summary import parse_attempt_summary, save_attempt_summary
from capt_feedback_generator import (
    generate_feedback,
    generate_structured_feedback,
    format_feedback_for_display,
)
from capt_config import FeedbackConfig


def mock_llm_function(prompt: str) -> str:
    """
    Mock LLM function for demonstration.
    In production, replace with actual OpenAI/Azure OpenAI call.
    """
    return (
        "素晴らしい進歩です！/h/の音が少し改善されました。"
        "次は'hello'全体の流暢さに注目しましょう。"
        "もう少しゆっくり、はっきりと発音してみてください。"
    )


def run_example():
    """Run complete example with test data."""
    
    print("=" * 70)
    print("CAPT Feedback Pipeline - Example Run")
    print("=" * 70)
    print()
    
    # Load test data (using existing test1.json)
    test_file = Path("asset/1/history/test1.json")
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        print("Please ensure test1.json exists in asset/1/history/")
        return
    
    with open(test_file, 'r', encoding='utf-8') as f:
        azure_result = json.load(f)
    
    print("✓ Loaded Azure Speech Assessment result")
    print(f"  Target: {azure_result.get('DisplayText', 'N/A')}")
    print()
    
    # ===== Step 1: Create Guidance Card =====
    print("━" * 70)
    print("Step 1: Creating Guidance Card (from first attempt)")
    print("━" * 70)
    
    config = FeedbackConfig(
        phoneme_error_threshold=70.0,
        word_error_threshold=70.0,
        max_guidance_phonemes=5,
        max_guidance_words=3,
    )
    
    guidance = parse_guidance_card(azure_result, config=config)
    
    print()
    print("📋 Guidance Card Summary:")
    print(guidance.get_summary())
    print()
    
    # Show detailed challenging elements
    print("🎯 Challenging Phonemes:")
    for i, phoneme in enumerate(guidance.challenging_phonemes[:3], 1):
        print(f"  {i}. /{phoneme.phoneme}/ in '{phoneme.word}' - Score: {phoneme.score:.0f}")
    print()
    
    print("📝 Challenging Words:")
    for i, word in enumerate(guidance.challenging_words[:3], 1):
        score_str = f"{word.score:.0f}" if word.score else "Omitted"
        print(f"  {i}. '{word.word}' - Score: {score_str} ({word.error_type.value})")
    print()
    
    # Save guidance card
    guidance_file = Path("asset/1/history/example_guidance.json")
    save_guidance_card(guidance, str(guidance_file))
    print(f"✓ Saved guidance card to {guidance_file}")
    print()
    
    # ===== Step 2: Parse Attempt (simulating 2nd attempt) =====
    print("━" * 70)
    print("Step 2: Analyzing Attempt #2 (incremental)")
    print("━" * 70)
    print()
    
    # For demo, use same data but treat as 2nd attempt
    attempt = parse_attempt_summary(
        azure_result,
        attempt_number=2,
        guidance_card=guidance,
        config=config
    )
    
    print("📊 Attempt Summary:")
    print(attempt.get_summary())
    print()
    
    # Save attempt summary
    attempt_file = Path("asset/1/history/example_attempt2.json")
    save_attempt_summary(attempt, str(attempt_file))
    print(f"✓ Saved attempt summary to {attempt_file}")
    print()
    
    # ===== Step 3: Generate Structured Feedback =====
    print("━" * 70)
    print("Step 3: Generating Structured Feedback (no LLM)")
    print("━" * 70)
    print()
    
    structured = generate_structured_feedback(guidance, attempt, config=config)
    
    print("📈 Structured Feedback:")
    display = format_feedback_for_display(structured)
    print(display)
    print()
    
    # ===== Step 4: Generate LLM-Based Feedback =====
    print("━" * 70)
    print("Step 4: Generating LLM-Based Feedback (mocked)")
    print("━" * 70)
    print()
    
    # Show the prompt that would be sent to LLM
    prompt = generate_feedback(guidance, attempt, llm_function=None, config=config)
    print("📝 LLM Prompt Preview (truncated):")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print()
    
    # Generate feedback with mock LLM
    feedback = generate_feedback(
        guidance, 
        attempt, 
        llm_function=mock_llm_function,
        config=config
    )
    
    print("💬 LLM-Generated Feedback:")
    print(feedback)
    print()
    
    # ===== Step 5: Token Comparison =====
    print("━" * 70)
    print("Step 5: Token Usage Comparison")
    print("━" * 70)
    print()
    
    # Estimate token counts (rough)
    full_json_str = json.dumps(azure_result)
    guidance_str = guidance.get_summary()
    attempt_str = attempt.get_summary()
    
    print(f"📊 Token Estimates:")
    print(f"  Full Azure JSON:     ~{len(full_json_str) // 4:,} tokens")
    print(f"  Guidance Card:       ~{len(guidance_str) // 4:,} tokens")
    print(f"  Attempt Summary:     ~{len(attempt_str) // 4:,} tokens")
    print(f"  Combined (G+A):      ~{(len(guidance_str) + len(attempt_str)) // 4:,} tokens")
    print()
    
    savings = (1 - (len(guidance_str) + len(attempt_str)) / len(full_json_str)) * 100
    print(f"  💰 Token savings:    ~{savings:.0f}%")
    print()
    
    # ===== Summary =====
    print("=" * 70)
    print("✅ Example Complete!")
    print("=" * 70)
    print()
    print("Key Takeaways:")
    print("  1. Guidance card captures stable reference (~500 tokens)")
    print("  2. Attempt summary captures only deltas (~300 tokens)")
    print("  3. Combined prompt is ~90% smaller than full JSON")
    print("  4. Feedback is concise, consistent, and actionable")
    print()
    print("Next Steps:")
    print("  - Integrate into your Streamlit app (see README)")
    print("  - Connect real LLM (OpenAI, Azure, etc.)")
    print("  - Customize thresholds in FeedbackConfig")
    print("  - Run tests: pytest test_capt_*.py")
    print()


def run_multi_attempt_example():
    """
    Example showing multiple attempts with progress tracking.
    """
    print("\n" + "=" * 70)
    print("BONUS: Multi-Attempt Progress Tracking")
    print("=" * 70)
    print()
    
    test_file = Path("asset/1/history/test1.json")
    if not test_file.exists():
        return
    
    with open(test_file, 'r', encoding='utf-8') as f:
        azure_result = json.load(f)
    
    # Create guidance from first attempt
    guidance = parse_guidance_card(azure_result)
    
    # Simulate 3 attempts with slight score improvements
    attempts = []
    base_score = azure_result["NBest"][0]["PronunciationAssessment"]["PronScore"]
    
    print("📈 Progress Tracking Across Attempts:\n")
    
    for i in range(1, 4):
        # For demo, modify score slightly
        modified_result = json.loads(json.dumps(azure_result))
        # Simulate improvement
        score_boost = (i - 1) * 5
        modified_result["NBest"][0]["PronunciationAssessment"]["PronScore"] = min(100, base_score + score_boost)
        modified_result["NBest"][0]["PronunciationAssessment"]["AccuracyScore"] = min(100, 
            modified_result["NBest"][0]["PronunciationAssessment"]["AccuracyScore"] + score_boost)
        
        previous = attempts[-1] if attempts else None
        
        attempt = parse_attempt_summary(
            modified_result,
            attempt_number=i,
            guidance_card=guidance,
            previous_attempt=previous
        )
        
        attempts.append(attempt)
        
        # Show progress
        print(f"Attempt #{i}:")
        print(f"  Overall Score: {attempt.overall_score:.1f}")
        print(f"  Accuracy: {attempt.accuracy_score:.1f}")
        print(f"  Improvements: {len(attempt.improved_words)} words")
        print(f"  Regressions: {len(attempt.regressed_words)} words")
        print()
    
    # Summary
    improvement = attempts[-1].overall_score - attempts[0].overall_score
    print(f"🎉 Total Improvement: {improvement:.1f} points")
    print()


if __name__ == "__main__":
    try:
        run_example()
        run_multi_attempt_example()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
