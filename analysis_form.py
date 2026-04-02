import time
import serial
import collections
from utils import *

class SerialWorker(QObject):
    data_received = pyqtSignal(str, str, str)

    def __init__(self, port_name="COM5", baud_rate=9600):
        super().__init__()
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.is_running = True
        self.serial_connection = None

    @pyqtSlot()
    def run(self):
        try:
            self.serial_connection = serial.Serial(self.port_name, self.baud_rate, timeout=0.1)
            history_data = collections.deque(maxlen=100)
            beats_data = collections.deque(maxlen=10)
            last_peak_time = time.time()
            is_peak = False
            
            while self.is_running:
                line_text = self.serial_connection.readline().decode("utf-8", "ignore").strip()
                if not line_text.isdigit():
                    continue
                
                value = int(line_text)
                history_data.append(value)
                if len(history_data) < 50:
                    continue
                
                current_time = time.time()
                max_value = max(history_data)
                average_value = sum(history_data) / len(history_data)
                threshold_value = average_value + (max_value - average_value) * 0.5
                
                if value > threshold_value and not is_peak and (current_time - last_peak_time) > 0.4:
                    bpm_value = int(60 / (current_time - last_peak_time))
                    if 45 < bpm_value < 180:
                        beats_data.append(bpm_value)
                    last_peak_time = current_time
                    is_peak = True
                elif value < average_value:
                    is_peak = False
                
                if beats_data:
                    result_bpm = sum(beats_data) // len(beats_data)
                else:
                    result_bpm = 0
                    
                if result_bpm > 0:
                    self.data_received.emit("OK", "OK", str(result_bpm))
                else:
                    self.data_received.emit("OK", "Поиск...", "--")
        except:
            self.data_received.emit("FAIL", "FAIL", "ERR")

    def stop(self):
        self.is_running = False
        if self.serial_connection and self.serial_connection.is_open: 
            self.serial_connection.close()

