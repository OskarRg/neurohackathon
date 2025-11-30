from dataclasses import dataclass
from enum import Enum
import os
import sys

from PyQt6.QtWidgets import (
    QFrame,
)
from PyQt6.QtCore import (
    Qt,
    QRectF,
)
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QLinearGradient,
)


@dataclass(frozen=True)
class AppConfig:
    APP_NAME: str = "StoicQuack Pro"
    WIDTH: int = 300
    DUCK_AREA_HEIGHT: int = 320
    CHAT_HEIGHT: int = 400
    BORDER_RADIUS: int = 30
    MARGIN: int = 25

    BG_COLOR: str = "#FFFFFF"
    TEXT_PRIMARY: str = "#1A1A1A"
    TEXT_SECONDARY: str = "#666666"
    INPUT_BG: str = "#F5F5F5"
    COLOR_STOIC: str = "#F2994A"

    GRADIENT_ZEN: tuple[str, str] = ("#00F260", "#0575E6")
    GRADIENT_FOCUS: tuple[str, str] = ("#667eea", "#764ba2")
    GRADIENT_WORRY: tuple[str, str] = ("#FF8008", "#FFC837")
    GRADIENT_STOIC: tuple[str, str] = ("#F2994A", "#F2C94C")


class DuckState(Enum):
    ZEN = "zen"
    FOCUS = "focus"
    WORRY = "worry"
    STOIC = "stoic"


DUCK_STATES_CONFIG = {
    DuckState.ZEN: {"file": "duck_zen.gif", "grad": AppConfig.GRADIENT_ZEN},
    DuckState.FOCUS: {"file": "duck_focus.gif", "grad": AppConfig.GRADIENT_FOCUS},
    DuckState.WORRY: {"file": "duck_worry.gif", "grad": AppConfig.GRADIENT_WORRY},
    DuckState.STOIC: {"file": "duck_stoic.gif", "grad": AppConfig.GRADIENT_STOIC},
}


class ResourceManager:
    @staticmethod
    def get_asset_path(filename: str) -> str:
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_path, "assets", filename)
        return path


class UnifiedFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self._border_color = QColor(AppConfig.GRADIENT_ZEN[1])
        self._bg_color = QColor(AppConfig.BG_COLOR)
        self._gradient_colors = AppConfig.GRADIENT_ZEN

    def set_border_gradient(self, colors: tuple[str, str]):
        self._gradient_colors = colors
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        path = QPainterPath()
        path.addRoundedRect(rect, AppConfig.BORDER_RADIUS, AppConfig.BORDER_RADIUS)

        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor(self._gradient_colors[0]))
        gradient.setColorAt(1, QColor(self._gradient_colors[1]))

        pen = QPen(QBrush(gradient), 6)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
