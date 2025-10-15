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

def create_waveform_plot(audio_file, pronunciation_result):
    """
    Creates customized regions for waveform visualization using streamlit_advanced_audio.
    Highlights word intervals with colors based on pronunciation accuracy scores.
    
    Args:
        audio_file (str): Path to the audio file
        pronunciation_result (dict): Dictionary containing pronunciation assessment data
    
    Returns:
        list: List of CustomizedRegion objects for use with audix component
    """
    from streamlit_advanced_audio import CustomizedRegion

    custom_regions = []

    # Extract words from pronunciation result
    words = pronunciation_result["NBest"][0]["Words"]

    for word in words:
        # Skip if word doesn't have pronunciation assessment
        if "PronunciationAssessment" not in word:
            continue

        # Get word timing information (Azure returns in 100-nanosecond units)
        start_time = word["Offset"] / 10000000  # Convert to seconds
        word_duration = word["Duration"] / 10000000  # Convert to seconds
        end_time = start_time + word_duration

        # Determine color based on error type and accuracy score
        error_type = word["PronunciationAssessment"].get("ErrorType", "None")

        if error_type == "Omission":
            # Omitted words get orange color
            color = get_color(None)
        else:
            # Get accuracy score and corresponding color
            score = word["PronunciationAssessment"].get("AccuracyScore", 0)
            color = get_color(score)

        # Convert hex color to rgba format with transparency for better visualization
        # Extract RGB values from hex
        hex_color = color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgba_color = f"rgba({r}, {g}, {b}, 0.5)"

        # Create customized region for this word
        region = CustomizedRegion(
            start=start_time,
            end=end_time,
            color=rgba_color
        )
        custom_regions.append(region)

    return custom_regions


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
            background-color: #000;
            border-radius: 8px;
            padding: 10px;
        }}
        .eval-table {{ 
            border-collapse: collapse; 
            min-width: 100%;
            font-size: 12px;
            background-color: #000;
            color: white;
            table-layout: auto;
        }}
        .eval-table th {{ 
            background-color: #2c5f7c;
            border: 2px solid #555;
            padding: 12px;
            text-align: center;
            font-weight: bold;
            font-size: 10px;
            white-space: nowrap;
        }}
        .eval-table td {{ 
            border: 2px solid #555;
            padding: 10px;
            text-align: center;
            min-width: 80px;
        }}
        .word-cell {{ 
            font-size: 14px;
            font-weight: bold;
            position: relative;
            padding: 15px 10px;
            min-width: 100px;
        }}
        .word-score {{
            position: absolute;
            top: 4px;
            right: 6px;
            font-size: 10px;
            font-weight: normal;
            opacity: 0.9;
        }}
        .phoneme-row {{
            font-size: 12px;
            padding: 8px;
            background-color: #1a1a1a;
        }}
        .phoneme-item {{
            display: inline-block;
            margin: 2px 3px;
            padding: 4px 6px;
            border-radius: 3px;
            font-weight: 500;
        }}
        .score-row {{
            font-size: 12px;
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
            font-size: 12px;
        }}
        .header-cell {{
            background-color: #1a4d6d !important;
        }}
    </style>
    <div class="table-container">
    <table class="eval-table">
        <tr>
            <th class="header-cell">Accuracy Score</th>
            <th class="header-cell">Fluency Score</th>
            <th class="header-cell">Completeness Score</th>
            <th class="header-cell">Pronunciation Score</th>
            <th class="header-cell">Words Omitted</th>
        </tr>
        <tr>
            <td class="score-cell">{acc}</td>
            <td class="score-cell">{flu}</td>
            <td class="score-cell">{comp}</td>
            <td class="score-cell">{pron}</td>
            <td style="font-size: 12px;">{omit}</td>
        </tr>
    """.format(
        acc=int(overall.get("AccuracyScore", 0)),
        flu=int(overall.get("FluencyScore", 0)),
        comp=int(overall.get("CompletenessScore", 0)),
        pron=int(overall.get("PronScore", 0)),
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
            output += '<td class="phoneme-row">-</td>'
        elif "Phonemes" in word:
            phoneme_html = ""
            for phoneme in word["Phonemes"]:
                phoneme_text = phoneme["Phoneme"]
                phoneme_score = phoneme.get("PronunciationAssessment", {}).get("AccuracyScore", 0)
                phoneme_color = get_color(phoneme_score)
                # Use background color instead of text color for better visibility
                text_color = 'white' if phoneme_score < 80 else 'black'
                phoneme_html += f'<span class="phoneme-item" style="background-color: {phoneme_color}; color: {text_color};">{phoneme_text}</span>'
            output += f'<td class="phoneme-row">{phoneme_html}</td>'
        else:
            output += f'<td class="phoneme-row">{word["Word"]}</td>'
    output += "</tr>"
    
    # Add score row for phonemes (numeric scores)
    output += "<tr>"
    for word in words:
        word_assessment = word.get("PronunciationAssessment", {})
        error_type = word_assessment.get("ErrorType", "None")
        
        if error_type == "Omission":
            output += '<td class="score-row">-</td>'
        elif "Phonemes" in word:
            score_html = ""
            for phoneme in word["Phonemes"]:
                phoneme_score = phoneme.get("PronunciationAssessment", {}).get("AccuracyScore", 0)
                phoneme_color = get_color(phoneme_score)
                text_color = 'white' if phoneme_score < 80 else 'black'
                score_html += f'<span class="score-badge" style="background-color: {phoneme_color}; color: {text_color};">{int(phoneme_score)}</span>'
            output += f'<td class="score-row">{score_html}</td>'
        else:
            output += '<td class="score-row">-</td>'
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


def create_doughnut_chart(data: pd.DataFrame, title: str):
    """Create a doughnut chart using Altair"""
    # Convert data to DataFrame
    df = pd.DataFrame(list(data.items()), columns=["Error", "Count"])

    return (
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


def plot_overall_score(data: pd.DataFrame):
    """Plot overall pronunciation score"""
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
                    values=list(range(1, 11)),
                    tickCount=10,
                    format="d",
                    grid=True,
                ),
                scale=alt.Scale(domain=[1, 10]),
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


def test_radar_chart():
    with open("asset/1/history/レッソン2-2024-12-24_16-43-01.json", "r", encoding="utf-8") as f:
        result = json.load(f)
    fig1 = create_radar_chart(result)
    fig1.savefig("radar_chart.png")

def test_syllable_table():
    with open("asset/1/history/レッソン2-2024-12-24_16-43-01.json", "r", encoding="utf-8") as f:
        result = json.load(f)
    html_table = create_syllable_table(result)
    st.html(html_table)



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
