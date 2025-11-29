import os
from typing import Iterator
import pygame
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from source.philosopher.utils import STOIC_VOICE_ID

load_dotenv()

class VoiceEngine:
    def __init__(self) -> None:
        """
        Initialize ElevenLabs client and  Pygame audio mixer.
        """
        api_key: str = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError(" Missing key `ELEVENLABS_API_KEY` in the file `.env`")
        
        self.client: ElevenLabs = ElevenLabs(api_key=api_key)
        self.voice_id: str = STOIC_VOICE_ID

        try:
            pygame.mixer.init()
        except pygame.error as e:
            print(f"Error initializing audio: {e}")

    def speak(self, text: str) -> None:
        """
        Converts text to audio and plays it.

        :param text: Text to be converted.
        """
        if not text:
            return

        try:
            audio_generator: Iterator[bytes] = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id="eleven_turbo_v2_5" 
            )
            print(audio_generator)
            print("typ", type(audio_generator))
            temp_file: str = "temp_speech.mp3"
            
            with open(temp_file, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)
            self._play_file(temp_file)

        except Exception as e:
            print(f"Error connected to ElevenLabs: {e}")

    def _play_file(self, file_path):
        """
        Plays out the audio.
        
        :param file_path: Audio file path.
        """
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()

            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
        except Exception as e:
            print(f"Error while playing audio: {e}")

if __name__ == "__main__":
    engine: VoiceEngine = VoiceEngine()
    engine.speak("As I said, never give up.")
