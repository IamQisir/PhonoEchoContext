import io
import os
import json
import librosa
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import soundfile as sf
import azure.cognitiveservices.speech as speechsdk
from datetime import datetime
import altair as alt

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


def create_radar_chart(pronunciation_result):
    """
    Creates an enhanced radar chart for pronunciation assessment visualization.

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

    # Get scores
    scores = [overall_assessment.get(categories[cat], 0) for cat in categories]

    # Create figure and polar axis
    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(projection="polar"))

    # Calculate angles for each category
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False)

    # Close the plot by appending first values
    scores += scores[:1]
    angles = np.concatenate((angles, [angles[0]]))

    # Plot data
    ax.plot(
        angles, scores, "o-", linewidth=3, label="Score", color="#2E86C1", markersize=10
    )
    ax.fill(angles, scores, alpha=0.25, color="#2E86C1")

    # Set chart properties
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories.keys(), size=20)

    # Add gridlines and adjust their style
    ax.set_rgrids(
        [20, 40, 60, 80, 100],
        labels=["20", "40", "60", "80", "100"],
        angle=0,
        fontsize=14,
    )  # Increased from 10 to 14

    # Add score labels at each point with larger font
    for angle, score in zip(angles[:-1], scores[:-1]):
        ax.text(
            angle,
            score + 5,
            f"{score:.1f}",
            ha="center",
            va="center",
            fontsize=20,  # Increased font size for score labels
            fontweight="bold",
        )

    # Customize grid
    ax.grid(True, linestyle="--", alpha=0.7, linewidth=1.5)  # Increased grid line width

    # Set chart limits and direction
    ax.set_ylim(0, 100)
    ax.set_theta_direction(-1)  # Clockwise
    ax.set_theta_offset(np.pi / 2)  # Start from top

    # Add title with larger font
    plt.title(
        "発音評価レーダーチャート\nPronunciation Assessment Radar Chart",
        pad=20,
        size=20,
        fontweight="bold",
    )  # Increased from 14 to 18

    # Add subtle background color
    ax.set_facecolor("#F8F9F9")
    fig.patch.set_facecolor("white")

    # Adjust layout
    plt.tight_layout()

    return fig


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
test_syllable_table()
