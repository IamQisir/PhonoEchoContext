import io
import os
import json
import librosa
import time
import numpy as np
import pandas as pd
import streamlit as st
import soundfile as sf
import azure.cognitiveservices.speech as speechsdk
from datetime import datetime
import altair as alt
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, RegularPolygon
from matplotlib.path import Path
from matplotlib.projections import register_projection
from matplotlib.projections.polar import PolarAxes
from matplotlib.spines import Spine
from matplotlib.transforms import Affine2D
from streamlit_advanced_audio import audix, CustomizedRegion, RegionColorOptions
from audio_process import extract_timestamps_dict

plt.rcParams["font.family"] = "MS Gothic"

def get_color(score):
    """
    Returns color based on pronunciation proficiency score.
    Based on Azure speech evaluation thresholds (Moxon, 2024).
    
    Args:
        score: int or float, pronunciation score (0-100)
               or None for omitted words
    
    Returns:
        str: hex color code
    """
    if score is None:
        # omitted words
        return "#ff8c00"  # orange
    elif score >= 80:
        # high proficiency
        return "#006400"  # dark green
    elif score >= 60:
        # satisfactory performance
        return "#90ee90"  # light green
    elif score >= 40:
        # moderate proficiency
        return "#ffff00"  # yellow
    else:
        # needing significant improvement (0-39)
        return "#ff0000"  # red


ERROR_TYPE_LABELS_JA = {
    "omission": "省略",
    "mispronunciation": "発音誤り",
    "insertion": "挿入",
    "none": "問題なし",
    "unknown": "不明",
}

DISPLAY_ERROR_KEYS = {"omission", "mispronunciation", "insertion"}

ERROR_CHART_COLOR_MAP = {
    "omission": "#FF4B4B",
    "mispronunciation": "#FFC000",
    "insertion": "#00B050",
}

ERROR_CHART_ORDER = [
    "omission",
    "mispronunciation",
    "insertion",
]

ERROR_ROW_COLOR_MAP = {
    "omission": "#b45309",
    "mispronunciation": "#b91c1c",
    "insertion": "#0ea5e9",
    "unknown": "#6b7280",
}


def normalize_error_key(value):
    """Normalize Azure error type names so they can be mapped reliably."""
    if not value:
        return "none"
    return (
        str(value)
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
        .lower()
    )


def get_error_label_ja(value):
    """Return the Japanese label for a given error type."""
    key = normalize_error_key(value)
    if key in ERROR_TYPE_LABELS_JA:
        return ERROR_TYPE_LABELS_JA[key]
    if value:
        return str(value)
    return ERROR_TYPE_LABELS_JA["unknown"]


def is_omitted_word(word: dict) -> bool:
    """Return True when Azure marks a reference word as omitted."""
    if not word:
        return False

    assessment = word.get("PronunciationAssessment") or {}
    error_type = assessment.get("ErrorType")
    if error_type == "Omission":
        return True

    duration = word.get("Duration")
    accuracy = assessment.get("AccuracyScore")
    if (duration is None or duration == 0) and (accuracy is None or accuracy == 0):
        return error_type in (None, "None", "Mispronunciation")

    return False

