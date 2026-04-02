from utils import *

class RegistrationForm(BaseWindow):
    signal_next = pyqtSignal(dict)

    def __init__(self, software_start_time, operator_data=None):
        super().__init__(1000, 490, "Регистрация")
        self.operator_data = operator_data if operator_data is not None else {}
        self.csv_file_path = csv_path()
        self.operators_directory = ensure_dirs()
        self.software_start_time = software_start_time
        
        self.video_capture = None
        self.camera_timer = QTimer(self)
        self.input_fields = {}

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

        titles_list = ["Регистрация оператора", "Идентификация", "Информационный блок"]
        
        for index, text in enumerate(titles_list):
            title_frame = QFrame()
            title_frame.setStyleSheet(f"background-color: {COLOR_BG};")
            title_frame.setFixedHeight(44)
            title_layout = QHBoxLayout(title_frame)
            
            if index == 1:
                self.button_identify = create_button("Идентификация", 200, 35, self.on_identify_clicked)
                title_layout.addWidget(self.button_identify)
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
        
        for field_name in ["Фамилия", "Имя", "Отчество", "Возраст"]:
            row_layout = QHBoxLayout()
            field_label = create_label(field_name)
            row_layout.addWidget(field_label, 1)
            
            input_widget = create_line_edit(field_height=36, font_size=14)
            row_layout.addWidget(input_widget, 2)
            
            left_layout.addLayout(row_layout)
            self.input_fields[field_name] = input_widget
            
        button_save = create_button("Записать", 120, 34, self.on_save_clicked)
        left_layout.addWidget(button_save, alignment=Qt.AlignRight)

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

        self.label_id_banner = create_label("", align=Qt.AlignCenter)
        self.label_id_banner.setFixedHeight(46)
        right_layout.addWidget(self.label_id_banner)
        
        self.label_info_hint = create_label("")
        right_layout.addWidget(self.label_info_hint)
        
        self.button_next = create_button("Далее", 100, 34, self.go_next)
        right_layout.addWidget(self.button_next, alignment=Qt.AlignRight)

    def init_logic(self):
        self.camera_timer.timeout.connect(self.process_camera_frame)
        self.update_ui()

    def on_save_clicked(self):
        age_text = self.input_fields["Возраст"].text()
        if not age_text.isdigit() or int(age_text) < 18:
            QMessageBox.warning(self, "Ошибка", "Минимальный возраст 18 лет")
            return
            
        self.current_id = next_id(self.csv_file_path)
        with open(self.csv_file_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                str(self.current_id), 
                self.input_fields["Фамилия"].text(), 
                self.input_fields["Имя"].text(),
                self.input_fields["Отчество"].text(), 
                age_text, 
                now_date_str(), 
                now_time_str(),
                self.software_start_time, 
                "00:00:00"
            ])

    def on_identify_clicked(self):
        self.video_capture = cv2.VideoCapture(0)
        self.camera_timer.start(30)
        self.update_identification_status(False)
        QTimer.singleShot(1200, self.try_verify_face)

    def process_camera_frame(self):
        if self.video_capture:
            is_successful, frame = self.video_capture.read()
            if is_successful:
                self.last_video_frame = cv2.flip(frame, 1)
                draw_to_label(self.last_video_frame, self.camera_view_label)

    def update_ui(self):
        self.current_id = None
        self.last_video_frame = None
        
        for input_widget in self.input_fields.values():
            input_widget.clear()
            
        self.update_identification_status(False)
        self.stop_camera()

    def update_identification_status(self, is_ok):
        status_config = {
            True: ("определен", COLOR_GREEN, f"ID {id_str(self.current_id)}", "Для запуска программы\nнажмите 'Далее'"),
            False: ("не определен", "red", "ID не присвоен", "Запуск программы\nневозможен")
        }
        
        status_text, banner_color, banner_text, hint_text = status_config[is_ok]
        
        self.label_status_text.setText(f"Оператор {status_text}")
        self.label_id_banner.setStyleSheet(f"background-color: {banner_color}; color: {COLOR_BTN_BG};")
        self.label_id_banner.setText(banner_text)
        self.label_info_hint.setText(hint_text)
        self.button_next.setEnabled(is_ok)
        
        icon_pixmap = make_icon(is_ok)
        if icon_pixmap:
            self.label_status_icon.setPixmap(icon_pixmap)

    def try_verify_face(self):
        if self.last_video_frame is None:
            return
            
        face_image, face_location = process_face(self.last_video_frame, draw_rectangle=False)
        
        if face_image is not None:
            image_path = os.path.join(self.operators_directory, f"ID_{id_str(self.current_id)}.jpg")
            opencv_save_jpg(self.last_video_frame, image_path, face_location)
            self.update_identification_status(True)
            return
            
        if QMessageBox.question(self, "Не пройдено", "Пройти идентификацию заново?") == QMessageBox.Yes:
            QTimer.singleShot(700, self.try_verify_face)

    def stop_camera(self):
        self.camera_timer.stop()
        if self.video_capture:
            self.video_capture.release()
        self.video_capture = None
        self.camera_view_label.clear()

    def go_next(self):
        self.stop_camera()
        if self.current_id:
            operator_data = find_operator_by_id(self.csv_file_path, self.current_id)
            self.signal_next.emit(operator_data)
        self.hide()

    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)