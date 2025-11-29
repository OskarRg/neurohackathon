import sys
import os
import keyboard
import threading
import time
from collections import deque
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QLabel, QWidget, QVBoxLayout, QFrame,
                             QGraphicsDropShadowEffect, QMenu, QTextEdit, QPushButton,
                             QScrollArea, QHBoxLayout, QDialog, QMessageBox)
from PyQt6.QtCore import (Qt, QPoint, QTimer, QSize, QPropertyAnimation, 
                          QEasingCurve, pyqtProperty, QRectF, pyqtSignal, QObject)
from PyQt6.QtGui import (QMovie, QColor, QCursor, QAction, QPainter, 
                         QPainterPath, QPen, QBrush, QFont)


# --- KONFIGURACJA ---
ASSETS_DIR = "assets"
DUCK_STATES = {
    "zen":   {"path": os.path.join(ASSETS_DIR, "duck_zen.gif"),   "color": "#00d2ff", "label": "Zen (< 20%)"},
    "focus": {"path": os.path.join(ASSETS_DIR, "duck_focus.gif"), "color": "#8899a6", "label": "Focus (20-50%)"},
    "worry": {"path": os.path.join(ASSETS_DIR, "duck_worry.gif"), "color": "#ff9900", "label": "Worry (50-80%)"},
    "stoic": {"path": os.path.join(ASSETS_DIR, "duck_stoic.gif"), "color": "#ffd700", "label": "Stoic (> 80%)"}
}

WIDGET_SIZE = 240
BORDER_RADIUS = 50
INTERNAL_MARGIN = 20


# --- SIGNALS ---
class DuckSignals(QObject):
    """Sygnały do integracji z neuro_reader i philosopher_ai"""
    stress_changed = pyqtSignal(float)
    intervention_triggered = pyqtSignal(str)
    user_message_sent = pyqtSignal(str)  # Użytkownik wysłał wiadomość
    ai_response_ready = pyqtSignal(str)  # AI przygotowało odpowiedź