@st.fragment
def create_waveform_plot(sentence_order, user, lesson, practice_times, lowest_word_phonemes_dict, pronunciation_result):
    """
    Creates customized regions for waveform visualization using streamlit_advanced_audio.
    Highlights word intervals with colors based on pronunciation accuracy scores.
    
    Args:
        sentence_order (list): List of sentence IDs in order
        user (int): User ID
        lesson (int): Lesson number
        practice_times (int): Number of practice attempts
        lowest_word_phonemes_dict (dict): Dictionary with lowest-scoring word info
        pronunciation_result (dict): Dictionary containing pronunciation assessment data
    
    Returns:
        None: Renders audix components directly
    """
    # Load target pronunciation result (reference audio)
    target_json_path = f"assets/learning_database/{sentence_order[lesson - 1]}.json"
    try:
        with open(target_json_path, "r", encoding="utf-8") as f:
            target_result = json.load(f)
        target_timestamps = extract_timestamps_dict(target_result)
    except FileNotFoundError:
        st.error(f"Target pronunciation file not found: {target_json_path}")
        target_timestamps = {}
    except Exception as e:
        st.error(f"Error loading target timestamps: {e}")
        target_timestamps = {}
    
    # Extract user timestamps from pronunciation_result
    user_timestamps = extract_timestamps_dict(pronunciation_result)

    # Get timestamps for the lowest-scoring word
    lowest_word = lowest_word_phonemes_dict["word"].lower()
    target_start_end = target_timestamps.get(lowest_word, None)
    user_start_end = user_timestamps.get(lowest_word, None)

    # Display target audio with timestamp if available
    if target_start_end:
        if target_start_end["start_time"] and target_start_end["end_time"] and target_start_end["end_time"] > target_start_end["start_time"]:
            audix(
                f"assets/learning_database/{sentence_order[lesson - 1]}.wav",
                key="target",
                start_time=target_start_end["start_time"],
                end_time=target_start_end["end_time"]
            )
        else:
            audix(f"assets/learning_database/{sentence_order[lesson - 1]}.wav", key="target")
    else:
        st.warning(f"Word '{lowest_word}' not found in target audio timestamps")
        audix(f"assets/learning_database/{sentence_order[lesson - 1]}.wav", key="target")

    # Display user audio with timestamp if available
    if user_start_end:
        if user_start_end["start_time"] and user_start_end["end_time"] and user_start_end["end_time"] > user_start_end["start_time"]:
            audix(
                f"assets/history_database/{user}/{lesson}-{practice_times}.wav",
                key="user",
                start_time=user_start_end["start_time"],
                end_time=user_start_end["end_time"]
            )
        else:
            audix(f"assets/history_database/{user}/{lesson}-{practice_times}.wav", key="user")
    else:
        st.warning(f"Word '{lowest_word}' not found in user audio timestamps")
        audix(f"assets/history_database/{user}/{lesson}-{practice_times}.wav", key="user")

