import os
import asyncio
from rag.AIVoiceAssistant import AIVoiceAssistant
from STT.DevsDoCode import SpeechToTextListener
from voice_service import init_audio, stop_audio_processor
import multiprocessing

multiprocessing.set_start_method('spawn', force=True)

print("\nInitializing AI Voice Assistant System...")

# Initialize audio system
if not init_audio():
    print("Failed to initialize audio system")
    exit(1)

print("System initialization completed.\n")

async def main():
    # Initialize AI assistant inside main
    ai_assistant = AIVoiceAssistant()
    context = ai_assistant.load_context()

    # Initialize speech-to-text listener inside main
    print("Initializing SpeechToTextListener with WebSocket integration")
    stt_listener = SpeechToTextListener(
        language="en-IN",
        ai_assistant=ai_assistant,
    )
    try:
        server = await stt_listener.start_websocket_server()
        await server.wait_closed()
    finally:
        print("\nCleaning up resources...")
        stop_audio_processor()
        if hasattr(stt_listener, 'driver') and stt_listener.driver:
            print("Quitting STT listener driver")
            stt_listener.driver.quit()
if __name__ == "__main__":
    multiprocessing.freeze_support()
    asyncio.run(main())
