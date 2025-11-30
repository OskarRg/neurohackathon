import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from config import CONVERSATION_STARTER, AppStateDict
from source.duck_widget.duck_widget import StoicDuckPro, dev_hotkeys
from source.neuro_reader.eeg_service import EEGService
from source.neuro_reader.utils import EEGDataDict
from source.neuro_reader.mock_service import MockEEGService
from source.philosopher.philosopher_ai import PhilosopherAI


class Bridge(QObject):
    ai_response_ready = pyqtSignal(str)
    user_speech_ready = pyqtSignal(str)


def main():
    app: QApplication = QApplication(sys.argv)

    duck_window: StoicDuckPro = StoicDuckPro()

    eeg_service = EEGService()
    # eeg_service: MockEEGService = MockEEGService()  #  used for testing
    eeg_service.start()

    philosopher: PhilosopherAI = PhilosopherAI()
    bridge: Bridge = Bridge()

    app_state: AppStateDict = {"stoic_mode_active": False, "conversation_locked": False}

    def on_ai_thought_callback(text_response: str) -> None:
        """
        Brain thread finished and emits signal to GUI.

        :param text_response: Text response from the philosopher module.
        """
        bridge.ai_response_ready.emit(text_response)

    def update_gui_chat(text: str):
        """
        Updates GUI from main pipeline.

        :param text: Text response from philosopher module.
        """
        duck_window.chat_area.add_response(text)
        duck_window.chat_area.set_locked(False)
        # TODO Add length based gif animation
        # duck_window._voice_effect(duration=len(text)*0.08)

    bridge.ai_response_ready.connect(update_gui_chat)

    try:
        duck_window.chat_area.message_sent.disconnect()
    except Exception:
        pass

    def handle_user_input_from_gui(user_text):
        """
        Trigger philosopher intervention with callback.

        :param user_text: User input to the chat.
        """
        duck_window.chat_area.set_locked(True)

        def on_ai_reply_to_user(text):
            on_ai_thought_callback(text)

            if app_state["conversation_locked"]:
                print("My job here is done. I go back monitoring EEG.")
                app_state["conversation_locked"] = False

        philosopher.trigger_intervention(
            user_context=user_text, on_response_callback=on_ai_reply_to_user, force=True
        )

    duck_window.chat_area.message_sent.connect(handle_user_input_from_gui)

    def show_user_speech_bubble(text):
        print(f"[GUI] Speech: {text}")
        duck_window.chat_area.add_user_response(f"{text}")

    bridge.user_speech_ready.connect(show_user_speech_bubble)

    def handle_recorded_audio(file_path: str):
        print(f"Got audio file from GUI: {file_path}")

        duck_window.chat_area.set_locked(True)

        def on_ai_voice_finish(text):
            bridge.ai_response_ready.emit(text)
            if app_state["conversation_locked"]:
                app_state["conversation_locked"] = False

        print("Starting the philosopher...")
        philosopher.process_wav_and_trigger(
            file_path=file_path,
            on_user_text_callback=lambda txt: bridge.user_speech_ready.emit(txt),
            on_ai_response_callback=on_ai_voice_finish,
        )
        print("finished this")

    duck_window.chat_area.mic_requested.connect(handle_recorded_audio)

    def polling_loop():
        data: EEGDataDict = eeg_service.get_data()

        raw_ratio: float = data.get("stress_index", 0.0)
        normalized_stress: float = min(raw_ratio / 3.0, 1.0)

        stress_to_show_in_gui: float = normalized_stress

        if app_state["conversation_locked"] or philosopher.is_speaking:
            stress_to_show_in_gui = max(normalized_stress, 0.95)
        dev_hotkeys(duck_window)
        duck_window.update_stress(stress_to_show_in_gui)

        if app_state["conversation_locked"]:
            return

        if normalized_stress > 0.8 and not app_state["stoic_mode_active"]:
            print("High stress detected, running stoic.")
            app_state["stoic_mode_active"] = True
            app_state["conversation_locked"] = True
            philosopher.is_speaking = True

            philosopher.say_specific_phrase(
                text=CONVERSATION_STARTER, on_response_callback=on_ai_thought_callback
            )
        elif normalized_stress < 0.3 and app_state["stoic_mode_active"]:
            if not philosopher.is_speaking:
                print(
                    "The distress is gone and Mentor is silent. Welcome to ZEN state."
                )
                app_state["stoic_mode_active"] = False

    timer: QTimer = QTimer()
    timer.timeout.connect(polling_loop)
    timer.start(200)

    duck_window.show()

    exit_code: int = app.exec()

    eeg_service.stop()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