def create_syllable_table(pronunciation_result):
    """
    Creates a compact pronunciation evaluation table similar to ALL-Talk system.
    Displays overall scores, word-level, and phoneme-level assessments in a grid format.
    
    Args:
        pronunciation_result (dict): Dictionary containing pronunciation assessment data
    
    Returns:
        str: HTML string for the evaluation table with horizontal scrolling
    """
    # Extract overall assessment
    overall = pronunciation_result["NBest"][0]["PronunciationAssessment"]
    words = pronunciation_result["NBest"][0]["Words"]
    
    # Start building HTML with improved styling
    output = """
    <style>
        .table-container {{
            overflow-x: auto;
            max-width: 100%;
            max-height: 300px;
            overflow-y: auto;
            background-color: #0E1117;
            border-radius: 8px;
            padding: 10px;
        }}
        .scoreboard {{
            display: inline-flex;
            flex-wrap: nowrap;
            gap: 0;
            margin-bottom: 14px;
        }}
        .score-card {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background-color: #1a4d6d;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 0;
            padding: 10px 16px;
            min-width: 90px;
            box-shadow: 0 0 6px rgba(0, 0, 0, 0.2);
            flex: 0 0 auto;
        }}
        .score-card:first-child {{
            border-top-left-radius: 10px;
            border-bottom-left-radius: 10px;
        }}
        .score-card:last-child {{
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
        }}
        .score-card + .score-card {{
            border-left: 0;
        }}
        .score-card-title {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: rgba(255, 255, 255, 0.8);
            margin-bottom: 6px;
        }}
        .score-card-value {{
            font-size: 20px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1;
        }}
        .eval-table {{
            border-collapse: collapse;
            width: 100%;
            font-size: 14px;
            background-color: #0E1117;
            color: white;
        }}
        .eval-table td {{
            border: 2px solid #555;
            padding: 10px;
            text-align: center;
        }}
        .eval-table td.word-row-wrapper {{
            padding: 0;
            border: none;
        }}
        .word-card-row {{
            display: inline-flex;
            flex-wrap: nowrap;
            gap: 0;
            width: 100%;
        }}
        .word-card {{
            display: flex;
            flex-direction: column;
            gap: 0;
            flex: 0 0 auto;
            width: var(--card-width, 80px);
            min-width: var(--card-width, 80px);
            background-color: #111827;
            border: 1px solid #2f3948;
            border-radius: 0;
            overflow: hidden;
        }}
        .word-card:first-child {{
            border-top-left-radius: 6px;
            border-bottom-left-radius: 6px;
        }}
        .word-card:last-child {{
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }}
        .word-card + .word-card {{
            border-left: 0;
        }}
        .word-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 10px;
            font-size: 16px;
            font-weight: 600;
            color: #f9fafb;
        }}
        .word-text {{
            flex: 1 1 auto;
            text-align: left;
            white-space: nowrap;
        }}
        .word-score {{
            margin-left: 8px;
            font-size: 12px;
            font-weight: 500;
            opacity: 0.9;
        }}
        .phoneme-strip {{
            display: grid;
            width: 100%;
            grid-template-columns: repeat(var(--phoneme-count, 1), minmax(0, 1fr));
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            background-color: rgba(17, 24, 39, 0.8);
        }}
        .phoneme-item {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 6px 8px;
            border-right: 1px solid rgba(15, 23, 42, 0.6);
            box-sizing: border-box;
            font-weight: 600;
            white-space: nowrap;
        }}
        .phoneme-item:last-child {{
            border-right: none;
        }}
        .phoneme-placeholder {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 6px 12px;
            grid-column: 1 / -1;
            font-weight: 500;
        }}
        .eval-table td.error-row-wrapper {{
            padding: 0;
            border: none;
        }}
        .error-card-row {{
            display: inline-flex;
            flex-wrap: nowrap;
            gap: 0;
            width: 100%;
        }}
        .error-card {{
            flex: 0 0 auto;
            padding: 8px 10px;
            font-size: 13px;
            font-weight: 600;
            color: white;
            text-align: center;
            border: 1px solid rgba(15, 23, 42, 0.2);
            border-radius: 0;
        }}
        .error-card:first-child {{
            border-top-left-radius: 6px;
            border-bottom-left-radius: 6px;
        }}
        .error-card:last-child {{
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }}
        .error-card + .error-card {{
            border-left: 0;
        }}
    </style>
    <div class="table-container">
        <div class="scoreboard">
            <div class="score-card">
                <span class="score-card-title">総合スコア</span>
                <span class="score-card-value">{pron}</span>
            </div>
            <div class="score-card">
                <span class="score-card-title">正確性</span>
                <span class="score-card-value">{acc}</span>
            </div>
            <div class="score-card">
                <span class="score-card-title">流暢性</span>
                <span class="score-card-value">{flu}</span>
            </div>
            <div class="score-card">
                <span class="score-card-title">完全性</span>
                <span class="score-card-value">{comp}</span>
            </div>
            <div class="score-card">
                <span class="score-card-title">韻律</span>
                <span class="score-card-value">{pros}</span>
            </div>
        </div>
        <table class="eval-table">
    """.format(
        pron=int(overall.get("PronScore", 0)),
        acc=int(overall.get("AccuracyScore", 0)),
        flu=int(overall.get("FluencyScore", 0)),
        comp=int(overall.get("CompletenessScore", 0)),
        pros=int(overall.get("ProsodyScore", 0)),
    )

    def get_contrast_text_color(hex_color: str) -> str:
        """Return readable text color for the given background."""
        if not isinstance(hex_color, str) or not hex_color.startswith("#") or len(hex_color) != 7:
            return "#f9fafb"

        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
        except ValueError:
            return "#f9fafb"

        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        return "#0f172a" if luminance > 160 else "#f9fafb"

    phoneme_unit_px = 26
    word_char_unit_px = 12
    base_padding_px = 32
    min_card_width_px = 52

    word_views = []
    for word in words:
        word_text = word.get("Word", "")
        word_assessment = word.get("PronunciationAssessment", {})
        phonemes = word.get("Phonemes") or []
        omitted = is_omitted_word(word)

        if omitted:
            word_score = None
            word_color = get_color(None)
            score_display = "-"
            phoneme_count = 1
        else:
            word_score = word_assessment.get("AccuracyScore", 0)
            word_color = get_color(word_score)
            score_display = f"{int(word_score)}"
            phoneme_count = max(len(phonemes), 1)

        header_text_color = get_contrast_text_color(word_color)
        header_html = (
            f'<div class="word-header" style="background-color: {word_color}; color: {header_text_color};">'
            f'<span class="word-text">{word_text}</span>'
            f'<span class="word-score">{score_display}</span>'
            "</div>"
        )

        card_min_width = max(
            phoneme_count * phoneme_unit_px,
            len(word_text) * word_char_unit_px + base_padding_px,
            min_card_width_px,
        )

        if omitted or not phonemes:
            phoneme_html = (
                '<div class="phoneme-strip">'
                '<span class="phoneme-placeholder">-</span>'
                "</div>"
            )
        else:
            phoneme_html = '<div class="phoneme-strip">'
            for phoneme in phonemes:
                phoneme_text = phoneme.get("Phoneme", "")
                phoneme_score = phoneme.get("PronunciationAssessment", {}).get("AccuracyScore", 0)
                phoneme_color = get_color(phoneme_score)
                phoneme_text_color = get_contrast_text_color(phoneme_color)
                phoneme_html += (
                    f'<span class="phoneme-item" style="background-color: {phoneme_color}; color: {phoneme_text_color};">'
                    f"{phoneme_text}</span>"
                )
            phoneme_html += "</div>"

        card_style = f"--card-width: {card_min_width}px; --phoneme-count: {phoneme_count};"
        word_views.append(
            {
                "card_html": f'<div class="word-card" style="{card_style}">{header_html}{phoneme_html}</div>',
                "width": card_min_width,
                "word_dict": word,
                "omitted": omitted,
            }
        )

    word_cards_html = "".join(view["card_html"] for view in word_views)
    output += (
        '<tr class="word-row">'
        '<td class="word-row-wrapper" colspan="5">'
        f'<div class="word-card-row">{word_cards_html}</div>'
        "</td>"
        "</tr>"
    )

    # Add error-type row
    def format_error_label(word_dict, omitted_flag):
        assessment = word_dict.get("PronunciationAssessment", {}) or {}
        error_type = assessment.get("ErrorType")
        key = "omission" if omitted_flag else normalize_error_key(error_type)

        if key in DISPLAY_ERROR_KEYS:
            label = ERROR_TYPE_LABELS_JA.get(key, get_error_label_ja(error_type))
            color = ERROR_ROW_COLOR_MAP.get(key, ERROR_ROW_COLOR_MAP["unknown"])
            return label, color

        return "&#128077;", "#1f4028"

    error_cards_html = []
    for view in word_views:
        label, bg_color = format_error_label(view["word_dict"], view["omitted"])
        width = view["width"]
        error_cards_html.append(
            f'<div class="error-card" style="background-color: {bg_color}; width: {width}px; min-width: {width}px;">{label}</div>'
        )

    output += (
        '<tr class="error-row">'
        '<td class="error-row-wrapper" colspan="5">'
        f'<div class="error-card-row">{"".join(error_cards_html)}</div>'
        "</td>"
        "</tr>"
    )
    
    output += "</table></div>"
    return output


