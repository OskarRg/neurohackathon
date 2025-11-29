import sys
import os
import keyboard
import threading
import time
from collections import deque
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QLabel, QWidget, QVBoxLayout, QFrame,
                             QGraphicsDropShadowEffect, QMenu, QTextEdit, QPushButton,
                             QHBoxLayout)
from PyQt6.QtCore import (Qt, QPoint, QTimer, QSize, QPropertyAnimation, 
                          QEasingCurve, pyqtProperty, QRectF, pyqtSignal, QObject, QRect)
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

# --- WYMIARY DLA IDEALNEGO DOPASOWANIA ---
VISUAL_WIDTH = 260          # Szerokość wizualna ramki i czatu
BORDER_RADIUS = 50          # Zaokrąglenie rogów
INTERNAL_MARGIN = 35        # Margines dla GIFa wewnątrz ramki

# --- SIGNALS ---
class DuckSignals(QObject):
    stress_changed = pyqtSignal(float)
    intervention_triggered = pyqtSignal(str)
    user_message_sent = pyqtSignal(str)
    ai_response_ready = pyqtSignal(str)

# --- RAMKA KACZKI (GÓRA) ---
class PremiumFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._border_color = QColor("#00d2ff")
        # Ustawiamy stały rozmiar, żeby pasował do czatu
        self.setFixedSize(VISUAL_WIDTH, VISUAL_WIDTH)

    def setBorderColor(self, color_hex):
        self._border_color = QColor(color_hex)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Rysujemy ramkę
        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        path = QPainterPath()
        path.addRoundedRect(rect, BORDER_RADIUS, BORDER_RADIUS)

        # Białe tło
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        # Kolorowa obwódka
        pen = QPen(self._border_color)
        pen.setWidth(6)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

