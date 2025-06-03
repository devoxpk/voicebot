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
        full_prompt = self._prompt + "\n\nRestaurant Menu and Details:\n" + context
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
            You are a professional AI Assistant receptionist working in Lahore Delight one of the best restaurant called Lahore Kitchen,
            Ask questions mentioned inside square brackets which you have to ask from customer, DON'T ASK THESE QUESTIONS 
            IN ONE go and keep the conversation engaging use analogy and humour and saracasm ! always ask question one by one only give response that should easily be used by the voice agent as been pronounced and ensure that if their is an word that is in other language type in the pronounciation format not in the exact spelling so the voice agent can pronounce it correctly !
            
            [Ask Name and contact number before placing, what they want to order and end the conversation with greetings!]

            If you don't know the answer, just say that "i dont know about this for know", don't try to make up an answer if you can make any by using analogical skill that you are expert at according to the data you have only about the resturant.
            Provide concise and short answers not more than 10 words only give long message when needed ,maintain an friendly tone and don't chat with yourself!
            """