def pronunciation_assessment(audio_file, reference_text):
    """
    Performs pronunciation assessment using Azure Speech SDK.
    
    Args:
        audio_file (str): Path to the audio file to assess
        reference_text (str): Reference text for pronunciation comparison
    
    Returns:
        dict: Pronunciation assessment results in JSON format
    """
    # Note: Using free tier keys here, but premium keys are used in Avatar
    speech_key, service_region = (
        st.secrets["Azure_Speech"]["SPEECH_KEY"],
        st.secrets["Azure_Speech"]["SPEECH_REGION"],
    )
    print(f"SPEECH_KEY: {speech_key}, SPEECH_REGION: {service_region}")

    # Create speech configuration
    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key, region=service_region
    )
    print("SpeechConfig created successfully")

    # Create audio configuration
    audio_config = speechsdk.audio.AudioConfig(filename=audio_file)
    print("AudioConfig created successfully")

    # Configure pronunciation assessment settings
    pronunciation_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=True,
    )
    pronunciation_config.enable_prosody_assessment()
    pronunciation_config.phoneme_alphabet = "IPA"
    print("PronunciationAssessmentConfig created successfully")

    try:
        # Create speech recognizer
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )
        print("SpeechRecognizer created successfully")

        # Apply pronunciation configuration
        pronunciation_config.apply_to(speech_recognizer)
        print("PronunciationConfig applied successfully")

        # Perform recognition
        result = speech_recognizer.recognize_once_async().get()
        print(f"Recognition result: {result}")

        # Parse JSON result
        pronunciation_result = json.loads(
            result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
        )
        print("JSON result parsed successfully")

        return pronunciation_result
    except Exception as e:
        st.error(f"Exception caught in pronunciation_assessment function: {str(e)}")
        import traceback

        st.error(traceback.format_exc())
        raise


