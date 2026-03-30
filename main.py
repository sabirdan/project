import sys
import os
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QGuiApplication
from PyQt5.QtWidgets import (
    QApplication, QPushButton, QVBoxLayout, QHBoxLayout
)

from utils import (
    now_time_str, ensure_dirs, csv_path, ensure_csv,
    BaseWindow, create_label, getbtn_style
)

from registration_form import RegistrationForm
from auth_screen import AuthScreen
from info_form import InfoForm
from instruction_form import InstructionForm
from analysis_form import AnalysisForm
from control_form import ControlForm

class StartScreen(BaseWindow):
    sig_open_reg = pyqtSignal()
    sig_open_auth = pyqtSignal()

    def __init__(self):
        super().__init__(400, 204, "Старт")
        root = QVBoxLayout(self.content_container)
        root.setContentsMargins(28, 24, 28, 22)

        self.title = create_label("Выберите необходимые\nдействия", 20, bold=True)
        root.addWidget(self.title, alignment=Qt.AlignLeft | Qt.AlignTop)
        root.addStretch(1)

        btn_row = QHBoxLayout()
        self.btn_reg = self.btn("Регистрация", lambda: self.sig_open_reg.emit())
        self.btn_auth = self.btn("Авторизация", lambda: self.sig_open_auth.emit())

        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_reg)
        btn_row.addSpacing(52)
        btn_row.addWidget(self.btn_auth)
        btn_row.addStretch(1)

        root.addLayout(btn_row)

    def btn(self, text: str, callback) -> QPushButton:
        b = QPushButton(text, self)
        b.setFixedSize(156, 52)
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet(getbtn_style())
        b.clicked.connect(callback)
        return b


class WindowManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.ops_dir = ensure_dirs(self.base_dir)
        self.csv_file = csv_path(self.base_dir)
        ensure_csv(self.csv_file)
        self.software_start_time = now_time_str()

        self.start_screen = StartScreen()
        
        self.start_screen.sig_open_reg.connect(self.show_registration)
        self.start_screen.sig_open_auth.connect(self.show_auth)

        self.reg_form = None
        self.auth_form = None
        self.info_form = None
        self.instr_form = None
        self.analysis_form = None
        self.control_form = None

    def show_start(self):
        self.start_screen.show()

    def show_registration(self):
        self.start_screen.hide()
        if not self.reg_form:
            self.reg_form = RegistrationForm(self.csv_file, self.ops_dir, self.software_start_time)
            self.reg_form.sig_go_back.connect(self.show_start)
        self.reg_form.reset_form()
        self.reg_form.show()

    def show_auth(self):
        self.start_screen.hide()
        if not self.auth_form:
            self.auth_form = AuthScreen(self.csv_file, self.ops_dir, self.software_start_time)
            self.auth_form.sig_go_back.connect(self.show_start)
            self.auth_form.sig_auth_success.connect(self.show_info)
        self.auth_form.show()

    def show_info(self, operator_row):
        if not self.info_form:
            self.info_form = InfoForm(operator_row, self.csv_file, self.ops_dir)
            self.info_form.sig_go_back.connect(self.show_auth)
            self.info_form.sig_go_next.connect(self.show_instruction)
        else:
            self.info_form.set_operator_row(operator_row)
        self.info_form.show()

    def show_instruction(self, operator_row):
        if not self.instr_form:
            self.instr_form = InstructionForm(operator_row)
            self.instr_form.sig_go_analysis.connect(self.show_analysis)
            self.instr_form.sig_go_control.connect(self.show_control)
        else:
            self.instr_form.operator_row = operator_row
        self.instr_form.show()

    def show_analysis(self, operator_row):
        if not self.analysis_form:
            self.analysis_form = AnalysisForm(operator_row)
            self.analysis_form.sig_go_instruction.connect(self.show_instruction)
            self.analysis_form.sig_go_control.connect(self.show_control)
        else:
            self.analysis_form.operator_row = operator_row
            self.analysis_form.fill_data()
        self.analysis_form.show()

    def show_control(self, operator_row):
        if not self.control_form:
            self.control_form = ControlForm(operator_row)
            self.control_form.sig_go_instruction.connect(self.show_instruction)
            self.control_form.sig_go_analysis.connect(self.show_analysis)
        else:
            self.control_form.operator_row = operator_row
            self.control_form.load_settings_from_csv()
        self.control_form.show()


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    policy = Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(policy)

    app = QApplication(sys.argv)
    app.setFont(QFont("Times New Roman", 14))
    
    manager = WindowManager()
    manager.show_start()
    
    sys.exit(app.exec_())