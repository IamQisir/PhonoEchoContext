import streamlit as st
import json
from typing import Optional
from tools import has_pronunciation_errors

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

def update_user_prompt(sentence, lowest_word_phonemes: dict, errors_dict: Optional[dict] = None):
    """
    Update user prompt based on detected errors.
    
    Prefers phoneme-level insight (lowest_word_phonemes). If that is not
    available but Azure still reports word-level mistakes (e.g., omission
    or insertion only), we pass a summarized error payload so the AI never
    congratulates the learner incorrectly.
    """
    sentence_text = (sentence or "").strip()
    errors_dict = errors_dict or {}
    if lowest_word_phonemes:
        phoneme_payload = lowest_word_phonemes
    elif has_pronunciation_errors(errors_dict):
        condensed_errors = {
            key: value for key, value in errors_dict.items() if value
        }
        phoneme_payload = {
            "status": "word_errors_detected",
            "error_summary": condensed_errors,
            "note": "音素エラーは抽出できませんでしたが、上記の語レベル誤りが検出されています。",
        }
    else:
        phoneme_payload = {
            "status": "no_detected_errors",
            "note": "音素エラーは検出されていません",
        }
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

    attempt_count = len(scores_timeline)
    structured_summary_json = json.dumps(
        {"scores_timeline": scores_timeline, "errors_summary": errors_summary},
        ensure_ascii=False,
        indent=2,
    )

    summary_prompt = (
        "あなたは system prompt で定義された「学習者の発音成績サマライザー」です。"
        "以下の JSON データだけを根拠に、Score Snapshot / Progress Insights / Encouragement の3段落を日本語敬体で作成してください。"
        "1レッスンあたり最大5回の練習が行われます。今回は"
        f"{attempt_count}回の記録があります。\n"
        "### 参照データ(JSON)\n"
        "```json\n"
        f"{structured_summary_json}\n"
        "```\n"
        "### 執筆ルール\n"
        "1. Score Snapshot: 最新 practice_index の overall / Accuracy / Fluency / Completeness / Prosody から有意な指標を選び、具体的な得点と最高値を紹介する。\n"
        "2. Progress Insights: `scores_timeline` が2件以上なら最初と最新、または直近2回の差分を整数（必要なら1桁小数）で記述し、上下動の要因は推測せずにデータだけで述べる。1件のみでも「初回記録として〜」と肯定的に説明し、「データ不足」という表現は使わない。\n"
        "3. Encouragement: `errors_summary` の多い順に最大1件触れつつ、今回の頑張りや次回への期待を励ましの言葉で締める。練習法や指示は書かない。\n"
        "4. `scores_timeline` が空のときのみ「記録がまだありません」と述べ、それ以外では数値に必ず触れる。\n"
    )
    return summary_prompt