def plot_overall_score(scores_history: dict):
    """Plot overall pronunciation score"""
    # Convert dict to DataFrame
    if not scores_history or "PronScore" not in scores_history or not scores_history["PronScore"]:
        # Return empty chart with message if no data
        return alt.Chart(pd.DataFrame()).mark_text(text="まだ学習記録がありません", size=20)

    data = pd.DataFrame(scores_history)
    data["Attempt"] = range(1, len(data) + 1)

    # Calculate y-axis range
    y_min_pron = max(0, data["PronScore"].min() - 5)
    y_max_pron = min(100, data["PronScore"].max() + 5)

    chart = (
        alt.Chart(data)
        .mark_line(color="#FF4B4B", point=True)
        .encode(
            x=alt.X(
                "Attempt:Q",
                axis=alt.Axis(
                    tickMinStep=1,
                    title="練習回数",
                    values=list(range(1, 7)),
                    tickCount=6,
                    format="d",
                    grid=True,
                ),
                scale=alt.Scale(domain=[1, 6]),
            ),
            y=alt.Y(
                "PronScore:Q",
                title="スコア",
                scale=alt.Scale(domain=[y_min_pron, y_max_pron]),
            ),
            tooltip=["Attempt", "PronScore"],
        )
        .properties(title="総合点スコア", width="container", height=300)
        .interactive()
    )

    return chart


def plot_detail_scores(scores_history: dict):
    """Plot detailed scores components"""
    # Convert dict to DataFrame
    metrics = ["AccuracyScore", "FluencyScore", "CompletenessScore", "ProsodyScore"]

    # Check if data exists
    if not scores_history or not any(
        metric in scores_history and scores_history[metric] for metric in metrics
    ):
        # Return empty chart with message if no data
        return alt.Chart(pd.DataFrame()).mark_text(
            text="まだ学習記録がありません", size=20
        )

    data = pd.DataFrame(scores_history)
    data["Attempt"] = range(1, len(data) + 1)

    # Prepare data
    detail_data = data.melt(
        id_vars=["Attempt"], value_vars=metrics, var_name="Metric", value_name="Score"
    )
    metric_labels = {
        "AccuracyScore": "正確性",
        "FluencyScore": "流暢性",
        "CompletenessScore": "完全性",
        "ProsodyScore": "韻律",
    }
    detail_data["Metric"] = detail_data["Metric"].map(metric_labels).fillna(
        detail_data["Metric"]
    )

    # Calculate y-axis range
    y_min_detail = max(0, min(data[metrics].min()) - 5)
    y_max_detail = min(100, max(data[metrics].max()) + 5)

    chart = (
        alt.Chart(detail_data)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "Attempt:Q",
                axis=alt.Axis(
                    tickMinStep=1,
                    title="練習回数",
                    values=list(range(1, 7)),
                    tickCount=7,
                    format="d",
                    grid=True,
                ),
                scale=alt.Scale(domain=[1, 6]),
            ),
            y=alt.Y(
                "Score:Q",
                title="スコア",
                scale=alt.Scale(domain=[y_min_detail, y_max_detail]),
            ),
            color=alt.Color(
                "Metric:N",
                scale=alt.Scale(range=["#00C957", "#4169E1", "#FFD700", "#FF69B4"]),
                legend=alt.Legend(title="評価項目", orient="right"),
            ),
            tooltip=["Attempt", "Score", "Metric"],
        )
        .properties(title="詳細スコア", width="container", height=300)
        .interactive()
    )

    return chart


