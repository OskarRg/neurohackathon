import sys
import os
import random
import time
import logging
import keyboard
from dataclasses import dataclass
from enum import Enum
from typing import Tuple

# PyQt Imports
from PyQt6.QtWidgets import (
    QApplication, QLabel, QWidget, QVBoxLayout, QFrame,
    QTextEdit, QPushButton, QHBoxLayout, QProgressBar
)
from PyQt6.QtCore import (
    Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, 
    pyqtProperty, QRectF, pyqtSignal, QObject, QThread, QPoint
)
from PyQt6.QtGui import (
    QMovie, QColor, QCursor, QPainter, 
    QPainterPath, QPen, QBrush, QFont, QLinearGradient
)

# --- 0. LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("StoicQuack")

# --- 1. KONFIGURACJA (WHITE THEME 2.0) ---

@dataclass(frozen=True)
class AppConfig:
    APP_NAME: str = "StoicQuack Pro"
    WIDTH: int = 300
    DUCK_AREA_HEIGHT: int = 320
    CHAT_HEIGHT: int = 400
    BORDER_RADIUS: int = 30
    MARGIN: int = 25
    
    # Kolory
    BG_COLOR: str = "#FFFFFF"       
    TEXT_PRIMARY: str = "#1A1A1A"   
    TEXT_SECONDARY: str = "#666666" 
    INPUT_BG: str = "#F5F5F5"       
    
    # --- GRADIENTY ---
    GRADIENT_ZEN: Tuple[str, str] = ("#00F260", "#0575E6")    
    GRADIENT_FOCUS: Tuple[str, str] = ("#667eea", "#764ba2")  
    GRADIENT_WORRY: Tuple[str, str] = ("#FF8008", "#FFC837")  
    GRADIENT_STOIC: Tuple[str, str] = ("#F2994A", "#F2C94C")  
    
    # Kolory pojedyncze (pomocnicze)
    COLOR_STOIC: str = "#F2994A" # Złoty kolor dla tekstu Mentora

    # AI Settings
    AI_THINK_MIN_SEC: float = 0.5
    AI_THINK_MAX_SEC: float = 1.5

class DuckState(Enum):
    ZEN = "zen"
    FOCUS = "focus"
    WORRY = "worry"
    STOIC = "stoic"

DUCK_STATES_CONFIG = {
    DuckState.ZEN:   {"file": "duck_zen.gif",   "grad": AppConfig.GRADIENT_ZEN},
    DuckState.FOCUS: {"file": "duck_focus.gif", "grad": AppConfig.GRADIENT_FOCUS},
    DuckState.WORRY: {"file": "duck_worry.gif", "grad": AppConfig.GRADIENT_WORRY},
    DuckState.STOIC: {"file": "duck_stoic.gif", "grad": AppConfig.GRADIENT_STOIC}
}

# --- 2. STYLE MANAGER (CSS) ---

class StyleSheetManager:
    @staticmethod
    def get_progress_bar_style(color_start: str, color_end: str) -> str:
        return f"""
            QProgressBar {{
                border: none;
                background-color: #F0F2F5;
                border-radius: 4px;
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                                  stop:0 {color_start}, stop:1 {color_end});
                border-radius: 4px;
            }}
        """

    @staticmethod
    def get_chat_style(accent_color: str) -> str:
        return f"""
            QTextEdit {{
                background: transparent;
                color: {AppConfig.TEXT_PRIMARY};
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                line-height: 1.4;
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: #F7F7F7;
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {accent_color};
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{ background-color: #555; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """

    @staticmethod
    def get_input_style() -> str:
        # FIX: Dodano ukrywanie scrollbarów
        return f"""
            QTextEdit {{
                background-color: {AppConfig.INPUT_BG};
                border: 1px solid #E0E6ED;
                border-radius: 20px;
                color: {AppConfig.TEXT_PRIMARY};
                padding: 8px 12px;
                font-family: 'Segoe UI';
                font-size: 12px;
                qproperty-alignment: AlignVCenter; /* Wyśrodkowanie w pionie */
            }}
            QTextEdit:focus {{
                border: 1px solid #74B9FF;
                background-color: #FFFFFF;
            }}
            /* Ukrywamy oba suwaki */
            QScrollBar:vertical, QScrollBar:horizontal {{
                height: 0px;
                width: 0px;
                border: none;
                background: transparent;
            }}
        """

    @staticmethod
    def get_send_btn_style(color1: str, color2: str) -> str:
        return f"""
            QPushButton {{
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                                  stop:0 {color1}, stop:1 {color2});
                color: white;
                border-radius: 20px;
                font-weight: bold;
                border: none;
                font-size: 16px;
                padding-bottom: 3px;
            }}
            QPushButton:hover {{
                margin-top: 1px;
            }}
        """

