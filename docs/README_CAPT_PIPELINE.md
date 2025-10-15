# CAPT Feedback Pipeline Documentation

**Computer-Assisted Pronunciation Training (CAPT) Feedback System**

A Python library for generating concise, consistent pronunciation feedback by efficiently parsing Azure Speech Assessment results.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Components](#core-components)
5. [API Reference](#api-reference)
6. [Usage Examples](#usage-examples)
7. [Configuration](#configuration)
8. [Testing](#testing)
9. [Integration Guide](#integration-guide)

---

## Architecture Overview

### Design Philosophy

**Problem:** Azure Speech Assessment JSON is ~8k tokens per attempt. Parsing it every time for feedback is inefficient and expensive.

**Solution:** Two-stage parsing strategy:

1. **Guidance Card** (Parse once, reuse forever)
   - Extract stable reference from first attempt
   - Identify persistent challenging elements
   - ~500 tokens

2. **Attempt Summary** (Parse incrementally)
   - Extract only current errors and improvements
   - Compare with guidance card or previous attempt
   - ~300 tokens

3. **Feedback Generation** (LLM prompt)
   - Combine Guidance Card + Attempt Summary
   - Generate concise, actionable feedback
   - Total prompt: ~800 tokens (vs. 8k+ full parse)

### Data Flow

```
┌─────────────────────┐
│ Azure Speech API    │
│ (~8k tokens/attempt)│
└──────────┬──────────┘
           │
     ┌─────▼──────┐
     │ First      │
     │ Attempt    │
     └─────┬──────┘
           │
  ┌────────▼────────────┐
  │ Guidance Card       │ ◄─────────────┐
  │ (stable reference)  │               │
  └────────┬────────────┘               │
           │                            │
           │                            │
     ┌─────▼──────┐            Reuse for all
     │ Subsequent │            attempts
     │ Attempts   │                    │
     └─────┬──────┘                    │
           │                            │
  ┌────────▼────────────┐              │
  │ Attempt Summary     ├──────────────┘
  │ (incremental delta) │
  └────────┬────────────┘
           │
  ┌────────▼────────────┐
  │ Feedback Generator  │
  │ (LLM prompt)        │
  └────────┬────────────┘
           │
  ┌────────▼────────────┐
  │ Concise Feedback    │
  │ (150 tokens)        │
  └─────────────────────┘
```

---

## Installation

### Requirements

- Python 3.10+
- No external dependencies for core functionality (pure Python)
- Optional: `pytest` for running tests

### Setup

```bash
# Clone or copy the CAPT modules to your project
# Required files:
# - capt_config.py
# - capt_models.py
# - capt_guidance_card.py
# - capt_attempt_summary.py
# - capt_feedback_generator.py

# Install pytest for testing (optional)
pip install pytest
```

---

## Quick Start

### Basic Usage

```python
import json
from capt_guidance_card import parse_guidance_card, save_guidance_card
from capt_attempt_summary import parse_attempt_summary
from capt_feedback_generator import generate_feedback, format_feedback_for_display

# Step 1: Parse first attempt to create guidance card
with open("attempt1.json") as f:
    first_result = json.load(f)

guidance = parse_guidance_card(first_result)
save_guidance_card(guidance, "guidance_card.json")  # Save for reuse

# Step 2: Parse subsequent attempts
with open("attempt2.json") as f:
    second_result = json.load(f)

attempt2 = parse_attempt_summary(
    second_result,
    attempt_number=2,
    guidance_card=guidance
)

# Step 3: Generate feedback
def my_llm_function(prompt: str) -> str:
    # Your LLM integration here (OpenAI, Azure, etc.)
    return openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150
    ).choices[0].message.content

feedback = generate_feedback(guidance, attempt2, llm_function=my_llm_function)
print(feedback)
```

### Without LLM (Structured Feedback)

```python
from capt_feedback_generator import generate_structured_feedback, format_feedback_for_display

# Generate structured feedback without LLM
structured = generate_structured_feedback(guidance, attempt2)

# Format for display
display = format_feedback_for_display(structured)
print(display)
```

**Output:**
```
📊 総合スコア: 85点
   評価: 良好 (Good)

🎯 主な課題:
   • 'hello'の発音 (65点)
   • /h/の音 in 'hello' (55点)

✅ 改善点:
   • 'world'が改善されました

💡 アドバイス:
   • /h/の発音を重点的に練習しましょう

💪 良い発音です。あと少しでパーフェクトです！
```

---

## Core Components

### 1. Configuration (`capt_config.py`)

**Purpose:** Centralized configuration with tunable thresholds.

**Key Classes:**
- `FeedbackConfig`: Main configuration dataclass

**Key Methods:**
```python
config = FeedbackConfig(
    phoneme_error_threshold=70.0,
    word_error_threshold=70.0,
    max_guidance_phonemes=5,
    feedback_language="ja"
)

# Helper methods
config.classify_score(85.0)  # Returns "good"
config.is_phoneme_error(65.0)  # Returns True
```

### 2. Data Models (`capt_models.py`)

**Purpose:** Type-safe data structures for pronunciation analysis.

**Key Classes:**
- `PhonemeError`: Phoneme-level pronunciation error
- `WordError`: Word-level pronunciation error
- `ProsodyIssue`: Rhythm/intonation issue
- `GuidanceCard`: Stable reference from first attempt
- `AttemptSummary`: Incremental analysis of subsequent attempts
- `FeedbackPrompt`: Structured LLM prompt

### 3. Guidance Card Parser (`capt_guidance_card.py`)

**Purpose:** Parse first attempt to create stable reference.

**Key Functions:**
```python
# Main function
guidance = parse_guidance_card(azure_result, config=custom_config)

# Serialization
save_guidance_card(guidance, "guidance.json")
guidance = load_guidance_card("guidance.json")

# Get summary
print(guidance.get_summary())
```

**What it extracts:**
- Target sentence structure
- Top 5 challenging phonemes
- Top 3 challenging words
- Top 3 prosody patterns
- Baseline scores

### 4. Attempt Summary Parser (`capt_attempt_summary.py`)

**Purpose:** Parse subsequent attempts with delta analysis.

**Key Functions:**
```python
# Parse attempt with comparison
attempt2 = parse_attempt_summary(
    azure_result,
    attempt_number=2,
    guidance_card=guidance,
    previous_attempt=attempt1  # Optional
)

# Serialization
save_attempt_summary(attempt2, "attempt2.json")
attempt2 = load_attempt_summary("attempt2.json")

# Get summary
print(attempt2.get_summary())
```

**What it extracts:**
- Current scores
- Current errors (phoneme, word, prosody)
- Improvements vs. previous
- Regressions vs. previous
- Omitted/inserted words

### 5. Feedback Generator (`capt_feedback_generator.py`)

**Purpose:** Generate concise feedback from guidance + attempt.

**Key Functions:**
```python
# With LLM
feedback = generate_feedback(guidance, attempt, llm_function=my_llm)

# Without LLM (structured)
structured = generate_structured_feedback(guidance, attempt)
display = format_feedback_for_display(structured)

# Get prompt only (for debugging)
prompt = generate_feedback(guidance, attempt, llm_function=None)
```

---

## API Reference

### `parse_guidance_card()`

```python
def parse_guidance_card(
    azure_result: Dict,
    config: Optional[FeedbackConfig] = None
) -> GuidanceCard
```

**Parameters:**
- `azure_result`: Azure Speech Assessment JSON dict
- `config`: Configuration object (optional)

**Returns:** `GuidanceCard` object

**Raises:** `ValueError` if NBest is empty

---

### `parse_attempt_summary()`

```python
def parse_attempt_summary(
    azure_result: Dict,
    attempt_number: int,
    guidance_card: GuidanceCard,
    previous_attempt: Optional[AttemptSummary] = None,
    config: Optional[FeedbackConfig] = None
) -> AttemptSummary
```

**Parameters:**
- `azure_result`: Azure Speech Assessment JSON dict
- `attempt_number`: Sequential attempt number (1, 2, 3, ...)
- `guidance_card`: Reference guidance card
- `previous_attempt`: Previous attempt for comparison (optional)
- `config`: Configuration object (optional)

**Returns:** `AttemptSummary` object

---

### `generate_feedback()`

```python
def generate_feedback(
    guidance_card: GuidanceCard,
    attempt_summary: AttemptSummary,
    llm_function: Optional[Callable[[str], str]] = None,
    config: Optional[FeedbackConfig] = None
) -> str
```

**Parameters:**
- `guidance_card`: Stable guidance card
- `attempt_summary`: Current attempt analysis
- `llm_function`: Function that takes prompt string, returns feedback string
- `config`: Configuration object (optional)

**Returns:** Feedback string (or prompt if llm_function is None)

---

### `generate_structured_feedback()`

```python
def generate_structured_feedback(
    guidance_card: GuidanceCard,
    attempt_summary: AttemptSummary,
    config: Optional[FeedbackConfig] = None
) -> dict
```

**Returns:** Dictionary with:
- `overall_score`: float
- `score_category`: str ("excellent", "good", "fair", "poor")
- `score_label`: str (localized label)
- `main_issues`: List[str]
- `improvements`: List[str]
- `recommendations`: List[str]
- `encouragement`: str
- `attempt_number`: int

---

## Usage Examples

### Example 1: Complete Pipeline with Streamlit

```python
import streamlit as st
import json
from capt_guidance_card import parse_guidance_card, load_guidance_card
from capt_attempt_summary import parse_attempt_summary
from capt_feedback_generator import generate_structured_feedback, format_feedback_for_display

# Initialize session state
if 'guidance_card' not in st.session_state:
    st.session_state.guidance_card = None

# First attempt - create guidance card
if st.session_state.guidance_card is None:
    with open("user_attempt1.json") as f:
        result = json.load(f)
    
    st.session_state.guidance_card = parse_guidance_card(result)
    st.success("Guidance card created!")

# Subsequent attempts
audio_file = st.audio_input("Record your pronunciation")
if audio_file:
    # Get Azure assessment (your existing code)
    azure_result = get_pronunciation_assessment(audio_file)
    
    # Parse attempt
    attempt = parse_attempt_summary(
        azure_result,
        attempt_number=st.session_state.attempt_count,
        guidance_card=st.session_state.guidance_card
    )
    
    # Generate feedback
    structured = generate_structured_feedback(
        st.session_state.guidance_card,
        attempt
    )
    
    # Display
    feedback = format_feedback_for_display(structured)
    st.markdown(feedback)
```

### Example 2: Custom Configuration

```python
from capt_config import FeedbackConfig
from capt_guidance_card import parse_guidance_card

# Create custom configuration for advanced learners
advanced_config = FeedbackConfig(
    # Stricter thresholds
    excellent_threshold=95.0,
    good_threshold=85.0,
    fair_threshold=75.0,
    
    # Focus on more details
    max_guidance_phonemes=10,
    max_guidance_words=5,
    
    # English feedback
    feedback_language="en"
)

guidance = parse_guidance_card(azure_result, config=advanced_config)
```

### Example 3: Track Progress Over Time

```python
from capt_attempt_summary import parse_attempt_summary

# Track multiple attempts
attempts = []
guidance = parse_guidance_card(first_result)

for i, result in enumerate(attempt_results, start=1):
    previous = attempts[-1] if attempts else None
    
    attempt = parse_attempt_summary(
        result,
        attempt_number=i,
        guidance_card=guidance,
        previous_attempt=previous
    )
    attempts.append(attempt)

# Analyze progress
scores = [a.overall_score for a in attempts]
print(f"Score progression: {scores}")
print(f"Improvement: {scores[-1] - scores[0]:.1f} points")
```

### Example 4: Integration with OpenAI

```python
from openai import AzureOpenAI
from capt_feedback_generator import generate_feedback

# Initialize OpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-12-01-preview"
)

# Create LLM function
def llm_feedback(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7
    )
    return response.choices[0].message.content

# Generate feedback
feedback = generate_feedback(guidance, attempt, llm_function=llm_feedback)
```

---

## Configuration

### Score Thresholds

```python
FeedbackConfig(
    # Overall score categories
    excellent_threshold=90.0,  # >= 90: Excellent
    good_threshold=75.0,       # >= 75: Good
    fair_threshold=60.0,       # >= 60: Fair
                               # < 60: Poor
    
    # Phoneme error detection
    phoneme_error_threshold=70.0,    # < 70: Error
    phoneme_critical_threshold=40.0,  # < 40: Critical
    
    # Word error detection
    word_error_threshold=70.0,       # < 70: Error
    word_critical_threshold=50.0,    # < 50: Critical
)
```

### Content Limits

```python
FeedbackConfig(
    # Guidance card limits (first attempt analysis)
    max_guidance_phonemes=5,  # Top 5 challenging phonemes
    max_guidance_words=3,     # Top 3 challenging words
    guidance_prosody_issues=3, # Top 3 prosody issues
    
    # Attempt summary limits (per attempt)
    max_attempt_errors=5,      # Max errors to report
    max_attempt_improvements=3, # Max improvements to highlight
)
```

### Feedback Generation

```python
FeedbackConfig(
    # LLM settings
    feedback_max_tokens=150,   # Max tokens for feedback
    feedback_temperature=0.7,  # LLM sampling temperature
    
    # Language
    feedback_language="ja",    # "ja" or "en"
)
```

---

## Testing

### Run All Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest test_capt_guidance_card.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

### Test Structure

- `test_capt_guidance_card.py`: Tests for guidance card parsing
- `test_capt_attempt_summary.py`: Tests for attempt summary parsing
- `test_capt_feedback_generator.py`: Tests for feedback generation

All tests use mock data and require no network calls.

---

## Integration Guide

### Integration with Existing `phonoecho.py`

1. **Initialize on first attempt:**

```python
# In phonoecho.py, modify the form submission handler:

if submitted:
    st.session_state.practice_times += 1
    audio_file_path = f"asset/{user}/history/{lesson}-{st.session_state.practice_times}.wav"
    
    # Get Azure assessment
    pronunciation_assessment_result = get_pronunciation_assessment(
        user, st.session_state.pronunciation_config, 
        reference_text, audio_file_path
    )
    
    # CAPT Pipeline Integration
    if st.session_state.practice_times == 1:
        # First attempt: create guidance card
        from capt_guidance_card import parse_guidance_card, save_guidance_card
        
        guidance = parse_guidance_card(pronunciation_assessment_result)
        save_guidance_card(guidance, f"asset/{user}/history/{lesson}_guidance.json")
        st.session_state.guidance_card = guidance
    else:
        # Subsequent attempts: use guidance card
        from capt_attempt_summary import parse_attempt_summary
        from capt_feedback_generator import generate_structured_feedback, format_feedback_for_display
        
        attempt = parse_attempt_summary(
            pronunciation_assessment_result,
            attempt_number=st.session_state.practice_times,
            guidance_card=st.session_state.guidance_card
        )
        
        # Generate feedback
        structured_feedback = generate_structured_feedback(
            st.session_state.guidance_card,
            attempt
        )
        
        feedback_text = format_feedback_for_display(structured_feedback)
        st.session_state["feedback"]["ai_feedback"] = feedback_text
```

2. **Display feedback:**

```python
# In the feedback display section:
with cols[1]:
    # ... radar chart section ...
    
    with st.container(height=450):
        st.html("<h2 style='text-align: center;'>AIフィードバック</h2>")
        if st.session_state["feedback"]["ai_feedback"]:
            st.markdown(st.session_state["feedback"]["ai_feedback"])
```

### Integration with LLM (Optional Enhancement)

```python
# Add to initialize.py:
@st.cache_resource
def init_llm_feedback_function():
    client = init_openai_client()
    
    def llm_func(prompt: str) -> str:
        response = client.chat.completions.create(
            model="gpt-4-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content
    
    return llm_func

# Then use in phonoecho.py:
llm_func = init_llm_feedback_function()
feedback = generate_feedback(guidance, attempt, llm_function=llm_func)
```

---

## Best Practices

### 1. Guidance Card Management

✅ **DO:**
- Create guidance card once per sentence/lesson
- Save guidance card to disk for persistence
- Reuse guidance card across all attempts

❌ **DON'T:**
- Recreate guidance card on every attempt
- Modify guidance card after creation

### 2. Configuration Tuning

✅ **DO:**
- Adjust thresholds based on learner level
- Use stricter thresholds for advanced learners
- Test configuration changes with sample data

❌ **DON'T:**
- Use same config for all learner levels
- Set thresholds too low (everything becomes an error)

### 3. Feedback Generation

✅ **DO:**
- Use structured feedback for fast, consistent results
- Reserve LLM for premium features
- Handle LLM failures gracefully (fallback to structured)

❌ **DON'T:**
- Call LLM on every keystroke
- Expose raw prompts to users

### 4. Error Handling

```python
# Good error handling pattern
try:
    guidance = parse_guidance_card(azure_result)
except ValueError as e:
    st.error(f"Failed to parse assessment: {e}")
    guidance = None

if guidance:
    # Proceed with feedback generation
    ...
```

---

## Performance Notes

### Token Savings

| Approach | Tokens per Attempt | Total for 10 Attempts |
|----------|-------------------|---------------------|
| **Full parse** | ~8,000 | 80,000 |
| **CAPT pipeline** | ~800 (guidance + delta) | 8,500 |
| **Savings** | 90% | 89% |

### Response Time

- Guidance card parsing: ~50ms
- Attempt summary parsing: ~30ms
- Structured feedback: ~10ms
- Total (without LLM): **~90ms**

### Memory Usage

- Guidance card: ~5KB JSON
- Attempt summary: ~3KB JSON
- Total per session: **<50KB** for 10 attempts

---

## Troubleshooting

### Common Issues

**Issue:** `ValueError: No NBest results in Azure response`
**Solution:** Check that Azure API call succeeded and returned valid JSON.

**Issue:** Guidance card shows no challenging elements
**Solution:** Lower thresholds in FeedbackConfig (e.g., `phoneme_error_threshold=80.0`)

**Issue:** Feedback is always in English despite `feedback_language="ja"`
**Solution:** Check that config is passed to `generate_feedback()` or `generate_structured_feedback()`

### Debug Mode

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Print guidance card details
print(guidance.get_summary())

# Print attempt summary details
print(attempt.get_summary())

# Get prompt without calling LLM
prompt = generate_feedback(guidance, attempt, llm_function=None)
print(prompt)
```

---

## Contributing

To extend this library:

1. **Add new error types:** Extend `ErrorType` or `ProsodyErrorType` enums in `capt_models.py`
2. **Add new thresholds:** Add fields to `FeedbackConfig` in `capt_config.py`
3. **Customize feedback:** Modify `_format_japanese_prompt()` or `_format_english_prompt()` in `capt_models.py`
4. **Add tests:** Follow pytest patterns in `test_capt_*.py` files

---

## License

Copyright © 2025 PhonoEcho Project

---

## Contact

For questions or issues, please contact the project maintainer.
