import sys
import os
import keyboard
import threading
import time
import random
from PyQt6.QtWidgets import (QApplication, QLabel, QWidget, QVBoxLayout, QFrame,
                             QGraphicsDropShadowEffect, QTextEdit, QPushButton,
                             QHBoxLayout, QProgressBar)
from PyQt6.QtCore import (Qt, QTimer, QSize, QPropertyAnimation, 
                          QEasingCurve, pyqtProperty, QRectF, pyqtSignal, QObject)
from PyQt6.QtGui import (QMovie, QColor, QCursor, QAction, QPainter, 
                         QPainterPath, QPen, QBrush)

# --- KONFIGURACJA ---
ASSETS_DIR = "assets"
DUCK_STATES = {
    "zen":   {"path": os.path.join(ASSETS_DIR, "duck_zen.gif"),   "color": "#00d2ff"},
    "focus": {"path": os.path.join(ASSETS_DIR, "duck_focus.gif"), "color": "#8899a6"},
    "worry": {"path": os.path.join(ASSETS_DIR, "duck_worry.gif"), "color": "#ff9900"},
    "stoic": {"path": os.path.join(ASSETS_DIR, "duck_stoic.gif"), "color": "#ffd700"}
}

# --- WYMIARY ---
WIDTH = 280                 
DUCK_AREA_HEIGHT = 300 # Zwiększono lekko, żeby zmieścić pasek
CHAT_AREA_HEIGHT = 300      
BORDER_RADIUS = 40          
MARGIN = 30                 

# ==========================================
# MOCK BACKEND
# ==========================================
class MockPhilosopherBrain:
    @staticmethod
    def get_response(user_text, stress_level):
        time.sleep(random.uniform(0.5, 1.5)) 
        
        if "SYSTEM_TRIGGER" in user_text:
            return "Widzę, że poziom stresu jest krytyczny. Jestem tutaj. Opowiedz mi o tym.", 2.0

        if stress_level > 0.8:
            responses = [
                "Widzę chaos w Twoim kodzie. Zatrzymaj się.",
                "Gniew to kwas, który niszczy naczynie.",
                "Nie kontrolujesz wyniku, ale swoje podejście."
            ]
        elif stress_level > 0.4:
            responses = [
                "Skupienie jest kluczem.",
                "Nie martw się przyszłymi błędami.",
                "Pisz dalej, ale z rozwagą."
            ]
        else:
            responses = [
                "Płyniesz z prądem kodu.",
                "Umysł czysty jak pusty plik.",
                "Spokój jest Twoją siłą."
            ]
            
        text = random.choice(responses)
        audio_duration = len(text.split()) * 0.4 
        return text, audio_duration

# ==========================================
# FRONTEND (UI)
# ==========================================

class DuckSignals(QObject):
    stress_changed = pyqtSignal(float)
    user_message_sent = pyqtSignal(str)
    ai_response_ready = pyqtSignal(str, float)

# --- UNIFIED FRAME (TŁO) ---
class UnifiedFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) 
        self.setStyleSheet("background: transparent;")
        
        self._border_color = QColor("#00d2ff")
        self._bg_color = QColor("#FFFFFF") 

    def setBorderColor(self, color_hex):
        self._border_color = QColor(color_hex)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        path = QPainterPath()
        path.addRoundedRect(rect, BORDER_RADIUS, BORDER_RADIUS)

        # Tło
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        # Ramka
        pen = QPen(self._border_color)
        pen.setWidth(6)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

# --- GÓRA: KACZKA + PASEK STRESU ---
class DuckArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(DUCK_AREA_HEIGHT)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, 15) # Mniejszy margines na dole dla paska
        
        # 1. KACZKA
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.label)
        
        # 2. PASEK STRESU (Bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6) # Cienki, elegancki pasek
        self.progress_bar.setTextVisible(False) # Bez tekstu procentowego
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # Styl bazowy paska
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #F0F0F0;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #00d2ff;
                border-radius: 3px;
            }
        """)
        
        layout.addSpacing(10) # Odstęp między kaczką a paskiem
        layout.addWidget(self.progress_bar)

    def update_bar_color(self, color_hex):
        """Aktualizuje kolor paska w zależności od stanu"""
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: #F0F0F0;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {color_hex};
                border-radius: 3px;
            }}
        """)

    def update_bar_value(self, value_float):
        """Aktualizuje długość paska (0.0 - 1.0 -> 0 - 100)"""
        self.progress_bar.setValue(int(value_float * 100))

