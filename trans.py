import whisper

print("Loading Whisper model...")
model = whisper.load_model("turbo")
print("Model loaded. Starting transcription...")
result = model.transcribe("./a4f-local/output.mp3")
print("Transcription complete. Result:")
print(result["text"])