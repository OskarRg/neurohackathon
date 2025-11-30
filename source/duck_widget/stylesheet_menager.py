from source.duck_widget.utils import AppConfig


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
                line-height: 1.3;
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
        return f"""
            QTextEdit {{
                background-color: {AppConfig.INPUT_BG};
                border: 1px solid transparent;
                border-radius: 20px;
                color: {AppConfig.TEXT_PRIMARY};
                padding: 10px 15px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }}
            QTextEdit:focus {{
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
            }}
            /* Styl dla stanu zablokowanego (gdy AI myśli) */
            QTextEdit:disabled {{
                background-color: #EEEEEE;
                color: #AAAAAA;
            }}
            
            /* Ukrycie scrollbarów w polu input */
            QScrollBar:vertical, QScrollBar:horizontal {{
                width: 0px;
                height: 0px;
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
                padding: 0 12px;
                height: 40px;
                outline: none;
            }}
            QPushButton:hover {{
                /* zachowaj zaokrąglony kształt na hover */
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 {color1}, stop:1 {color2});
                border-radius: 20px;
                margin: 0;
            }}
            QPushButton:pressed {{
                /* delikatny efekt "wciśnięcia" bez zmiany kształtu */
                padding-top: 2px;
            }}
            QPushButton:disabled {{
                background-color: #CCCCCC;
                color: #888888;
            }}
        """

    @staticmethod
    def get_record_btn_style(color1: str, color2: str) -> str:
        # Styl dla przycisku nagrywania (neutralny / przygotowany pod przyszłe aktywności)
        return f"""
            QPushButton {{
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                                  stop:0 #FFFFFF, stop:1 #F3F4F6);
                color: {AppConfig.TEXT_PRIMARY};
                border-radius: 20px;
                border: 1px solid #E2E8F0;
                font-size: 16px;
            }}
            QPushButton:hover {{
                border: 1px solid {color2};
            }}
            QPushButton:disabled {{
                background-color: #F7F7F7;
                color: #BBBBBB;
            }}
        """
