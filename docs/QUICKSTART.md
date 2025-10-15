# 🚀 Quick Start: CAPT Integration Fix

## ✅ Problem Fixed!

The `CAPTFeedbackPipeline` requires **3 arguments**:
1. `user_id` - User identifier
2. `lesson_id` - Lesson identifier  
3. `config` - FeedbackConfig (optional, uses defaults if not provided)

---

## 📝 Correct Usage

### Simple Way (Default Config)
```python
from capt_integration import CAPTFeedbackPipeline

# Initialize with user and lesson IDs
pipeline = CAPTFeedbackPipeline(
    user_id=1,
    lesson_id=1
)
```

### Custom Config
```python
from capt_integration import CAPTFeedbackPipeline
from capt_config import FeedbackConfig

# Create custom config
config = FeedbackConfig(
    fair_threshold=60.0,
    phoneme_error_threshold=70.0,
    word_error_threshold=70.0,
    prosody_error_threshold=65.0,
    max_attempt_errors=5
)

# Initialize pipeline
pipeline = CAPTFeedbackPipeline(
    user_id=1,
    lesson_id=1,
    config=config
)
```

### Streamlit Integration
```python
import streamlit as st
from capt_integration import CAPTFeedbackPipeline
from capt_config import FeedbackConfig

# In your Streamlit app, after getting user and lesson from sidebar
if "capt_pipeline" not in st.session_state:
    config = FeedbackConfig(
        fair_threshold=60.0,
        max_attempt_errors=5
    )
    st.session_state.capt_pipeline = CAPTFeedbackPipeline(
        user_id=user,      # ✅ Required
        lesson_id=lesson,  # ✅ Required
        config=config      # ✅ Optional
    )
```

---

## 🎯 Using the Pipeline

### Method 1: Simple Processing (Recommended)
```python
# Process an attempt (automatically handles guidance card and summaries)
structured_feedback = pipeline.get_structured_feedback(
    azure_result=pronunciation_assessment_result,
    attempt_number=1
)

# structured_feedback is a dictionary with:
# - summary: Overall assessment and scores
# - key_issues: List of main problems
# - recommendations: Practice suggestions
# - detailed_errors: Full error breakdown
```

### Method 2: With LLM Feedback
```python
# Define LLM function
def my_llm_function(prompt: str) -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# Process with LLM
feedback_text = pipeline.process_attempt(
    azure_result=pronunciation_assessment_result,
    attempt_number=1,
    llm_function=my_llm_function,
    use_llm=True
)
```

---

## 📊 Complete Example

```python
import streamlit as st
from capt_integration import CAPTFeedbackPipeline

# Sidebar inputs
user = st.number_input("User ID", value=1)
lesson = st.number_input("Lesson ID", value=1)

# Initialize pipeline (once per user/lesson combination)
if "capt_pipeline" not in st.session_state:
    st.session_state.capt_pipeline = CAPTFeedbackPipeline(
        user_id=user,
        lesson_id=lesson
    )

# When user submits audio
if st.button("Get Feedback"):
    # Get pronunciation assessment from Azure
    azure_result = get_pronunciation_assessment(audio_file, reference_text)
    
    # Process with CAPT pipeline
    structured_feedback = st.session_state.capt_pipeline.get_structured_feedback(
        azure_result,
        attempt_number=st.session_state.practice_times
    )
    
    # Display feedback
    st.write("### Feedback")
    st.write(structured_feedback["summary"]["overall_assessment"])
    
    st.write("### Key Issues")
    for issue in structured_feedback["key_issues"]:
        st.write(f"- {issue}")
    
    st.write("### Recommendations")
    for rec in structured_feedback["recommendations"]:
        st.write(f"- {rec}")
```

---

## 🔑 Key Points

1. **Always provide `user_id` and `lesson_id`**
   ```python
   # ❌ WRONG
   pipeline = CAPTFeedbackPipeline(config)
   
   # ✅ CORRECT
   pipeline = CAPTFeedbackPipeline(user_id=1, lesson_id=1, config=config)
   ```

2. **The pipeline automatically manages:**
   - Guidance card creation (first attempt)
   - Attempt summaries (all attempts)
   - File storage (saves to `asset/{user_id}/history/`)

3. **Two main methods:**
   - `get_structured_feedback()` - Returns dictionary (for custom UI)
   - `process_attempt()` - Returns formatted string (with optional LLM)

4. **Progress tracking:**
   ```python
   progress = pipeline.get_progress_summary()
   # Returns: lesson_id, target_text, initial_score, current_score, improvement, etc.
   ```

---

## 🧪 Test It

Run the updated integration example:
```bash
streamlit run phonoecho_integration_example.py
```

---

## 📚 Documentation

All documentation has been moved to the `docs/` folder:
- `docs/FIX_SUMMARY.md` - Complete parameter reference
- `docs/CAPT_INTEGRATION_GUIDE.md` - Detailed integration guide
- `docs/README_CAPT_PIPELINE.md` - Full API documentation

---

## 💡 Tips

- **Change user/lesson?** Create a new pipeline instance
- **Reset progress?** Call `pipeline.reset_lesson()`
- **Check progress?** Use `pipeline.get_progress_summary()`
- **Custom storage?** Pass `storage_dir` parameter

---

## ✅ Summary

**Fixed issues:**
1. ✅ Added required `user_id` and `lesson_id` parameters
2. ✅ Simplified to use `get_structured_feedback()` method
3. ✅ Updated AI feedback generation to work with structured data
4. ✅ Moved all documentation to `docs/` folder

**Ready to use!** 🎉
