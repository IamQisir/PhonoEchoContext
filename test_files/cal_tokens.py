import tiktoken

with open("asset/1/history/レッソン2-2024-12-24_16-43-01.json", "r", encoding="utf-8") as f:
    data = f.read()

print(data)

# Choose the model's tokenizer
encoding = tiktoken.encoding_for_model("gpt-5")

# Example input text (e.g., the transcript or pronunciation result)
text = "Please provide pronunciation feedback for the following sentence: 'The quick brown fox jumps over the lazy dog.'"

# Count tokens
num_tokens = len(encoding.encode(data))
print(f"Tokens: {num_tokens}")
