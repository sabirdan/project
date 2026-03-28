import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QGuiApplication
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, 
    QVBoxLayout, QHBoxLayout
)
from utils import (
    _now_time_str, _ensure_dirs, _csv_path, _ensure_csv
)
from registration_form import RegistrationForm
from auth_screen import AuthScreen


class StartScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.software_start_time = _now_time_str()

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.ops_dir = _ensure_dirs(self.base_dir)
        self.csv_file = _csv_path(self.base_dir)
        _ensure_csv(self.csv_file)

        self.reg_form = None
        self.auth_form = None

        self.setFixedSize(400, 204)
        self.setWindowTitle("Старт")
        self.setStyleSheet("background-color: #D9D9D9;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.top_grey_area = QWidget(self)
        self.top_grey_area.setFixedHeight(30)
        
        top_layout = QHBoxLayout(self.top_grey_area)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("X", self.top_grey_area)
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(
            "color: #FF0000; border: none; font-size: 24px; font-weight: bold;"
        )
        self.btn_close.clicked.connect(self.close)
        
        top_layout.addWidget(self.btn_close)
        main_layout.addWidget(self.top_grey_area)

        self.top_white_line = QWidget(self)
        self.top_white_line.setFixedHeight(4)
        self.top_white_line.setStyleSheet("background-color: #FFFFFF;")
        main_layout.addWidget(self.top_white_line)

        content_container = QWidget(self)
        main_layout.addWidget(content_container)

        root = QVBoxLayout(content_container)
        root.setContentsMargins(28, 24, 28, 22)

        self.title = QLabel("Выберите необходимые\nдействия", self)
        self.title.setFont(QFont("Times New Roman", 20, QFont.Bold))
        root.addWidget(self.title, alignment=Qt.AlignLeft | Qt.AlignTop)
        root.addStretch(1)

        btn_row = QHBoxLayout()
        self.btn_reg = self._btn("Регистрация", self.open_registration)
        self.btn_auth = self._btn("Авторизация", self.open_auth)

        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_reg)
        btn_row.addSpacing(52)
        btn_row.addWidget(self.btn_auth)
        btn_row.addStretch(1)

        root.addLayout(btn_row)

    def _btn(self, text: str, callback) -> QPushButton:
        b = QPushButton(text, self)
        b.setFixedSize(156, 52)
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet("""
            QPushButton { 
                background-color: #2C2C2C; 
                color: #FFFFFF; 
                border-radius: 8px; 
                font-weight: 600; 
                font-size: 14px;
            }
            QPushButton:hover { background-color: #44CC29; }
            QPushButton:pressed { background-color: #1F1F1F; }
        """)
        b.clicked.connect(callback)
        return b

    def open_registration(self):
        if not self.reg_form:
            self.reg_form = RegistrationForm(
                self, self.csv_file, self.ops_dir, self.software_start_time
            )
            
        self.reg_form.reset_form()
        self.reg_form.show()
        self.hide()

    def open_auth(self):
        if not self.auth_form:
            self.auth_form = AuthScreen(
                self, self.csv_file, self.ops_dir, self.software_start_time
            )
            
        self.auth_form.show()
        self.hide()

    def closeEvent(self, event):
        if self.reg_form:
            self.reg_form.close()
            
        if self.auth_form:
            self.auth_form.close()
            
        super().closeEvent(event)


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    policy = Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(policy)

    app = QApplication(sys.argv)
    app.setFont(QFont("Times New Roman", 14))
    
    w = StartScreen()
    w.show()
    
    sys.exit(app.exec_())