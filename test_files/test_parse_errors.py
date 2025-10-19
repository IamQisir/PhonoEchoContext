import json
from ai_feedback import parse_pronunciation_assessment

# Load the test JSON file
with open("assets/1/history/1-2.json", "r", encoding="utf-8") as f:
    pronunciation_result = json.load(f)

# Parse the pronunciation assessment
scores_dict, errors_dict, lowest_word_phonemes_dict = parse_pronunciation_assessment(pronunciation_result)

print("=" * 60)
print("SCORES:")
print("=" * 60)
for key, value in scores_dict.items():
    print(f"{key}: {value}")

print("\n" + "=" * 60)
print("ERRORS:")
print("=" * 60)
for error_type, words in errors_dict.items():
    print(f"{error_type}: {len(words)} words")
    if words:
        print(f"  Words: {words}")

print("\n" + "=" * 60)
print("LOWEST SCORING WORD:")
print("=" * 60)
if lowest_word_phonemes_dict:
    print(f"Word: {lowest_word_phonemes_dict['word']}")
    print(f"Score: {lowest_word_phonemes_dict['word_score']}")
    print(f"Phonemes: {len(lowest_word_phonemes_dict['phonemes'])}")
    for phoneme_info in lowest_word_phonemes_dict['phonemes']:
        print(f"  {phoneme_info['phoneme']}: {phoneme_info['score']}")
else:
    print("None")

print("\n" + "=" * 60)
print("SUMMARY:")
print("=" * 60)
total_errors = sum(len(words) for words in errors_dict.values())
print(f"Total errors detected: {total_errors}")