class AnalysisForm(BaseWindow):
    signal_next = pyqtSignal(dict)

    def __init__(self, operator_data=None):
        super().__init__(1000, 490, "Анализ оператора")
        self.operator_data = operator_data if operator_data is not None else {}
        self.csv_file_path = csv_path()
        
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
        header_grid.addWidget(self.menu_frame, 0, 0)
        
        self.logo_frame = QFrame()
        self.logo_frame.setStyleSheet(f"background-color: {COLOR_GREEN};")
        header_grid.addWidget(self.logo_frame, 0, 1)
        
        self.id_frame = QFrame()
        self.id_frame.setStyleSheet(f"background-color: {COLOR_BG};")
        header_grid.addWidget(self.id_frame, 0, 2)
        
        main_layout.addWidget(header_container)

        menu_layout = QVBoxLayout(self.menu_frame)
        label_menu = create_label("Меню управления", 18, align=Qt.AlignCenter)
        menu_layout.addWidget(label_menu)
        
        buttons_layout = QHBoxLayout()
        button_style = "color: white; border-radius: 18px; font: bold 14px 'Times New Roman';"
        
        button_instruction = QPushButton("Инструкция")
        button_instruction.setFixedHeight(36)
        button_instruction.setStyleSheet(f"background-color: purple; {button_style}")
        buttons_layout.addWidget(button_instruction)
        
        button_analysis = QPushButton("Анализ")
        button_analysis.setFixedHeight(36)
        button_analysis.setStyleSheet(f"background-color: {COLOR_GREEN}; {button_style}")
        buttons_layout.addWidget(button_analysis)
        
        button_control = QPushButton("Управление")
        button_control.setFixedHeight(36)
        button_control.setStyleSheet(f"background-color: purple; {button_style}")
        buttons_layout.addWidget(button_control)
        
        menu_layout.addLayout(buttons_layout)

        logo_layout = QVBoxLayout(self.logo_frame)
        label_logo_title = create_label("НейроБодр", 24, "white", Qt.AlignCenter)
        logo_layout.addWidget(label_logo_title)
        
        separator_line = QFrame()
        separator_line.setFixedHeight(2)
        separator_line.setStyleSheet("background-color: white; margin-left: 40px; margin-right: 40px;")
        logo_layout.addWidget(separator_line)
        
        label_logo_subtitle = create_label("Программа для мониторинга\nсостояния водителей", color="white", align=Qt.AlignCenter)
        logo_layout.addWidget(label_logo_subtitle)

        id_layout = QVBoxLayout(self.id_frame)
        id_layout.setContentsMargins(0, 0, 0, 0)
        
        label_id_title = create_label("Идентификация", align=Qt.AlignCenter)
        label_id_title.setFixedHeight(48)
        label_id_title.setStyleSheet("border-bottom: 4px solid white;")
        id_layout.addWidget(label_id_title)
        
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
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(0, 4, 0, 0)
        main_layout.addWidget(body_container, stretch=1)

        self.left_column = QFrame()
        self.left_column.setStyleSheet(f"background-color: {COLOR_BG};")
        body_layout.addWidget(self.left_column, stretch=2)
        
        left_column_layout = QVBoxLayout(self.left_column)
        left_column_layout.setContentsMargins(0, 0, 0, 0)

        label_left_title = create_label("Анализ оператора", align=Qt.AlignCenter)
        label_left_title.setFixedHeight(44)
        label_left_title.setStyleSheet("border-bottom: 4px solid white;")
        left_column_layout.addWidget(label_left_title)

        inner_left_layout = QVBoxLayout()
        inner_left_layout.setSpacing(0)
        
        threshold_value = self.operator_data.get("pulse_threshold_critical")
        normal_value = self.operator_data.get("pulse_normal")
        
        input_frame = QWidget()
        input_layout = QHBoxLayout(input_frame)
        
        field_values_layout = QVBoxLayout()
        
        self.edit_threshold = self.build_input_row(field_values_layout, "Укажите порог вашего пульса", threshold_value)
        self.edit_normal = self.build_input_row(field_values_layout, "Укажите норму вашего пульса", normal_value)
        input_layout.addLayout(field_values_layout)
        
        if not (threshold_value and normal_value):
            button_save = create_button("Записать", 110, 40, self.save_data_to_csv)
            input_layout.addWidget(button_save, alignment=Qt.AlignCenter)
        
        inner_left_layout.addWidget(input_frame)
        
        separator_line_two = QFrame()
        separator_line_two.setFixedHeight(4)
        separator_line_two.setStyleSheet("background-color: white;")
        inner_left_layout.addWidget(separator_line_two)
        
        label_terminal_title = create_label("Терминальный блок информации", align=Qt.AlignCenter)
        label_terminal_title.setFixedHeight(44)
        inner_left_layout.addWidget(label_terminal_title)

        self.label_terminal = create_label("", align=Qt.AlignTop)
        self.label_terminal.setStyleSheet(f"background-color: {COLOR_BTN_BG}; color: white; padding: 20px; margin: 10px;")
        inner_left_layout.addWidget(self.label_terminal, stretch=1)
        left_column_layout.addLayout(inner_left_layout)

        self.right_column = QFrame()
        self.right_column.setStyleSheet(f"background-color: {COLOR_BG};")
        body_layout.addWidget(self.right_column, stretch=1)
        
        right_column_layout = QVBoxLayout(self.right_column)
        right_column_layout.setContentsMargins(0, 0, 0, 0)

        label_right_title = create_label("Вид подключения", align=Qt.AlignCenter)
        label_right_title.setFixedHeight(44)
        label_right_title.setStyleSheet("border-bottom: 4px solid white;")
        right_column_layout.addWidget(label_right_title)

        inner_right_layout = QVBoxLayout()
        inner_right_layout.setContentsMargins(10, 10, 10, 10)
        
        images_layout = QHBoxLayout()
        
        image_names = ["hand1.png", "hand2.png"]
        for name in image_names:
            image_box = QLabel()
            image_box.setStyleSheet("background-color: white;")
            image_box.setAlignment(Qt.AlignCenter)
            pixmap = QPixmap(f"assets/{name}").scaled(100, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_box.setPixmap(pixmap)
            images_layout.addWidget(image_box)
            
        inner_right_layout.addLayout(images_layout)
        
        label_connection_hint = create_label("Наклеить электроды как показано\nна рисунке и подключить контакты")
        inner_right_layout.addWidget(label_connection_hint)
        
        self.button_next = create_button("Далее", 110, 36, self.go_next)
        inner_right_layout.addWidget(self.button_next, alignment=Qt.AlignRight)
        right_column_layout.addLayout(inner_right_layout)

    def init_logic(self):
        self.update_terminal_interface("WAIT", "WAIT", "--")
        self.serial_thread = QThread()
        self.serial_worker = SerialWorker(port_name="COM5")
        self.serial_worker.moveToThread(self.serial_thread)
        self.serial_thread.started.connect(self.serial_worker.run)
        self.serial_worker.data_received.connect(self.update_terminal_interface)
        self.serial_thread.start()

    def go_next(self):
        self.stop_serial_worker()
        self.signal_next.emit(self.operator_data)
        self.hide()

    def build_input_row(self, parent_layout, text_label, value_data):
        row_layout = QHBoxLayout()
        label_widget = create_label(text_label)
        row_layout.addWidget(label_widget)
        
        if value_data:
            value_label = create_label(value_data)
            row_layout.addWidget(value_label)
            parent_layout.addLayout(row_layout)
            return None
            
        input_widget = create_line_edit(35, 14, 5)
        input_widget.setFixedWidth(200)
        row_layout.addWidget(input_widget)
        parent_layout.addLayout(row_layout)
        return input_widget

    def update_terminal_interface(self, signal_status, pulse_status, current_pulse):
        lines_list = [
            f"Проверка сигнала . . . . . . . . . . . . . . . {signal_status}",
            f"Проверка пульса . . . . . . . . . . . . . . . . {pulse_status}",
            f"Пульс . . . . . . . . . . . . . . . . . . . . . . . . . . . {current_pulse}"
        ]
        
        if signal_status == "OK" and pulse_status == "OK" and current_pulse not in ["--", "ERR"]:
            lines_list.append("Для перехода в режим управления нажмите далее")
            
        self.label_terminal.setText("\n".join(lines_list))

    def save_data_to_csv(self):
        threshold_text = self.edit_threshold.text().strip()
        normal_text = self.edit_normal.text().strip()
        
        if not threshold_text.isdigit() or not normal_text.isdigit():
            QMessageBox.warning(self, "Ошибка", "Введите числа.")
            return
        
        update_dictionary = {
            "pulse_threshold_critical": threshold_text, 
            "pulse_normal": normal_text, 
            "current_pulse": "0"
        }
        
        try:
            update_db(self.csv_file_path, self.operator_data.get("id"), update_dictionary)
            self.operator_data.update(update_dictionary)
            QMessageBox.information(self, "Успех", "Данные сохранены")
        except Exception as error:
            QMessageBox.critical(self, "Ошибка", str(error))

    def stop_serial_worker(self):   
        self.serial_worker.stop()
        self.serial_thread.quit()
        self.serial_thread.wait()

    def closeEvent(self, event):
        self.stop_serial_worker()
        super().closeEvent(event)