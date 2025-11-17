import streamlit as st
import json

@st.cache_data
def load_participant_sentence_order(user: int) -> list:
    """Load participant sentence order from JSON file."""
    with open("assets/participant_sentence_order.json", "r", encoding="utf-8") as f:
        participant_sentence_order = json.load(f)
    return participant_sentence_order.get(str(user), [])

def determine_avatar_order(user: int) -> list:
    """Determine avatar order based on user ID."""
    if user % 2 == 1:
        return [1, 2, 3, 4]
    return [1, 3, 2, 4]

@st.cache_data
def load_video(sentence_order: list, user: int, lesson: int):
    """Load video file path based on user and lesson."""
    avatar_order = determine_avatar_order(user)
    video_path = f"assets/learning_database/{sentence_order[lesson-1]}-{avatar_order[lesson-1]}.mp4"
    st.video(video_path)

@st.cache_data
def load_text(sentence_order: list, lesson: int):
    """Load text file content based on user and lesson."""
    txt = ""
    with open(f"assets/learning_database/{sentence_order[lesson-1]}.txt", "r", encoding="utf-8") as f:
        txt = f.read()
    st.html(f"<h2 style='text-align: center; color: white;'>{txt}</h2>")
    return txt

@DeprecationWarning
def load_ai_history(user:int, lesson:int):
    """Load AI feedback history for the user."""
    history = []
    try:
        with open(f"assets/{user}/ai_feedback/history.txt", "r", encoding="utf-8") as f:
            history = f.readlines()
    except FileNotFoundError:
        st.warning("No AI feedback history found.")
    return history

@st.cache_data
def load_system_prompt(file_path: str = "system_prompt.txt"):
    """Load system prompt from file."""
    with open(file_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()
    
    return system_prompt

def update_user_prompt(sentence, lowest_word_phonemes: dict):
    """Update user prompt based on lowest scoring words and phonemes."""
    sentence_text = (sentence or "").strip()
    phoneme_payload = (
        lowest_word_phonemes
        if lowest_word_phonemes
        else {"status": "no_detected_errors", "note": "音素エラーは検出されていません"}
    )
    phoneme_payload_json = json.dumps(phoneme_payload, ensure_ascii=False, indent=2)

    user_prompt = (
        "あなたは system prompt で定義された「英語発音改善アシスタント」です。"
        "以下の構造化データを使って、必須要素（太字の単語再提示／音素別アドバイス／ミニ練習指示／励ましの締め）を"
        "Markdown 3〜6 行で日本語（です・ます調）出力してください。\n"
        "### 入力データ\n"
        f"- 練習文: {sentence_text or '（空）'}\n"
        "- 低スコア語の詳細(JSON):\n"
        "```json\n"
        f"{phoneme_payload_json}\n"
        "```\n"
        "### 執筆ルール\n"
        "1. JSONの `word` と `phonemes` の `phoneme`/`score` を上から順に参照し、最大2音素まで扱う。\n"
        "2. `status` が `no_detected_errors` の場合は「今回は誤りなし」と祝福し、復習アイデアを1つ返す。\n"
        "3. 専門用語は必要最低限、例えは日本語ネイティブに分かる体感描写を1つ含める。\n"
        "4. 画像や外部資料への誘導は禁止、文章だけで完結させる。\n"
    )
    return user_prompt

def update_summary_prompt(scores_history, errors_history):
    """Create a summary prompt for AI Summary."""
    scores_history = scores_history or {}
    errors_history = errors_history or {}

    max_attempts = max(
        (len(values) for values in scores_history.values() if isinstance(values, list)),
        default=0,
    )
    scores_timeline = []
    for idx in range(max_attempts):
        entry = {"practice_index": idx + 1}
        for metric, values in scores_history.items():
            if isinstance(values, list) and idx < len(values):
                entry[metric] = values[idx]
        scores_timeline.append(entry)

    errors_summary = [
        {"error_type": key, "count": value} for key, value in errors_history.items()
    ]

    structured_summary_json = json.dumps(
        {"scores_timeline": scores_timeline, "errors_summary": errors_summary},
        ensure_ascii=False,
        indent=2,
    )

    summary_prompt = (
        "あなたは system prompt で定義された「学習者の発音成績サマライザー」です。"
        "以下の JSON データだけを根拠に、助言なし・事実ベースで 3 段落（成果ハイライト／推移の要約／停滞・ばらつき観測）を作成してください。\n"
        "### 参照データ(JSON)\n"
        "```json\n"
        f"{structured_summary_json}\n"
        "```\n"
        "### 執筆ルール\n"
        "1. 各段落で具体的な数値（最初と最新、最大/最小、practice_index）を引用し、差分は整数・または1桁小数で示す。\n"
        "2. `scores_timeline` が2件未満なら「データが限られているため長期推移の判断は保留」と明記してから分かる範囲を記述する。\n"
        "3. 停滞判定は直近3回で変化が ±2 未満の指標を対象とし、該当がなければ「顕著な停滞なし」と書く。\n"
        "4. `errors_summary` は件数の多い順に最大2件まで触れる。値が0のときは誤りが見られない旨を述べる。\n"
    )
    return summary_prompt
