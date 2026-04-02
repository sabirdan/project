from utils import *

class AuthScreen(BaseWindow):
    signal_next = pyqtSignal(dict)

    def __init__(self, operator_data=None):
        super().__init__(400, 200, "Авторизация")
        self.operator_data = operator_data if operator_data is not None else {}
        self.csv_file_path = csv_path()
        self.build_ui()

    def build_ui(self):
        main_layout = QVBoxLayout(self.content_container)

        title_label = create_label("Авторизация оператора\nвведите ID", 20)
        main_layout.addWidget(title_label)

        row_layout = QHBoxLayout()
        
        self.input_operator_id = create_line_edit()
        self.input_operator_id.setValidator(QIntValidator(1, 999999))
        self.input_operator_id.returnPressed.connect(self.on_login_clicked)
        row_layout.addWidget(self.input_operator_id)
        
        self.button_login = create_button("Авторизоваться", 150, 50, self.on_login_clicked)
        row_layout.addWidget(self.button_login)
        
        main_layout.addLayout(row_layout)

    def on_login_clicked(self):
        user_id_text = self.input_operator_id.text().strip()

        operator_data = find_operator_by_id(self.csv_file_path, int(user_id_text))
        self.signal_next.emit(operator_data)
        self.hide()

    def closeEvent(self, event):
        super().closeEvent(event)