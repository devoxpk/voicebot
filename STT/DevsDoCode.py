from a4f_local import A4F
from typing import Optional
import asyncio
import websockets
import json
import base64
import io
import wave
import os
from faster import transcribe_audio_faster_whisper

class SpeechToTextListener:
    def __init__(self, language: str = "en-US", ai_assistant=None):
        self.language = language
        self.ai_assistant = ai_assistant
        self.active_connections = set()
        self.tts_client = A4F()
        self.is_processing = False
        self.audio_buffer = bytearray()

    def save_audio_as_mp3(self, audio_data: bytes, filename: str = "received.mp3") -> str:
        """Save audio data as MP3 file."""
        try:
            filepath = os.path.join(os.getcwd(), filename)
            with open(filepath, 'wb') as mp3_file:
                mp3_file.write(audio_data)
            print(f"Audio saved as {filepath}, size: {len(audio_data)} bytes")
            return filepath
        except Exception as e:
            print(f"Error saving audio file: {e}")
            return ""

    async def process_audio_to_text(self, audio_data: bytes) -> str:
        """Convert raw PCM audio data to text using faster-whisper."""
        try:
            print(f"Processing audio data of size: {len(audio_data)} bytes")
            
            # Save audio as MP3 file
            audio_file = self.save_audio_as_mp3(audio_data, "received.mp3")
            if not audio_file:
                return ""
            
            # Use faster-whisper for transcription
            text = transcribe_audio_faster_whisper(audio_file)
            print(f"Transcribed text: {text}")
            
            # Clean up the temporary file
            try:
                os.remove(audio_file)
            except:
                pass
                
            return text
        except Exception as e:
            print(f"Error in audio transcription: {e}")
            return ""

    async def text_to_speech(self, text: str, websocket) -> None:
        """Convert text to speech using A4F and send to websocket."""
        try:
            audio_bytes = self.tts_client.audio.speech.create(
                model="tts-1-hd",
                input=text,
                voice="onyx"
            )
            # if websocket.open:
            await websocket.send(audio_bytes)
            print(f"Sent audio response for text: {text}")
            
            # Send a message to indicate processing is complete
            status_msg = {"type": "status", "message": "Ready for next input"}
            await websocket.send(json.dumps(status_msg))
        except Exception as e:
            print(f"Error in text-to-speech conversion: {e}")
            error_msg = {"type": "error", "message": "Failed to generate speech"}
            if websocket.open:
                await websocket.send(json.dumps(error_msg))

    async def handle_websocket_connection(self, websocket):
        print(f"New WebSocket connection established. Total connections: {len(self.active_connections) + 1}")
        try:
            self.active_connections.add(websocket)
            self.audio_buffer = bytearray()  # Reset buffer for new connection
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')
                    print(f"Received message type: {message_type}")

                    if message_type == 'audio_data' and not self.is_processing:
                        try:
                            self.is_processing = True
                            # Send status to client
                            status_msg = {"type": "status", "message": "Processing audio..."}
                            # if websocket.open:
                            await websocket.send(json.dumps(status_msg))
                                
                            # Decode base64 audio data
                            audio_base64 = data.get('audio_data')
                            if not audio_base64:
                                print("Error: No audio data in message")
                                error_msg = {"type": "error", "message": "No audio data received"}
                                # if websocket.open:
                                await websocket.send(json.dumps(error_msg))
                                self.is_processing = False
                                continue

                            # Extract and decode the PCM audio data
                            try:
                                if ',' in audio_base64:
                                    audio_data = base64.b64decode(audio_base64.split(',')[1])
                                else:
                                    audio_data = base64.b64decode(audio_base64)
                                    
                                print(f"Received complete audio buffer of size: {len(audio_data)} bytes")

                                # Process the complete audio buffer
                                if len(audio_data) > 0:
                                    text = await self.process_audio_to_text(audio_data)
                                    if text and text.strip():
                                        print(f"Transcribed text: '{text}'")
                                        # Get AI response
                                        if self.ai_assistant:
                                            try:
                                                response = self.ai_assistant.interact_with_llm(text)
                                                print(f"AI response: {response}")
                                                # Convert response to speech
                                                await self.text_to_speech(response, websocket)
                                            except Exception as e:
                                                print(f"Error getting AI response: {e}")
                                                error_msg = {"type": "error", "message": "Failed to get AI response"}
                                                # if websocket.open:
                                                await websocket.send(json.dumps(error_msg))
                                        else:
                                            # No AI assistant, just echo the transcription
                                            status_msg = {"type": "status", "message": f"Transcribed: {text}"}
                                            # if websocket.open:
                                            await websocket.send(json.dumps(status_msg))
                                    else:
                                        print("No text was transcribed or text was empty")
                                        status_msg = {"type": "status", "message": "No speech detected. Please try again."}
                                        # if websocket.open:
                                        await websocket.send(json.dumps(status_msg))
                                else:
                                    print("Received empty audio data")
                                    error_msg = {"type": "error", "message": "Empty audio data received"}
                                    # if websocket.open:
                                    await websocket.send(json.dumps(error_msg))
                                        
                            except Exception as e:
                                print(f"Error decoding/processing audio data: {e}")
                                error_msg = {"type": "error", "message": f"Audio processing failed: {str(e)}"}
                                # if websocket.open:
                                await websocket.send(json.dumps(error_msg))
                            finally:
                                self.is_processing = False
                                
                        except Exception as e:
                            print(f"Error in audio_data handler: {e}")
                            error_msg = {"type": "error", "message": "Internal processing error"}
                            # if websocket.open:
                            await websocket.send(json.dumps(error_msg))
                            self.is_processing = False
                            
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON message: {e}")
                    error_msg = {"type": "error", "message": "Invalid message format"}
                    # if websocket.open:
                    await websocket.send(json.dumps(error_msg))
                except Exception as e:
                    print(f"Error handling message: {e}")
                    error_msg = {"type": "error", "message": "Message handling failed"}
                    # if websocket.open:
                    await websocket.send(json.dumps(error_msg))

        except Exception as e:
            print(f"WebSocket connection error: {e}")
        finally:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            print(f"WebSocket connection closed. Active connections: {len(self.active_connections)}")

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
