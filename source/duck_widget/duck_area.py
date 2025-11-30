import os
from source.duck_widget.stylesheet_menager import StyleSheetManager
from source.duck_widget.utils import AppConfig, ResourceManager


from PyQt6.QtWidgets import (
    QLabel,
    QWidget,
    QVBoxLayout,
    QProgressBar,
)
from PyQt6.QtCore import (
    Qt,
    QSize,
)
from PyQt6.QtGui import (
    QMovie,
)


class DuckArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(AppConfig.DUCK_AREA_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            AppConfig.MARGIN, AppConfig.MARGIN, AppConfig.MARGIN, 10
        )

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)

        layout.addSpacing(20)
        layout.addWidget(self.progress_bar)

        self.update_style(AppConfig.GRADIENT_ZEN)
        self.movie = None
        self.target_size = QSize(100, 100)

    def update_style(self, colors: tuple[str, str]):
        self.progress_bar.setStyleSheet(
            StyleSheetManager.get_progress_bar_style(colors[0], colors[1])
        )

    def set_stress_value(self, value: float):
        self.progress_bar.setValue(int(value * 100))

    def load_gif(self, filename: str):
        path = ResourceManager.get_asset_path(filename)
        if not os.path.exists(path):
            return

        if self.movie:
            self.movie.stop()
            try:
                self.movie.frameChanged.disconnect()
            except Exception:
                pass

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
                Qt.TransformationMode.SmoothTransformation,
            )
            self.label.setPixmap(hq_pixmap)
