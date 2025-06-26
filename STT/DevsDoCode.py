from a4f_local import A4F
from typing import Optional
import asyncio
import websockets
import json
import base64
import io
import wave
import os
from faster import transcribe_audio_faster_whisper, initialize_whisper_model
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

class SpeechToTextListener:
    def __init__(self, language: str = "en-US", ai_assistant=None):
        self.language = language
        self.active_connections = set()
        self.tts_client = A4F()
        self.is_processing = False
        self.audio_buffer = bytearray()
        
        # Initialize Whisper model and OpenAI model at startup
        print("Initializing models at startup...")
        if not initialize_whisper_model(model_size="base", device="cpu", compute_type="int8"):
            print("Failed to initialize Whisper model!")
            raise RuntimeError("Failed to initialize Whisper model")
        print("Whisper model initialized successfully!")
        
        # Initialize AI assistant
        if ai_assistant:
            print("Initializing OpenAI model...")
            try:
                self.ai_assistant = ai_assistant
                # Warm up the model with a test prompt
                self.ai_assistant.interact_with_llm("Hello")
                print("OpenAI model initialized successfully!")
            except Exception as e:
                print(f"Failed to initialize OpenAI model: {e}")
                raise RuntimeError("Failed to initialize OpenAI model")
        else:
            self.ai_assistant = None

    def save_audio_as_mp3(self, audio_data: bytes, filename: str = "received.mp3") -> str:
        """Save audio data as MP3 file."""
        try:
            print(f"save_audio_as_mp3: Attempting to save audio to {filename}.")
            filepath = os.path.join(os.getcwd(), filename)
            with open(filepath, 'wb') as mp3_file:
                mp3_file.write(audio_data)
            print(f"save_audio_as_mp3: Audio saved as {filepath}, size: {len(audio_data)} bytes")
            return filepath
        except Exception as e:
            print(f"save_audio_as_mp3: Error saving audio file: {e}")
            return ""

    async def process_audio_to_text(self, audio_data: bytes) -> str:
        """Convert raw PCM audio data to text using faster-whisper."""
        try:
            print("process_audio_to_text: Starting audio to text processing.")
            print(f"process_audio_to_text: Processing audio data of size: {len(audio_data)} bytes")
            
            # Save audio as MP3 file
            print("process_audio_to_text: Saving audio as MP3.")
            audio_file = self.save_audio_as_mp3(audio_data, "received.mp3")
            if not audio_file:
                print("process_audio_to_text: Failed to save audio as MP3.")
                return ""
            
            # Use faster-whisper for transcription (model already loaded)
            print("process_audio_to_text: Transcribing audio with pre-loaded faster-whisper.")
            text = transcribe_audio_faster_whisper(audio_file)
            print(f"process_audio_to_text: Transcribed text: {text}")
            
            # Clean up the temporary file
            try:
                os.remove(audio_file)
                print(f"process_audio_to_text: Cleaned up temporary file: {audio_file}")
            except Exception as e:
                print(f"process_audio_to_text: Error cleaning up temporary file: {e}")
                
            print("process_audio_to_text: Audio to text processing completed.")
            return text
        except Exception as e:
            print(f"process_audio_to_text: Error in audio transcription: {e}")
            return ""

    async def text_to_speech(self, text: str, websocket) -> None:
        """Convert text to speech using A4F and send to websocket."""
        try:
            print("text_to_speech: Starting text-to-speech process.")
            print(f"text_to_speech: Type of websocket: {type(websocket)}")
            # First send a status message to inform the client that TTS is in progress
            status_msg = {"type": "status", "message": "Generating speech..."}
            await websocket.send(json.dumps(status_msg))
            print("text_to_speech: Sent 'Generating speech...' status.")
            
            print(f"text_to_speech: Generating audio for text: '{text[:50]}...'")
            # Generate the audio
            audio_bytes = self.tts_client.audio.speech.create(
                model="tts-1",
                input=text,
                voice="onyx"
            )
            print(f"text_to_speech: Audio generated, size: {len(audio_bytes)} bytes.")
            
            # Send the binary audio data
            print(f"text_to_speech: Attributes of websocket: {dir(websocket)}")
            try:
                await websocket.send(audio_bytes)
                print(f"Sent audio response for text: {text}")
                
                # Wait a moment before sending the ready status
                await asyncio.sleep(0.5)
                print("text_to_speech: Waited 0.5 seconds.")
                
                # Send a message to indicate processing is complete
                status_msg = {"type": "status", "message": "Ready for next input"}
                await websocket.send(json.dumps(status_msg))
                print("text_to_speech: Sent 'Ready for next input' status.")
            except (ConnectionClosedOK, ConnectionClosedError) as e:
                print(f"text_to_speech: WebSocket connection closed while sending audio: {e}")
            except Exception as ae:
                print(f"text_to_speech: Unexpected error during websocket send: {ae}. Type of websocket: {type(websocket)}")
                raise ae # Re-raise to ensure the original error is not masked
        except Exception as e:
            print(f"text_to_speech: Error in text-to-speech conversion: {e}")
            error_msg = {"type": "error", "message": "Failed to generate speech"}
            try:
                await websocket.send(json.dumps(error_msg))
                print("text_to_speech: Sent error message due to TTS failure.")
            except (ConnectionClosedOK, ConnectionClosedError) as e:
                print(f"text_to_speech: WebSocket connection closed while sending error message: {e}")

    async def handle_websocket_connection(self, websocket):
        print(f"handle_websocket_connection: Type of websocket received: {type(websocket)}")
        print(f"New WebSocket connection established. Total connections: {len(self.active_connections) + 1}")
        try:
            self.active_connections.add(websocket)
            self.audio_buffer = bytearray()  # Reset buffer for new connection
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')
                    print(f"Received message type: {message_type}")

                    if message_type == 'text_data' and not self.is_processing:
                        try:
                            self.is_processing = True
                            print("handle_websocket_connection: Processing text data.")
                            
                            text = data.get('text')
                            if not text:
                                print("handle_websocket_connection: Error: No text data in message.")
                                error_msg = {"type": "error", "message": "No text data received"}
                                try:
                                    await websocket.send(json.dumps(error_msg))
                                except (ConnectionClosedOK, ConnectionClosedError) as e:
                                    print(f"handle_websocket_connection: WebSocket connection closed while sending error: {e}")
                                self.is_processing = False
                                continue

                            # Process text with AI assistant
                            if self.ai_assistant:
                                try:
                                    print("handle_websocket_connection: Calling interact_with_llm.")
                                    response = self.ai_assistant.interact_with_llm(text)
                                    print(f"handle_websocket_connection: AI response: {response}")
                                    # Send text response first
                                    response_msg = {"type": "response", "message": response}
                                    await websocket.send(json.dumps(response_msg))
                                    # Convert response to speech
                                    await self.text_to_speech(response, websocket)
                                except (ConnectionClosedOK, ConnectionClosedError) as e:
                                    print(f"handle_websocket_connection: WebSocket connection closed: {e}")
                                except Exception as e:
                                    print(f"handle_websocket_connection: Error getting AI response: {e}")
                                    error_msg = {"type": "error", "message": "Failed to get AI response"}
                                    try:
                                        await websocket.send(json.dumps(error_msg))
                                    except (ConnectionClosedOK, ConnectionClosedError) as e:
                                        print(f"handle_websocket_connection: WebSocket connection closed while sending error: {e}")
                            else:
                                status_msg = {"type": "status", "message": "AI assistant not available"}
                                try:
                                    await websocket.send(json.dumps(status_msg))
                                except (ConnectionClosedOK, ConnectionClosedError) as e:
                                    print(f"handle_websocket_connection: WebSocket connection closed while sending status: {e}")
                            
                            self.is_processing = False
                            
                        except Exception as e:
                            print(f"handle_websocket_connection: Error in text_data handler: {e}")
                            error_msg = {"type": "error", "message": "Internal processing error"}
                            try:
                                await websocket.send(json.dumps(error_msg))
                            except (ConnectionClosedOK, ConnectionClosedError) as e:
                                print(f"handle_websocket_connection: WebSocket connection closed while sending error: {e}")
                            self.is_processing = False

                    elif message_type == 'audio_data' and not self.is_processing:
                        try:
                            self.is_processing = True
                            print("handle_websocket_connection: Entered audio_data processing block.")
                            # Send status to client
                            
                            # Decode base64 audio data
                            audio_base64 = data.get('audio_data')
                            if not audio_base64:
                                print("handle_websocket_connection: Error: No audio data in message.")
                                error_msg = {"type": "error", "message": "No audio data received"}
                                try:
                                    await websocket.send(json.dumps(error_msg))
                                except (ConnectionClosedOK, ConnectionClosedError) as e:
                                    print(f"handle_websocket_connection: WebSocket connection closed while sending error: {e}")
                                self.is_processing = False
                                print("handle_websocket_connection: Exiting audio_data processing due to no audio data.")
                                continue

                            # Extract and decode the PCM audio data
                            try:
                                if ',' in audio_base64:
                                    audio_data = base64.b64decode(audio_base64.split(',')[1])
                                else:
                                    audio_data = base64.b64decode(audio_base64)
                                    
                                print(f"handle_websocket_connection: Received complete audio buffer of size: {len(audio_data)} bytes")

                                # Process the complete audio buffer
                                if len(audio_data) > 0:
                                    print("handle_websocket_connection: Calling process_audio_to_text.")
                                    text = await self.process_audio_to_text(audio_data)
                                    print(f"handle_websocket_connection: process_audio_to_text returned: '{text}'.")
                                    if text and text.strip():
                                        print(f"handle_websocket_connection: Transcribed text: '{text}'")
                                        # Process transcribed text but don't send it to frontend
                                        # Get AI response
                                        if self.ai_assistant:
                                            try:
                                                print("handle_websocket_connection: Calling interact_with_llm.")
                                                response = self.ai_assistant.interact_with_llm(text)
                                                print(f"handle_websocket_connection: AI response: {response}")
                                                # Send text response first
                                                response_msg = {"type": "response", "message": response}
                                                await websocket.send(json.dumps(response_msg))
                                                # Convert response to speech
                                                print(f"handle_websocket_connection: Type of websocket before text_to_speech: {type(websocket)}")
                                                print("handle_websocket_connection: Calling text_to_speech.")
                                                await self.text_to_speech(response, websocket)
                                                print("handle_websocket_connection: text_to_speech completed.")
                                            except (ConnectionClosedOK, ConnectionClosedError) as e:
                                                print(f"handle_websocket_connection: WebSocket connection closed: {e}")
                                            except Exception as e:
                                                print(f"handle_websocket_connection: Error getting AI response: {e}")
                                                error_msg = {"type": "error", "message": "Failed to get AI response"}
                                                try:
                                                    await websocket.send(json.dumps(error_msg))
                                                except (ConnectionClosedOK, ConnectionClosedError) as e:
                                                    print(f"handle_websocket_connection: WebSocket connection closed while sending error: {e}")
                                        else:
                                            # No AI assistant, just send a ready status
                                            status_msg = {"type": "status", "message": "Ready for next input"}
                                            try:
                                                await websocket.send(json.dumps(status_msg))
                                            except (ConnectionClosedOK, ConnectionClosedError) as e:
                                                print(f"handle_websocket_connection: WebSocket connection closed while sending status: {e}")
                                    else:
                                        print("handle_websocket_connection: No text was transcribed or text was empty.")
                                        status_msg = {"type": "status", "message": "No speech detected. Please try again."}
                                        try:
                                            await websocket.send(json.dumps(status_msg))
                                        except (ConnectionClosedOK, ConnectionClosedError) as e:
                                            print(f"handle_websocket_connection: WebSocket connection closed while sending status: {e}")
                                else:
                                    print("handle_websocket_connection: Received empty audio data.")
                                    error_msg = {"type": "error", "message": "Empty audio data received"}
                                    try:
                                        await websocket.send(json.dumps(error_msg))
                                    except (ConnectionClosedOK, ConnectionClosedError) as e:
                                        print(f"handle_websocket_connection: WebSocket connection closed while sending error: {e}")
                                        
                            except Exception as e:
                                print(f"handle_websocket_connection: Error decoding/processing audio data: {e}")
                                error_msg = {"type": "error", "message": f"Audio processing failed: {str(e)}"}
                                try:
                                    await websocket.send(json.dumps(error_msg))
                                except (ConnectionClosedOK, ConnectionClosedError) as e:
                                    print(f"handle_websocket_connection: WebSocket connection closed while sending error: {e}")
                            finally:
                                self.is_processing = False
                                print("handle_websocket_connection: Exited audio_data processing block (finally).")
                                
                        except Exception as e:
                            print(f"handle_websocket_connection: Error in audio_data handler (outer try-except): {e}")
                            error_msg = {"type": "error", "message": "Internal processing error"}
                            try:
                                await websocket.send(json.dumps(error_msg))
                            except (ConnectionClosedOK, ConnectionClosedError) as e:
                                print(f"handle_websocket_connection: WebSocket connection closed while sending error: {e}")
                            self.is_processing = False
                            print("handle_websocket_connection: Exited audio_data processing block (outer try-except).")
                            
                except json.JSONDecodeError as e:
                    print(f"handle_websocket_connection: Error decoding JSON message: {e}")
                    error_msg = {"type": "error", "message": "Invalid message format"}
                    try:
                        await websocket.send(json.dumps(error_msg))
                    except (ConnectionClosedOK, ConnectionClosedError) as e:
                        print(f"handle_websocket_connection: WebSocket connection closed while sending error: {e}")
                except Exception as e:
                    print(f"handle_websocket_connection: Error handling message (outer loop): {e}")
                    error_msg = {"type": "error", "message": "Message handling failed"}
                    try:
                        await websocket.send(json.dumps(error_msg))
                    except (ConnectionClosedOK, ConnectionClosedError) as e:
                        print(f"handle_websocket_connection: WebSocket connection closed while sending error: {e}")

        except Exception as e:
            print(f"handle_websocket_connection: WebSocket connection error (outer try-except): {e}")
        finally:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            print(f"handle_websocket_connection: WebSocket connection closed. Active connections: {len(self.active_connections)}")
            try:
                # Always send a graceful close message
                await websocket.send(json.dumps({"type": "status", "message": "Connection closed by server"}))
                await websocket.close(code=1000, reason="Server shutdown")
            except (ConnectionClosedOK, ConnectionClosedError) as e:
                print(f"Error sending close message or closing websocket: {e}")
            except Exception as e:
                print(f"Error sending close message: {e}")

    async def start_websocket_server(self, host="localhost", port=8765):
        """Start the WebSocket server."""
        server = await websockets.serve(self.handle_websocket_connection, host, port)
        print(f"WebSocket server started on ws://{host}:{port}")
        return server

if __name__ == "__main__":
    from rag.AIVoiceAssistant import AIVoiceAssistant

    ai_assistant = AIVoiceAssistant()
    listener = SpeechToTextListener(language="en-IN", ai_assistant=ai_assistant)

    async def main():
        server = await listener.start_websocket_server()
        await server.wait_closed()

    asyncio.run(main())
