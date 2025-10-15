# 📊 CAPT Data Models Reference

Quick reference for accessing data from GuidanceCard and AttemptSummary objects.

---

## GuidanceCard Attributes

`GuidanceCard` is created from the **first attempt** and serves as a stable reference.

### Basic Info
```python
guidance_card.target_text           # str: Reference text (e.g., "Hello world")
guidance_card.target_display        # str: Formatted display text
guidance_card.total_words           # int: Number of words
guidance_card.total_phonemes        # int: Number of phonemes
```

### Challenging Elements (Lists)
```python
guidance_card.challenging_phonemes  # List[PhonemeError]: Difficult phonemes
guidance_card.challenging_words     # List[WordError]: Difficult words
guidance_card.prosody_patterns      # List[ProsodyIssue]: Prosody issues
```

### Reference Scores (from first attempt)
```python
guidance_card.reference_overall      # float: Overall pronunciation score
guidance_card.reference_accuracy     # float: Accuracy score
guidance_card.reference_fluency      # float: Fluency score
guidance_card.reference_prosody      # float: Prosody score
guidance_card.reference_completeness # float: Completeness score
```

### Methods
```python
guidance_card.get_summary()         # str: Text summary
```

---

## AttemptSummary Attributes

`AttemptSummary` captures data from **each attempt** (including first).

### Attempt Info
```python
attempt_summary.attempt_number      # int: Sequential number (1, 2, 3...)
```

### Current Scores
```python
attempt_summary.overall_score       # float: Current overall score
attempt_summary.accuracy_score      # float: Current accuracy
attempt_summary.fluency_score       # float: Current fluency
attempt_summary.prosody_score       # float: Current prosody
attempt_summary.completeness_score  # float: Current completeness
```

### Current Errors (Lists)
```python
attempt_summary.current_phoneme_errors  # List[PhonemeError]: Current phoneme errors
attempt_summary.current_word_errors     # List[WordError]: Current word errors
attempt_summary.current_prosody_issues  # List[ProsodyIssue]: Current prosody issues
```

### Progress Tracking (Lists)
```python
attempt_summary.improved_phonemes   # List[str]: Phonemes that improved
attempt_summary.improved_words      # List[str]: Words that improved
attempt_summary.regressed_phonemes  # List[str]: Phonemes that got worse
attempt_summary.regressed_words     # List[str]: Words that got worse
```

### Additional Info (Lists)
```python
attempt_summary.omitted_words       # List[str]: Words that were omitted
attempt_summary.inserted_words      # List[str]: Words incorrectly inserted
```

### Methods
```python
attempt_summary.get_summary()       # str: Text summary
attempt_summary.get_improvement_summary()  # str: Improvement details
```

---

## Common Mistakes ❌ → ✅

### Mistake 1: Wrong attribute name for overall score
```python
# ❌ WRONG
score = guidance_card.overall_scores.pronunciation_score
score = guidance_card.pronunciation_score

# ✅ CORRECT
score = guidance_card.reference_overall
```

### Mistake 2: Wrong attribute name for error lists
```python
# ❌ WRONG
errors = guidance_card.word_errors
prosody = guidance_card.prosody_issues

# ✅ CORRECT
errors = guidance_card.challenging_words
prosody = guidance_card.prosody_patterns
```

### Mistake 3: Assuming score is never None
```python
# ❌ WRONG (can crash if score is None for omitted words)
st.write(f"{error.score}/100")

# ✅ CORRECT
if error.score is not None:
    st.write(f"{error.score:.0f}/100")
else:
    st.write("N/A")
```

---

## Quick Examples

### Display Overall Score
```python
if guidance_card:
    score = guidance_card.reference_overall
    st.metric("Pronunciation Score", f"{score:.0f}/100")
```

### Display Error Count
```python
if guidance_card:
    error_count = len(guidance_card.challenging_words)
    st.metric("Challenging Words", error_count)
```

### Display Detailed Errors
```python
if guidance_card and guidance_card.challenging_words:
    st.write("### Challenging Words")
    for error in guidance_card.challenging_words[:5]:
        st.write(f"- **{error.word}**: {error.error_type.value}")
        if error.score is not None:
            st.write(f"  Score: {error.score:.0f}/100")
```

### Show Progress (AttemptSummary)
```python
if attempt_summary.attempt_number > 1:
    if attempt_summary.improved_words:
        st.success(f"✅ Improved: {', '.join(attempt_summary.improved_words)}")
    if attempt_summary.regressed_words:
        st.warning(f"⚠️ Needs work: {', '.join(attempt_summary.regressed_words)}")
```

### Compare Scores
```python
if guidance_card and attempt_summary:
    initial_score = guidance_card.reference_overall
    current_score = attempt_summary.overall_score
    improvement = current_score - initial_score
    
    st.metric(
        "Pronunciation Score",
        f"{current_score:.0f}/100",
        delta=f"{improvement:+.0f}"
    )
```

---

## WordError Details

When iterating through word errors:

