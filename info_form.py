from utils import *

class InfoForm(BaseWindow):
    signal_next = pyqtSignal(dict)

    def __init__(self, operator_data=None):
        super().__init__(1000, 490, "Информация оператора")
        self.operator_data = operator_data if operator_data is not None else {}
        self.csv_file_path = csv_path()
        self.operators_directory = ensure_dirs()
        
        self.video_capture = None
        self.camera_timer = QTimer(self)
        self.clock_timer = QTimer(self)

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
        label_title = create_label("НейроБодр", 40, "white", Qt.AlignCenter)
        header_layout.addWidget(label_title)

        separator_line = QFrame()
        separator_line.setFixedSize(700, 4)
        separator_line.setStyleSheet("background-color: white;")
        header_layout.addWidget(separator_line, alignment=Qt.AlignCenter)

        label_subtitle = create_label("Программа для мониторинга состояния водителей", 16, "white", Qt.AlignCenter)
        header_layout.addWidget(label_subtitle)
        main_layout.addWidget(header_frame)

        grid_container = QWidget()
        grid_container.setStyleSheet("background-color: white;")
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(0, 4, 0, 0)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)
        main_layout.addWidget(grid_container)

        titles_list = ["Информация оператора", "Идентификация", "Информационный блок"]
        for index, text in enumerate(titles_list):
            title_frame = QFrame()
            title_frame.setStyleSheet(f"background-color: {COLOR_BG};")
            title_frame.setFixedHeight(44)
            title_layout = QHBoxLayout(title_frame)
            
            if index == 1:
                self.button_identify_dummy = create_button("Идентификация", 200, 35)
                title_layout.addWidget(self.button_identify_dummy)
            else:
                title_label = create_label(text, align=Qt.AlignCenter)
                title_layout.addWidget(title_label)
                
            grid_layout.addWidget(title_frame, 0, index)

        self.panel_left = QFrame()
        self.panel_middle = QFrame()
        self.panel_right = QFrame()
        
        panels_list = [self.panel_left, self.panel_middle, self.panel_right]
        for index, panel in enumerate(panels_list):
            panel.setStyleSheet(f"background-color: {COLOR_BG};")
            grid_layout.addWidget(panel, 1, index)
            
        left_layout = QVBoxLayout(self.panel_left)
        
        profile_layout = QHBoxLayout()
        self.photo_label = QLabel()
        self.photo_label.setFixedSize(90, 100)
        self.photo_label.setStyleSheet("background-color: white;")
        profile_layout.addWidget(self.photo_label)
        
        name_age_layout = QVBoxLayout()
        self.label_name = create_label("", 18)
        self.label_age = create_label("", 18)
        self.label_name.setWordWrap(True)
        name_age_layout.addWidget(self.label_name)
        name_age_layout.addWidget(self.label_age)
        
        profile_layout.addLayout(name_age_layout)
        left_layout.addLayout(profile_layout)
        
        self.label_datetime = create_label("")
        self.label_start_time = create_label("")
        self.label_drive_time = create_label("")
        self.label_time_left = create_label("")
        
        left_layout.addWidget(self.label_datetime)
        left_layout.addWidget(self.label_start_time)
        left_layout.addWidget(self.label_drive_time)
        left_layout.addWidget(self.label_time_left)

        middle_layout = QVBoxLayout(self.panel_middle)
        self.camera_view_label = QLabel()
        self.camera_view_label.setFixedSize(300, 220)
        self.camera_view_label.setStyleSheet("background-color: white;")
        middle_layout.addWidget(self.camera_view_label, alignment=Qt.AlignCenter)

        right_layout = QVBoxLayout(self.panel_right)
        
        status_row_layout = QHBoxLayout()
        self.label_status_text = create_label("")
        self.label_status_icon = QLabel()
        
        status_row_layout.addWidget(self.label_status_text)
        status_row_layout.addWidget(self.label_status_icon)
        right_layout.addLayout(status_row_layout)
        
        self.label_id_banner = create_label("", 18, align=Qt.AlignCenter)
        self.label_id_banner.setFixedHeight(46)
        right_layout.addWidget(self.label_id_banner)
        
        self.label_info_hint = create_label("")
        right_layout.addWidget(self.label_info_hint)
        
        self.button_next = create_button("Далее", 120, 36, self.go_next)
        right_layout.addWidget(self.button_next, alignment=Qt.AlignRight)

    def init_logic(self):
        self.camera_timer.timeout.connect(self.process_camera_frame)
        self.clock_timer.timeout.connect(self.update_clock_label)
        self.clock_timer.start(1000)

    def go_next(self):
        self.stop_camera()
        self.signal_next.emit(self.operator_data)
        self.hide()

    def set_operator_row(self, operator_data):
        self.operator_data = operator_data
        
        operator_id_string = str(operator_data.get("id", "0")).strip()
        self.operator_id = int(operator_id_string) if operator_id_string else 0
        
        self.is_verified = False
        self.result_rectangle = None
        self.result_color = None
        
        self.update_ui()
        self.update_identification_status()
        self.stop_camera()
        
        self.start_camera()
        QTimer.singleShot(1200, self.try_verify_face)

    def update_ui(self):
        data = self.operator_data if self.operator_data is not None else {}
            
        name_parts = [data.get(field) for field in ("last_name", "first_name", "middle_name") if data.get(field)]
        self.label_name.setText(" ".join(name_parts) or "—")
        
        age = data.get("age")
        self.label_age.setText(f"{age} лет" if age else "—")
            
        start_time = data.get("software_start_time", "—")
        self.label_start_time.setText(f"Время запуска ПО: {start_time or '—'}")
        self.label_drive_time.setText("Время в дороге: 00:00:00")
        self.label_time_left.setText("Оставшееся время: 09:00:00")
        
        image_path = os.path.join(self.operators_directory, f"ID_{id_str(self.operator_id)}.jpg")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path).scaled(90, 100, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            self.photo_label.setPixmap(pixmap)
            reference_image = opencv_imread_unicode(image_path)
            self.reference_face = cv2.cvtColor(reference_image, cv2.COLOR_BGR2GRAY) if reference_image is not None else None
        else:
            self.reference_face = None

    def update_clock_label(self):
        current_time_string = f"{now_date_str()} / {now_time_str()}"
        self.label_datetime.setText(f"Дата/время: {current_time_string}")

    def update_identification_status(self):
        is_ok = self.is_verified
        
        status_config = {
            True: ("определен", COLOR_GREEN, f"ID {id_str(self.operator_id)}", "Для запуска программы\nнажмите 'Далее'"),
            False: ("не определен", "red", "ID не определен", "Запуск программы\nневозможен")
        }
        
        status_result, banner_color, banner_text, hint_text = status_config[is_ok]
        
        self.label_status_text.setText(f"Оператор {status_result}")
        self.label_id_banner.setStyleSheet(f"background-color: {banner_color}; color: {COLOR_BTN_BG};")
        self.label_id_banner.setText(banner_text)
        self.label_info_hint.setText(hint_text)
        self.button_next.setEnabled(is_ok)
        
        icon_pixmap = make_icon(is_ok)
        if icon_pixmap:
            self.label_status_icon.setPixmap(icon_pixmap)

    def start_camera(self):
        self.video_capture = cv2.VideoCapture(0)
        self.camera_timer.start(30)
        return True

    def stop_camera(self):
        self.camera_timer.stop()
        if self.video_capture:
            self.video_capture.release()
        self.video_capture = None

    def process_camera_frame(self):
        if self.video_capture:
            is_successful, frame = self.video_capture.read()
            if is_successful:
                self.last_video_frame = cv2.flip(frame, 1)
                if self.result_rectangle:
                    x, y, width, height = self.result_rectangle
                    cv2.rectangle(self.last_video_frame, (x, y), (x + width, y + height), self.result_color, 2)
                draw_to_label(self.last_video_frame, self.camera_view_label)

    def try_verify_face(self):
        if self.last_video_frame is None:
            return
        
        live_face, face_location = process_face(self.last_video_frame, draw_rectangle=False)
        
        if face_location is not None and cv_compare_faces(self.reference_face, live_face):
            self.is_verified = True
        else:
            self.is_verified = False
        
        if face_location is not None:
            self.result_rectangle = face_location
            self.result_color = (0, 255, 0) if self.is_verified else (0, 0, 255)
        
        self.update_identification_status()
        
        if not self.is_verified:
            if QMessageBox.question(self, "Не пройдено", "Пройти идентификацию заново?") == QMessageBox.Yes:
                self.result_rectangle = None
                QTimer.singleShot(700, self.try_verify_face)

    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)