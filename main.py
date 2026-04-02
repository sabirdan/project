import sys
from utils import *

from registration_form import RegistrationForm
from auth_screen import AuthScreen
from info_form import InfoForm
from instruction_form import InstructionForm
from analysis_form import AnalysisForm
from control_form import ControlForm

class StartScreen(BaseWindow):
    signal_open_registration = pyqtSignal()
    signal_open_auth = pyqtSignal()

    def __init__(self):
        super().__init__(400, 200, "Старт")
        self.build_ui()

    def build_ui(self):
        main_layout = QVBoxLayout(self.content_container)

        title_label = create_label("Выберите необходимые\nдействия", 20)
        main_layout.addWidget(title_label)

        buttons_layout = QHBoxLayout()
        
        self.button_registration = create_button("Регистрация", 150, 50, self.signal_open_registration.emit)
        self.button_auth = create_button("Авторизация", 150, 50, self.signal_open_auth.emit)
        
        buttons_layout.addWidget(self.button_registration)
        buttons_layout.addWidget(self.button_auth)
        
        main_layout.addLayout(buttons_layout)

class WindowManager:
    def __init__(self):
        self.csv_file_path = csv_path()
        self.operators_directory = ensure_dirs()
        ensure_csv(self.csv_file_path)
        self.software_start_time = now_time_str()

        self.start_screen = StartScreen()
        self.start_screen.signal_open_registration.connect(self.show_registration_form)
        self.start_screen.signal_open_auth.connect(self.show_auth_screen)

    def show_start_screen(self):
        self.start_screen.show()

    def show_auth_screen(self):
        self.auth_screen = AuthScreen()
        self.auth_screen.signal_next.connect(self.show_info_form)
        self.auth_screen.show()

    def show_registration_form(self):
        self.registration_form = RegistrationForm(self.software_start_time)
        self.registration_form.signal_next.connect(self.show_instruction_form)
        self.registration_form.show()

    def show_info_form(self, operator_data):
        self.info_form = InfoForm(operator_data)
        self.info_form.signal_next.connect(self.show_instruction_form)
        self.info_form.set_operator_row(operator_data)
        self.info_form.show()

    def show_instruction_form(self, operator_data):
        self.instruction_form = InstructionForm(operator_data)
        self.instruction_form.signal_next.connect(self.show_analysis_form)
        self.instruction_form.show()

    def show_analysis_form(self, operator_data):
        self.analysis_form = AnalysisForm(operator_data)
        self.analysis_form.signal_next.connect(self.show_control_form)
        self.analysis_form.show()

    def show_control_form(self, operator_data):
        self.control_form = ControlForm(operator_data)
        self.control_form.show()

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    application = QApplication(sys.argv)
    application.setFont(QFont("Times New Roman", 14))
    
    manager = WindowManager()
    manager.show_start_screen()
    
    sys.exit(application.exec_())