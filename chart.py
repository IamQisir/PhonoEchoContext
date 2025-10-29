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

@st.fragment
def create_waveform_plot(user, lesson, practice_times, lowest_word_phonemes_dict, pronunciation_result):
    """
    Creates customized regions for waveform visualization using streamlit_advanced_audio.
    Highlights word intervals with colors based on pronunciation accuracy scores.
    
    Args:
        user (int): User ID
        lesson (int): Lesson number
        practice_times (int): Number of practice attempts
        lowest_word_phonemes_dict (dict): Dictionary with lowest-scoring word info
        pronunciation_result (dict): Dictionary containing pronunciation assessment data
    
    Returns:
        None: Renders audix components directly
    """
    # Load target pronunciation result (reference audio)
    target_json_path = f"assets/{user}/resources/{lesson}.json"
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
        audix(
            f"assets/{user}/resources/{lesson}.wav", 
            key="target", 
            start_time=target_start_end["start_time"], 
            end_time=target_start_end["end_time"]
        )
    else:
        st.warning(f"Word '{lowest_word}' not found in target audio timestamps")
        audix(f"assets/{user}/resources/{lesson}.wav", key="target")
    
    # Display user audio with timestamp if available
    if user_start_end:
        audix(
            f"assets/{user}/history/{lesson}-{practice_times}.wav",
            key="user",
            start_time=user_start_end["start_time"],
            end_time=user_start_end["end_time"]
        )
    else:
        st.warning(f"Word '{lowest_word}' not found in user audio timestamps")
        audix(f"assets/{user}/history/{lesson}-{practice_times}.wav", key="user")

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
    
    # Count omitted words
    omitted_words = [w["Word"] for w in words if w.get("PronunciationAssessment", {}).get("ErrorType") == "Omission"]
    omitted_text = ", ".join(omitted_words) if omitted_words else "-"
    
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
        .eval-table {{ 
            border-collapse: collapse; 
            min-width: 100%;
            font-size: 14px;
            background-color: #0E1117;
            color: white;
            table-layout: auto;
        }}
        .eval-table th {{ 
            background-color: #2c5f7c;
            border: 2px solid #555;
            padding: 12px;
            text-align: center;
            font-weight: bold;
            font-size: 12px;
            white-space: nowrap;
        }}
        .eval-table td {{ 
            border: 2px solid #555;
            padding: 10px;
            text-align: center;
            min-width: 80px;
        }}
        .word-cell {{ 
            font-size: 16px;
            font-weight: bold;
            position: relative;
            padding: 15px 10px;
            min-width: 100px;
        }}
        .word-score {{
            position: absolute;
            top: 4px;
            right: 6px;
            font-size: 12px;
            font-weight: normal;
            opacity: 0.9;
        }}
        .phoneme-row {{
            font-size: 16px;
            padding: 0;
        }}
        .phoneme-container {{
            display: flex;
            justify-content: center;
            align-items: stretch;
            height: 100%;
            min-height: 25px;
        }}
        .phoneme-item {{
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0;
            font-weight: 500;
            border-right: 2px solid #555;
            flex: 1;
            min-width: 40px;
        }}
        .phoneme-item:last-child {{
            border-right: none;
        }}
        .score-row {{
            font-size: 14px;
            padding: 8px;
            background-color: #0a0a0a;
        }}
        .score-badge {{
            display: inline-block;
            margin: 2px 3px;
            padding: 6px 8px;
            border-radius: 4px;
            font-weight: bold;
            min-width: 35px;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        .score-cell {{
            font-weight: bold;
            font-size: 14px;
        }}
        .header-cell {{
            background-color: #1a4d6d !important;
        }}
    </style>
    <div class="table-container">
    <table class="eval-table">
        <tr>
            <th class="header-cell">Pronunciation Score</th>
            <th class="header-cell">Accuracy Score</th>
            <th class="header-cell">Fluency Score</th>
            <th class="header-cell">Completeness Score</th>
            <th class="header-cell">Prosody Score</th>
            <th class="header-cell">Words Omitted</th>
        </tr>
        <tr>
            <td class="score-cell">{pron}</td>
            <td class="score-cell">{acc}</td>
            <td class="score-cell">{flu}</td>
            <td class="score-cell">{comp}</td>
            <td class="score-cell">{pros}</td>
            <td style="font-size: 12px;">{omit}</td>
        </tr>
    """.format(
        pron=int(overall.get("PronScore", 0)),
        acc=int(overall.get("AccuracyScore", 0)),
        flu=int(overall.get("FluencyScore", 0)),
        comp=int(overall.get("CompletenessScore", 0)),
        pros=int(overall.get("ProsodyScore", 0)),
        omit=omitted_text
    )
    
    # Add word-level row
    output += "<tr>"
    for word in words:
        word_text = word["Word"]
        word_assessment = word.get("PronunciationAssessment", {})
        error_type = word_assessment.get("ErrorType", "None")
        
        if error_type == "Omission":
            word_score = None
            word_color = get_color(None)
        else:
            word_score = word_assessment.get("AccuracyScore", 0)
            word_color = get_color(word_score)
        
        score_display = f"{int(word_score)}" if word_score is not None else "-"
        
        output += f"""
        <td class="word-cell" style="background-color: {word_color}; color: {'white' if word_score and word_score < 80 else 'black'};">
            <div>{word_text}<span class="word-score">{score_display}</span></div>
        </td>
        """
    output += "</tr>"
    
    # Add phoneme-level row (with color-coded phonemes)
    output += "<tr>"
    for word in words:
        word_assessment = word.get("PronunciationAssessment", {})
        error_type = word_assessment.get("ErrorType", "None")
        
        if error_type == "Omission":
            output += '<td class="phoneme-row"><div class="phoneme-container">-</div></td>'
        elif "Phonemes" in word:
            phoneme_html = '<div class="phoneme-container">'
            for phoneme in word["Phonemes"]:
                phoneme_text = phoneme["Phoneme"]
                phoneme_score = phoneme.get("PronunciationAssessment", {}).get("AccuracyScore", 0)
                phoneme_color = get_color(phoneme_score)
                # Use background color instead of text color for better visibility
                text_color = 'white' if phoneme_score < 80 else 'black'
                phoneme_html += f'<div class="phoneme-item" style="background-color: {phoneme_color}; color: {text_color};">{phoneme_text}</div>'
            phoneme_html += '</div>'
            output += f'<td class="phoneme-row">{phoneme_html}</td>'
        else:
            output += f'<td class="phoneme-row"><div class="phoneme-container">{word["Word"]}</div></td>'
    output += "</tr>"
    
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

    # Create figure with wider, lower aspect ratio: 800px x 200px (8.0 x 2.0 inches at 100 DPI)
    fig, ax = plt.subplots(figsize=(8.0, 2.0), subplot_kw=dict(projection="radar"))
    fig.subplots_adjust(top=0.92, bottom=0.08, left=0.12, right=0.88)

    # Set radial gridlines with WHITE text (reduced font size)
    ax.set_rgrids(
        [0.2, 0.4, 0.6, 0.8, 1.0],
        labels=["20", "40", "60", "80", "100"],
        angle=0,
        fontsize=7,  # Reduced from 9
        color="white",
    )

    # Add inner dashed pentagon for reference (e.g., at 60% level)
    reference_level = 0.6
    reference_values = [reference_level] * N
    ax.plot(
        theta,
        reference_values,
        linestyle="--",
        linewidth=1.5,
        color="#FF6B6B",
        alpha=0.6,
    )
    ax.fill(theta, reference_values, alpha=0.05, color="#FF6B6B")

    # Plot the actual scores
    ax.plot(
        theta,
        scores,
        "o-",
        linewidth=3,
        color="#1E88E5",
        markersize=10,
        markerfacecolor="#1E88E5",
        markeredgecolor="white",
        markeredgewidth=2,
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

def update_scores_history(session_state, scores_dict):
    """Update scores history in session state."""
    for key, value in scores_dict.items():
        if key in session_state.scores_history:
            session_state.scores_history[key].append(value)
        else:
            session_state.scores_history[key] = [value]

def update_errors_history(session_state, errors_dict):
    """Update errors history in session state.
    
    Args:
        session_state: Streamlit session state object
        errors_dict: Dictionary with error types as keys and lists of words as values
                    Format: {"Omission": ["word1", "word2"], ...}
    """
    for key, value in errors_dict.items():
        # Convert list to count
        count = len(value) if isinstance(value, list) else value
        
        if key in session_state.errors_history:
            session_state.errors_history[key] += count
        else:
            session_state.errors_history[key] = count


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
    # Convert list values to counts if necessary
    processed_data = {}
    for key, value in data.items():
        if isinstance(value, list):
            processed_data[key] = len(value)
        elif isinstance(value, (int, float)):
            processed_data[key] = value
        else:
            # Skip non-numeric, non-list values
            continue
    
    # Filter out zero counts (now safe since all values are numeric)
    processed_data = {k: v for k, v in processed_data.items() if v > 0}
    
    # Check if data is empty
    if not processed_data:
        return alt.Chart(pd.DataFrame()).mark_text(
            text="エラーなし", 
            size=20,
            color="green"
        ).properties(title=title, width=300, height=300)
    
    # Convert data to DataFrame
    df = pd.DataFrame(list(processed_data.items()), columns=["Error", "Count"])

    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta(field="Count", type="quantitative"),
            color=alt.Color(
                field="Error",
                type="nominal",
                scale=alt.Scale(
                    range=[
                        "#FF4B4B",
                        "#FFC000",
                        "#00B050",
                        "#2F75B5",
                        "#7030A0",
                        "#000000",
                    ]
                ),
            ),
            tooltip=["Error", "Count"],
        )
        .properties(title=title, width=300, height=300)
    )
    
    return chart

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
