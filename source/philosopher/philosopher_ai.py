import threading
import time
import pygame
from source.philosopher.gemini_brain import GeminiBrain
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
            pygame.mixer.Sound("assets/gong_sound.mp3")
        except Exception:
            self.gong = None

    def trigger_intervention(self, force=False):
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

        thread: threading.Thread = threading.Thread(target=self._intervention_process)
        thread.start()

    def _intervention_process(self):
        """
        The code that runs the AI logic in the background.
        Creates response for the user input, and converts it into `.mp3` file.
        """
        try:
            if self.gong:
                self.gong.play()
                time.sleep(2)

            advice: str = self.brain.generate_stoic_advice()

            self.voice.speak(advice)

        except Exception as e:
            print(f"AI module error: {e}")
        finally:
            self.is_speaking = False
