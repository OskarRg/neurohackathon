from pathlib import Path
import threading
import time
from typing import Callable
import pygame
from source.philosopher.gemini_brain import GeminiBrain
from source.philosopher.utils import CONVERSATION_STARTER_PATH, GONG_SOUND_PATH
from source.philosopher.voice_engine import VoiceEngine


class PhilosopherAI:
    def __init__(self) -> None:
        """
        This class connects brain and voice og the duck.
        Manages threading and cooldown not to slow down the application.
        """
        self.brain: GeminiBrain = GeminiBrain()
        self.voice: VoiceEngine = VoiceEngine()

        self.is_speaking: bool = False
        self.last_intervention_time: int = 0
        self.cooldown_seconds = 60  # Np. 60 seconds timeout between

        try:
            self.gong: pygame.mixer.Sound | None = pygame.mixer.Sound(GONG_SOUND_PATH)
        except Exception:
            self.gong: pygame.mixer.Sound | None = None

    def trigger_intervention(
        self,
        user_context: str,
        on_response_callback: Callable | None = None,
        force=False,
    ):
        """
        Main pipeline that is run in main.py.
        Decides when to run the intervention in the background.
        :param force: If True, ignore cooldown.
        """
        current_time: float = time.time()

        if self.is_speaking:
            return

        if not force:
            if current_time - self.last_intervention_time < self.cooldown_seconds:
                return  # Too early for another request

        self.last_intervention_time: float = current_time
        self.is_speaking = True

        thread: threading.Thread = threading.Thread(
            target=self._intervention_process,
            args=(
                user_context,
                on_response_callback,
            ),
        )
        thread.start()

    def _intervention_process(self, user_context: str, callback: Callable | None):
        """
        The code that runs the AI logic in the background.
        Creates response for the user input, and converts it into `.mp3` file.
        """
        try:
            advice: str = self.brain.generate_stoic_advice(user_context=user_context)
            print("Advice: ", advice)
            if callback:
                try:
                    callback(advice)
                except Exception as e:
                    print(f"Callback to GUI error: {e}")

            self.voice.speak(advice)
            time.sleep(3.0)
        except Exception as e:
            print(f"AI module error: {e}")
        finally:
            self.is_speaking = False

    def say_specific_phrase(self, text: str, on_response_callback=None):
        """
        Sends the text to GUI and plays the audio.
        Can be used for scripted events (e.g., standard conversation started.).

        :param text:
        """
        self.is_speaking = True  # not needed

        def _speak_thread():
            try:
                if on_response_callback:
                    on_response_callback(text)
                if self.gong:
                    self.gong.play()
                    time.sleep(1.5)

                audio_path: Path = Path(CONVERSATION_STARTER_PATH)
                if audio_path.exists():
                    try:
                        if pygame.mixer.music.get_busy():
                            pygame.mixer.music.stop()
                        try:
                            pygame.mixer.music.unload()
                        except AttributeError:
                            pass

                        pygame.mixer.music.load(CONVERSATION_STARTER_PATH)
                        pygame.mixer.music.play()

                        while pygame.mixer.music.get_busy():
                            time.sleep(0.1)
                    except Exception as e:
                        print(f"Could not play distress_speech: {e}")
                else:
                    print(f"Could not find audio: {audio_path}")
            finally:
                self.is_speaking = False

        thread = threading.Thread(target=_speak_thread)
        thread.start()
