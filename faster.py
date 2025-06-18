from faster_whisper import WhisperModel
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def transcribe_audio_faster_whisper(audio_file_path, model_size="base", device="cpu", compute_type="int8"):
    """
    Transcribes an audio file using Faster Whisper.

    Args:
        audio_file_path (str): The path to the audio file to transcribe.
        model_size (str): The size of the Whisper model to use (e.g., "base", "small", "medium", "large").
        device (str): The device to use for inference ("cpu" or "cuda").
        compute_type (str): The compute type for inference (e.g., "int8", "float16", "int8_float16").

    Returns:
        str: The transcribed text.
    """
    if not os.path.exists(audio_file_path):
        logging.error(f"Audio file not found: {audio_file_path}")
        return ""

    logging.info(f"Loading Whisper model '{model_size}' on {device} with compute type {compute_type}...")
    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logging.info("Model loaded successfully.")
    except Exception as e:
        logging.error(f"Error loading Whisper model: {e}")
        return ""

    logging.info(f"Transcribing audio file: {audio_file_path}...")
    transcribed_segments = []
    try:
        segments, info = model.transcribe(audio_file_path, beam_size=5)
        logging.info(f"Detected language: {info.language} with probability {info.language_probability:.2f}")
        logging.info(f"Transcription complete. Processing segments...")
        for segment in segments:
            transcribed_segments.append(segment.text)
    except Exception as e:
        logging.error(f"Error during transcription: {e}")
        return ""

    transcribed_text = " ".join(transcribed_segments)
    logging.info("Transcription process finished.")
    return transcribed_text

if __name__ == "__main__":
    audio_file = "f:\\New folder\\mainwebs\\callcenter\\voice_assistant_llm-main - Copy\\a4f-local\\output.mp3"
    # You can choose different model sizes, devices, and compute types
    # For CPU, 'int8' is generally recommended for performance.
    # For GPU, 'float16' is generally recommended.
    transcription = transcribe_audio_faster_whisper(audio_file, model_size="base", device="cpu", compute_type="int8")
    if transcription:
        logging.info(f"\nFinal Transcription:\n{transcription}")
    else:
        logging.warning("Transcription failed or returned empty.")