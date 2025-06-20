import os
import json
import warnings
from dotenv import load_dotenv
import google.generativeai as genai
from functools import lru_cache

warnings.filterwarnings("ignore")

# Load environment variables and configure Gemini
load_dotenv()
GEMINI_API_KEY = "AIzaSyD0GidvZyvhWOM4zPXdT0KtOMER9ZGTBjs"
genai.configure(api_key=GEMINI_API_KEY)

class AIVoiceAssistant:
    def __init__(self):
        print("\nInitializing AI Voice Assistant...")
        self._data_file = "data.json"
        self.model = genai.GenerativeModel(model_name='gemini-2.0-flash', generation_config={'temperature': 0.9})

        self.chat = self.model.start_chat(history=[])
        print("Gemini model initialized successfully.")
        self._initialize_assistant()

    def _initialize_assistant(self):
        print("Configuring assistant with initial prompt...")
        context = self.load_context()
        full_prompt = self._prompt
        self.chat.send_message(full_prompt)
        print("Assistant configuration completed with menu context.")

    @lru_cache(maxsize=1)
    def load_context(self):
        print("\nLoading restaurant context...")
        try:
            with open(self._data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                context = data.get('context', '')
            print("Restaurant context loaded successfully!")
            return context
        except Exception as e:
            print(f"Error while loading context: {e}")
            return ""

    @lru_cache(maxsize=100)
    def interact_with_llm(self, customer_query):
        print("\nProcessing customer query...")
        try:
            # Send the query to Gemini
            response = self.chat.send_message(customer_query)
            answer = response.text
            print("Response generated successfully.")
            return answer
        except Exception as e:
            print(f"Error while processing query: {e}")
            return "I apologize, but I'm having trouble processing your request at the moment."

    @property
    def _prompt(self):
        return """
            You are a professional AI Assistant capable of answering questions on various subjects, including science, and general queries.
            Your goal is to provide helpful and informative responses.
            
            If you don't know the answer, state that you don't know. Do not make up information.
            Provide clear and concise answers. Maintain a friendly and informative tone.
            """