def plot_score_history():
    # Check if learning_state exists and has scores_history
    if (
        "learning_state" not in st.session_state
        or "scores_history" not in st.session_state.learning_state
    ):
        st.warning("まだ学習記録がありません")
        return

    lesson_index = st.session_state.lesson_index

    if lesson_index not in st.session_state.learning_state["scores_history"]:
        st.warning(f"レッスン {lesson_index + 1} の記録がありません")
        return

    # Check if data exists
    scores = st.session_state.learning_state["scores_history"][lesson_index]
    if not any(scores.values()):  # Check if all score lists are empty
        st.warning("まだ学習記録がありません")
        return

    # Ensure all arrays have the same length before creating DataFrame
    max_length = max(len(v) for v in scores.values() if v)
    if max_length == 0:
        st.warning("まだ学習記録がありません")
        return

    # Pad shorter arrays with None or use only the minimum length
    min_length = min(len(v) for v in scores.values() if v)

    # Create a clean scores dict with consistent lengths
    clean_scores = {}
    for key, value_list in scores.items():
        if value_list:  # Only include non-empty lists
            clean_scores[key] = value_list[:min_length]  # Truncate to minimum length

    if not clean_scores or min_length == 0:
        st.warning("まだ学習記録がありません")
        return

    # Create DataFrame only if we have data
    data = pd.DataFrame(clean_scores)
    if len(data) == 0:
        st.warning("まだ学習記録がありません")
        return

    data["Attempt"] = range(1, len(data) + 1)

    # Create two columns for charts
    col1, col2 = st.columns([2, 3])

    # Plot charts in columns
    with col1:
        overall_chart = plot_overall_score(data)
        st.altair_chart(overall_chart, use_container_width=True)

    with col2:
        detail_chart = plot_detail_scores(data)
        st.altair_chart(detail_chart, use_container_width=True)


def radar_factory(num_vars, frame="circle"):
    """
    Create a radar chart with `num_vars` Axes.

    This function creates a RadarAxes projection and registers it.

    Parameters
    ----------
    num_vars : int
        Number of variables for radar chart.
    frame : {'circle', 'polygon'}
        Shape of frame surrounding Axes.

    """
    # calculate evenly-spaced axis angles
    theta = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)

    class RadarTransform(PolarAxes.PolarTransform):

        def transform_path_non_affine(self, path):
            # Paths with non-unit interpolation steps correspond to gridlines,
            # in which case we force interpolation (to defeat PolarTransform's
            # autoconversion to circular arcs).
            if path._interpolation_steps > 1:
                path = path.interpolated(num_vars)
            return Path(self.transform(path.vertices), path.codes)

    class RadarAxes(PolarAxes):

        name = "radar"
        PolarTransform = RadarTransform

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # rotate plot such that the first axis is at the top
            self.set_theta_zero_location("N")

        def fill(self, *args, closed=True, **kwargs):
            """Override fill so that line is closed by default"""
            return super().fill(closed=closed, *args, **kwargs)

        def plot(self, *args, **kwargs):
            """Override plot so that line is closed by default"""
            lines = super().plot(*args, **kwargs)
            for line in lines:
                self._close_line(line)

        def _close_line(self, line):
            x, y = line.get_data()
            if x[0] != x[-1]:
                x = np.append(x, x[0])
                y = np.append(y, y[0])
                line.set_data(x, y)

        def set_varlabels(self, labels):
            self.set_thetagrids(np.degrees(theta), labels)

        def _gen_axes_patch(self):
            if frame == "circle":
                return Circle((0.5, 0.5), 0.5)
            elif frame == "polygon":
                return RegularPolygon((0.5, 0.5), num_vars, radius=0.5, edgecolor="k")
            else:
                raise ValueError("Unknown value for 'frame': %s" % frame)

        def _gen_axes_spines(self):
            if frame == "circle":
                return super()._gen_axes_spines()
            elif frame == "polygon":
                spine = Spine(
                    axes=self,
                    spine_type="circle",
                    path=Path.unit_regular_polygon(num_vars),
                )
                spine.set_transform(
                    Affine2D().scale(0.5).translate(0.5, 0.5) + self.transAxes
                )
                return {"polar": spine}
            else:
                raise ValueError("Unknown value for 'frame': %s" % frame)

    register_projection(RadarAxes)
    return theta


