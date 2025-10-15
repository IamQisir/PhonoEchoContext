# CAPT Pipeline - Quick Reference Card

## 🚀 Instant Integration (3 Lines of Code!)

```python
from capt_integration import CAPTFeedbackPipeline

pipeline = CAPTFeedbackPipeline(user_id=1, lesson_id=1)
feedback = pipeline.process_attempt(azure_result, attempt_number=1)
```

---

## 📋 Common Tasks

### Initialize Pipeline

```python
from capt_integration import CAPTFeedbackPipeline

pipeline = CAPTFeedbackPipeline(
    user_id=1, 
    lesson_id=1,
    config=custom_config  # Optional
)
```

### Process Attempt

```python
# Returns formatted feedback string
feedback = pipeline.process_attempt(
    azure_result,
    attempt_number=2
)
```

### Get Structured Data

```python
# Returns dict with detailed components
structured = pipeline.get_structured_feedback(
    azure_result,
    attempt_number=2
)
# Access: structured["overall_score"], structured["main_issues"], etc.
```

### Use with LLM

```python
def my_llm(prompt: str) -> str:
    return openai_client.chat.completions.create(...)

feedback = pipeline.process_attempt(
    azure_result,
    attempt_number=2,
    llm_function=my_llm,
    use_llm=True
)
```

### Reset Lesson

```python
pipeline.reset_lesson()  # Clear guidance card & history
```

### Check Progress

```python
progress = pipeline.get_progress_summary()
print(progress["improvement"])  # Points improved
```

---

## 🔧 Streamlit Integration

### One-Time Setup

```python
# In phonoecho.py
from capt_integration import init_capt_pipeline_for_streamlit

# In your initialization section
pipeline = init_capt_pipeline_for_streamlit(
    st.session_state,
    user=user,
    lesson=lesson
)
```

### In Form Submit Handler

```python
if submitted:
    # Your existing Azure call
    pronunciation_result = get_pronunciation_assessment(...)
    
    # Generate feedback (one line!)
    feedback = pipeline.process_attempt(
        pronunciation_result,
        attempt_number=st.session_state.practice_times
    )
    
    # Display
    st.markdown(feedback)
```

---

## ⚙️ Configuration Quick Reference

```python
from capt_config import FeedbackConfig

config = FeedbackConfig(
    # Score thresholds (0-100)
    excellent_threshold=90.0,
    good_threshold=75.0,
    fair_threshold=60.0,
    
    # Error detection
    phoneme_error_threshold=70.0,
    word_error_threshold=70.0,
    
    # Content limits
    max_guidance_phonemes=5,
    max_guidance_words=3,
    max_attempt_errors=5,
    
    # Feedback
    feedback_language="ja",  # or "en"
    feedback_max_tokens=150,
)
```

---

## 📊 Output Format

### Structured Feedback Dictionary

```python
{
    "overall_score": 85.0,
    "score_category": "good",
    "score_label": "良好 (Good)",
    "main_issues": ["'hello'の発音 (65点)", ...],
    "improvements": ["'world'が改善されました", ...],
    "recommendations": ["/h/の発音を練習しましょう", ...],
    "encouragement": "良い発音です！",
    "attempt_number": 2
}
```

### Formatted Display Text

```
📊 総合スコア: 85点
   評価: 良好 (Good)

🎯 主な課題:
   • 'hello'の発音 (65点)

✅ 改善点:
   • 'world'が改善されました

💡 アドバイス:
   • /h/の発音を練習しましょう

💪 良い発音です！
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run example
python example_capt_usage.py

# Run integration helper
python capt_integration.py
```

---

## 📁 File Structure

```
project/
├── capt_config.py              # Configuration
├── capt_models.py              # Data structures
├── capt_guidance_card.py       # Guidance parser
├── capt_attempt_summary.py     # Attempt parser
├── capt_feedback_generator.py  # Feedback generator
├── capt_integration.py         # 🌟 High-level API (USE THIS!)
│
├── test_capt_guidance_card.py
├── test_capt_attempt_summary.py
├── test_capt_feedback_generator.py
│
├── example_capt_usage.py       # Runnable example
├── README_CAPT_PIPELINE.md     # Full documentation
└── CAPT_PROJECT_SUMMARY.md     # Project overview
```

---

## 🎯 Key Concepts

### Guidance Card
- Created from **first attempt** only
- Stores challenging phonemes, words, prosody
- **Reused** for all subsequent attempts
- ~500 tokens

### Attempt Summary
- Created for **each attempt**
- Stores only **deltas** (errors + improvements)
- Compares with previous attempt
- ~300 tokens

### Token Savings
- Full parse: ~8,000 tokens/attempt
- CAPT pipeline: ~800 tokens/attempt
- **Savings: 90%**

---

## 💡 Tips

### DO ✅
- Create guidance card once per lesson
- Save guidance card to disk (auto-handled by pipeline)
- Use structured feedback for instant results
- Reserve LLM for premium features

### DON'T ❌
- Recreate guidance card every attempt
- Call LLM without error handling
- Ignore token savings (use pipeline!)

---

## 🔗 Related Files

- **Full docs:** `README_CAPT_PIPELINE.md`
- **Examples:** `example_capt_usage.py`
- **Tests:** `test_capt_*.py`

---

## 🆘 Troubleshooting

### "No NBest results"
→ Check Azure API call succeeded

### "No challenging elements"
→ Lower thresholds in FeedbackConfig

### "Feedback in wrong language"
→ Set `feedback_language="ja"` in config

### "Tests failing"
→ Install pytest: `pip install pytest`

---

## 📞 Quick Help

```python
# Check if guidance exists
if pipeline.guidance_card is None:
    print("No guidance card yet")

# Get target text
print(pipeline.guidance_card.target_text)

# Get last score
if pipeline.last_attempt:
    print(pipeline.last_attempt.overall_score)

# View progress
progress = pipeline.get_progress_summary()
print(progress)
```

---

**🌟 Start Here: `capt_integration.py`**

**📖 Need Details: `README_CAPT_PIPELINE.md`**

**🚀 See Example: `python example_capt_usage.py`**
