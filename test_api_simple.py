"""
Super simple API test - minimal code to test OpenAI API
"""
import streamlit as st
from initialize import init_openai_client

st.title("🔬 最小限 API テスト")

client = init_openai_client()

if client:
    st.success("✅ Client initialized")
    
    # Test with minimal parameters
    if st.button("テスト実行"):
        st.write("**送信するメッセージ:**")
        st.code("""
messages=[
    {"role": "system", "content": "あなたは親切なアシスタントです。"},
    {"role": "user", "content": "こんにちは！元気ですか？"}
]
        """)
        
        try:
            st.write("**API 呼び出し中...**")
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": "あなたは親切なアシスタントです。"},
                    {"role": "user", "content": "こんにちは！元気ですか？"}
                ]
            )
            
            st.write("**✅ API 呼び出し成功！**")
            st.divider()
            
            # Show complete response
            st.write("**完全なレスポンス:**")
            st.json(response.model_dump())
            
            st.divider()
            
            # Extract content
            st.write("**コンテンツ:**")
            content = response.choices[0].message.content
            st.write(f"Type: {type(content)}")
            st.write(f"Length: {len(content) if content else 0}")
            st.write(f"Value: `{content}`")
            
            if content:
                st.success("✅ コンテンツあり！")
                st.markdown("---")
                st.markdown("### 📝 AI の返答:")
                st.write(content)
            else:
                st.error("❌ コンテンツが空です！")
                
        except Exception as e:
            st.error(f"❌ エラー: {type(e).__name__}")
            st.code(str(e))
            import traceback
            st.code(traceback.format_exc())
else:
    st.error("❌ Client initialization failed")
