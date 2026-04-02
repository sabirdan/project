import sys
from utils import *

class AuthScreen(BaseWindow):
    def __init__(self, remote_form_instance):
        super().__init__(300, 150, "Авторизация")
        self.remote_form_instance = remote_form_instance
        self.setWindowModality(Qt.ApplicationModal)

        self.build_ui()

    def build_ui(self):
        main_layout = QVBoxLayout(self.content_container)

        label_title = create_label("Введите ID_оператора")
        main_layout.addWidget(label_title)

        row_layout = QHBoxLayout()

        self.input_operator_id = create_line_edit(field_height=36, font_size=18, text_padding=8)
        self.input_operator_id.setValidator(QIntValidator(1, 999999))
        
        self.button_login = create_button("Далее", 100, 36, self.on_login_clicked)

        row_layout.addWidget(self.input_operator_id, 1)
        row_layout.addWidget(self.button_login, 0)
        main_layout.addLayout(row_layout)

    def on_login_clicked(self):
        user_id_text = self.input_operator_id.text().strip()
        found_user_data = find_operator_by_id(csv_path(), int(user_id_text))

        self.remote_form_instance.init_session(found_user_data)
        self.remote_form_instance.show()
        self.close()


class RemoteForm(BaseWindow):
    def __init__(self):
        super().__init__(1000, 490, "Удаленный мониторинг")
        self.base_directory = os.path.dirname(os.path.abspath(__file__))
        
        self.operator_data = {}
        self.current_status = "NORMAL"
        self.last_played_status = None
        
        self.audio_player = QMediaPlayer()
        self.timer_monitor = QTimer(self)

        self.status_configuration = {
            "NORMAL": ("НОРМА", "green", "turquoise", COLOR_DISABLED, COLOR_DISABLED, None, "Состояние нормальное\nПульс {}"),
            "WARNING": ("ВНИМАНИЕ", "gold", COLOR_DISABLED, "gold", COLOR_DISABLED, "yellowSound.mp3", "Состояние 'ВНИМАНИЕ'\nПульс {}\nЗапуск звукового оповещения!\nНеобходимо связаться с водителем!"),
            "CRITICAL": ("КРИТИЧНО!", "red", COLOR_DISABLED, COLOR_DISABLED, "red", "redSound.mp3", "Состояние критичное!\nПульс {}\nЗапуск звукового оповещения!\nНеобходимо связаться с водителем!")
        }

        self.build_ui()
        self.init_logic()

    def build_ui(self):
        main_layout = QVBoxLayout(self.content_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header_frame = QFrame()
        header_frame.setFixedHeight(120)
        header_frame.setStyleSheet(f"background-color: {COLOR_GREEN};")
        
        header_layout = QVBoxLayout(header_frame)
        label_header_title = create_label("НейроБодр", 40, "white", Qt.AlignCenter)
        header_layout.addWidget(label_header_title)
        
        separator_line = QFrame()
        separator_line.setFixedSize(700, 4)
        separator_line.setStyleSheet("background-color: white;")
        header_layout.addWidget(separator_line, alignment=Qt.AlignCenter)
        
        label_header_subtitle = create_label("Программа для мониторинга состояния водителей", 16, "white", Qt.AlignCenter)
        header_layout.addWidget(label_header_subtitle)
        main_layout.addWidget(header_frame)

        grid_container = QWidget()
        grid_container.setStyleSheet("background-color: white;")
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(0, 4, 0, 0)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)
        main_layout.addWidget(grid_container)

        titles_list = ["Информация оператора", "Терминальный блок", "Блок индикации"]
        
        for index, text in enumerate(titles_list):
            title_frame = QFrame()
            title_frame.setStyleSheet(f"background-color: {COLOR_BG};")
            title_frame.setFixedHeight(44)
            title_layout = QHBoxLayout(title_frame)
            
            title_label = create_label(text, 14, align=Qt.AlignCenter)
            title_layout.addWidget(title_label)
                
            grid_layout.addWidget(title_frame, 0, index)

        self.panel_left = QFrame()
        self.panel_middle = QFrame()
        self.panel_right = QFrame()
        
        panels_list = [self.panel_left, self.panel_middle, self.panel_right]
        colors_list = [COLOR_BG, COLOR_BTN_BG, COLOR_BG]
        
        for index, panel in enumerate(panels_list):
            panel.setStyleSheet(f"background-color: {colors_list[index]};")
            grid_layout.addWidget(panel, 1, index)
            
        left_layout = QVBoxLayout(self.panel_left)
        
        profile_layout = QHBoxLayout()
        self.photo_label = QLabel()
        self.photo_label.setFixedSize(90, 100)
        self.photo_label.setStyleSheet("background-color: white;")
        profile_layout.addWidget(self.photo_label)
        
        name_age_layout = QVBoxLayout()
        self.label_name = create_label("", 16)
        self.label_name.setWordWrap(True)
        self.label_age = create_label("", 16)
        
        name_age_layout.addWidget(self.label_name)
        name_age_layout.addWidget(self.label_age)
        profile_layout.addLayout(name_age_layout)
        left_layout.addLayout(profile_layout)

        self.label_datetime = create_label("", 14)
        self.label_start_time = create_label("", 14)
        self.label_drive_time = create_label("", 14)
        self.label_time_left = create_label("", 14)
        self.label_status = create_label("", 14)
        
        left_layout.addWidget(self.label_datetime)
        left_layout.addWidget(self.label_start_time)
        left_layout.addWidget(self.label_drive_time)
        left_layout.addWidget(self.label_time_left)
        left_layout.addWidget(self.label_status)
        
        self.update_ui()

        middle_layout = QVBoxLayout(self.panel_middle)
        self.label_middle_info = create_label("", color="white", align=Qt.AlignTop)
        middle_layout.addWidget(self.label_middle_info)

        right_layout = QVBoxLayout(self.panel_right)
        
        pulse_layout = QHBoxLayout()
        label_pulse_title = create_label("Пульс:", 28)
        pulse_layout.addWidget(label_pulse_title)
        
        self.label_pulse_value = create_label("", 42, color="red")
        pulse_layout.addWidget(self.label_pulse_value)
        right_layout.addLayout(pulse_layout)

        shapes_layout = QHBoxLayout()
        self.shape_green = ShapeWidget("circle", COLOR_DISABLED, widget_size=80)
        self.shape_yellow = ShapeWidget("triangle", COLOR_DISABLED, widget_size=80)
        self.shape_red = ShapeWidget("square", COLOR_DISABLED, widget_size=80)
        
        shapes_layout.addWidget(self.shape_green)
        shapes_layout.addWidget(self.shape_yellow)
        shapes_layout.addWidget(self.shape_red)
        
        right_layout.addLayout(shapes_layout)
        right_layout.addStretch()

        button_stop_program = create_button("Стоп программа", 130, 40, self.stop_program)
        right_layout.addWidget(button_stop_program, alignment=Qt.AlignRight)

    def init_logic(self):
        self.timer_monitor.timeout.connect(self.update_monitor_data)

    def init_session(self, user_row_data):
        self.operator_data = user_row_data
        
        last_name = user_row_data.get("last_name", "")
        first_name = user_row_data.get("first_name", "")
        middle_name = user_row_data.get("middle_name", "")
        
        self.label_name.setText(f"{last_name} {first_name}\n{middle_name}")
        self.label_age.setText(f"{user_row_data.get('age', '')} лет")

        operator_id = int(user_row_data.get('id', '0'))
        photo_file_path = os.path.join(ensure_dirs(), f"ID_{id_str(operator_id)}.jpg")
        
        self.photo_label.setPixmap(QPixmap(photo_file_path).scaled(self.photo_label.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation))

        start_time_string = user_row_data.get('software_start_time', '00:00:00')
        self.label_start_time.setText(f"Время запуска ПО: {start_time_string}")
        self.timer_monitor.start(1000)

    def update_ui(self):
        self.label_name.setText("Фамилия Имя\nОтчество")
        self.label_age.setText("Возраст")
        self.label_datetime.setText("Дата/время: 00.00.0000 / 00:00:00")
        self.label_start_time.setText("Время запуска ПО: 00:00:00")
        self.label_drive_time.setText("Время в дороге: 00:00:00")
        self.label_time_left.setText("Оставшееся время: 00:00:00")
        self.label_status.setText("Состояние: ")

        default_photo_path = os.path.join(self.base_directory, "assets", "user.png")
        default_pixmap = QPixmap(default_photo_path)
        
        scaled_pixmap = default_pixmap.scaled(self.photo_label.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.photo_label.setPixmap(scaled_pixmap)

    def update_monitor_data(self):
        target_operator_id = self.operator_data.get("id")
        if not target_operator_id:
            return

        fresh_operator_data = find_operator_by_id(csv_path(), int(target_operator_id))
        current_pulse = 0
        operator_status = "NORMAL"
        drive_duration_text = "00:00:00"

        if fresh_operator_data:
            pulse_raw_text = fresh_operator_data.get("current_pulse", "0")
            if pulse_raw_text.isdigit():
                current_pulse = int(pulse_raw_text)
            else:
                current_pulse = 0
                
            operator_status = fresh_operator_data.get("operator_status", "NORMAL")
            drive_duration_text = fresh_operator_data.get("drive_duration", "00:00:00")

        self.current_status = operator_status
        current_datetime = datetime.now()
        date_string = current_datetime.strftime('%d.%m.%Y')
        time_string = current_datetime.strftime('%H:%M:%S')
        
        self.label_datetime.setText(f"Дата/время: {date_string} / {time_string}")
        self.label_drive_time.setText(f"Время в дороге: {drive_duration_text}")

        seconds_driven = parse_hms_to_seconds(drive_duration_text)
        remaining_seconds = max(0, 9 * 3600 - seconds_driven)
        remaining_time_text = seconds_to_hms(remaining_seconds)
        self.label_time_left.setText(f"Оставшееся время: {remaining_time_text}")

        self.update_indication_and_terminal(current_pulse)

    def update_indication_and_terminal(self, current_pulse):
        if current_pulse > 0:
            pulse_string = str(current_pulse)
        else:
            pulse_string = "--"
            
        self.label_pulse_value.setText(pulse_string)
        
        is_status_changed = (self.current_status != self.last_played_status)
        if is_status_changed:
            self.audio_player.stop()
            self.last_played_status = self.current_status

        status_text, text_color, color_green_shape, color_yellow_shape, color_red_shape, sound_file, terminal_template = self.status_configuration[self.current_status]

        self.label_status.setText(f"Состояние: <span style='color:{text_color}'>{status_text}</span>")
        self.label_pulse_value.setStyleSheet(f"color: {text_color};")
        
        self.shape_green.set_color(color_green_shape)
        self.shape_yellow.set_color(color_yellow_shape)
        self.shape_red.set_color(color_red_shape)
        
        self.label_middle_info.setText(terminal_template.format(pulse_string))

        if is_status_changed and sound_file:
            media_content = QMediaContent(QUrl.fromLocalFile(sound_file))
            self.audio_player.setMedia(media_content)
            self.audio_player.play()

    def stop_program(self):
        self.timer_monitor.stop()
        self.audio_player.stop()
        self.last_played_status = None

        self.shape_green.set_color(COLOR_DISABLED)
        self.shape_yellow.set_color(COLOR_DISABLED)
        self.shape_red.set_color(COLOR_DISABLED)

        self.update_ui()
        self.label_middle_info.setText("")
        self.label_pulse_value.setText("")

        self.auth_window = AuthScreen(self)
        self.auth_window.show()

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    application = QApplication(sys.argv)
    application.setFont(QFont("Times New Roman", 14))

    main_application_window = RemoteForm()
    main_application_window.show()

    authorization_window = AuthScreen(main_application_window)
    authorization_window.show()

    sys.exit(application.exec_())