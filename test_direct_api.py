"""
Direct API test - Compare ai_feedback.py approach vs integration example approach
"""
import streamlit as st
from initialize import init_openai_client

st.title("🧪 API 直接テスト")

# Initialize client
if "openai_client" not in st.session_state:
    st.session_state.openai_client = init_openai_client()

client = st.session_state.openai_client

if client:
    st.success("✅ OpenAI client initialized successfully")
    
    # Show client info
    st.write("**Client Info:**")
    st.write(f"- Endpoint: {client._base_url}")
    st.write(f"- API Version: {client._custom_query.get('api-version', 'N/A') if hasattr(client, '_custom_query') else 'N/A'}")
    
    st.divider()
    
    # Test 1: Simple call with gpt-5-mini (like ai_feedback.py)
    st.subheader("テスト 1: ai_feedback.py と同じ方法")
    if st.button("テスト 1 実行"):
        try:
            with st.spinner("API 呼び出し中..."):
                response = client.chat.completions.create(
                    model="gpt-5-mini",  # Same as ai_feedback.py
                    messages=[
                        {"role": "system", "content": "あなたは発音の専門家です。"},
                        {"role": "user", "content": "簡単なテストメッセージです。こんにちは！"},
                    ],
                    stream=True,
                )
                st.write("**Response (streaming):**")
                st.write_stream(response)
                st.success("✅ テスト 1 成功！")
        except Exception as e:
            st.error(f"❌ テスト 1 失敗: {type(e).__name__}: {str(e)}")
    
    st.divider()
    
    # Test 2: Non-streaming call (like integration example)
    st.subheader("テスト 2: 統合例と同じ方法（非ストリーミング）")
    if st.button("テスト 2 実行"):
        try:
            with st.spinner("API 呼び出し中..."):
                # Note: gpt-5-mini is a reasoning model, needs more tokens for reasoning + output
                response = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[
                        {"role": "system", "content": "あなたは発音の専門家です。"},
                        {"role": "user", "content": "簡単なテストメッセージです。こんにちは！"},
                    ],
                    max_completion_tokens=2000  # Increased for reasoning model
                )
                
                # Debug: Show full response object
                st.write("**Debug Info:**")
                st.write(f"- Response type: {type(response)}")
                st.write(f"- Choices count: {len(response.choices)}")
                st.write(f"- First choice: {response.choices[0]}")
                st.write(f"- Message: {response.choices[0].message}")
                st.write(f"- Content type: {type(response.choices[0].message.content)}")
                st.write(f"- Content length: {len(response.choices[0].message.content) if response.choices[0].message.content else 0}")
                
                st.divider()
                st.write("**Response (non-streaming):**")
                content = response.choices[0].message.content
                if content:
                    st.write(content)
                    st.success("✅ テスト 2 成功！")
                else:
                    st.warning("⚠️ Response is empty!")
                    st.json(response.model_dump())
        except Exception as e:
            st.error(f"❌ テスト 2 失敗: {type(e).__name__}: {str(e)}")
    
    st.divider()
    
    # Test 3: Try with other common deployment names
    st.subheader("テスト 3: 他のデプロイメント名を試す")
    deployment_name = st.text_input("デプロイメント名", value="gpt-5-mini")
    if st.button("テスト 3 実行"):
        try:
            with st.spinner(f"'{deployment_name}' で API 呼び出し中..."):
                # Note: reasoning models need higher token limits
                response = client.chat.completions.create(
                    model=deployment_name,
                    messages=[
                        {"role": "system", "content": "あなたは発音の専門家です。"},
                        {"role": "user", "content": "簡単なテストメッセージです。こんにちは！"},
                    ],
                    max_completion_tokens=1500
                )
                st.write(f"**Response with '{deployment_name}':**")
                st.write(response.choices[0].message.content)
                st.success(f"✅ テスト 3 成功！デプロイメント名 '{deployment_name}' は動作します。")
        except Exception as e:
            st.error(f"❌ テスト 3 失敗: {type(e).__name__}: {str(e)}")
            st.info(f"💡 デプロイメント名 '{deployment_name}' は利用できません。")
    
    st.divider()
    
    # Test 4: Check secrets configuration
    st.subheader("テスト 4: secrets.toml 設定確認")
    try:
        st.write("**AzureGPT Secrets:**")
        azure_gpt = st.secrets.get("AzureGPT", {})
        st.write(f"- AZURE_OPENAI_ENDPOINT: {azure_gpt.get('AZURE_OPENAI_ENDPOINT', 'Not set')}")
        st.write(f"- AZURE_OPENAI_API_KEY: {'***' + azure_gpt.get('AZURE_OPENAI_API_KEY', '')[-4:] if azure_gpt.get('AZURE_OPENAI_API_KEY') else 'Not set'}")
        st.write(f"- DEPLOYMENT_NAME: {azure_gpt.get('DEPLOYMENT_NAME', 'Not set (using default)')}")
    except Exception as e:
        st.error(f"Error reading secrets: {e}")

else:
    st.error("❌ OpenAI client initialization failed")
