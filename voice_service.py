import io
import pygame
import threading
import queue
from gtts import gTTS
from STT.DevsDoCode import SpeechToTextListener
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
# Global audio queue for async processing
audio_queue = queue.Queue()
_audio_thread = None
_is_processing = False
_stt_listener = None
_speech_detected = False
_stt_lock = threading.Lock()  # Add lock for thread safety

def init_audio():
    print("Initializing audio system.")
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=24000)
        return True
    except Exception as e:
        print(f"Error initializing audio: {e}")
        return False

def _check_for_speech():
    print("Checking for speech.")
    global _speech_detected, _stt_listener
    try:
        with _stt_lock:
            if _stt_listener is None:
                print("Initializing SpeechToTextListener in voice_service.py")
                _stt_listener = SpeechToTextListener(language="en-IN")
            else:
                print("SpeechToTextListener already initialized, reusing instance.")
            try:
                # Verify driver is valid before attempting to get text
                if not _stt_listener.driver or not _stt_listener.driver.service.is_connectable():
                    print("Driver is not connected, reinitializing listener.")
                    _stt_listener = None
                    return False
                
                text = _stt_listener.get_text()
                if text and len(text.strip()) > 0:
                    _speech_detected = True
                    return True
            except (StaleElementReferenceException, WebDriverException, ValueError) as e:
                print(f"Speech detection error: {e}. Attempting to continue with existing listener.")
                try:
                    # Try to verify if the driver is still valid
                    if _stt_listener.driver and _stt_listener.driver.current_url:
                        print("Driver is still valid, continuing with existing instance.")
                    else:
                        print("Driver is invalid, reinitializing listener.")
                        _stt_listener = None
                except:
                    print("Error checking driver state, reinitializing listener.")
                    _stt_listener = None
    except Exception as e:
        print(f"Unexpected error in speech detection: {e}")
    return False

def _process_audio_queue():
    print("Processing audio queue.")
    global _is_processing, _speech_detected
    while _is_processing:
        try:
            fp = audio_queue.get_nowait()
            if fp:
                try:
                    pygame.mixer.music.load(fp)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy() and not _speech_detected:
                        try:
                            with _stt_lock:
                                if _stt_listener and _stt_listener.driver and _stt_listener.driver.service.is_connectable():
                                    if not _check_for_speech():
                                        pygame.time.Clock().tick(30)
                                else:
                                    # Skip speech check during audio playback if listener is invalid
                                    pygame.time.Clock().tick(30)
                        except Exception as e:
                            print(f"Error checking speech during audio playback: {e}")
                            pygame.time.Clock().tick(30)
                    if _speech_detected:
                        pygame.mixer.music.stop()
                        _speech_detected = False
                finally:
                    fp.close()
                    audio_queue.task_done()
        except queue.Empty:
            pygame.time.Clock().tick(10)
        except Exception as e:
            print(f"Error in audio processing: {e}")

def stop_audio_processor():
    print("Stopping audio processor.")
    global _is_processing, _stt_listener
    _is_processing = False
    with _stt_lock:
        if _stt_listener:
            try:
                if _stt_listener.driver:
                    print("Closing browser.")
                    _stt_listener.driver.quit()
                    print("Browser closed successfully.")
            except Exception as e:
                print(f"Error closing browser: {e}")
            finally:
                _stt_listener = None
                print("STT listener instance cleared.")
    if _audio_thread:
        print("Waiting for audio thread to finish.")
        _audio_thread.join()
        print("Audio thread finished.")

def start_audio_processor():
    print("Starting audio processor.")
    global _audio_thread, _is_processing
    if not _audio_thread or not _audio_thread.is_alive():
        _is_processing = True
        _audio_thread = threading.Thread(target=_process_audio_queue, daemon=True)
        _audio_thread.start()
        print("Audio processor thread started.")

async def play_text_to_speech(text, websocket, language='en', emotion='happy'):
    print(f"Generating speech for text: {text[:50]}...")
    if not init_audio():
        error_msg = "Failed to initialize audio system"
        print(error_msg)
        if websocket and websocket.open:
            await websocket.send(error_msg)
        return
    
    try:
        # Configure speech parameters
        tts_speed = True  # Default to normal speed
        if emotion == 'happy' or emotion == 'angry':
            tts_speed = False  # Faster speech
        
        print(f"Generating speech with parameters: language={language}, speed={tts_speed}")
        # Create gTTS instance and generate speech
        tts = gTTS(text=text, lang=language, slow=tts_speed)
        
        # Save speech to BytesIO buffer
        fp = io.BytesIO()
        print("Converting text to speech...")
        tts.write_to_fp(fp)
        
        # Get the audio data as bytes
        fp.seek(0)
        audio_data = fp.read()
        print(f"Generated audio data size: {len(audio_data)} bytes")
        
        # Send audio data to frontend if WebSocket is still open
        if websocket and websocket.open:
            print("Sending audio data to frontend...")
            try:
                await websocket.send(audio_data)
                print("Audio data sent successfully")
            except Exception as e:
                print(f"Error sending audio data through WebSocket: {e}")
                raise
        else:
            print("WebSocket connection is not available or closed")
            return
        
        # Clean up
        fp.close()
        print("Audio generation and transmission completed")
        
    except Exception as e:
        error_msg = f"Error generating audio: {e}"
        print(error_msg)
        if websocket and websocket.open:
            try:
                await websocket.send(error_msg)
            except Exception as ws_error:
                print(f"Error sending error message through WebSocket: {ws_error}")
        init_audio()  # Try to reinitialize audio if error occurs