# --- 3. HELPERY ---

class ResourceManager:
    @staticmethod
    def get_asset_path(filename: str) -> str:
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_path, "assets", filename)
        return path

# --- 4. BACKEND MOCK ---

class AIWorker(QThread):
    response_ready = pyqtSignal(str, float)

    def __init__(self, user_text: str, stress_level: float):
        super().__init__()
        self.user_text = user_text
        self.stress_level = stress_level

    def run(self):
        time.sleep(random.uniform(AppConfig.AI_THINK_MIN_SEC, AppConfig.AI_THINK_MAX_SEC))
        response, duration = self._mock_brain()
        self.response_ready.emit(response, duration)

    def _mock_brain(self) -> Tuple[str, float]:
        if "SYSTEM_TRIGGER" in self.user_text:
            return "Wykryto wysoki poziom stresu. Jestem tutaj, aby pomóc.", 2.0
        
        if self.stress_level > 0.8:
            responses = [
                "Widzę chaos w Twoim kodzie. Zatrzymaj się.",
                "Gniew to kwas. Nie kompiluj pod wpływem emocji."
            ]
        else:
            responses = [
                "Płyniesz z prądem kodu. Doskonale.",
                "Umysł czysty jak pusty plik main.py."
            ]
        text = random.choice(responses)
        return text, len(text.split()) * 0.4

# --- 5. KOMPONENTY UI ---

class UnifiedFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self._border_color = QColor(AppConfig.GRADIENT_ZEN[1])
        self._bg_color = QColor(AppConfig.BG_COLOR)
        self._gradient_colors = AppConfig.GRADIENT_ZEN

    def set_border_gradient(self, colors: Tuple[str, str]):
        self._gradient_colors = colors
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        path = QPainterPath()
        path.addRoundedRect(rect, AppConfig.BORDER_RADIUS, AppConfig.BORDER_RADIUS)

        # Tło
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        # Ramka Gradientowa
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor(self._gradient_colors[0]))
        gradient.setColorAt(1, QColor(self._gradient_colors[1]))
        
        pen = QPen(QBrush(gradient), 6)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

class DuckArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(AppConfig.DUCK_AREA_HEIGHT)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(AppConfig.MARGIN, AppConfig.MARGIN, AppConfig.MARGIN, 10)
        
        # GIF
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.label)
        
        # Pasek
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        
        layout.addSpacing(20)
        layout.addWidget(self.progress_bar)
        
        self.update_style(AppConfig.GRADIENT_ZEN)
        self.movie = None
        self.target_size = QSize(100, 100) 

    def update_style(self, colors: Tuple[str, str]):
        self.progress_bar.setStyleSheet(
            StyleSheetManager.get_progress_bar_style(colors[0], colors[1])
        )

    def set_stress_value(self, value: float):
        self.progress_bar.setValue(int(value * 100))

    def load_gif(self, filename: str):
        path = ResourceManager.get_asset_path(filename)
        if not os.path.exists(path): return
        
        if self.movie:
            self.movie.stop()
            try: self.movie.frameChanged.disconnect()
            except: pass
            
        self.movie = QMovie(path)
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        
        av_w = AppConfig.WIDTH - (AppConfig.MARGIN * 2)
        self.target_size = QSize(av_w, av_w)
        
        self.movie.frameChanged.connect(self._update_frame_hq)
        self.movie.start()

    def _update_frame_hq(self):
        current_pixmap = self.movie.currentPixmap()
        if not current_pixmap.isNull():
            hq_pixmap = current_pixmap.scaled(
                self.target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.label.setPixmap(hq_pixmap)

class ChatArea(QWidget):
    message_sent = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(AppConfig.CHAT_HEIGHT)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 25)
        
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #E0E0E0; border: none; max-height: 1px;")
        layout.addWidget(line)

        # Header
        header = QLabel("MENTOR STOICKI")
        header.setStyleSheet(f"color: {AppConfig.TEXT_SECONDARY}; font-weight: 700; font-family: 'Segoe UI'; margin-top: 15px; font-size: 10px; letter-spacing: 2px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # History
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setStyleSheet(StyleSheetManager.get_chat_style(AppConfig.GRADIENT_ZEN[1]))
        layout.addWidget(self.history)
        
        # Input Box
        input_box = QHBoxLayout()
        input_box.setSpacing(10) 
        
        # Input
        self.input = QTextEdit()
        self.input.setPlaceholderText("Wpisz myśl...")
        self.input.setFixedHeight(40)
        self.input.setStyleSheet(StyleSheetManager.get_input_style())
        self.input.keyPressEvent = self._on_key
        
        # Button
        self.btn = QPushButton("➤") 
        self.btn.setFixedSize(40, 40)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setStyleSheet(StyleSheetManager.get_send_btn_style(AppConfig.GRADIENT_ZEN[0], AppConfig.GRADIENT_ZEN[1]))
        self.btn.clicked.connect(self._send)
        
        input_box.addWidget(self.input)
        input_box.addWidget(self.btn)
        layout.addLayout(input_box)

    def update_accent(self, colors: Tuple[str, str]):
        self.history.setStyleSheet(StyleSheetManager.get_chat_style(colors[1]))
        self.btn.setStyleSheet(StyleSheetManager.get_send_btn_style(colors[0], colors[1]))

    def _on_key(self, event):
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self._send()
            event.accept()
        else:
            QTextEdit.keyPressEvent(self.input, event)

    def _send(self):
        text = self.input.toPlainText().strip()
        if not text: return
        self._append_message("TY", text, is_user=True)
        self.input.clear()
        self.message_sent.emit(text)

    def add_response(self, text):
        self._append_message("MENTOR", text, is_user=False)

    def _append_message(self, sender: str, text: str, is_user: bool):
        if is_user:
            label_color = "#999999"
            label_text = "TY"
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
                font-size: 12px; 
                line-height: 1.4; 
                text-align: left;">
                {text}
            </div>
        </div>
        """
        
        self.history.append(html)
        sb = self.history.verticalScrollBar()
        sb.setValue(sb.maximum())

# --- 6. MAIN CONTROLLER ---

class StoicDuckPro(QWidget):
    def __init__(self):
        super().__init__()
        
        self.stress_level = 0.0
        self.current_state_enum = DuckState.ZEN
        self.is_expanded = False
        self.is_speaking = False
        self.drag_pos = None
        self.movie = None
        
        self._init_window()
        self._init_ui()
        self.change_state(DuckState.ZEN)

    def _init_window(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(
            screen_geo.width() - AppConfig.WIDTH - 50, 
            50, 
            AppConfig.WIDTH + 40, 
            AppConfig.DUCK_AREA_HEIGHT + 40
        )

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.shell = UnifiedFrame()
        self.main_layout.addWidget(self.shell)
        
        self.inner_layout = QVBoxLayout(self.shell)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(0)
        
        self.duck_area = DuckArea()
        self.inner_layout.addWidget(self.duck_area)
        
        self.chat_area = ChatArea()
        self.chat_area.setFixedHeight(0)
        self.chat_area.hide()
        self.chat_area.message_sent.connect(self._handle_user_message)
        self.inner_layout.addWidget(self.chat_area)

        # Cień usunięty (aby uniknąć błędów graficznych)
        # self.glow = QGraphicsDropShadowEffect() ...

    def update_stress(self, stress: float):
        self.stress_level = max(0.0, min(1.0, stress))
        self.duck_area.set_stress_value(self.stress_level)
        
        new_state = DuckState.ZEN
        if self.stress_level < 0.2: new_state = DuckState.ZEN
        elif self.stress_level < 0.5: new_state = DuckState.FOCUS
        elif self.stress_level < 0.8: new_state = DuckState.WORRY
        else: new_state = DuckState.STOIC
        
        if new_state == DuckState.STOIC and not self.is_expanded:
            self._toggle_expand(True)
            self._handle_user_message("SYSTEM_TRIGGER: HIGH_STRESS")
        elif new_state != DuckState.STOIC and self.is_expanded:
            self._toggle_expand(False)

        self.change_state(new_state)

    def change_state(self, state_enum: DuckState):
        if state_enum == self.current_state_enum and self.duck_area.movie: return
        self.current_state_enum = state_enum
        
        config = DUCK_STATES_CONFIG[state_enum]
        colors = config["grad"]
        
        # Update UI
        self.shell.set_border_gradient(colors)
        self.duck_area.update_style(colors)
        self.chat_area.update_accent(colors)
        
        self._load_gif(config["file"])

    def _load_gif(self, filename: str):
        self.duck_area.load_gif(filename)

    def _handle_user_message(self, text: str):
        self.worker = AIWorker(text, self.stress_level)
        self.worker.response_ready.connect(self._on_ai_response)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _on_ai_response(self, text: str, duration: float):
        self.chat_area.add_response(text)
        self._voice_effect(duration)

    def _voice_effect(self, duration):
        self.is_speaking = True
        self.shell.set_border_gradient(AppConfig.GRADIENT_STOIC)
        QTimer.singleShot(int(duration * 1000), self._end_voice_effect)

    def _end_voice_effect(self):
        self.is_speaking = False
        config = DUCK_STATES_CONFIG[self.current_state_enum]
        self.shell.set_border_gradient(config["grad"])

    def _toggle_expand(self, expand: bool):
        if self.is_expanded == expand: return
        self.is_expanded = expand
        
        start_h = 0 if expand else AppConfig.CHAT_HEIGHT
        end_h = AppConfig.CHAT_HEIGHT if expand else 0
        base_h = AppConfig.DUCK_AREA_HEIGHT + 40
        
        if expand: self.chat_area.show()

        self.anim_timer = QTimer()
        self.anim_step = 0
        self.anim_steps = 25
        self.anim_delta = (end_h - start_h) / self.anim_steps
        self.anim_current_h = start_h
        
        def animate_step():
            self.anim_current_h += self.anim_delta
            self.anim_step += 1
            if self.anim_step >= self.anim_steps:
                self.chat_area.setFixedHeight(end_h)
                self.resize(self.width(), base_h + end_h)
                self.anim_timer.stop()
                if not expand: self.chat_area.hide()
            else:
                h = int(self.anim_current_h)
                self.chat_area.setFixedHeight(h)
                self.resize(self.width(), base_h + h)
        
        self.anim_timer.timeout.connect(animate_step)
        self.anim_timer.start(15)

    # --- DRAG & DROP ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: white; border: 1px solid #ddd; padding: 5px; color: black; }")
        ac = QAction("Zamknij", self)
        ac.triggered.connect(QApplication.quit)
        menu.addAction(ac)
        menu.exec(event.globalPosition().toPoint())

# --- ENTRY POINT ---
def dev_hotkeys(app):
    try:
        if keyboard.is_pressed('1'): app.update_stress(0.1)
        elif keyboard.is_pressed('2'): app.update_stress(0.4)
        elif keyboard.is_pressed('3'): app.update_stress(0.7)
        elif keyboard.is_pressed('4'): app.update_stress(0.95)
        elif keyboard.is_pressed('q'): QApplication.quit()
    except: pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = StoicDuckPro()
    window.show()
    
    timer = QTimer()
    timer.timeout.connect(lambda: dev_hotkeys(window))
    timer.start(100)
    
    sys.exit(app.exec())