class PremiumFrame(QFrame):
    """Zaokrąglona ramka z biofeedback kolorem"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._border_color = QColor("#00d2ff")

    def setBorderColor(self, color_hex):
        self._border_color = QColor(color_hex)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        path = QPainterPath()
        path.addRoundedRect(rect, BORDER_RADIUS, BORDER_RADIUS)

        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        pen = QPen(self._border_color)
        pen.setWidth(6)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


class ChatPanel(QWidget):
    """
    Panel czatu z kaczką
    """
    message_sent = pyqtSignal(str)  # Emituje wiadomość użytkownika
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #00d2ff;
                border-radius: 8px;
                padding: 10px;
                font-size: 11px;
            }
            QPushButton {
                background-color: #00d2ff;
                color: #1e1e1e;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #00b8d4;
            }
            QPushButton:pressed {
                background-color: #008fa3;
            }
        """)
        
        self.setGeometry(100, 100, 400, 500)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Tytuł
        title = QLabel("💬 Chat z Mentorem Stoickim")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #00d2ff;")
        layout.addWidget(title)
        
        # Scroll area dla historii wiadomości
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #2d2d2d;
                border: 1px solid #00d2ff;
                border-radius: 8px;
            }
            QScrollBar:vertical {
                width: 8px;
                background-color: #1e1e1e;
            }
            QScrollBar::handle:vertical {
                background-color: #00d2ff;
                border-radius: 4px;
            }
        """)
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setFont(QFont("Courier", 9))
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: none;
                padding: 10px;
            }
        """)
        scroll_area.setWidget(self.chat_history)
        layout.addWidget(scroll_area)
        
        # Input field
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Napisz swoją myśl... (Ctrl+Enter = Wyślij)")
        self.input_field.setFixedHeight(80)
        self.input_field.setFont(QFont("Arial", 10))
        layout.addWidget(self.input_field)
        
        # Przycisk wysyłania
        send_button = QPushButton("🚀 Wyślij do Mentora")
        send_button.clicked.connect(self._send_message)
        send_button.setFixedHeight(35)
        layout.addWidget(send_button)
        
        # Łączenie Ctrl+Enter
        self.input_field.keyPressEvent = self._on_key_press
    
    def _on_key_press(self, event):
        """Ctrl+Enter = Wyślij wiadomość"""
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._send_message()
        else:
            QTextEdit.keyPressEvent(self.input_field, event)
    
    def _send_message(self):
        """Wyślij wiadomość użytkownika"""
        text = self.input_field.toPlainText().strip()
        
        if not text:
            return
        
        # Dodaj do historii
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_history.append(f"\n<span style='color: #00d2ff;'>[{timestamp}] Ty:</span>")
        self.chat_history.append(f"<span style='color: #ffffff;'>{text}</span>")
        
        # Wyczyść input
        self.input_field.clear()
        
        # Emituj sygnał
        self.message_sent.emit(text)
    
    def add_ai_response(self, response: str):
        """Dodaj odpowiedź od mentora"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_history.append(f"\n<span style='color: #ffd700;'>[{timestamp}] 🏛️ Mentor:</span>")
        self.chat_history.append(f"<span style='color: #cccccc;'>{response}</span>")
        
        # Scroll to bottom
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )
    
    def clear_history(self):
        """Wyczyść historię czatu"""
        self.chat_history.clear()


class ModernDuckWidget(QWidget):
    """
    Profesjonalny widget Kaczki Stoickiej z:
    - Biofeedback wizualnym
    - Historią stresu
    - Integracją z AI i audio
    - Obsługą hotkeys
    - Chat z mentorem (NOWE!)
    """
    
    # Sygnały
    signals = DuckSignals()
    
    def __init__(self, debug_mode=False):
        super().__init__()
        self.debug_mode = debug_mode
        
        # --- Konfiguracja stanu ---
        self._opacity = 1.0
        self.movie = None
        self.current_state_name = ""
        self.oldPos = self.pos()
        
        # --- Metryki ---
        self.stress_level = 0.0
        self.stress_history = deque(maxlen=180)
        self.last_intervention_time = 0
        self.intervention_cooldown = 300
        
        # --- Chat Panel ---
        self.chat_panel = None
        self.in_chat_mode = False
        
        # --- Setup Okna ---
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.width() - 320, screen.height() - 350, WIDGET_SIZE + 60, WIDGET_SIZE + 60)

        # --- Kontener główny ---
        self.container = PremiumFrame(self)
        self.container.setGeometry(30, 30, WIDGET_SIZE, WIDGET_SIZE)

        # Layout
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(INTERNAL_MARGIN, INTERNAL_MARGIN, INTERNAL_MARGIN, INTERNAL_MARGIN)

        # --- Label z Kaczką ---
        self.label = QLabel(self.container)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background-color: transparent; border: none;")
        self.layout.addWidget(self.label)

        # --- Glow (Poświata biofeedback) ---
        self.glow = QGraphicsDropShadowEffect()
        self.glow.setBlurRadius(60)
        self.glow.setOffset(0, 0)
        self.glow.setColor(QColor("#00d2ff"))
        self.container.setGraphicsEffect(self.glow)

        # --- Tooltip z statystyką ---
        self._init_tooltip()
        
        # --- Timer do aktualizacji ---
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_metrics)
        self.update_timer.start(100)
        
        # --- Audio callback placeholder ---
        self.audio_callback = None
        self.ai_callback = None
        
        self.change_state_smooth("zen")
        
        if self.debug_mode:
            print("[DuckWidget] Inicjalizacja w DEBUG MODE (+ Chat)")

    def _init_tooltip(self):
        """Inicjalizuje tooltip z informacjami o stresie"""
        self.setToolTip("🦆 StoicQuack | Stres: 0% | Brak interwencji | Prawy klik = Chat")

    def _update_metrics(self):
        """Aktualizuje tooltip z bieżącymi metrykami"""
        if len(self.stress_history) > 0:
            avg_stress = sum(self.stress_history) / len(self.stress_history)
            min_stress = min(self.stress_history)
            max_stress = max(self.stress_history)
            tooltip = (
                f"🦆 StoicQuack\n"
                f"Stres teraz: {self.stress_level*100:.1f}%\n"
                f"Średnia (3min): {avg_stress*100:.1f}%\n"
                f"Min/Max: {min_stress*100:.0f}% / {max_stress*100:.0f}%\n"
                f"Stan: {DUCK_STATES[self.current_state_name]['label']}\n"
                f"💬 Prawy klik na kaczkę = Chat z mentorem"
            )
            self.setToolTip(tooltip)

    # --- Property Fade ---
    def getOpacity(self):
        return self._opacity
    
    def setOpacity(self, opacity):
        self._opacity = opacity
        self.setWindowOpacity(opacity)
    
    opacity_prop = pyqtProperty(float, getOpacity, setOpacity)

    # --- API dla Student 1 (Neuro Reader) ---
    def update_stress(self, stress_level):
        """
        Główny hook z neuro_reader.py
        Parametr: stress_level (float 0.0-1.0)
        """
        self.stress_level = max(0.0, min(1.0, stress_level))
        self.stress_history.append(self.stress_level)
        
        # Emituj sygnał dla innych modułów
        self.signals.stress_changed.emit(self.stress_level)
        
        # Logika stanu
        if self.stress_level < 0.2:
            self.change_state_smooth("zen")
        elif self.stress_level < 0.5:
            self.change_state_smooth("focus")
        elif self.stress_level < 0.8:
            self.change_state_smooth("worry")
        else:
            self.change_state_smooth("stoic")
            # Trigger interwencji (tylko raz na cooldown)
            self._trigger_intervention()

    def _trigger_intervention(self):
        """
        Wywoływana gdy stres > 80%.
        Uruchamia AI + Audio w osobnym wątku
        """
        current_time = time.time()
        if current_time - self.last_intervention_time < self.intervention_cooldown:
            if self.debug_mode:
                print(f"[Intervention] Cooldown aktywny ({self.intervention_cooldown}s)")
            return
        
        self.last_intervention_time = current_time
        
        # Dźwięk GONG
        self._play_gong()
        
        # Wątek dla AI + Audio (żeby UI się nie zacinał)
        if self.ai_callback:
            thread = threading.Thread(target=self.ai_callback, daemon=True)
            thread.start()
        
        # Emit sygnału
        self.signals.intervention_triggered.emit("STRESS_CRITICAL")
        
        # Automatycznie otwórz chat gdy stres krytyczny
        if not self.in_chat_mode:
            self._open_chat_with_message("Jestem w kryzysie...")

    def _play_gong(self):
        """Odgłos przywołania mentora (placeholder dla audio)"""
        gong_path = os.path.join(ASSETS_DIR, "gong_sound.mp3")
        if os.path.exists(gong_path) and self.audio_callback:
            thread = threading.Thread(
                target=lambda: self.audio_callback(gong_path),
                daemon=True
            )
            thread.start()
        elif self.debug_mode:
            print("[Audio] Gong sound placeholder")

    def _open_chat_with_message(self, initial_message: str = ""):
        """Otwórz chat z opcjonalną początkową wiadomością"""
        if not self.chat_panel:
            self._create_chat_panel()
        
        self.chat_panel.show()
        self.chat_panel.raise_()
        self.in_chat_mode = True
        
        if initial_message:
            self.chat_panel.input_field.setText(initial_message)
            self.chat_panel.input_field.setFocus()

    def _create_chat_panel(self):
        """Tworzy panel czatu"""
        self.chat_panel = ChatPanel()
        self.chat_panel.message_sent.connect(self._on_user_message)
        
        if self.debug_mode:
            print("[ChatPanel] Utworzony")

    def _on_user_message(self, user_text: str):
        """Obsługuje wiadomość od użytkownika"""
        if self.debug_mode:
            print(f"[User Message] {user_text}")
        
        # Emituj sygnał
        self.signals.user_message_sent.emit(user_text)
        
        # Jeśli jest callback do AI, uruchom w wątku
        if self.ai_callback:
            def ai_thread():
                response = self.ai_callback(user_text, self.stress_level)
                if response:
                    self.chat_panel.add_ai_response(response)
                    self.signals.ai_response_ready.emit(response)
            
            thread = threading.Thread(target=ai_thread, daemon=True)
            thread.start()

    # --- Zmiana stanu z animacją ---
    def change_state_smooth(self, state_name):
        if state_name == self.current_state_name:
            return
        if state_name not in DUCK_STATES:
            return

        new_color = DUCK_STATES[state_name]["color"]
        
        self.container.setBorderColor(new_color)
        self.glow.setColor(QColor(new_color))

        # Animacja fade out
        self.anim_out = QPropertyAnimation(self, b"opacity_prop")
        self.anim_out.setDuration(150)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim_out.finished.connect(lambda: self._finish_transition(state_name))
        self.anim_out.start()

    def _finish_transition(self, state_name):
        self._load_gif(state_name)
        
        # Animacja fade in
        self.anim_in = QPropertyAnimation(self, b"opacity_prop")
        self.anim_in.setDuration(300)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.Type.InQuad)
        self.anim_in.start()

    def _load_gif(self, state_name):
        gif_path = DUCK_STATES[state_name]["path"]
        if not os.path.exists(gif_path):
            if self.debug_mode:
                print(f"[Warning] GIF nie znaleziony: {gif_path}")
            return

        if self.movie:
            self.movie.stop()
        
        self.movie = QMovie(gif_path)
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        
        target_size = QSize(WIDGET_SIZE - (INTERNAL_MARGIN * 2), WIDGET_SIZE - (INTERNAL_MARGIN * 2))
        self.movie.setScaledSize(target_size)
        
        self.label.setMovie(self.movie)
        self.movie.start()
        self.current_state_name = state_name

    # --- Myszka (Drag & Drop) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            self.glow.setBlurRadius(30)

    def mouseReleaseEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.glow.setBlurRadius(60)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

    def mouseDoubleClickEvent(self, event):
        """Double-click = Otwórz chat"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_chat_with_message()

    # --- Menu kontekstowe ---
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #ddd; padding: 5px; border-radius: 8px; }
            QMenu::item { color: #333; padding: 8px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #f0f0f0; }
        """)
        
        # Chat
        chat = QAction("💬 Otwórz Chat z Mentorem", self)
        chat.triggered.connect(self._open_chat_with_message)
        menu.addAction(chat)
        
        # Reset
        menu.addSeparator()
        reset = QAction("🧘 Zresetuj (Zen)", self)
        reset.triggered.connect(lambda: self.update_stress(0.0))
        menu.addAction(reset)
        
        # Symulacja testowa (Wizard of Oz)
        menu.addSeparator()
        test_zen = QAction("Test: Zen", self)
        test_zen.triggered.connect(lambda: self.update_stress(0.1))
        menu.addAction(test_zen)
        
        test_focus = QAction("Test: Focus", self)
        test_focus.triggered.connect(lambda: self.update_stress(0.4))
        menu.addAction(test_focus)
        
        test_worry = QAction("Test: Worry", self)
        test_worry.triggered.connect(lambda: self.update_stress(0.7))
        menu.addAction(test_worry)
        
        test_stoic = QAction("Test: Stoic (TRIGGER)", self)
        test_stoic.triggered.connect(lambda: self.update_stress(0.95))
        menu.addAction(test_stoic)
        
        # Statystyka
        menu.addSeparator()
        stats = QAction(f"📊 Stres: {self.stress_level*100:.1f}%", self)
        stats.setEnabled(False)
        menu.addAction(stats)
        
        # Zamknij
        menu.addSeparator()
        quit_app = QAction("❌ Zamknij", self)
        quit_app.triggered.connect(QApplication.quit)
        menu.addAction(quit_app)
        
        menu.exec(event.globalPosition().toPoint())

    # --- Hotkeys (Wizard of Oz + Debug) ---
    def check_hotkeys(self):
        """Wywołujesz to w main.py w timer loop"""
        try:
            if keyboard.is_pressed('1'): self.update_stress(0.1)
            elif keyboard.is_pressed('2'): self.update_stress(0.4)
            elif keyboard.is_pressed('3'): self.update_stress(0.7)
            elif keyboard.is_pressed('4'): self.update_stress(0.95)
            elif keyboard.is_pressed('c'): self._open_chat_with_message()  # C = Chat
            elif keyboard.is_pressed('q'): QApplication.quit()
        except Exception as e:
            if self.debug_mode:
                print(f"[Hotkeys Error] {e}")

    # --- Getter dla integracji z innymi modułami ---
    def get_current_stress(self):
        """Dla innych modułów"""
        return self.stress_level
    
    def get_stress_history(self):
        """Dla analityki"""
        return list(self.stress_history)
    
    def get_current_state(self):
        """Zwraca bieżący stan kaczki"""
        return self.current_state_name
    
    def get_conversation_history(self):
        """Zwraca historię rozmowy"""
        if self.chat_panel:
            return self.chat_panel.chat_history.toPlainText()
        return ""


# --- MAIN (Przykład integracji) ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    duck = ModernDuckWidget(debug_mode=True)
    
    # --- Placeholder dla integracji z Student 2 (AI) ---
    def philosopher_ai_callback(user_message: str = "", stress_level: float = 0.0):
        """
        To będzie zaimplementowane w philosopher_ai.py
        
        Parametry:
        - user_message: Wiadomość od użytkownika (string)
        - stress_level: Bieżący poziom stresu (0.0-1.0)
        
        Return: Odpowiedź mentora (string)
        """
        print(f"[AI] Otrzymałem wiadomość: {user_message}")
        print(f"[AI] Stres użytkownika: {stress_level*100:.1f}%")
        
        # Placeholder odpowiedzi
        responses = {
            "low": "Oddychaj spokojnie. To, co Cię niepokoi, jest niezavisne od Twojej woli.",
            "medium": "Pamiętaj: nie kontrolujesz zdarzenia, tylko swoją reakcję na nie.",
            "high": "KRYZYS! Zatrzymaj się. Co rzeczywiście możesz kontrolować w tej chwili?"
        }
        
        if stress_level > 0.8:
            response = responses["high"]
        elif stress_level > 0.5:
            response = responses["medium"]
        else:
            response = responses["low"]
        
        return response
    
    duck.ai_callback = philosopher_ai_callback
    
    duck.show()
    
    # Hotkeys timer
    timer = QTimer()
    timer.timeout.connect(duck.check_hotkeys)
    timer.start(100)
    
    print("[Main] StoicQuack Professional Widget + Chat uruchomiony")
    print("[Main] Hotkeys: 1=Zen, 2=Focus, 3=Worry, 4=Stoic, C=Chat, Q=Quit")
    print("[Main] Double-click = Chat | Prawy klik = Menu | Przeciągnij = Przesuń")
    
    sys.exit(app.exec())