# --- DÓŁ: CZAT ---
class ChatArea(QWidget):
    message_sent = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(CHAT_AREA_HEIGHT)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 20)
        
        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setStyleSheet("background-color: #EEEEEE; border: none; max-height: 1px;")
        layout.addWidget(self.line)

        self.header = QLabel("🏛️ MENTOR STOICKI")
        self.header.setStyleSheet("color: #D4AF37; font-weight: bold; font-family: Segoe UI; margin-top: 10px; font-size: 12px;")
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.header)
        
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setStyleSheet("""
            QTextEdit {
                background: transparent;
                color: #333333;
                font-family: Segoe UI;
                font-size: 12px;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #F5F5F5;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #FFD700;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #FFC107;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; border: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        layout.addWidget(self.history)
        
        input_box = QHBoxLayout()
        self.input = QTextEdit()
        self.input.setPlaceholderText("Napisz... (Ctrl+Enter)")
        self.input.setFixedHeight(40)
        self.input.setStyleSheet("""
            QTextEdit {
                background-color: #F5F5F5;
                border-radius: 10px;
                color: #000000;
                padding: 5px;
                border: 1px solid #E0E0E0;
            }
        """)
        self.input.keyPressEvent = self._on_key
        
        btn = QPushButton("➤") 
        btn.setFixedSize(40, 40)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #FFD700;
                color: black;
                border-radius: 20px;
                font-weight: bold;
                border: none;
                font-size: 16px;
                padding-bottom: 2px;
            }
            QPushButton:hover { background-color: #FFEA00; }
            QPushButton:pressed { background-color: #D4AF37; }
        """)
        btn.clicked.connect(self._send)
        
        input_box.addWidget(self.input)
        input_box.addWidget(btn)
        layout.addLayout(input_box)

    def _on_key(self, event):
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._send()
            event.accept()
        else:
            QTextEdit.keyPressEvent(self.input, event)

    def _send(self):
        text = self.input.toPlainText().strip()
        if not text: return
        self.history.append(f"<div style='margin-bottom: 5px;'><b style='color:#555'>Ty:</b> {text}</div>")
        self.input.clear()
        self.message_sent.emit(text)

    def add_response(self, text):
        self.history.append(f"<div style='margin-bottom: 10px;'><b style='color:#D4AF37'>Mentor:</b> <i>{text}</i></div>")
        sb = self.history.verticalScrollBar()
        sb.setValue(sb.maximum())

