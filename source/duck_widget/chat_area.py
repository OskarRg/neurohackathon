import os
import threading
import time
from PyQt6.QtWidgets import (
    QLabel,
    QWidget,
    QVBoxLayout,
    QFrame,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    pyqtSignal,
)

from source.duck_widget.stylesheet_menager import StyleSheetManager
from source.duck_widget.utils import AppConfig

# optional recording backend
try:
    import sounddevice as sd
    import soundfile as sf

    _REC_AVAILABLE = True
except Exception:
    sd = None
    sf = None
    _REC_AVAILABLE = False


class ChatArea(QWidget):
    message_sent = pyqtSignal(str)
    mic_requested = pyqtSignal(str)
    recording_finished_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(AppConfig.CHAT_HEIGHT)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 25)
        self._last_recording = None
        self._is_playing = False
        self.recording_finished_signal.connect(self._on_recording_finished)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #E0E0E0; border: none; max-height: 1px;")
        layout.addWidget(line)

        # Header
        header = QLabel("STOIC MENTOR")
        header.setStyleSheet(
            f"color: {AppConfig.TEXT_SECONDARY}; font-weight: 700; font-family: 'Segoe UI'; margin-top: 15px; font-size: 10px; letter-spacing: 2px;"
        )
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # History
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setStyleSheet(
            StyleSheetManager.get_chat_style(AppConfig.GRADIENT_ZEN[1])
        )
        layout.addWidget(self.history)

        # Input Box
        input_box = QHBoxLayout()
        input_box.setSpacing(10)

        # Input
        self.input = QTextEdit()
        self.input.setPlaceholderText("What doubts you...")
        self.input.setFixedHeight(40)
        self.input.setStyleSheet(StyleSheetManager.get_input_style())
        self.input.keyPressEvent = self._on_key

        # Send Button
        self.btn = QPushButton("➤")
        self.btn.setFixedSize(40, 40)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setStyleSheet(
            StyleSheetManager.get_send_btn_style(
                AppConfig.GRADIENT_ZEN[0], AppConfig.GRADIENT_ZEN[1]
            )
        )
        self.btn.clicked.connect(self._send)

        # Record Button (placeholder for future voice recording -> transcription)
        self.record_btn = QPushButton("🎤")
        self.record_btn.setFixedSize(40, 40)
        self.record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_btn.setToolTip("Record voice (future)")
        self.record_btn.setStyleSheet(
            StyleSheetManager.get_record_btn_style(
                AppConfig.GRADIENT_ZEN[0], AppConfig.GRADIENT_ZEN[1]
            )
        )

        # Recording state
        self._is_recording = False
        self._record_thread = None
        self._stop_recording = threading.Event()
        self._rec_available = _REC_AVAILABLE
        if not self._rec_available:
            # disable if backend missing
            self.record_btn.setEnabled(False)
            self.record_btn.setToolTip(
                "Recording requires 'sounddevice' and 'soundfile' packages"
            )

        self.record_btn.clicked.connect(self._toggle_recording)

        input_box.addWidget(self.input)
        input_box.addWidget(self.record_btn)  # <-- now next to input and before send
        input_box.addWidget(self.btn)
        layout.addLayout(input_box)

    def update_accent(self, colors: tuple[str, str]):
        self.history.setStyleSheet(StyleSheetManager.get_chat_style(colors[1]))
        self.btn.setStyleSheet(
            StyleSheetManager.get_send_btn_style(colors[0], colors[1])
        )
        # update record button style if present
        if hasattr(self, "record_btn"):
            self.record_btn.setStyleSheet(
                StyleSheetManager.get_record_btn_style(colors[0], colors[1])
            )

    def set_locked(self, locked: bool):
        """Blocks input and button, changes placeholder."""
        self.input.setReadOnly(locked)
        self.input.setEnabled(not locked)  # Wyszarzenie
        self.btn.setEnabled(not locked)
        if hasattr(self, "record_btn"):
            self.record_btn.setEnabled(not locked)

        if locked:
            self.input.setPlaceholderText("Mentor is thinking...")
            self.btn.setCursor(Qt.CursorShape.ForbiddenCursor)
            if hasattr(self, "record_btn"):
                self.record_btn.setCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            self.input.setPlaceholderText("What doubts you...")
            self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if hasattr(self, "record_btn"):
                self.record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.input.setFocus()

    def _on_key(self, event):
        if (
            event.key() == Qt.Key.Key_Return
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            self._send()
            event.accept()
        else:
            QTextEdit.keyPressEvent(self.input, event)

    def _send(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        self._append_message(text, is_user=True)
        self.input.clear()
        self.message_sent.emit(text)

    # New toggle handler: start/stop recording and emit mic_requested when done
    def _toggle_recording(self):
        if not self._rec_available:
            self._append_message("Recording backend not available.", is_user=False)
            return

        if self._is_recording:
            self._stop_recording.set()
            QTimer.singleShot(0, lambda: self.record_btn.setText("🎤"))
            return

        # start recording
        self._stop_recording.clear()
        self._is_recording = True
        QTimer.singleShot(0, lambda: self.record_btn.setText("⏹"))

        self._record_thread = threading.Thread(target=self._record_worker, daemon=True)
        self._record_thread.start()

    def _on_recording_finished(self, filename: str):
        """
        Function will run in the main thread using Signal.

        :param filename: Filename to the recording.
        """
        self._is_recording = False
        self.record_btn.setText("🎤")
        self._last_recording = filename
        self.mic_requested.emit(str(filename))

    def _record_worker(self):
        """
        Records audio to a WAV file saved under the project folder ~/neurohackathon/assets.
        Emits mic_requested(filename) when finished.
        """
        try:
            samplerate = 16000
            channels = 1

            # ensure recordings directory inside project root (two levels up from this file)
            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            rec_dir = os.path.join(project_root, "assets")
            os.makedirs(rec_dir, exist_ok=True)

            filename = os.path.join(rec_dir, "voice_recording.wav")

            # Use soundfile to write chunks from sounddevice InputStream
            with sf.SoundFile(
                filename,
                mode="w",
                samplerate=samplerate,
                channels=channels,
                subtype="PCM_16",
            ) as file:

                def callback(indata, frames, timeinfo, status):
                    if status:
                        # write status to console but continue
                        print(f"Recording status: {status}")
                    file.write(indata)

                with sd.InputStream(
                    samplerate=samplerate, channels=channels, callback=callback
                ):
                    # keep recording until stop requested
                    while not self._stop_recording.is_set():
                        time.sleep(0.1)

            # finalize state on main thread
            def finish():
                self._is_recording = False
                self.record_btn.setText("🎤")
                # save last recording path and enable play button
                self._last_recording = filename
                self.play_btn.setVisible(True)
                # emit filename to listeners
                QTimer.singleShot(0, lambda: self.mic_requested.emit(filename))

            self.recording_finished_signal.emit(filename)
        except Exception as e:
            print(f"Recording error: {e}")

            def on_error():
                self._is_recording = False
                self.record_btn.setText("🎤")
                self._append_message("Recording failed.", is_user=False)

            QTimer.singleShot(0, on_error)

    def add_response(self, text):
        self._append_message(text, is_user=False)

    def add_user_response(self, text):
        self._append_message(text, is_user=True)

    def _append_message(self, text: str, is_user: bool):
        if is_user:
            label_color = "#999999"
            label_text = "YOU"
        else:
            label_color = AppConfig.COLOR_STOIC
            label_text = "MENTOR"

        html = f"""
        <div style="
            display: flex; 
            flex-direction: column; 
            align-items: flex-start; 
            margin-bottom: 10px; 
            border-bottom: 1px solid #F5F5F5; 
            padding-bottom: 8px;">
            
            <div style="
                color: {label_color}; 
                font-size: 9px; 
                margin-bottom: 3px; 
                font-weight: bold; 
                letter-spacing: 0.5px;">
                {label_text}
            </div>
            
            <div style="
                color: {AppConfig.TEXT_PRIMARY}; 
                font-size: 11px; 
                line-height: 1.3; 
                text-align: left;">
                {text}
            </div>
        </div>
        """

        self.history.append(html)
        sb = self.history.verticalScrollBar()
        sb.setValue(sb.maximum())
