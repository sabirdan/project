import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QGuiApplication
from PyQt5.QtWidgets import (
    QApplication, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit
)

from utils import (
    _now_time_str, _ensure_dirs, _csv_path, _ensure_csv,
    BaseWindow, create_label, COLOR_BTN_BG, COLOR_GREEN
)

def create_line_edit(height=52, font_size=24, padding=12):
    le = QLineEdit()
    le.setFixedHeight(height)
    le.setFont(QFont("Times New Roman", font_size))
    le.setStyleSheet(f"background-color: white; border: none; padding-left: {padding}px;")
    return le

def get_btn_style():
    return f"""
        QPushButton {{ 
            background-color: {COLOR_BTN_BG}; 
            color: white; 
            border-radius: 8px; 
            font-family: "Times New Roman"; 
            font-size: 14px; 
            font-weight: 600; 
        }} 
        QPushButton:hover {{ background-color: {COLOR_GREEN}; }}
    """

from registration_form import RegistrationForm
from auth_screen import AuthScreen

class StartScreen(BaseWindow):
    def __init__(self):
        super().__init__(400, 204, "Старт")
        
        self.software_start_time = _now_time_str()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.ops_dir = _ensure_dirs(self.base_dir)
        self.csv_file = _csv_path(self.base_dir)
        _ensure_csv(self.csv_file)

        self.reg_form = None
        self.auth_form = None

        root = QVBoxLayout(self.content_container)
        root.setContentsMargins(28, 24, 28, 22)

        self.title = create_label("Выберите необходимые\nдействия", 20, bold=True)
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
        b.setStyleSheet(get_btn_style())
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