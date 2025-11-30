import sys
import logging
import keyboard

from source.duck_widget.chat_area import ChatArea
from source.duck_widget.duck_area import DuckArea
from source.duck_widget.utils import (
    DUCK_STATES_CONFIG,
    AppConfig,
    DuckState,
    UnifiedFrame,
)

# winsound fallback for playback on Windows
try:
    import winsound
except Exception:
    winsound = None

# PyQt Imports
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QMenu,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QEvent,
)
from PyQt6.QtGui import (
    QFont,
    QAction,
)

# --- 0. LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("StoicQuack")

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
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(
            screen_geo.width() - AppConfig.WIDTH - 50,
            50,
            AppConfig.WIDTH + 40,
            AppConfig.DUCK_AREA_HEIGHT + 40,
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
        self.inner_layout.addWidget(self.chat_area)

        # Install event filters on main widgets so context menu is handled
        # regardless of which child widget was clicked.
        for w in (
            self,
            self.shell,
            self.duck_area,
            getattr(self.duck_area, "label", None),
            self.chat_area,
            getattr(self.chat_area, "history", None),
            getattr(self.chat_area, "input", None),
            getattr(self.chat_area, "btn", None),
            getattr(self.chat_area, "record_btn", None),
        ):
            if w is not None:
                w.installEventFilter(self)

    def eventFilter(self, obj, event):
        # Catch right-click mouse press (earlier than ContextMenu) and ContextMenu events
        # so our custom menu is shown for the whole widget instead of child default menus.
        if event.type() == QEvent.Type.MouseButtonPress:
            try:
                if event.button() == Qt.MouseButton.RightButton:
                    try:
                        gp = event.globalPosition().toPoint()
                    except Exception:
                        gp = event.globalPos()
                    self._show_context_menu(gp)
                    return True
            except Exception:
                pass

        if event.type() == QEvent.Type.ContextMenu:
            try:
                gp = event.globalPosition().toPoint()
            except Exception:
                gp = event.globalPos()
            self._show_context_menu(gp)
            return True

        return super().eventFilter(obj, event)

    def _show_context_menu(self, gp):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: white; border: 1px solid #ddd; padding: 5px; color: black; }"
        )
        ac = QAction("Close", self)
        ac.triggered.connect(QApplication.quit)
        menu.addAction(ac)
        menu.exec(gp)

    def update_stress(self, stress: float):
        self.stress_level = max(0.0, min(1.0, stress))
        self.duck_area.set_stress_value(self.stress_level)

        new_state = DuckState.ZEN
        if self.stress_level < 0.2:
            new_state = DuckState.ZEN
        elif self.stress_level < 0.5:
            new_state = DuckState.FOCUS
        elif self.stress_level < 0.8:
            new_state = DuckState.WORRY
        else:
            new_state = DuckState.STOIC

        if new_state == DuckState.STOIC and not self.is_expanded:
            self._toggle_expand(True)
        elif new_state != DuckState.STOIC and self.is_expanded:
            self._toggle_expand(False)

        self.change_state(new_state)

    def change_state(self, state_enum: DuckState):
        if state_enum == self.current_state_enum and self.duck_area.movie:
            return
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

    def _on_ai_response(self, text: str, duration: float):
        self.chat_area.add_response(text)
        # INTERFACE BLOCKADE LIFTED
        self.chat_area.set_locked(False)
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
        if self.is_expanded == expand:
            return
        self.is_expanded = expand

        start_h = 0 if expand else AppConfig.CHAT_HEIGHT
        end_h = AppConfig.CHAT_HEIGHT if expand else 0
        base_h = AppConfig.DUCK_AREA_HEIGHT + 40

        if expand:
            self.chat_area.show()

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
                if not expand:
                    self.chat_area.hide()
            else:
                h = int(self.anim_current_h)
                self.chat_area.setFixedHeight(h)
                self.resize(self.width(), base_h + h)

        self.anim_timer.timeout.connect(animate_step)
        self.anim_timer.start(15)

    # --- DRAG & DROP ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: white; border: 1px solid #ddd; padding: 5px; color: black; }"
        )
        ac = QAction("Close", self)
        ac.triggered.connect(QApplication.quit)
        menu.addAction(ac)
        # QContextMenuEvent may provide globalPos() (QPoint) instead of globalPosition()
        try:
            gp = event.globalPosition().toPoint()
        except Exception:
            gp = event.globalPos()
        menu.exec(gp)


# --- ENTRY POINT ---
def dev_hotkeys(app):
    try:
        if keyboard.is_pressed("1"):
            app.update_stress(0.1)
        elif keyboard.is_pressed("2"):
            app.update_stress(0.4)
        elif keyboard.is_pressed("3"):
            app.update_stress(0.7)
        elif keyboard.is_pressed("4"):
            app.update_stress(0.95)
        elif keyboard.is_pressed("q"):
            QApplication.quit()
    except Exception:
        pass


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
