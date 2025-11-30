import os
import google.generativeai as genai
from google.generativeai.types.generation_types import GenerateContentResponse
from dotenv import load_dotenv

from source.philosopher.utils import (
    MODEL_NAME,
    SYSTEM_INSTRUCTION,
)

load_result = load_dotenv()


class GeminiBrain:
    def __init__(self) -> None:
        """
        Initialize connection with z Google Gemini.
        """
        api_key: str = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Missing key `GEMINI_API_KEY` in the file `.env`")

        genai.configure(api_key=api_key)

        self.model: genai.GenerativeModel = genai.GenerativeModel(
            model_name=MODEL_NAME, system_instruction=SYSTEM_INSTRUCTION
        )
        self.chat = self.model.start_chat(history=[])

    def generate_stoic_advice(self, user_context="I am stressed about my job.") -> str:
        """
        Sends a question to the Gemini model and returns a response.

        :param user_context: Text input from the user.
        """
        try:
            response: GenerateContentResponse = self.chat.send_message(user_context)
            raw_text: str = response.text.strip()
            clean_text: str = (
                raw_text.replace("*", "").replace("`", "").replace("_", "")
            )
            return clean_text

        except Exception as e:
            print(f"Gemini Error: {e}")
            return "Patience. The API is silent, but your mind must remain clear even in the time of doubt."


if __name__ == "__main__":
    """
    Use `.\.venv\Scripts\python.exe -m source.philosopher.gemini_brain` to run the script below.
    """
    brain: GeminiBrain = GeminiBrain()
    print(brain.generate_stoic_advice("My code keeps faulting!"))
