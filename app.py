import os
import json
import time
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from rag.AIVoiceAssistant import AIVoiceAssistant

from STT.DevsDoCode import SpeechToTextListener
from voice_service import play_text_to_speech, stop_audio_processor, init_audio

print("\nInitializing AI Voice Assistant System...")
ai_assistant = AIVoiceAssistant()
# Load restaurant context
context = ai_assistant.load_context()
print("System initialization completed.\n")

def main():
    print("Entering main function.")
    try:
        # Initialize audio system
        if not init_audio():
            print("Failed to initialize audio system")
            return

        # Initialize speech-to-text listener
        print("Initializing SpeechToTextListener in app.py")
        stt_listener = SpeechToTextListener(language="en-IN")
        
        print("\nAI Assistant is ready! Listening for your voice...")
        print("Entering main loop.")
        while True:
            try:
                # Listen for user speech
                user_input = stt_listener.listen(prints=True)
                
                if user_input:
                    print(f"User input detected: {user_input}")
                    if user_input.lower() != 'exit':
                        # Get response from AI assistant
                        response = ai_assistant.interact_with_llm(user_input)
                        if response:
                            print(f"AI Assistant Response: {response}")
                            # Convert response to speech
                            play_text_to_speech(response, language='en', emotion='happy')
                            
                    elif user_input.lower() == 'exit':
                        print("Exit command received. Stopping AI Assistant.")
                        break
            except (StaleElementReferenceException, WebDriverException) as e:
                print(f"\nSpeech service error: {e}. Attempting to continue...")
                time.sleep(1) # Small delay before retrying
            except Exception as e:
                print(f"\nAn unexpected error occurred: {e}. Attempting to continue...")
                time.sleep(1) # Small delay before retrying
                
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Stopping AI Assistant...")
    finally:
        print("Cleaning up resources.")
        # Clean up resources
        stop_audio_processor()
        if 'stt_listener' in locals():
            print("Quitting STT listener driver.")
            stt_listener.driver.quit()

if __name__ == "__main__":
    main()