```python
for error in guidance_card.challenging_words:
    error.word              # str: The word text
    error.score             # Optional[float]: Accuracy score (None if omitted)
    error.error_type        # ErrorType enum: MISPRONUNCIATION, OMISSION, etc.
    error.phoneme_errors    # List[PhonemeError]: Problematic phonemes
    error.offset_ms         # int: Timing offset in milliseconds
    error.duration_ms       # int: Word duration in milliseconds
```

### ErrorType Values
```python
ErrorType.NONE                  # "None"
ErrorType.MISPRONUNCIATION      # "Mispronunciation"
ErrorType.OMISSION              # "Omission"
ErrorType.INSERTION             # "Insertion"

# Usage
if error.error_type == ErrorType.MISPRONUNCIATION:
    st.write("Pronunciation needs improvement")
elif error.error_type == ErrorType.OMISSION:
    st.write("Word was skipped")
```

---

## PhonemeError Details

When iterating through phoneme errors:

```python
for phoneme in error.phoneme_errors:
    phoneme.phoneme         # str: IPA symbol (e.g., 'r', 'θ', 'ð')
    phoneme.score           # float: Accuracy score
    phoneme.word            # str: Parent word
    phoneme.position        # int: Position in word (0-indexed)
    phoneme.expected_phoneme # Optional[str]: Expected phoneme if substitution
```

---

## ProsodyIssue Details

When iterating through prosody issues:

```python
for issue in guidance_card.prosody_patterns:
    issue.issue_type        # ProsodyErrorType enum
    issue.word              # str: Word where issue occurs
    issue.confidence        # float: Confidence (0-1)
    issue.break_length_ms   # int: Pause length
    issue.description       # str: Human-readable description
```

### ProsodyErrorType Values
```python
ProsodyErrorType.UNEXPECTED_BREAK   # "UnexpectedBreak"
ProsodyErrorType.MISSING_BREAK      # "MissingBreak"
ProsodyErrorType.MONOTONE           # "Monotone"
```

---

## Complete UI Example

```python
import streamlit as st

# Display guidance card info
if st.session_state.guidance_card:
    gc = st.session_state.guidance_card
    
    # Header
    st.write(f"### Target: {gc.target_text}")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Overall", f"{gc.reference_overall:.0f}/100")
    with col2:
        st.metric("Accuracy", f"{gc.reference_accuracy:.0f}/100")
    with col3:
        st.metric("Fluency", f"{gc.reference_fluency:.0f}/100")
    with col4:
        st.metric("Prosody", f"{gc.reference_prosody:.0f}/100")
    
    # Challenging elements
    if gc.challenging_words:
        with st.expander("🎯 Challenging Words"):
            for error in gc.challenging_words:
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{error.word}**")
                with col2:
                    st.write(error.error_type.value)
                with col3:
                    if error.score is not None:
                        st.write(f"{error.score:.0f}/100")
                    else:
                        st.write("Omitted")
    
    if gc.challenging_phonemes:
        with st.expander("🔊 Challenging Phonemes"):
            for phoneme in gc.challenging_phonemes:
                st.write(f"/{phoneme.phoneme}/ in '{phoneme.word}': {phoneme.score:.0f}/100")
    
    if gc.prosody_patterns:
        with st.expander("🎵 Prosody Patterns"):
            for issue in gc.prosody_patterns:
                st.write(f"{issue.issue_type.value} at '{issue.word}'")
```

---

## AttemptSummary Progress Display

```python
import streamlit as st

if st.session_state.capt_pipeline.last_attempt:
    attempt = st.session_state.capt_pipeline.last_attempt
    
    # Current scores
    st.write(f"### Attempt #{attempt.attempt_number}")
    st.metric("Score", f"{attempt.overall_score:.0f}/100")
    
    # Progress tracking
    if attempt.attempt_number > 1:
        if attempt.improved_words:
            st.success(f"✅ Improved: {', '.join(attempt.improved_words)}")
        if attempt.regressed_words:
            st.warning(f"⚠️ Needs attention: {', '.join(attempt.regressed_words)}")
    
    # Current errors
    if attempt.current_word_errors:
        st.write("**Current Issues:**")
        for error in attempt.current_word_errors[:3]:
            st.write(f"- {error.word}: {error.error_type.value}")
```

---

## Summary

**Key Points:**
- ✅ Use `reference_overall`, `reference_accuracy`, etc. (not `overall_scores`)
- ✅ Use `challenging_words`, `challenging_phonemes`, `prosody_patterns` (not `word_errors`, etc.)
- ✅ Check `if error.score is not None` before using score
- ✅ Use `.value` to get string from Enum types
- ✅ AttemptSummary has `current_*` attributes for current errors
- ✅ AttemptSummary has `improved_*` and `regressed_*` for progress tracking

**See also:**
- [capt_models.py](../capt_models.py) - Full dataclass definitions
- [QUICKSTART.md](./QUICKSTART.md) - Integration guide
- [CAPT_INTEGRATION_GUIDE.md](./CAPT_INTEGRATION_GUIDE.md) - UI examples
