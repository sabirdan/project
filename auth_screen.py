from PyQt5.QtCore import Qt, QRegularExpression
from PyQt5.QtGui import QFont, QRegularExpressionValidator
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit,
    QMessageBox, QVBoxLayout, QHBoxLayout
)
from utils import _find_operator_by_id
from info_form import InfoForm


class AuthScreen(QWidget):
    def __init__(self, start_screen, csv_file: str, ops_dir: str, software_start_time: str):
        super().__init__()
        self.start_screen = start_screen
        self.csv_file = csv_file
        self.ops_dir = ops_dir
        self.software_start_time = software_start_time

        self.info_form = None

        self.setFixedSize(400, 170)
        self.setWindowTitle("Авторизация")
        self.setStyleSheet("background-color: #D9D9D9;")

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(0)

        title = QLabel("Авторизация оператора\nвведите ID", self)
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        title.setFont(QFont("Times New Roman", 22, QFont.Bold))
        title.setStyleSheet("color: #000000; background: transparent;")
        root.addWidget(title)

        root.addStretch(1)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(18)

        self.in_id = QLineEdit(self)
        self.in_id.setFixedHeight(52)
        self.in_id.setFont(QFont("Times New Roman", 24, QFont.Normal))
        self.in_id.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: none;
                padding-left: 12px;
            }
        """)
        self.in_id.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d+"), self))

        self.btn_login = QPushButton("Авторизоваться", self)
        self.btn_login.setFixedSize(156, 52)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2C; color: #FFFFFF; border: none;
                border-radius: 8px; font-family: "Times New Roman"; font-size: 14px; font-weight: 600;
            } 
            QPushButton:hover { background-color: #44CC29; }
            QPushButton:pressed { background-color: #1F1F1F; }
        """)

        row.addWidget(self.in_id, 1)
        row.addWidget(self.btn_login, 0)
        root.addLayout(row)

        self.btn_login.clicked.connect(self._on_login)
        self.in_id.returnPressed.connect(self._on_login)


    def _on_login(self):
        raw = (self.in_id.text() or "").strip()
        if not raw.isdigit():
            QMessageBox.warning(self, "Авторизация", "Введите числовой ID.")
            return

        op_id = int(raw)
        if op_id <= 0:
            QMessageBox.warning(self, "Авторизация", "ID должен быть больше 0.")
            return

        row = _find_operator_by_id(self.csv_file, op_id)
        if not row:
            QMessageBox.warning(self, "Авторизация", "Оператор с таким ID не найден.")
            return

        if self.info_form is None:
            self.info_form = InfoForm(
                start_screen=self.start_screen,
                auth_screen=self,
                operator_row=row,
                csv_file=self.csv_file,
                ops_dir=self.ops_dir
            )
        else:
            self.info_form.set_operator_row(row)

        self.info_form.show()
        self.hide()

    def closeEvent(self, event):
        try:
            if self.start_screen is not None:
                self.start_screen.show()
        except Exception:
            pass
        super().closeEvent(event)