def create_radar_chart(pronunciation_result):
    """
    Creates an enhanced pentagon radar chart for pronunciation assessment visualization.
    Uses proper pentagon frame without circular border.

    Args:
        pronunciation_result (dict): Dictionary containing pronunciation assessment data

    Returns:
        matplotlib.figure.Figure: The generated radar chart
    """
    # Extract overall assessment
    overall_assessment = pronunciation_result["NBest"][0]["PronunciationAssessment"]

    # Define categories with Japanese labels
    categories = {
        "総合": "PronScore",
        "正確性": "AccuracyScore",
        "流暢性": "FluencyScore",
        "完全性": "CompletenessScore",
        "韻律": "ProsodyScore",
    }

    # Get scores (normalize to 0-1 range for radar chart)
    scores = [overall_assessment.get(categories[cat], 0) / 100.0 for cat in categories]
    labels = list(categories.keys())

    # Number of variables
    N = len(categories)

    # Create radar chart with pentagon frame
    theta = radar_factory(N, frame="polygon")

    # Create figure and keep the plotting area square so grid spacing stays uniform
    fig, ax = plt.subplots(figsize=(6.0, 4.0), subplot_kw=dict(projection="radar"))
    fig.subplots_adjust(top=0.92, bottom=0.08, left=0.12, right=0.88)
    ax.set_aspect("equal", adjustable="box")

    # Configure evenly spaced radial gridlines and hide numeric labels
    grid_levels = np.linspace(0.2, 1.0, 5)
    grid_labels = [f"{int(level * 100)}" for level in grid_levels]
    ax.set_rgrids(
        grid_levels,
        labels=grid_labels,
        angle=0,
        fontsize=7,
        color="white",
    )
    ax.set_ylim(0, 1)
    ax.yaxis.grid(True, linestyle="--", linewidth=0.8, color="white", alpha=0.25)

    # Add inner dashed pentagon for reference (e.g., at 60% level)
    reference_level = 0.6
    reference_values = [reference_level] * N
    ax.plot(
        theta,
        reference_values,
        linestyle="--",
        linewidth=1.0,
        color="white",
        alpha=0.35,
    )
    ax.fill(theta, reference_values, alpha=0.05, color="white")

    # Plot the actual scores
    ax.plot(
        theta,
        scores,
        "o-",
        linewidth=1.0,
        color="#1E88E5",
        markersize=3.5,
        markerfacecolor="#1E88E5",
        markeredgecolor="white",
        markeredgewidth=0.7,
    )
    ax.fill(theta, scores, alpha=0.25, color="#1E88E5")

    # Set labels with WHITE color (reduced font size)
    ax.set_varlabels(labels)
    # Set label font size and color
    for label in ax.get_xticklabels():
        label.set_fontsize(12)  # Reduced from 16
        label.set_fontweight("bold")
        label.set_color("white")

    # Add score values INSIDE the pentagon with smart positioning to avoid overlap
    for idx, (angle, score, label) in enumerate(zip(theta, scores, labels)):
        actual_score = score * 100  # Convert back to 0-100 scale

        # Position scores FULLY INSIDE the pentagon - deeper negative offsets
        if idx == 0:  # 総合 (top)
            offset = -0.18
            va = "center"
        elif idx == 1:  # 正確性 (top-right)
            offset = -0.16
            va = "center"
        elif idx == 2:  # 流暢性 (bottom-right)
            offset = -0.16
            va = "center"
        elif idx == 3:  # 完全性 (bottom-left)
            offset = -0.16
            va = "center"
        else:  # 韻律 (top-left)
            offset = -0.16
            va = "center"

        # Calculate position INSIDE the pentagon with better constraint
        x = angle
        y = max(0.20, score + offset)  # Increased minimum distance from center

        ax.text(
            x,
            y,
            f"{actual_score:.0f}",
            ha="center",
            va=va,
            fontsize=9,  # Reduced from 12
            fontweight="bold",
            color="white",
            bbox=dict(
                boxstyle="round,pad=0.3",  # Slightly reduced padding
                facecolor="#1E88E5",
                edgecolor="white",
                linewidth=1.5,  # Slightly thinner border
            ),
            transform=ax.transData,
            zorder=10,
        )
    # Style improvements - Light gray background
    ax.set_facecolor("#0E1117")
    fig.patch.set_facecolor("#0E1117")

    # Customize grid appearance
    ax.grid(True, linestyle="--", alpha=0.3, linewidth=1, color="#CCCCCC")

    # Set spine color
    ax.spines['polar'].set_edgecolor('white')
    ax.spines['polar'].set_linewidth(1.5)

    return fig