# --- PANEL CZATU (DÓŁ) ---
class ChatPanel(QFrame):
    message_sent = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Szerokość identyczna jak ramka kaczki
        self.setFixedWidth(VISUAL_WIDTH)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(30, 30, 30, 240);
                border-bottom-left-radius: {BORDER_RADIUS}px;
                border-bottom-right-radius: {BORDER_RADIUS}px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                border: 2px solid #ffd700; /* Złota ramka Stoika */
            }}
            QTextEdit {{
                background-color: #222;
                color: #eee;
                border: none;
                border-radius: 10px;
                padding: 8px;
                font-family: Segoe UI;
            }}
            QPushButton {{
                background-color: #ffd700; /* Złoty przycisk */
                color: #000;
                border-radius: 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #ffea00; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 25) # Większy margines na dole na zaokrąglenie
        
        # Nagłówek
        self.header = QLabel("🏛️ MENTOR STOICKI")
        self.header.setStyleSheet("color: #ffd700; font-weight: bold; border: none; background: transparent;")
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.header)
        
        # Historia
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("background: transparent; font-size: 11px;")
        layout.addWidget(self.chat_history)
        
        # Input
        input_layout = QHBoxLayout()
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Wpisz myśl...")
        self.input_field.setFixedHeight(35)
        self.input_field.keyPressEvent = self._on_key_press
        
        send_btn = QPushButton("➤")
        send_btn.setFixedSize(35, 35)
        send_btn.clicked.connect(self._send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
    def _on_key_press(self, event):
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._send_message()
        else:
            QTextEdit.keyPressEvent(self.input_field, event)
            
    def _send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text: return
        self.chat_history.append(f"<b style='color:#ccc'>Ty:</b> {text}")
        self.input_field.clear()
        self.message_sent.emit(text)
        
    def add_ai_response(self, text):
        self.chat_history.append(f"<br><b style='color:#ffd700'>Mentor:</b> <i>{text}</i>")
        sb = self.chat_history.verticalScrollBar()
        sb.setValue(sb.maximum())

# --- GŁÓWNY WIDGET ---
class ModernDuckWidget(QWidget):
    signals = DuckSignals()
    
    def __init__(self, debug_mode=False):
        super().__init__()
        self.debug_mode = debug_mode
        
        # Setup Stanu
        self.stress_level = 0.0
        self.current_state_name = ""
        self.is_chat_visible = False
        
        # Setup Okna
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Pozycja Startowa
        screen = QApplication.primaryScreen().geometry()
        # Wysokość startowa = tylko kaczka
        self.setGeometry(screen.width() - 350, screen.height() - 400, VISUAL_WIDTH + 20, VISUAL_WIDTH + 20)
        
        # --- LAYOUT GŁÓWNY ---
        # Używamy QVBoxLayout z zerowymi marginesami między elementami, żeby się stykały
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0) 
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # 1. KONTENER KACZKI
        self.duck_container = PremiumFrame(self)
        
        # Wnętrze kaczki
        self.duck_inner_layout = QVBoxLayout(self.duck_container)
        self.duck_inner_layout.setContentsMargins(INTERNAL_MARGIN, INTERNAL_MARGIN, INTERNAL_MARGIN, INTERNAL_MARGIN)
        
        self.label = QLabel(self.duck_container)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: transparent; border: none;")
        self.duck_inner_layout.addWidget(self.label)
        
        # Cień pod kaczką
        self.glow = QGraphicsDropShadowEffect()
        self.glow.setBlurRadius(50)
        self.glow.setOffset(0, 0)
        self.glow.setColor(QColor("#00d2ff"))
        self.duck_container.setGraphicsEffect(self.glow)
        
        self.main_layout.addWidget(self.duck_container)

        # 2. PANEL CZATU (Domyślnie UKRYTY i o wysokości 0)
        self.chat_panel = ChatPanel(self)
        self.chat_panel.setFixedHeight(0) # Startujemy zamknięci
        self.chat_panel.hide()
        self.chat_panel.message_sent.connect(self._on_user_message)
        
        self.main_layout.addWidget(self.chat_panel)

        # Inicjalizacja
        self.movie = None
        self._opacity = 1.0
        self.oldPos = self.pos()
        self.ai_callback = None
        
        self.change_state_smooth("zen")

    # --- LOGIKA STRESU (AUTO-TRIGGER) ---
    def update_stress(self, stress_level):
        self.stress_level = max(0.0, min(1.0, stress_level))
        
        # Logika zmiany stanów
        if self.stress_level < 0.2: 
            self.change_state_smooth("zen")
            self._ensure_chat_closed() # Zen = zamknij czat
        elif self.stress_level < 0.5: 
            self.change_state_smooth("focus")
            self._ensure_chat_closed() # Focus = zamknij czat
        elif self.stress_level < 0.8: 
            self.change_state_smooth("worry")
            self._ensure_chat_closed() # Worry = zamknij czat
        else:
            self.change_state_smooth("stoic")
            # STOIC = AUTO OPEN CHAT
            if not self.is_chat_visible:
                self._toggle_chat(open=True)
                # Opcjonalnie: Wiadomość powitalna tylko raz na sesję
                self.chat_panel.add_ai_response("Widzę, że sytuacja jest krytyczna. Jestem tu.")

    # --- MECHANIKA OTWIERANIA/ZAMYKANIA ---
    def _ensure_chat_closed(self):
        if self.is_chat_visible:
            self._toggle_chat(open=False)

    def _toggle_chat(self, open=True):
        """Animacja wysuwania/chowania czatu"""
        self.is_chat_visible = open
        
        start_geo = self.geometry()
        duck_h = VISUAL_WIDTH + 20 # Marginesy cienia
        chat_h = 300 # Wysokość docelowa czatu
        
        if open:
            self.chat_panel.show()
            start_h = 0
            end_h = chat_h
            total_h = duck_h + chat_h
        else:
            start_h = chat_h
            end_h = 0
            total_h = duck_h # Wracamy do rozmiaru samej kaczki

        # 1. Animacja wysokości panelu czatu
        self.anim_chat = QPropertyAnimation(self.chat_panel, b"maximumHeight") # Używamy property pośrednio przez fixedHeight
        # Trick na animację widgetu w layoucie: animujemy fixedHeight programowo
        self.animation_timer = QTimer()
        self.animation_step = 0
        self.animation_frames = 20
        self.h_diff = end_h - start_h
        self.current_h = start_h
        
        # Prosta pętla animacji manualnej (bo layouty w Qt ciężko się animuje property)
        def animate_step():
            self.current_h += self.h_diff / self.animation_frames
            if (self.h_diff > 0 and self.current_h >= end_h) or (self.h_diff < 0 and self.current_h <= end_h):
                self.chat_panel.setFixedHeight(end_h)
                self.animation_timer.stop()
                if not open: self.chat_panel.hide()
                # Korekta wielkości okna na koniec
                self.resize(self.width(), total_h)
            else:
                self.chat_panel.setFixedHeight(int(self.current_h))
                # Dynamiczna zmiana wielkości okna w trakcie
                self.resize(self.width(), duck_h + int(self.current_h))
                
        self.animation_timer.timeout.connect(animate_step)
        self.animation_timer.start(10)

    # --- RESZTA LOGIKI WIZUALNEJ ---
    def getOpacity(self): return self._opacity
    def setOpacity(self, o): 
        self._opacity = o
        self.setWindowOpacity(o)
    opacity_prop = pyqtProperty(float, getOpacity, setOpacity)

    def change_state_smooth(self, state_name):
        if state_name == self.current_state_name: return
        
        data = DUCK_STATES[state_name]
        self.duck_container.setBorderColor(data["color"])
        self.glow.setColor(QColor(data["color"]))
        
        # Animacja GIFa
        self.anim_out = QPropertyAnimation(self, b"opacity_prop")
        self.anim_out.setDuration(150)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(lambda: self._finish_transition(state_name))
        self.anim_out.start()

    def _finish_transition(self, state_name):
        self._load_gif(state_name)
        self.anim_in = QPropertyAnimation(self, b"opacity_prop")
        self.anim_in.setDuration(300)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.start()

    def _load_gif(self, state_name):
        path = DUCK_STATES[state_name]["path"]
        if not os.path.exists(path): return
        
        if self.movie: self.movie.stop()
        self.movie = QMovie(path)
        # Rozmiar kaczki wewnątrz
        size = VISUAL_WIDTH - (INTERNAL_MARGIN * 2)
        self.movie.setScaledSize(QSize(size, size))
        self.label.setMovie(self.movie)
        self.movie.start()
        self.current_state_name = state_name

    def _on_user_message(self, text):
        if self.ai_callback:
            threading.Thread(target=lambda: self._handle_ai(text), daemon=True).start()

    def _handle_ai(self, text):
        # Symulacja opóźnienia AI
        time.sleep(1) 
        response = self.ai_callback(text, self.stress_level)
        # Bezpieczne wywołanie GUI z wątku
        QTimer.singleShot(0, lambda: self.chat_panel.add_ai_response(response))

    # --- MYSZKA I MENU ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

    def mouseReleaseEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: white; border: 1px solid #ddd; padding: 5px; }")
        
        # Pokaż opcję czatu TYLKO jeśli jesteśmy w trybie Stoic
        if self.current_state_name == "stoic":
            toggle_act = QAction("Schowaj/Pokaż Czat", self)
            toggle_act.triggered.connect(lambda: self._toggle_chat(not self.is_chat_visible))
            menu.addAction(toggle_act)
        else:
            locked = QAction("🔒 Czat dostępny tylko w trybie Stoika", self)
            locked.setEnabled(False)
            menu.addAction(locked)

        quit_app = QAction("Zamknij", self)
        quit_app.triggered.connect(QApplication.quit)
        menu.addAction(quit_app)
        menu.exec(event.globalPosition().toPoint())

# --- KEYBOARD SIMULATION ---
def check_hotkeys(widget):
    try:
        if keyboard.is_pressed('1'): widget.update_stress(0.1)
        elif keyboard.is_pressed('2'): widget.update_stress(0.4)
        elif keyboard.is_pressed('3'): widget.update_stress(0.7)
        elif keyboard.is_pressed('4'): widget.update_stress(0.95) # TO OTWORZY CZAT
        elif keyboard.is_pressed('q'): QApplication.quit()
    except: pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    duck = ModernDuckWidget(debug_mode=True)
    
    # Callback AI
    duck.ai_callback = lambda msg, stress: f"Jako Marek Aureliusz w kaczce rzekę: {msg} to błahostka."
    
    duck.show()
    
    timer = QTimer()
    timer.timeout.connect(lambda: check_hotkeys(duck))
    timer.start(100)
    
    sys.exit(app.exec())