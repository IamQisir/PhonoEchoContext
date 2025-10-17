import time
import json
from openai import AzureOpenAI
import streamlit as st
from initialize import init_openai_client
import azure.cognitiveservices.speech as speechsdk

def get_pronunciation_assessment(
    user, pronunciation_config, reference_text, audio_file_path
):
    """Get pronunciation assessment from Azure Speech Service."""
    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=st.secrets["Azure_Speech"]["SPEECH_KEY"],
            region=st.secrets["Azure_Speech"]["SPEECH_REGION"],
        )
        audio_input = speechsdk.AudioConfig(filename=audio_file_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_input
        )
        pronunciation_config.reference_text = reference_text
        st.session_state.pronunciation_config = pronunciation_config

        pronunciation_config.apply_to(recognizer)

        result = recognizer.recognize_once_async().get()
        pronunciation_result = json.loads(
            result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
        )

        return pronunciation_result
    except Exception as e:
        st.error(f"Error during pronunciation assessment: {e}")
        return None

def save_pronunciation_assessment(pronunciation_result, filepath):
    """Save pronunciation assessment result to a JSON file."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(pronunciation_result, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Error saving pronunciation assessment: {e}")

def parse_pronunciation_assessment(pronunciation_result):
    """
    Parse pronunciation assessment result from Azure Speech Service.
    
    Args:
        pronunciation_result (dict): JSON result from Azure pronunciation assessment
        
    Returns:
        tuple: (scores_dict, errors_dict, lowest_word_phonemes_dict)
            - scores_dict: 5 dimensional scores (AccuracyScore, FluencyScore, ProsodyScore, 
                          CompletenessScore, PronScore)
            - errors_dict: 5 types of errors with word lists (Omission, Mispronunciation, 
                          Insertion, UnexpectedBreak, MissingBreak)
            - lowest_word_phonemes_dict: Phoneme details for the lowest-scoring word
                          {"word": str, "word_score": float, "phonemes": [{"phoneme": str, "score": float}]}
                          
    Raises:
        ValueError: If pronunciation_result is malformed or missing required fields
    """
    try:
        # Extract overall scores from NBest[0].PronunciationAssessment
        if not pronunciation_result or "NBest" not in pronunciation_result:
            raise ValueError("pronunciation_result is missing 'NBest' field")
            
        if len(pronunciation_result["NBest"]) == 0:
            raise ValueError("NBest array is empty")
            
        overall_assessment = pronunciation_result["NBest"][0].get("PronunciationAssessment", {})
        
        # 1. Extract 5-dimensional scores
        scores_dict = {
            "AccuracyScore": overall_assessment.get("AccuracyScore", 0.0),
            "FluencyScore": overall_assessment.get("FluencyScore", 0.0),
            "ProsodyScore": overall_assessment.get("ProsodyScore", 0.0),
            "CompletenessScore": overall_assessment.get("CompletenessScore", 0.0),
            "PronScore": overall_assessment.get("PronScore", 0.0)
        }
        
        # 2. Initialize errors dict with 5 fixed keys (always present, empty lists if no errors)
        errors_dict = {
            "Omission": [],
            "Mispronunciation": [],
            "Insertion": [],
            "UnexpectedBreak": [],
            "MissingBreak": []
        }
        
        # Extract words from pronunciation result
        words = pronunciation_result["NBest"][0].get("Words", [])
        
        if not words:
            # No words to analyze, return empty errors and None for lowest word
            return scores_dict, errors_dict, None
        
        # Track lowest scoring word
        lowest_word = None
        lowest_score = float('inf')
        
        # Parse each word for errors and find lowest scoring word
        for word in words:
            word_text = word.get("Word", "")
            word_assessment = word.get("PronunciationAssessment", {})
            error_type = word_assessment.get("ErrorType", "None")
            accuracy_score = word_assessment.get("AccuracyScore", 100.0)
            
            # Collect word-level errors
            if error_type == "Omission":
                errors_dict["Omission"].append(word_text)
            elif error_type == "Mispronunciation":
                errors_dict["Mispronunciation"].append(word_text)
            elif error_type == "Insertion":
                errors_dict["Insertion"].append(word_text)
            
            # Check for prosody errors in Feedback
            feedback = word_assessment.get("Feedback", {})
            prosody = feedback.get("Prosody", {})
            break_info = prosody.get("Break", {})
            break_error_types = break_info.get("ErrorTypes", [])
            
            # Collect prosody-related errors
            if "UnexpectedBreak" in break_error_types:
                errors_dict["UnexpectedBreak"].append(word_text)
            if "MissingBreak" in break_error_types:
                errors_dict["MissingBreak"].append(word_text)
            
            # Track lowest scoring word (only for non-omitted words)
            if error_type != "Omission" and accuracy_score < lowest_score:
                lowest_score = accuracy_score
                lowest_word = word
        
        # 3. Extract phoneme details for lowest-scoring word
        lowest_word_phonemes_dict = None
        if lowest_word is not None:
            phonemes_list = []
            phonemes = lowest_word.get("Phonemes", [])
            
            for phoneme in phonemes:
                phoneme_text = phoneme.get("Phoneme", "")
                phoneme_assessment = phoneme.get("PronunciationAssessment", {})
                phoneme_score = phoneme_assessment.get("AccuracyScore", 0.0)
                
                phonemes_list.append({
                    "phoneme": phoneme_text,
                    "score": phoneme_score
                })
            
            lowest_word_phonemes_dict = {
                "word": lowest_word.get("Word", ""),
                "word_score": lowest_word.get("PronunciationAssessment", {}).get("AccuracyScore", 0.0),
                "phonemes": phonemes_list
            }
        
        return scores_dict, errors_dict, lowest_word_phonemes_dict
        
    except KeyError as e:
        raise ValueError(f"Missing required field in pronunciation_result: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error parsing pronunciation assessment: {str(e)}")

def create_openai_client():
    # openai client creation for test
    try:
        client = AzureOpenAI(
            azure_endpoint=st.secrets["AzureGPT"]["AZURE_OPENAI_ENDPOINT"],
            api_key=st.secrets["AzureGPT"]["AZURE_OPENAI_API_KEY"],
            api_version="2024-12-01-preview",
        )
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
    return client

def get_ai_feedback(client, messages):
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=messages,
            stream=False,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error getting AI feedback: {e}")
        return None

# --- Test functions ---
def ai_chatbot_test(client, messages):
    while user_input := input("質問を入力してください："):
        if user_input.lower() == "q":
            break
        messages.append({
            "role": "user",
            "content": user_input,
        })
        response = get_ai_feedback(client, messages, user_input)
        messages.append(
            {
                "role": "assistant",
                "content": response,
            }
        )
        print(response)
    with open("messages_log.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

def ai_feedback_test(client, messages):
    while user_input := input("質問を入力してください："):
        if user_input.lower() == "q":
            break
        elif user_input.split()[0].lower() == "r":
            with open(f"asset/1/history/{user_input.split()[1]}.json", "r", encoding="utf-8") as f:
                pronunciation_result = json.load(f)
            errors = parse_pronunciation_assessment(pronunciation_result)[-1]
            processed_user_input = f"{errors}"
        else:
            processed_user_input = user_input
        messages.append({
            "role": "user",
            "content": str(processed_user_input),
        })
        response = get_ai_feedback(client, messages)
        messages.append(
            {
                "role": "assistant",
                "content": response,
            }
        )
        print(response)
        print("-" * 20)
    with open("messages_log.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    client = create_openai_client()
    messages = [
        {
            "role": "system",
            "content": "You are a helpful English pronunciation assistant. Personalize your feedback based on the user's pronunciation assessment data. Please keep the feedback concise and respond in Japanese.",
        }
    ]
    ai_feedback_test(client, messages)
