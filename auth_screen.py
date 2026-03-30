from PyQt5.QtCore import Qt, QRegularExpression
from PyQt5.QtGui import QRegularExpressionValidator
from PyQt5.QtWidgets import QPushButton, QMessageBox, QVBoxLayout, QHBoxLayout

from utils import find_operator_by_id, BaseWindow, create_label, create_line_edit, getbtn_style
from info_form import InfoForm

class AuthScreen(BaseWindow):
    def __init__(self, start_screen, csv_file: str, ops_dir: str, software_start_time: str):
        super().__init__(400, 204, "Авторизация")
        
        self.start_screen = start_screen
        self.csv_file = csv_file
        self.ops_dir = ops_dir
        self.software_start_time = software_start_time
        self.info_form = None

        root = QVBoxLayout(self.content_container)
        root.setContentsMargins(28, 24, 28, 22)

        title = create_label("Авторизация оператора\nвведите ID", 22, bold=True)
        root.addWidget(title, alignment=Qt.AlignLeft | Qt.AlignTop)
        root.addStretch(1)

        row = QHBoxLayout()
        row.setSpacing(18)

        self.in_id = create_line_edit()
        validator = QRegularExpressionValidator(QRegularExpression(r"\d+"), self)
        self.in_id.setValidator(validator)

        self.btn_login = QPushButton("Авторизоваться", self)
        self.btn_login.setFixedSize(156, 52)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet(getbtn_style())

        row.addWidget(self.in_id, 1)
        row.addWidget(self.btn_login, 0)
        root.addLayout(row)

        self.btn_login.clicked.connect(self.on_login)
        self.in_id.returnPressed.connect(self.on_login)

    def on_login(self):
        raw = self.in_id.text().strip()
        
        if not raw.isdigit() or int(raw) <= 0:
            QMessageBox.warning(self, "Авторизация", "Введите корректный числовой ID больше 0.")
            return

        row = find_operator_by_id(self.csv_file, int(raw))
        
        if not row:
            QMessageBox.warning(self, "Авторизация", "Оператор с таким ID не найден.")
            return

        if self.info_form is None:
            self.info_form = InfoForm(
                self.start_screen, self, row, self.csv_file, self.ops_dir
            )
        else:
            self.info_form.set_operator_row(row)

        self.info_form.show()
        self.hide()

    def close_event(self, event):
        if self.start_screen:
            self.start_screen.show()
        super().close_event(event)