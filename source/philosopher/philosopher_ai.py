from pathlib import Path
import threading
import time
from typing import Callable
import pygame
import speech_recognition as sr
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

    def process_wav_and_trigger(
        self, file_path: str, on_user_text_callback=None, on_ai_response_callback=None
    ):
        """
        1. Records user.
        2. Speech to text conversion (Google STT).
        3. Send text to GUI do GUI.
        4. Send text to Gemini -> ElevenLabs -> GUI .

        :param file_path: Path to the voice recording.
        :param on_user_text_callback: Function to pass text feedback.
        :param on_ai_response_callback: Function to pass voice feedback.
        """
        if self.is_speaking:
            print("Mentor is speaking, pay attention now.")
            return

        self.is_speaking = True

        def _listen_thread():
            recognizer: sr.Recognizer = sr.Recognizer()

            try:
                with sr.AudioFile(file_path) as source:
                    audio_data = recognizer.record(source)

                # language='pl-PL' for polish, 'en-US' for english
                user_text: str = recognizer.recognize_google(
                    audio_data, language="en-us"
                )
                if on_user_text_callback:
                    try:
                        on_user_text_callback(user_text)
                    except Exception as e:
                        print(f"User callback error: {e}")

                ai_advice: str = self.brain.generate_stoic_advice(
                    user_context=user_text
                )
                print(f"AI advice: {ai_advice}")

                if on_ai_response_callback:
                    try:
                        on_ai_response_callback(ai_advice)
                    except Exception as e:
                        print(f"Błąd callbacka AI: {e}")

                self.voice.speak(ai_advice)
                time.sleep(3.0)

            except sr.WaitTimeoutError:
                print("Timeout: Could hear you.")
            except sr.UnknownValueError:
                print("Could not understand you.")
            except sr.RequestError as e:
                print(f"No connection to Google API: {e}")
            except Exception as e:
                print(f"Critical mic audio error: {e}")
            finally:
                self.is_speaking = False
                print("End listening.")

        threading.Thread(target=_listen_thread).start()