# --- GŁÓWNY WIDGET ---
class StoicDuckWidget(QWidget):
    signals = DuckSignals()

    def __init__(self):
        super().__init__()
        
        self.stress_level = 0.0
        self.current_state_name = ""
        self.is_expanded = False
        self.has_triggered_intro = False
        self.dragPos = None
        self.is_speaking = False 
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        screen_geo = QApplication.primaryScreen().availableGeometry()
        initial_x = screen_geo.width() - WIDTH - 50
        initial_y = 50
        self.setGeometry(initial_x, initial_y, WIDTH + 20, DUCK_AREA_HEIGHT + 20)

        # 1. Shell
        self.shell = UnifiedFrame(self)
        self.window_layout = QVBoxLayout(self)
        self.window_layout.setContentsMargins(10, 10, 10, 10)
        self.window_layout.addWidget(self.shell)

        # 2. Wnętrze
        self.shell_layout = QVBoxLayout(self.shell)
        self.shell_layout.setContentsMargins(0, 0, 0, 0)
        self.shell_layout.setSpacing(0)

        # Kaczka (z Paskiem)
        self.duck_area = DuckArea()
        self.shell_layout.addWidget(self.duck_area)
        
        # Czat
        self.chat_area = ChatArea()
        self.chat_area.setFixedHeight(0)
        self.chat_area.hide()
        self.chat_area.message_sent.connect(self.handle_user_message)
        self.shell_layout.addWidget(self.chat_area)

        # Cień
        self.glow = QGraphicsDropShadowEffect()
        self.glow.setBlurRadius(40)
        self.glow.setOffset(0, 0)
        self.glow.setColor(QColor("#00d2ff"))
        self.shell.setGraphicsEffect(self.glow)

        self.movie = None
        self._opacity = 1.0
        
        self.signals.ai_response_ready.connect(self.display_ai_response)
        
        self.change_state("zen")

    def handle_user_message(self, text):
        threading.Thread(target=self._run_mock_backend, args=(text,), daemon=True).start()

    def _run_mock_backend(self, user_text):
        response_text, audio_duration = MockPhilosopherBrain.get_response(user_text, self.stress_level)
        self.signals.ai_response_ready.emit(response_text, audio_duration)

    def display_ai_response(self, text, duration):
        self.chat_area.add_response(text)
        self._pulse_glow_for_audio(duration)

    def _pulse_glow_for_audio(self, duration):
        self.is_speaking = True
        self.glow.setColor(QColor("#FFD700"))
        QTimer.singleShot(int(duration * 1000), self._reset_glow_after_audio)

    def _reset_glow_after_audio(self):
        self.is_speaking = False
        current_data = DUCK_STATES.get(self.current_state_name, DUCK_STATES["zen"])
        self.glow.setColor(QColor(current_data["color"]))

    # --- EXPAND LOGIC ---
    def toggle_expand(self, expand=True):
        if self.is_expanded == expand: return
        self.is_expanded = expand

        if expand:
            self.chat_area.show()
            target_h = DUCK_AREA_HEIGHT + CHAT_AREA_HEIGHT + 20 
            chat_target_h = CHAT_AREA_HEIGHT
        else:
            target_h = DUCK_AREA_HEIGHT + 20
            chat_target_h = 0

        self.anim_chat = QPropertyAnimation(self.chat_area, b"maximumHeight")
        self.anim_timer = QTimer()
        self.anim_frames = 25
        self.current_chat_h = 0 if expand else CHAT_AREA_HEIGHT
        self.step = chat_target_h / self.anim_frames if expand else -CHAT_AREA_HEIGHT / self.anim_frames
        
        def animate():
            self.current_chat_h += self.step
            if (expand and self.current_chat_h >= chat_target_h) or (not expand and self.current_chat_h <= 0):
                self.chat_area.setFixedHeight(chat_target_h)
                self.resize(self.width(), target_h)
                self.anim_timer.stop()
                if not expand: self.chat_area.hide()
            else:
                h = int(self.current_chat_h)
                self.chat_area.setFixedHeight(h)
                self.resize(self.width(), DUCK_AREA_HEIGHT + h + 20)
        
        self.anim_timer.timeout.connect(animate)
        self.anim_timer.start(10)

    # --- STRESS LOGIC ---
    def update_stress(self, stress):
        self.stress_level = stress
        
        # Aktualizuj wartość paska stresu w DuckArea
        self.duck_area.update_bar_value(stress)
        
        if stress < 0.2: 
            self.change_state("zen")
            self.toggle_expand(False)
            self.has_triggered_intro = False
        elif stress < 0.5: 
            self.change_state("focus")
            self.toggle_expand(False)
            self.has_triggered_intro = False
        elif stress < 0.8: 
            self.change_state("worry")
            self.toggle_expand(False)
            self.has_triggered_intro = False
        else: 
            self.change_state("stoic")
            self.toggle_expand(True)
            
            if not self.has_triggered_intro:
                self.has_triggered_intro = True
                self.handle_user_message("SYSTEM_TRIGGER: HIGH_STRESS")

    def change_state(self, state_name):
        if state_name == self.current_state_name: return
        
        data = DUCK_STATES[state_name]
        new_color = data["color"]
        
        self.shell.setBorderColor(new_color)
        
        # Aktualizuj kolor paska stresu
        self.duck_area.update_bar_color(new_color)
        
        if not self.is_speaking:
            self.glow.setColor(QColor(new_color))
        
        self._load_gif(state_name)
        self.current_state_name = state_name

    def _load_gif(self, state_name):
        path = DUCK_STATES[state_name]["path"]
        if not os.path.exists(path): return
        
        if self.movie: self.movie.stop()
        self.movie = QMovie(path)
        
        # Skalowanie GIFa (z uwzględnieniem paska na dole)
        # Odejmujemy więcej z wysokości, żeby zrobić miejsce na bar
        s_w = WIDTH - (MARGIN * 2)
        s_h = WIDTH - (MARGIN * 2) 
        self.movie.setScaledSize(QSize(s_w, s_h))
        
        self.duck_area.label.setMovie(self.movie)
        self.movie.start()

    # --- MOUSE EVENTS ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragPos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragPos = None
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.dragPos:
            self.move(event.globalPosition().toPoint() - self.dragPos)
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: white; border: 1px solid #ddd; padding: 5px; color: black; }")
        quit_act = QAction("Zamknij", self)
        quit_act.triggered.connect(QApplication.quit)
        menu.addAction(quit_act)
        menu.exec(event.globalPosition().toPoint())

# --- SIMULATION ---
def check_hotkeys(widget):
    try:
        if keyboard.is_pressed('1'): widget.update_stress(0.1)
        elif keyboard.is_pressed('2'): widget.update_stress(0.4)
        elif keyboard.is_pressed('3'): widget.update_stress(0.7)
        elif keyboard.is_pressed('4'): widget.update_stress(0.95)
        elif keyboard.is_pressed('q'): QApplication.quit()
    except: pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = StoicDuckWidget()
    widget.show()
    
    t = QTimer()
    t.timeout.connect(lambda: check_hotkeys(widget))
    t.start(100)
    
    sys.exit(app.exec())