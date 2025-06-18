from whispercpp import Whisper

w = Whisper.from_pretrained("tiny.en")  # Automatically downloads ggml-tiny.en
result = w.transcribe("path/to/audio.wav")
print(result)
