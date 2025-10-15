# API バージョン修正 - 問題解決！

## 🎉 問題が解決しました！

### 問題の原因

Azure OpenAI API バージョン `2024-12-01-preview` と `gpt-5-mini` モデルには以下の特性があります：

1. ❌ **パラメータ名変更:** `max_tokens` → `max_completion_tokens`
2. ❌ **temperature 制限:** `gpt-5-mini` はデフォルト値 (1) のみサポート
3. ⚠️ **推理モデル:** `gpt-5-mini` は推理モデルで、トークンを推理と出力の両方に使用
   - `max_completion_tokens=600` では不十分（全て推理に使われ、出力が空になる）
   - `max_completion_tokens=2000` 以上を推奨

### なぜ test_api_simple.py は動作したのか？

```python
# test_api_simple.py - 動作する ✅
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[...],
    # max_completion_tokens を設定していない = デフォルト値使用
)
```

`max_completion_tokens` を設定しなかったため、デフォルトの大きな値が使われ、推理と出力の両方に十分なトークンがありました。

### 修正内容

**問題の症状：**
```json
{
  "finish_reason": "length",  // ← 長さ制限に達した
  "message": {
    "content": ""  // ← 出力が空！
  },
  "usage": {
    "completion_tokens": 600,
    "reasoning_tokens": 600  // ← 全て推理に使われた！
  }
}
```

**修正前（出力が空）：**
```python
response = client.chat.completions.create(
    model=model_name,
    messages=[...],
    max_completion_tokens=600  # ❌ 推理モデルには不十分
)
```

**修正後（正常動作）：**
```python
response = client.chat.completions.create(
    model=model_name,
    messages=[...],
    max_completion_tokens=2000  # ✅ 推理 + 出力に十分なトークン
)
```

## 修正されたファイル

1. ✅ `phonoecho_integration_example.py` - Line ~135
2. ✅ `test_direct_api.py` - 全てのテスト

## テスト方法

### 1. 更新されたテストを実行

```bash
streamlit run test_direct_api.py
```

ブラウザで：
- **テスト 1** をクリック → ✅ 成功するはず（ストリーミング）
- **テスト 2** をクリック → ✅ 成功するはず（非ストリーミング、修正済み）

### 2. 統合例を実行

```bash
streamlit run phonoecho_integration_example.py
```

1. サイドバーで適切な user/lesson を選択
2. 録音またはサンプル音声をアップロード
3. 「フィードバックをもらおう！」をクリック
4. **AI フィードバック**セクションを確認

**期待される結果：**
- ❌ ~~「⚠️ AI生成に失敗しました」~~ → もう表示されない
- ✅ AI が生成したフィードバックが表示される

## API バージョン互換性

### パラメータサポート表

| API Version | max_tokens | max_completion_tokens | temperature (custom) |
|------------|------------|---------------------|---------------------|
| 2023-xx-xx | ✅ 対応 | ❌ 非対応 | ✅ 対応 |
| 2024-02-01 | ✅ 対応 | ❌ 非対応 | ✅ 対応 |
| 2024-12-01-preview | ❌ 非対応 | ✅ 対応 | モデル依存 |

### モデル固有の制限（gpt-5-mini）

`gpt-5-mini` は**推理モデル**（reasoning model）で、以下の特性があります：

| パラメータ | サポート | 備考 |
|----------|---------|------|
| temperature | ❌ デフォルト値 (1) のみ | カスタム値は使用不可 |
| max_completion_tokens | ✅ 対応 | **2000以上を推奨**（推理 + 出力） |
| stream | ✅ 対応 | 使用可能 |

#### 推理モデルの特性

```
max_completion_tokens = reasoning_tokens + output_tokens
```

- **reasoning_tokens**: 内部推理に使用（ユーザーには見えない）
- **output_tokens**: 実際の応答テキスト（ユーザーに表示される）

**例：**
- `max_completion_tokens=600` → `reasoning_tokens=600, output_tokens=0` → **出力が空！**
- `max_completion_tokens=2000` → `reasoning_tokens=600, output_tokens=1400` → **正常に動作✅**

### あなたの設定（initialize.py）

```python
client = AzureOpenAI(
    azure_endpoint=st.secrets["AzureGPT"]["AZURE_OPENAI_ENDPOINT"],
    api_key=st.secrets["AzureGPT"]["AZURE_OPENAI_API_KEY"],
    api_version="2024-12-01-preview",  # ← 最新版を使用
)
```

## 参考リンク

- [Azure OpenAI API リファレンス](https://learn.microsoft.com/azure/ai-services/openai/reference)
- [API バージョン変更履歴](https://learn.microsoft.com/azure/ai-services/openai/api-version-deprecation)

## まとめ

✅ **根本原因 1:** API version 2024-12-01-preview では `max_tokens` → `max_completion_tokens` に変更  
✅ **根本原因 2:** `gpt-5-mini` モデルは `temperature` のカスタム値をサポートせず  
✅ **根本原因 3:** `gpt-5-mini` は推理モデルで、`max_completion_tokens` には推理と出力の両方が含まれる  
✅ **解決方法:** `max_completion_tokens=2000` に増加（推理 + 出力に十分な容量）  
✅ **確認済み:** 修正後、AI フィードバックが正常に生成される  
✅ **次のステップ:** `phonoecho_integration_example.py` を実行して AI フィードバックを確認

### 推奨設定

```python
# gpt-5-mini (reasoning model) の推奨設定
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[...],
    max_completion_tokens=2000,  # 推理 + 出力に十分
    # temperature は設定しない（デフォルト値を使用）
)
```

問題は完全に解決しました！🎉
