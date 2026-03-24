import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QGuiApplication
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
)

from utils import (
    _now_time_str, _ensure_dirs, _csv_path, _ensure_csv
)
from registration_form import RegistrationForm
from auth_screen import AuthScreen


class StartScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.software_start_time = _now_time_str()

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.ops_dir = _ensure_dirs(self.base_dir)
        self.csv_file = _csv_path(self.base_dir)
        _ensure_csv(self.csv_file)

        self.reg_form = None
        self.auth_form = None

        self.setFixedSize(400, 170)
        self.setWindowTitle("Старт")
        self.setStyleSheet("background-color: #D9D9D9;")

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(0)

        self.title = QLabel("Выберите необходимые\nдействия", self)
        self.title.setWordWrap(True)
        self.title.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.title.setFont(QFont("Times New Roman", 20, QFont.Bold))
        self.title.setStyleSheet("color: #000000; background: transparent;")
        root.addWidget(self.title)

        root.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(0)

        self.btn_reg = self._btn("Регистрация")
        self.btn_auth = self._btn("Авторизация")

        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_reg)
        btn_row.addSpacing(52)
        btn_row.addWidget(self.btn_auth)
        btn_row.addStretch(1)

        root.addLayout(btn_row)

        self.btn_reg.clicked.connect(self.open_registration)
        self.btn_auth.clicked.connect(self.open_auth)

    def _btn(self, text: str) -> QPushButton:
        b = QPushButton(text, self)
        b.setFixedSize(156, 52)
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2C;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-family: "Times New Roman";
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #3A3A3A; }
            QPushButton:pressed { background-color: #1F1F1F; }
        """)
        return b


    def open_registration(self):
        if self.reg_form is None:
            self.reg_form = RegistrationForm(
                start_screen=self,
                csv_file=self.csv_file,
                ops_dir=self.ops_dir,
                software_start_time=self.software_start_time
            )
        
        self.reg_form.reset_form()
        
        self.reg_form.show()
        self.hide()

    def open_auth(self):
        if self.auth_form is None:
            self.auth_form = AuthScreen(
                start_screen=self,
                csv_file=self.csv_file,
                ops_dir=self.ops_dir,
                software_start_time=self.software_start_time
            )
        self.auth_form.show()
        self.hide()

    def closeEvent(self, event):
        try:
            if self.reg_form is not None:
                self.reg_form.close()
        except Exception:
            pass
        try:
            if self.auth_form is not None:
                self.auth_form.close()
        except Exception:
            pass
        super().closeEvent(event)


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setFont(QFont("Times New Roman", 14))

    w = StartScreen()
    w.show()
    sys.exit(app.exec_())