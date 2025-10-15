# 📚 CAPT Pipeline Documentation

Complete documentation for the Computer-Assisted Pronunciation Training (CAPT) feedback pipeline.

---

## 🚀 Quick Start

**Start here:** [QUICKSTART.md](./QUICKSTART.md)

Quick guide to fix the integration and get started with the CAPT pipeline.

---

## 📖 Documentation Files

### Core Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** ⭐ **START HERE**
  - How to initialize CAPTFeedbackPipeline correctly
  - Common usage patterns
  - Complete examples

- **[FINAL_FIX.md](./FINAL_FIX.md)** 🔧 **LATEST FIX**
  - Fixed AI feedback generation error
  - Correct structured_feedback dictionary keys
  - Fallback for when AI fails

- **[DATA_MODELS_REFERENCE.md](./DATA_MODELS_REFERENCE.md)** 🔑 **ESSENTIAL**
  - GuidanceCard and AttemptSummary attributes
  - Correct attribute names (avoid common mistakes!)
  - Code examples for accessing data

- **[README_CAPT_PIPELINE.md](./README_CAPT_PIPELINE.md)**
  - Detailed API documentation
  - Module descriptions
  - Architecture overview

- **[CAPT_INTEGRATION_GUIDE.md](./CAPT_INTEGRATION_GUIDE.md)**
  - Step-by-step integration into PhonoEcho
  - Multiple UI display options
  - Best practices

### Reference

- **[FIX_SUMMARY.md](./FIX_SUMMARY.md)**
  - Complete FeedbackConfig parameter reference
  - All available configuration options
  - Helper methods documentation

- **[CAPT_PROJECT_SUMMARY.md](./CAPT_PROJECT_SUMMARY.md)**
  - Project overview
  - Design decisions
  - Token optimization strategy

---

## 🎯 Common Tasks

