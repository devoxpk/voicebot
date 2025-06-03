"""
Author: Devs Do Code (Sree)
Project: Realtime Speech to Text Listener
Description: A Python script that uses Selenium to interact with a website and listen to user input & print them in real time.
"""

from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
# import os

class SpeechToTextListener:
    """A class for performing speech-to-text using a web-based service."""

    def __init__(
            self, 
            # website_path: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), r"ENGINE\STT\src\index.html"),
            website_path: str = "https://realtime-stt-devs-do-code.netlify.app/", 
            language: str = "hi-IN",
            wait_time: int = 10):
        
        """Initializes the STT class with the given website path and language."""
        self.website_path = website_path
        self.language = language
        self.chrome_options = Options()
        self.chrome_options.add_argument("--use-fake-ui-for-media-stream")
        self.chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
        # self.chrome_options.add_argument("--headless=new") # Commented out to make browser visible
        # Use ChromeDriverManager to automatically handle driver compatibility
        service = Service(ChromeDriverManager().install())
        self.driver = None
        self.service = service
        self._initialize_driver()
        self.wait = WebDriverWait(self.driver, wait_time)
        print("Made By Abuzar")
        print("Driver initialized.")

    def _initialize_driver(self):
        if self.driver is None or not self.driver.service.is_connectable():
            print("Driver not connected or not initialized. Attempting to re-initialize driver.")
            if self.driver:
                try:
                    self.driver.quit()
                    print("Existing driver quit successfully.")
                except Exception as e:
                    print(f"Error quitting existing driver: {e}")
            self.driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
            print("Driver re-initialized.")

    def stream(self, content: str):
        """Prints the given content to the console with a yellow color, overwriting previous output, with "speaking..." added."""
        print("\033[96m\rUser Speaking: \033[93m" + f" {content}", end='', flush=True)

    def get_text(self) -> str:
        """Retrieves the transcribed text from the website."""
        return self.driver.find_element(By.ID, "convert_text").text

    def select_language(self):
        """Selects the language from the dropdown using JavaScript."""
        self.driver.execute_script(
            f"""
            var select = document.getElementById('language_select');
            select.value = '{self.language}';
            var event = new Event('change');
            select.dispatchEvent(event);
            """
        )

    def verify_language_selection(self):
        """Verifies if the language is correctly selected."""
        language_select = self.driver.find_element(By.ID, "language_select")
        selected_language = language_select.find_element(By.CSS_SELECTOR, "option:checked").get_attribute("value")
        return selected_language == self.language

    def main(self, retry_count: int = 0) -> Optional[str]:
        """Performs speech-to-text conversion and returns the transcribed text."""
        print(f"Entering main method (retry_count: {retry_count})")
        if retry_count >= 3:
            print("Failed to initialize recording after multiple attempts")
            return None
            

        try:
            # Check if we're already on the correct page
            current_url = self.driver.current_url
            if not current_url or not current_url.startswith(self.website_path):
                print("Reloading page due to URL mismatch or error.")
                print(f"Loading page: {self.website_path}")
            self.driver.get(self.website_path)
        except Exception as e:
            print(f"Error checking current URL: {e}. Reloading page.")
            print(f"Loading page: {self.website_path}")
            self.driver.get(self.website_path)
        
        try:
            # Wait for and verify recording button state
            record_button = self.wait.until(EC.presence_of_element_located((By.ID, "click_to_record")))
            is_recording = self.driver.find_element(By.ID, "is_recording")
            
            # If not already recording, set up and start recording
            if not is_recording.text.startswith("Recording: True"):
                # Ensure the dropdown options are fully loaded before selecting
                self.wait.until(EC.presence_of_element_located((By.ID, "language_select")))
                
                # Select the language using JavaScript
                print(f"Attempting to select language: {self.language}")
                self.select_language()

                # Verify the language selection
                if not self.verify_language_selection():
                    print(f"Error: Failed to select the correct language. Selected: {self.verify_language_selection():}, Expected: {self.language}")
                    return None
                print("Language selected successfully.")

                print("Clicking record button.")
                record_button.click()
                print("Record button clicked.")
        except Exception as e:
            print(f"Error setting up recording: {e}. Reloading page and retrying.")
            # If there's any error in setup, reload the page and try again
            print("Reloading page due to URL mismatch or error.")
            self.driver.get(self.website_path)
            return self.main(retry_count + 1)

        is_recording = self.wait.until(
            EC.presence_of_element_located((By.ID, "is_recording"))
        )

        print("\033[94m\rListening...", end='', flush=True)
        while is_recording.text.startswith("Recording: True"):
            text = self.get_text()
            if text:
                self.stream(text)
            is_recording = self.driver.find_element(By.ID, "is_recording")

        return self.get_text()

    def listen(self, prints: bool = False) -> Optional[str]:
        """Starts the listening process by navigating to the website, selecting the desired language, and
            initiating speech-to-text conversion. The function returns the transcribed text if the
            listening process completes successfully.
        """
        print("Entering listen method.")
        while True:
            result = self.main()
            if result and len(result) != 0:
                print("\r" + " " * (len(result) + 16) + "\r", end="", flush=True)
                if prints: print("\033[92m\rYOU SAID: " + f"{result}\033[0m\n")
                break
        return result

if __name__ == "__main__":
    listener = SpeechToTextListener(language="en-IN")  # You can specify the desired language here
    speech = listener.listen()
    print("FINAL EXTRACTION: ", speech)
