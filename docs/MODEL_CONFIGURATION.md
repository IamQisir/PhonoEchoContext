# Model Configuration Guide

## Issue
Getting warning: "⚠️ AI生成に失敗しました。構造化フィードバックを表示します。"

This means the AI model call is failing.

---

## Common Causes

### 1. Wrong Model Name
The model name might not match what's available in your Azure OpenAI deployment.

**Common model names:**
- `gpt-4o-mini` (OpenAI standard)
- `gpt-4o`
- `gpt-4`
- `gpt-35-turbo` (Azure naming)
- `gpt-4-turbo`

**For Azure OpenAI, you need to use your deployment name, not the model name!**

### 2. Azure OpenAI Configuration
If you're using Azure OpenAI (which you likely are based on `AzureOpenAI` in your code), you need to use the **deployment name**, not the model name.

---

## Solution: Find Your Deployment Name

### Option 1: Check Azure Portal
1. Go to Azure Portal
2. Navigate to your Azure OpenAI resource
3. Go to "Model deployments"
4. Look for your deployment name (NOT the model name)
5. Use that deployment name in the code

Example:
- Model: `gpt-4o-mini`
- **Deployment name**: `gpt-5-mini` or `gpt4o-mini` or whatever you named it

### Option 2: Check Your Secrets
Look at your `st.secrets` or `.streamlit/secrets.toml`:

```toml
[AzureGPT]
AZURE_OPENAI_ENDPOINT = "https://your-resource.openai.azure.com/"
AZURE_OPENAI_API_KEY = "your-api-key"
AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-5-mini"  # This is what you need!
```

---

## How to Fix

### Fix 1: Use the Correct Deployment Name

Open `phonoecho_integration_example.py` and change line 122:

```python
# Current (may be wrong)
model="gpt-4o-mini"

# Change to YOUR deployment name
model="gpt-5-mini"  # Use your actual deployment name from Azure
```

### Fix 2: Make it Configurable

Add to your `secrets.toml`:
```toml
[AzureGPT]
DEPLOYMENT_NAME = "gpt-5-mini"  # Your deployment name
```

Then in code:
```python
model = st.secrets["AzureGPT"].get("DEPLOYMENT_NAME", "gpt-4o-mini")
```

---

## Quick Test Script

Create this file to test your configuration:

```python
# test_openai.py
import streamlit as st
from initialize import init_openai_client

st.title("OpenAI Configuration Test")

# Initialize client
client = init_openai_client()

# Try different model names
test_models = [
    "gpt-5-mini",
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-35-turbo",
    "gpt-4-turbo",
]

st.write("Testing model names...")

for model_name in test_models:
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        st.success(f"✅ **{model_name}** - Works!")
        break
    except Exception as e:
        st.error(f"❌ **{model_name}** - Failed: {str(e)}")

st.write("---")
st.write("Use the model name that works above!")
```

Run: `streamlit run test_openai.py`

---

## Quick Fix for phonoecho_integration_example.py

Replace line ~122 with:

```python
# Try to get deployment name from secrets, fallback to common names
try:
    model_name = st.secrets["AzureGPT"].get("DEPLOYMENT_NAME", "gpt-5-mini")
except:
    model_name = "gpt-5-mini"  # Your default deployment name

response = client.chat.completions.create(
    model=model_name,
    messages=[...],
    ...
)
```

---

## What the Updated Code Does

The code now shows the **actual error message** when AI generation fails:

```
⚠️ AI生成に失敗: BadRequestError: Invalid model name
💡 構造化フィードバックを表示します。
```

This will help you see exactly what's wrong!

---

## Expected Behavior

### If Model Name is Correct ✅
- AI generates personalized feedback
- No warning messages
- Natural language output

### If Model Name is Wrong ❌
- Warning shows with error details
- Structured feedback displays instead
- App continues to work (fallback)

---

## Recommended Steps

1. **Run the app again** - The updated code now shows the actual error
2. **Check the error message** - It will tell you what's wrong
3. **Find your deployment name** - Check Azure Portal or secrets.toml
4. **Update the model name** - Change line 122 in the file
5. **Test again** - Should work now!

---

## Common Error Messages and Solutions

| Error | Solution |
|-------|----------|
| `The model 'gpt-4o-mini' does not exist` | Use your Azure deployment name |
| `Deployment not found` | Check deployment name in Azure Portal |
| `Invalid API key` | Check AZURE_OPENAI_API_KEY in secrets |
| `Resource not found` | Check AZURE_OPENAI_ENDPOINT in secrets |
| `Rate limit exceeded` | Wait a moment and try again |

---

## Alternative: Disable AI Generation

If you just want to use structured feedback without AI:

```python
# Option 1: Skip AI entirely
def generate_ai_feedback_from_structured(client, structured_feedback, reference_text):
    # Just return formatted feedback, no AI call
    overall_score = structured_feedback.get("overall_score", 0)
    # ... rest of the formatting code
    return "\n".join(feedback_lines)
```

---

## Summary

1. ✅ Code updated to show actual error message
2. 🔍 Run app again to see what error you're getting
3. 🔧 Fix the model name based on the error
4. ✅ App will work (with fallback if needed)

The structured feedback fallback is actually quite good, so even if AI fails, you still get useful feedback!