### Initialize the Pipeline
```python
from capt_integration import CAPTFeedbackPipeline

pipeline = CAPTFeedbackPipeline(
    user_id=1,
    lesson_id=1
)
```
See: [QUICKSTART.md](./QUICKSTART.md#correct-usage)

### Process a Pronunciation Attempt
```python
structured_feedback = pipeline.get_structured_feedback(
    azure_result,
    attempt_number=1
)
```
See: [QUICKSTART.md](./QUICKSTART.md#using-the-pipeline)

### Integrate into Streamlit
```python
if "capt_pipeline" not in st.session_state:
    st.session_state.capt_pipeline = CAPTFeedbackPipeline(
        user_id=user,
        lesson_id=lesson
    )
```
See: [CAPT_INTEGRATION_GUIDE.md](./CAPT_INTEGRATION_GUIDE.md#step-by-step-integration)

### Configure Thresholds
```python
from capt_config import FeedbackConfig

config = FeedbackConfig(
    fair_threshold=60.0,
    phoneme_error_threshold=70.0,
    word_error_threshold=70.0,
    max_attempt_errors=5
)
```
See: [FIX_SUMMARY.md](./FIX_SUMMARY.md#complete-parameter-reference)

---

## 🏗️ Architecture

The CAPT pipeline consists of 5 core modules:

1. **capt_config.py** - Configuration and thresholds
2. **capt_models.py** - Data structures (dataclasses)
3. **capt_guidance_card.py** - Parse first attempt (stable reference)
4. **capt_attempt_summary.py** - Parse subsequent attempts (lightweight)
5. **capt_feedback_generator.py** - Generate structured feedback
6. **capt_integration.py** - High-level API wrapper

**Token Optimization:**
- First attempt: Full JSON (~8000 tokens) → Guidance Card
- Subsequent: Incremental summaries (~800 tokens each)
- **90% token reduction** for repeated assessments

See: [CAPT_PROJECT_SUMMARY.md](./CAPT_PROJECT_SUMMARY.md)

---

## 🧪 Examples

### Example 1: Basic Usage
```python
from capt_integration import CAPTFeedbackPipeline
import json

# Load Azure assessment result
with open("assessment.json") as f:
    azure_result = json.load(f)

# Initialize pipeline
pipeline = CAPTFeedbackPipeline(user_id=1, lesson_id=1)

# Process first attempt
feedback = pipeline.get_structured_feedback(azure_result, attempt_number=1)
print(feedback["summary"]["overall_assessment"])
```

### Example 2: With LLM
```python
def my_llm(prompt):
    # Your LLM call here
    return openai.chat.completions.create(...)

feedback_text = pipeline.process_attempt(
    azure_result,
    attempt_number=1,
    llm_function=my_llm,
    use_llm=True
)
```

### Example 3: Streamlit Integration
See: [phonoecho_integration_example.py](../phonoecho_integration_example.py)

---

## 🔍 Module Reference

### CAPTFeedbackPipeline

Main high-level interface.

**Methods:**
- `__init__(user_id, lesson_id, config=None, storage_dir=None)`
- `get_structured_feedback(azure_result, attempt_number)` → dict
- `process_attempt(azure_result, attempt_number, llm_function=None, use_llm=False)` → str
- `get_progress_summary()` → dict
- `reset_lesson()`

See: [README_CAPT_PIPELINE.md](./README_CAPT_PIPELINE.md)

### FeedbackConfig

Configuration object with all thresholds.

**Key Parameters:**
- Score thresholds: `fair_threshold`, `good_threshold`, `excellent_threshold`
- Error detection: `phoneme_error_threshold`, `word_error_threshold`, `prosody_error_threshold`
- Limits: `max_attempt_errors`, `max_guidance_phonemes`, `max_guidance_words`
- AI: `feedback_temperature`, `feedback_language`

See: [FIX_SUMMARY.md](./FIX_SUMMARY.md#complete-parameter-reference)

---

## 🐛 Troubleshooting

### TypeError: missing 1 required positional argument: 'lesson_id'

**Problem:** Not providing required arguments to CAPTFeedbackPipeline

**Solution:**
```python
# ❌ Wrong
pipeline = CAPTFeedbackPipeline(config)

# ✅ Correct
pipeline = CAPTFeedbackPipeline(user_id=1, lesson_id=1, config=config)
```

### TypeError: got an unexpected keyword argument 'accuracy_threshold'

**Problem:** Using wrong parameter names for FeedbackConfig

**Solution:** See [FIX_SUMMARY.md](./FIX_SUMMARY.md#common-mistakes-to-avoid)

### Guidance card not found

**Problem:** Pipeline creates files in `asset/{user_id}/history/`

**Solution:** Ensure directory exists or specify custom `storage_dir`

---

## 📊 Token Usage

| Scenario | Tokens | Notes |
|----------|--------|-------|
| First attempt (full JSON) | ~8,000 | Creates guidance card |
| Subsequent attempts (summary) | ~800 | 90% reduction |
| With guidance card reference | ~1,000 | Includes context |

See: [CAPT_PROJECT_SUMMARY.md](./CAPT_PROJECT_SUMMARY.md#token-optimization)

---

## 🎨 UI Display Options

The integration guide provides **4 different UI approaches**:

1. **Simple Display** - Clean, minimal feedback
2. **Tabbed Interface** - Multiple views (overview/issues/tips)
3. **Progress Comparison** - Show improvement metrics
4. **Interactive Cards** - Expandable error details

See: [CAPT_INTEGRATION_GUIDE.md](./CAPT_INTEGRATION_GUIDE.md#implementation-ideas)

---

## ✅ Testing

All modules have comprehensive unit tests:

```bash
# Run all CAPT tests
python run_all_tests.py

# Run specific test file
pytest test_capt_guidance_card.py -v
pytest test_capt_attempt_summary.py -v
pytest test_capt_feedback_generator.py -v
```

**Test Coverage:** 60+ test cases across all modules

---

## 📝 Contributing

When adding new features:

1. Update relevant dataclasses in `capt_models.py`
2. Add configuration parameters to `capt_config.py`
3. Write unit tests
4. Update documentation in this folder

---

## 📧 Support

Questions? Check these files in order:

1. [QUICKSTART.md](./QUICKSTART.md) - Quick answers
2. [FIX_SUMMARY.md](./FIX_SUMMARY.md) - Common issues
3. [CAPT_INTEGRATION_GUIDE.md](./CAPT_INTEGRATION_GUIDE.md) - Integration help
4. [README_CAPT_PIPELINE.md](./README_CAPT_PIPELINE.md) - API details

---

## 🎉 Quick Links

- 🚀 [Get Started](./QUICKSTART.md)
- 📖 [Full API Docs](./README_CAPT_PIPELINE.md)
- 🔧 [Integration Guide](./CAPT_INTEGRATION_GUIDE.md)
- 📊 [Configuration Reference](./FIX_SUMMARY.md)
- 💡 [Project Overview](./CAPT_PROJECT_SUMMARY.md)

---

**Last Updated:** October 16, 2025  
**Version:** 1.0
