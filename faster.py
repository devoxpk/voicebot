from faster_whisper import WhisperModel
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global model instance
_whisper_model = None

def initialize_whisper_model(model_size="base", device="cpu", compute_type="int8"):
    """
    Initialize the Whisper model once at startup.
    
    Args:
        model_size (str): The size of the Whisper model to use (e.g., "base", "small", "medium", "large").
        device (str): The device to use for inference ("cpu" or "cuda").
        compute_type (str): The compute type for inference (e.g., "int8", "float16", "int8_float16").
    
    Returns:
        bool: True if model loaded successfully, False otherwise.
    """
    global _whisper_model
    
    logging.info(f"Initializing Whisper model '{model_size}' on {device} with compute type {compute_type}...")
    try:
        _whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logging.info("Whisper model initialized successfully.")
        return True
    except Exception as e:
        logging.error(f"Error initializing Whisper model: {e}")
        _whisper_model = None
        return False

def transcribe_audio_faster_whisper(audio_file_path):
    """
    Transcribes an audio file using the pre-loaded Faster Whisper model.

    Args:
        audio_file_path (str): The path to the audio file to transcribe.

    Returns:
        str: The transcribed text.
    """
    global _whisper_model
    
    if _whisper_model is None:
        logging.error("Whisper model not initialized. Call initialize_whisper_model() first.")
        return ""
    
    if not os.path.exists(audio_file_path):
        logging.error(f"Audio file not found: {audio_file_path}")
        return ""

    logging.info(f"Transcribing audio file: {audio_file_path}...")
    transcribed_segments = []
    try:
        segments, info = _whisper_model.transcribe(audio_file_path, beam_size=5)
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
    
    # Initialize model first
    if initialize_whisper_model(model_size="base", device="cpu", compute_type="int8"):
        # Now transcribe using the pre-loaded model
        transcription = transcribe_audio_faster_whisper(audio_file)
        if transcription:
            logging.info(f"\nFinal Transcription:\n{transcription}")
        else:
            logging.error("Transcription failed.")
    else:
        logging.error("Failed to initialize Whisper model.")