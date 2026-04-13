import time
from analysis_form import SerialWorker
from utils import *

class ControlForm(BaseWindow):
    def __init__(self, operator_data=None):
        super().__init__(1000, 490, "Управление")
        self.operator_data = operator_data if operator_data is not None else {}
        self.csv_file_path = csv_path()
        
        self.bad_posture_start_time = None
        self.current_pulse = 0
        self.current_state = "NORMAL"
        self.remaining_seconds = 9 * 3600

        self.status_configuration = {
            "NORMAL": ("НОРМА", "green", "turquoise", COLOR_DISABLED, COLOR_DISABLED, None, "Состояние нормальное\nПульс {}"),
            "WARNING": ("ВНИМАНИЕ", "gold", COLOR_DISABLED, "gold", COLOR_DISABLED, "yellowSound.mp3", "Состояние оператора выходит за пределы\n«ВНИМАНИЕ»\nПульс {}\nЗапуск звукового оповещения «ВНИМАНИЕ»"),
            "CRITICAL": ("КРИТИЧНО!", "red", COLOR_DISABLED, COLOR_DISABLED, "red", "redSound.mp3", "Состояние критичное!\nПульс {}\nЗапуск звукового оповещения!")
        }
        
        self.pulse_minimum = 60
        self.pulse_maximum = 80
        self.pulse_critical = 100
        
        self.audio_player = QMediaPlayer()

        self.build_ui()
        self.init_logic()

    def build_ui(self):
        main_layout = QVBoxLayout(self.content_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header_container = QWidget()
        header_container.setFixedHeight(120)
        header_container.setStyleSheet("background-color: white;")
        header_grid = QGridLayout(header_container)
        header_grid.setContentsMargins(0, 0, 0, 0)
        header_grid.setColumnStretch(0, 2)
        header_grid.setColumnStretch(1, 3)
        header_grid.setColumnStretch(2, 2)

        self.menu_frame = QFrame()
        self.menu_frame.setStyleSheet(f"background-color: {COLOR_BG};")
        
        self.logo_frame = QFrame()
        self.logo_frame.setStyleSheet(f"background-color: {COLOR_GREEN};")
        
        self.id_frame = QFrame()
        self.id_frame.setStyleSheet(f"background-color: {COLOR_BG};")

        header_grid.addWidget(self.menu_frame, 0, 0)
        header_grid.addWidget(self.logo_frame, 0, 1)
        header_grid.addWidget(self.id_frame, 0, 2)
        main_layout.addWidget(header_container)

        menu_layout = QVBoxLayout(self.menu_frame)
        label_menu_title = create_label("Меню управления", 18, align=Qt.AlignCenter)
        menu_layout.addWidget(label_menu_title)
        
        buttons_layout = QHBoxLayout()
        button_style = "color: white; border-radius: 18px; font: bold 14px 'Times New Roman';"
        
        button_instruction = QPushButton("Инструкция")
        button_instruction.setFixedHeight(36)
        button_instruction.setStyleSheet(f"background-color: purple; {button_style}")
        buttons_layout.addWidget(button_instruction)
        
        button_analysis = QPushButton("Анализ")
        button_analysis.setFixedHeight(36)
        button_analysis.setStyleSheet(f"background-color: purple; {button_style}")
        buttons_layout.addWidget(button_analysis)
        
        button_control = QPushButton("Управление")
        button_control.setFixedHeight(36)
        button_control.setStyleSheet(f"background-color: {COLOR_GREEN}; {button_style}")
        buttons_layout.addWidget(button_control)
        
        menu_layout.addLayout(buttons_layout)

        logo_layout = QVBoxLayout(self.logo_frame)
        label_logo_title = create_label("НейроБодр", 24, "white", Qt.AlignCenter)
        logo_layout.addWidget(label_logo_title)
        
        line_layout = QHBoxLayout()
        separator_line = QFrame()
        separator_line.setFixedHeight(2)
        separator_line.setStyleSheet("background-color: white;")
        line_layout.addStretch(1)
        line_layout.addWidget(separator_line, stretch=3)
        line_layout.addStretch(1)
        logo_layout.addLayout(line_layout)
        
        label_logo_subtitle = create_label("Программа для мониторинга\nсостояния водителей", color="white", align=Qt.AlignCenter)
        logo_layout.addWidget(label_logo_subtitle)

        id_layout = QVBoxLayout(self.id_frame)
        id_layout.setContentsMargins(0, 0, 0, 0)
        
        label_id_title = create_label("Идентификация", align=Qt.AlignCenter)
        label_id_title.setFixedHeight(44)
        id_layout.addWidget(label_id_title)
        
        id_separator = QFrame()
        id_separator.setFixedHeight(4)
        id_separator.setStyleSheet("background-color: white;")
        id_layout.addWidget(id_separator)
        
        data_layout = QHBoxLayout()
        data_layout.setContentsMargins(10, 10, 10, 10)
        label_operator_defined = create_label("Оператор\nопределен:")
        data_layout.addWidget(label_operator_defined)
        
        first_name = self.operator_data.get("first_name", "")
        last_name = self.operator_data.get("last_name", "")
        label_operator_name = create_label(f"{last_name} {first_name}", 16)
        data_layout.addWidget(label_operator_name)
        id_layout.addLayout(data_layout)

        body_container = QWidget()
        body_container.setStyleSheet("background-color: white;")
        body_grid = QGridLayout(body_container)
        body_grid.setContentsMargins(0, 4, 0, 0)
        main_layout.addWidget(body_container, stretch=1)

        self.left_column = QFrame()
        self.left_column.setStyleSheet(f"background-color: {COLOR_BG};")
        
        self.video_column = QFrame()
        self.video_column.setStyleSheet(f"background-color: {COLOR_BTN_BG};")

        body_grid.addWidget(self.left_column, 0, 0)
        body_grid.addWidget(self.video_column, 0, 1)
        main_layout.addWidget(body_container, stretch=1)
        
        self.build_left_info_panel()
        self.build_video_area()

    def build_left_info_panel(self):
        left_panel_layout = QVBoxLayout(self.left_column)
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.setSpacing(0)
        
        info_frame = QFrame()
        info_frame.setStyleSheet(f"background-color: {COLOR_BG};")
        info_frame.setFixedHeight(85)
        info_grid_layout = QGridLayout(info_frame)
        
        self.label_datetime_value = create_label("", 12)
        start_time_text = self.operator_data.get("software_start_time", "")
        self.label_start_time_value = create_label(start_time_text, 12)
        self.label_state_value = create_label("")
        
        info_items = [
            ("Дата/время:", self.label_datetime_value),
            ("Время запуска:", self.label_start_time_value),
            ("Состояние оператора:", self.label_state_value)
        ]
        
        for row_index, (text_title, widget_value) in enumerate(info_items):
            title_label = create_label(text_title, 12)
            info_grid_layout.addWidget(title_label, row_index, 0)
            info_grid_layout.addWidget(widget_value, row_index, 1)

        left_panel_layout.addWidget(info_frame)
        
        separator_one = QFrame()
        separator_one.setFixedHeight(4)
        separator_one.setStyleSheet("background-color: white;")
        left_panel_layout.addWidget(separator_one)

        terminal_header_frame = QFrame()
        terminal_header_frame.setStyleSheet(f"background-color: {COLOR_BG};")
        terminal_header_frame.setFixedHeight(35)
        terminal_header_layout = QVBoxLayout(terminal_header_frame)
        label_terminal_title = create_label("Терминальный блок", align=Qt.AlignCenter)
        terminal_header_layout.addWidget(label_terminal_title)
        
        left_panel_layout.addWidget(terminal_header_frame)
        
        separator_two = QFrame()
        separator_two.setFixedHeight(4)
        separator_two.setStyleSheet("background-color: white;")
        left_panel_layout.addWidget(separator_two)

        self.label_terminal_text = create_label("", 11, color="white", align=Qt.AlignTop)
        self.label_terminal_text.setFixedHeight(140)
        self.label_terminal_text.setStyleSheet(f"background-color: {COLOR_BTN_BG}; padding: 5px; color: white;")
        
        left_panel_layout.addWidget(self.label_terminal_text)
        
        separator_three = QFrame()
        separator_three.setFixedHeight(4)
        separator_three.setStyleSheet("background-color: white;")
        left_panel_layout.addWidget(separator_three)

        time_header_frame = QFrame()
        time_header_frame.setStyleSheet(f"background-color: {COLOR_BG};")
        time_header_frame.setFixedHeight(35)
        time_header_layout = QVBoxLayout(time_header_frame)
        label_time_title = create_label("Допустимое время", align=Qt.AlignCenter)
        time_header_layout.addWidget(label_time_title)
        
        left_panel_layout.addWidget(time_header_frame)
        
        separator_four = QFrame()
        separator_four.setFixedHeight(4)
        separator_four.setStyleSheet("background-color: white;")
        left_panel_layout.addWidget(separator_four)

        time_clock_frame = QFrame()
        time_clock_frame.setStyleSheet(f"background-color: {COLOR_BG};")
        self.label_clock = create_label("09:00", 42, align=Qt.AlignCenter)
        time_clock_layout = QVBoxLayout(time_clock_frame)
        time_clock_layout.addWidget(self.label_clock)
        
        left_panel_layout.addWidget(time_clock_frame)

    def build_video_area(self):
        video_layout = QVBoxLayout(self.video_column)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_label_background = QLabel()
        video_layout.addWidget(self.video_label_background)
        self.video_capture_background = cv2.VideoCapture("videoBG.mp4")

        overlay_layout = QVBoxLayout(self.video_label_background)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        
        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(0)

        strip_frame = QFrame()
        strip_frame.setFixedHeight(70)
        strip_frame.setStyleSheet("background-color: rgba(255, 255, 255, 100); border: none;")
        strip_layout = QHBoxLayout(strip_frame)
        
        self.shape_green = ShapeWidget("circle", "turquoise")
        self.shape_yellow = ShapeWidget("triangle", "gold")
        self.shape_red = ShapeWidget("square", "red")
        
        strip_layout.addWidget(self.shape_green)
        strip_layout.addWidget(self.shape_yellow)
        strip_layout.addWidget(self.shape_red)
        strip_layout.addStretch()
        
        label_pulse_title = create_label("Пульс:", 28, color=COLOR_BTN_BG)
        label_pulse_title.setStyleSheet("background: transparent;")
        
        self.label_pulse_overlay = create_label("--", 42,)
        self.label_pulse_overlay.setStyleSheet("background: transparent;")
        
        strip_layout.addWidget(label_pulse_title)
        strip_layout.addWidget(self.label_pulse_overlay)

        face_frame = QFrame()
        face_frame.setFixedSize(220, 170)
        face_frame.setStyleSheet("background-color: white;")
        face_layout = QVBoxLayout(face_frame)
        
        self.label_camera_feed = QLabel()
        face_layout.addWidget(self.label_camera_feed)
        
        top_row_layout.addWidget(strip_frame, stretch=1, alignment=Qt.AlignTop)
        top_row_layout.addWidget(face_frame, alignment=Qt.AlignTop)
        
        overlay_layout.addLayout(top_row_layout)

    def init_logic(self):
        self.setup_thresholds()
        
        self.serial_thread = QThread()
        self.serial_worker = SerialWorker(port_name="COM5")
        self.serial_worker.moveToThread(self.serial_thread)
        self.serial_thread.started.connect(self.serial_worker.run)
        self.serial_worker.data_received.connect(self.on_pulse_data_received)
        self.serial_thread.start()
        
        self.timer_main_clock = QTimer(self)
        self.timer_main_clock.timeout.connect(self.update_time_logic)
        self.timer_main_clock.start(1000)
        
        self.video_capture = cv2.VideoCapture(0)
        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self.process_camera_frame)
        self.camera_timer.timeout.connect(self.update_video_frame)
        self.camera_timer.start(30)
        
        date_string = now_date_str()
        time_string = now_time_str()
        self.label_datetime_value.setText(f"{date_string} / {time_string}")

    def setup_thresholds(self):
        normal_value = self.operator_data.get("pulse_normal", "")
        critical_value = self.operator_data.get("pulse_threshold_critical", "")
        
        if "-" in normal_value:
            parts = normal_value.split("-")
            self.pulse_minimum = int(parts[0])
            self.pulse_maximum = int(parts[1])
        elif normal_value.isdigit():
            self.pulse_maximum = int(normal_value)
            
        if critical_value.isdigit():
            self.pulse_critical = int(critical_value)

    def update_video_frame(self):
        is_successful, video_frame = self.video_capture_background.read()
        if not is_successful:
            self.video_capture_background.set(cv2.CAP_PROP_POS_FRAMES, 0)
            is_successful, video_frame = self.video_capture_background.read()
            
        if is_successful:
            draw_to_label(video_frame, self.video_label_background)

    @pyqtSlot(str, str, str)
    def on_pulse_data_received(self, signal_code, status_pulse, pulse_string):
        if pulse_string.isdigit():
            self.current_pulse = int(pulse_string)
            self.label_pulse_overlay.setText(pulse_string)
        else:
            self.current_pulse = 0
            self.label_pulse_overlay.setText("--")
            
        self.check_operator_status()

    def process_camera_frame(self):
        if not self.video_capture:
            return
            
        is_successful, camera_frame = self.video_capture.read()
        if not is_successful:
            return
            
        camera_frame = cv2.flip(camera_frame, 1)
        face_image, face_location = process_face(camera_frame, draw_rectangle=True)
        
        if face_location is None:
            if not self.bad_posture_start_time:
                self.bad_posture_start_time = time.time()
        else:
            self.bad_posture_start_time = None
            
        draw_to_label(camera_frame, self.label_camera_feed)
        self.check_operator_status()

    def check_operator_status(self):
        if self.bad_posture_start_time:
            seconds_bad_posture = time.time() - self.bad_posture_start_time
        else:
            seconds_bad_posture = 0
            
        pulse_value = self.current_pulse
        calculated_state = "NORMAL"
        
        is_pulse_critically_low = pulse_value > 0 and pulse_value <= (self.pulse_minimum * 0.65)
        is_pulse_critically_high = pulse_value >= self.pulse_critical
        is_critical = is_pulse_critically_low or is_pulse_critically_high
        
        is_pulse_warning_low = pulse_value > 0 and pulse_value <= (self.pulse_minimum * 0.85)
        is_pulse_warning_high = pulse_value >= (self.pulse_maximum * 1.15) and pulse_value < self.pulse_critical
        is_warning = is_pulse_warning_low or is_pulse_warning_high
        
        if is_critical or seconds_bad_posture > 7.0:
            calculated_state = "CRITICAL"
        elif is_warning or seconds_bad_posture > 4.0:
            calculated_state = "WARNING"
            
        if calculated_state != self.current_state:
            self.current_state = calculated_state
            self.update_ui()
            
        pulse_text = str(pulse_value) if pulse_value > 0 else "--"
        terminal_message = self.status_configuration[self.current_state][6].format(pulse_text)
        self.label_terminal_text.setText(terminal_message)

    def update_ui(self):
        self.audio_player.stop()
        
        state_text, text_color, color_green_shape, color_yellow_shape, color_red_shape, sound_file, _ = self.status_configuration[self.current_state]
        
        self.label_state_value.setText(state_text)
        self.label_state_value.setStyleSheet(f"color: {text_color};")
        
        self.label_pulse_overlay.setStyleSheet(f"color: {text_color}; background: transparent;")
        
        self.shape_green.set_color(color_green_shape)
        self.shape_yellow.set_color(color_yellow_shape)
        self.shape_red.set_color(color_red_shape)
        
        if sound_file:
            media_content = QMediaContent(QUrl.fromLocalFile(sound_file))
            self.audio_player.setMedia(media_content)
            self.audio_player.play()

    def update_time_logic(self):
        self.label_datetime_value.setText(f"{now_date_str()} / {now_time_str()}")
        
        self.remaining_seconds -= 1
        h = self.remaining_seconds // 3600
        m = (self.remaining_seconds % 3600) // 60
        self.label_clock.setText(f"{h:02d}:{m:02d}")
            
        self.update_csv_log()

    def update_csv_log(self):
        target_id = self.operator_data.get("id", "")
        if not target_id:
            return
            
        seconds_driven = (9 * 3600) - self.remaining_seconds
        drive_duration_string = seconds_to_hms(seconds_driven)
        
        update_dictionary = {
            "current_pulse": str(self.current_pulse), 
            "operator_status": self.current_state, 
            "drive_duration": drive_duration_string
        }
        
        try:
            update_db(self.csv_file_path, target_id, update_dictionary)
        except Exception:
            pass

    def closeEvent(self, event):
        self.update_csv_log()
        
        self.serial_worker.stop()
        self.serial_thread.quit()
        self.serial_thread.wait()
        
        self.timer_main_clock.stop()
        self.camera_timer.stop()
        self.video_capture.release()
        self.video_capture_background.release()
        self.audio_player.stop()
            
        super().closeEvent(event)