def create_doughnut_chart(data: dict, title: str):
    """
    Create a doughnut chart using Altair.
    
    Args:
        data: Dictionary with error types as keys and counts as values
              Format 1: {"Omission": 2, "Mispronunciation": 1, ...}
              Format 2: {"Omission": ["word1", "word2"], ...} (will be converted to counts)
        title: Chart title
    
    Returns:
        Altair chart object
    """
    # Convert list values to counts if necessary, restricting to displayable error types
    processed_counts = {}
    for key, value in data.items():
        normalized = normalize_error_key(key)
        if normalized not in DISPLAY_ERROR_KEYS:
            continue

        if isinstance(value, list):
            count = len(value)
        elif isinstance(value, (int, float)):
            count = value
        else:
            continue

        if count > 0:
            processed_counts[normalized] = processed_counts.get(normalized, 0) + count
    
    # Check if data is empty
    if not processed_counts:
        return alt.Chart(pd.DataFrame()).mark_text(
            text="エラーはありません",
            size=20,
            color="green"
        ).properties(title=title, width=300, height=300)
    
    records = [
        {
            "Key": key,
            "Label": ERROR_TYPE_LABELS_JA.get(key, key.title()),
            "Count": processed_counts[key],
        }
        for key in ERROR_CHART_ORDER
        if key in processed_counts
    ]

    if not records:
        return alt.Chart(pd.DataFrame()).mark_text(
            text="エラーはありません",
            size=20,
            color="green"
        ).properties(title=title, width=300, height=300)

    df = pd.DataFrame(records)
    
    color_domain = [record["Label"] for record in records]
    color_range = [ERROR_CHART_COLOR_MAP.get(record["Key"], "#6b7280") for record in records]

    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta(field="Count", type="quantitative"),
            color=alt.Color(
                field="Label",
                type="nominal",
                scale=alt.Scale(domain=color_domain, range=color_range),
                legend=alt.Legend(title="エラータイプ"),
            ),
            tooltip=[
                alt.Tooltip("Label:N", title="エラータイプ"),
                alt.Tooltip("Count:Q", title="件数"),
            ],
        )
        .properties(title=title, width=300, height=300)
    )
    
    return chart

def _get_metric_value(scores_history: dict, key: str, decimals: int = 1):
    """Return the latest value and delta rounded to the desired decimals."""
    values = scores_history.get(key, [])
    if not values:
        return 0.0, None

    latest = round(values[-1], decimals)
    delta = None
    if len(values) > 1:
        delta = round(values[-1] - values[-2], decimals)
    return latest, delta


def create_metric_cards(practice_times: int, scores_history: dict):
    metric_card_cols = st.columns(5)
    if practice_times <= 1:
        pron_value, _ = _get_metric_value(scores_history, "PronScore")
        acc_value, _ = _get_metric_value(scores_history, "AccuracyScore")
        flu_value, _ = _get_metric_value(scores_history, "FluencyScore")
        comp_value, _ = _get_metric_value(scores_history, "CompletenessScore")
        pros_value, _ = _get_metric_value(scores_history, "ProsodyScore")

        metric_card_cols[0].metric("総合スコア", pron_value)
        metric_card_cols[1].metric("正確性", acc_value)
        metric_card_cols[2].metric("流暢性", flu_value)
        metric_card_cols[3].metric("完全性", comp_value)
        metric_card_cols[4].metric("韻律", pros_value)
    else:
        pron_value, pron_delta = _get_metric_value(scores_history, "PronScore")
        acc_value, acc_delta = _get_metric_value(scores_history, "AccuracyScore")
        flu_value, flu_delta = _get_metric_value(scores_history, "FluencyScore")
        comp_value, comp_delta = _get_metric_value(scores_history, "CompletenessScore")
        pros_value, pros_delta = _get_metric_value(scores_history, "ProsodyScore")

        metric_card_cols[0].metric("総合スコア", pron_value, delta=pron_delta)
        metric_card_cols[1].metric("正確性", acc_value, delta=acc_delta)
        metric_card_cols[2].metric("流暢性", flu_value, delta=flu_delta)
        metric_card_cols[3].metric("完全性", comp_value, delta=comp_delta)
        metric_card_cols[4].metric("韻律", pros_value, delta=pros_delta)

def test_radar_chart():
    with open(
        "asset/1/history/レッソン2-2024-12-24_16-43-01.json", "r", encoding="utf-8"
    ) as f:
        result = json.load(f)
    fig1 = create_radar_chart(result)
    fig1.savefig("radar_chart.png")


def test_syllable_table():
    with open(
        "asset/1/history/レッソン2-2024-12-24_16-43-01.json", "r", encoding="utf-8"
    ) as f:
        result = json.load(f)
    html_table = create_syllable_table(result)
    st.html(html_table)
