import os
import csv
import time
import serial
import collections
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QLineEdit, 
    QMessageBox, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
)

class SerialWorker(QObject):
    data_received = pyqtSignal(str, str, str)

    def __init__(self, port="COM5", baud=9600):
        super().__init__()
        self.port = port
        self.baud = baud
        self.running = True
        self.ser = None
        self.raw_buffer = collections.deque(maxlen=10)
        self.history = collections.deque(maxlen=150)
        self.is_peak = False

    @pyqtSlot()
    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            last_peak_time = time.time()
            beats = []

            while self.running:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line.isdigit():
                        val = int(line)
                        self.raw_buffer.append(val)
                        
                        filtered_val = int(sum(self.raw_buffer) / len(self.raw_buffer))
                        self.history.append(filtered_val)
                        curr_time = time.time()
                        
                        if len(self.history) >= 50:
                            l_max = max(self.history)
                            l_min = min(self.history)
                            amp = l_max - l_min
                            
                            th_on = l_min + (amp * 0.7)
                            th_off = l_min + (amp * 0.4)
                            
                            if amp > 30:
                                if not self.is_peak and filtered_val > th_on:
                                    dur = curr_time - last_peak_time
                                    if dur > 0.3:
                                        bpm = int(60 / dur)
                                        if 40 < bpm < 180:
                                            beats.append(bpm)
                                            if len(beats) > 8:
                                                beats.pop(0)
                                        last_peak_time = curr_time
                                    self.is_peak = True
                                
                                elif self.is_peak and filtered_val < th_off:
                                    self.is_peak = False
                            else:
                                self.is_peak = False
                        
                        avg_bpm = int(sum(beats) / len(beats)) if beats else 0
                        
                        status_pulse = "OK" if avg_bpm > 0 else "Поиск..."
                        pulse_val = str(avg_bpm) if avg_bpm > 0 else "--"
                        
                        self.data_received.emit("OK", status_pulse, pulse_val)
                else:
                    time.sleep(0.005)
        except Exception:
            self.data_received.emit("FAIL", "FAIL", "ERR")

    def stop(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()

class AnalysisForm(QWidget):
    def __init__(self, operator_row: dict = None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.operator_row = operator_row or {}
        
        dir_path = os.path.dirname(__file__)
        self.csv_path = os.path.abspath(os.path.join(dir_path, 'operators_db.csv'))
        
        self.instr_window = None
        self.control_window = None

        self.W = 1000
        self.H = 450
        self.setFixedSize(self.W, self.H + 34)
        self.setWindowTitle("Анализ оператора")
        self.setStyleSheet("background-color: #D9D9D9;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_grey = QWidget(self)
        top_grey.setFixedHeight(30)
        top_layout = QHBoxLayout(top_grey)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("X", top_grey)
        self.btn_close.setFixedSize(45, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(
            "color: #FF0000; border: none; font-size: 24px; font-weight: bold;"
        )
        self.btn_close.clicked.connect(self.close)
        
        top_layout.addWidget(self.btn_close)
        main_layout.addWidget(top_grey)

        top_white = QWidget(self)
        top_white.setFixedHeight(4)
        top_white.setStyleSheet("background-color: #FFFFFF;")
        main_layout.addWidget(top_white)

        self.content_container = QWidget(self)
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        main_layout.addWidget(self.content_container)

        self._build_ui(content_layout)
        self._fill_data()

        self.thread = QThread()
        self.worker = SerialWorker(port="COM5")
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.data_received.connect(self._update_terminal_ui)
        self.thread.start()

    def _fill_data(self):
        f_name = self.operator_row.get('first_name', '')
        l_name = self.operator_row.get('last_name', '')
        self.lbl_op_name.setText(f"{l_name} {f_name}")
        
        if self.operator_row.get("pulse_threshold_critical"):
            self.edit_threshold.setText(self.operator_row["pulse_threshold_critical"])
        
        if self.operator_row.get("pulse_normal"):
            self.edit_normal.setText(self.operator_row["pulse_normal"])

    def _build_ui(self, parent_layout):
        header_container = QWidget()
        header_container.setFixedHeight(120)
        header_container.setStyleSheet("background-color: #FFFFFF;")
        
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        menu_frame = QFrame(); menu_frame.setStyleSheet("background-color: #D9D9D9;")
        logo_frame = QFrame(); logo_frame.setStyleSheet("background-color: #44CC29;")
        id_frame = QFrame(); id_frame.setStyleSheet("background-color: #D9D9D9;")

        header_layout.addWidget(menu_frame, stretch=1)
        header_layout.addWidget(logo_frame, stretch=1)
        header_layout.addWidget(id_frame, stretch=1)

        menu_vbox = QVBoxLayout(menu_frame)
        menu_vbox.setContentsMargins(10, 15, 10, 15)
        
        lbl_menu = QLabel("Меню управления")
        lbl_menu.setAlignment(Qt.AlignCenter)
        lbl_menu.setFont(QFont("Times New Roman", 18))
        menu_vbox.addWidget(lbl_menu)
        
        menu_vbox.addStretch()
        
        btn_hbox = QHBoxLayout()
        b_style = (
            "color: white; border-radius: 18px; "
            "font-family: 'Times New Roman'; font-size: 14px; font-weight: bold;"
        )
        
        self.btn_instr = QPushButton("Инструкция")
        self.btn_instr.setFixedHeight(36)
        self.btn_instr.setStyleSheet(
            f"QPushButton {{ background-color: #8D3C7F; {b_style} }} "
            f"QPushButton:hover {{ background-color: #9E4576; }}"
        )
        self.btn_instr.clicked.connect(self._go_instruction)
        
        self.btn_analysis = QPushButton("Анализ")
        self.btn_analysis.setFixedHeight(36)
        self.btn_analysis.setStyleSheet(
            f"QPushButton {{ background-color: #44CC29; {b_style} }} "
            f"QPushButton:hover {{ background-color: #45D44A; }}"
        )
        
        self.btn_control = QPushButton("Управление")
        self.btn_control.setFixedHeight(36)
        self.btn_control.setStyleSheet(
            f"QPushButton {{ background-color: #8D3C7F; {b_style} }} "
            f"QPushButton:hover {{ background-color: #9E4576; }}"
        )
        self.btn_control.clicked.connect(self._go_control)
        
        btn_hbox.addWidget(self.btn_instr)
        btn_hbox.addWidget(self.btn_analysis)
        btn_hbox.addWidget(self.btn_control)
        menu_vbox.addLayout(btn_hbox)

        logo_vbox = QVBoxLayout(logo_frame)
        logo_vbox.setContentsMargins(0, 10, 0, 10)
        logo_vbox.setSpacing(5)
        
        lbl_logo = QLabel("НейроБодр")
        lbl_logo.setAlignment(Qt.AlignCenter)
        lbl_logo.setStyleSheet("color: white; font-weight: bold;")
        lbl_logo.setFont(QFont("Times New Roman", 24))
        logo_vbox.addWidget(lbl_logo)
        
        line_layout = QHBoxLayout()
        line_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet("background-color: white;")
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line_layout.addWidget(line, stretch=3) 
        line_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        logo_vbox.addLayout(line_layout)
        
        lbl_desc = QLabel("Программа для мониторинга\nсостояния водителей")
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet("color: white;")
        lbl_desc.setFont(QFont("Times New Roman", 14))
        logo_vbox.addWidget(lbl_desc)

        id_vbox = QVBoxLayout(id_frame)
        id_vbox.setContentsMargins(0, 0, 0, 0)
        id_vbox.setSpacing(0)
        
        lbl_id_title = QLabel("Идентификация")
        lbl_id_title.setFixedHeight(44)
        lbl_id_title.setAlignment(Qt.AlignCenter)
        lbl_id_title.setFont(QFont("Times New Roman", 14))
        id_vbox.addWidget(lbl_id_title)
        
        id_sep = QFrame()
        id_sep.setFixedHeight(4)
        id_sep.setStyleSheet("background-color: white;")
        id_vbox.addWidget(id_sep)
        
        id_data_hbox = QHBoxLayout()
        id_data_hbox.setContentsMargins(20, 10, 20, 10)
        
        lbl_op_status = QLabel("Оператор\nопределен:")
        lbl_op_status.setFont(QFont("Times New Roman", 14))
        
        self.lbl_op_name = QLabel("")
        self.lbl_op_name.setFont(QFont("Times New Roman", 16))
        
        id_data_hbox.addWidget(lbl_op_status)
        id_data_hbox.addStretch()
        id_data_hbox.addWidget(self.lbl_op_name)
        
        id_vbox.addLayout(id_data_hbox)

        parent_layout.addWidget(header_container)

        body_container = QWidget()
        body_container.setStyleSheet("background-color: #FFFFFF;")
        
        body_main_layout = QVBoxLayout(body_container)
        body_main_layout.setContentsMargins(0, 4, 0, 0)
        body_main_layout.setSpacing(4)

        top_row = QWidget()
        top_row.setFixedHeight(44)
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        left_header = QFrame(); left_header.setStyleSheet("background-color: #D9D9D9;")
        right_header = QFrame(); right_header.setStyleSheet("background-color: #D9D9D9;")

        top_layout.addWidget(left_header, stretch=2)
        top_layout.addWidget(right_header, stretch=1)

        lh_layout = QVBoxLayout(left_header)
        lbl_analysis = QLabel("Анализ оператора")
        lbl_analysis.setAlignment(Qt.AlignCenter)
        lbl_analysis.setFont(QFont("Times New Roman", 14))
        lh_layout.addWidget(lbl_analysis)

        rh_layout = QVBoxLayout(right_header)
        lbl_conn = QLabel("Вид подключения")
        lbl_conn.setAlignment(Qt.AlignCenter)
        lbl_conn.setFont(QFont("Times New Roman", 14))
        rh_layout.addWidget(lbl_conn)

        body_main_layout.addWidget(top_row)

        bottom_row = QWidget()
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(4)

        self.left_col = QFrame(); self.left_col.setStyleSheet("background-color: #D9D9D9;")
        self.right_col = QFrame(); self.right_col.setStyleSheet("background-color: #D9D9D9;")

        bottom_layout.addWidget(self.left_col, stretch=2)
        bottom_layout.addWidget(self.right_col, stretch=1)

        body_main_layout.addWidget(bottom_row, stretch=1)
        parent_layout.addWidget(body_container, stretch=1)

        self._build_analysis_content()
        self._build_connection_content()

    def _build_analysis_content(self):
        left_layout = QVBoxLayout(self.left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0) 
        
        inputs_frame = QWidget()
        inputs_layout = QHBoxLayout(inputs_frame)
        inputs_layout.setContentsMargins(20, 15, 20, 15)
        
        fields_vbox = QVBoxLayout()
        fields_vbox.setSpacing(10)
        
        row1 = QHBoxLayout()
        lbl_p1 = QLabel("Укажите порог вашего пульса")
        lbl_p1.setFixedWidth(280)
        lbl_p1.setFont(QFont("Times New Roman", 12))
        self.edit_threshold = QLineEdit()
        self.edit_threshold.setFixedSize(200, 35)
        self.edit_threshold.setStyleSheet("background: white; padding-left: 5px; border: none;")
        self.edit_threshold.setFont(QFont("Times New Roman", 14))
        row1.addWidget(lbl_p1)
        row1.addWidget(self.edit_threshold)
        row1.addStretch()
        
        row2 = QHBoxLayout()
        lbl_p2 = QLabel("Укажите норму вашего пульса")
        lbl_p2.setFixedWidth(280)
        lbl_p2.setFont(QFont("Times New Roman", 12))
        self.edit_normal = QLineEdit()
        self.edit_normal.setFixedSize(200, 35)
        self.edit_normal.setStyleSheet("background: white; padding-left: 5px; border: none;")
        self.edit_normal.setFont(QFont("Times New Roman", 14))
        row2.addWidget(lbl_p2)
        row2.addWidget(self.edit_normal)
        row2.addStretch()
        
        fields_vbox.addLayout(row1)
        fields_vbox.addLayout(row2)
        
        inputs_layout.addLayout(fields_vbox)
        
        btn_save = QPushButton("Записать")
        btn_save.setFixedSize(110, 40)
        btn_save.setStyleSheet(
            "QPushButton { background: #2C2C2C; color: white; border-radius: 6px; "
            "font-weight: bold; font-size: 14px; } "
            "QPushButton:hover { background: #44CC29; }"
        )
        btn_save.clicked.connect(self._save_to_csv)
        inputs_layout.addWidget(btn_save, alignment=Qt.AlignVCenter | Qt.AlignRight)
        
        left_layout.addWidget(inputs_frame)

        line_sep = QFrame()
        line_sep.setFixedHeight(4)
        line_sep.setStyleSheet("background-color: white; border: none;")
        left_layout.addWidget(line_sep)
        
        term_header_frame = QWidget()
        term_header_frame.setFixedHeight(44)
        term_header_layout = QVBoxLayout(term_header_frame)
        term_header_layout.setContentsMargins(0,0,0,0)
        
        lbl_term_title = QLabel("Терминальный блок информации")
        lbl_term_title.setAlignment(Qt.AlignCenter)
        lbl_term_title.setFont(QFont("Times New Roman", 14))
        term_header_layout.addWidget(lbl_term_title)
        
        left_layout.addWidget(term_header_frame)
        
        term_content_frame = QWidget()
        term_content_layout = QVBoxLayout(term_content_frame)
        term_content_layout.setContentsMargins(20, 0, 20, 20)
        
        term_box = QFrame()
        term_box.setStyleSheet("background-color: black;")
        term_box_layout = QVBoxLayout(term_box)
        
        self.lbl_term = QLabel("")
        self.lbl_term.setStyleSheet("color: white; background: transparent;")
        self.lbl_term.setFont(QFont("Times New Roman", 11))
        self.lbl_term.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        term_box_layout.addWidget(self.lbl_term)
        
        term_content_layout.addWidget(term_box)
        left_layout.addWidget(term_content_frame, stretch=1)
        
        self._update_terminal_ui("WAIT", "WAIT", "--")

    def _build_connection_content(self):
        right_layout = QVBoxLayout(self.right_col)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        images_hbox = QHBoxLayout()
        images_hbox.setSpacing(20)
        
        for img_name in ["hand1.png", "hand2.png"]:
            box = QLabel()
            box.setStyleSheet("background-color: white;")
            img_path = f"assets/{img_name}"
            if os.path.exists(img_path):
                 box.setPixmap(QPixmap(img_path).scaled(100, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            box.setAlignment(Qt.AlignCenter)
            images_hbox.addWidget(box)
            
        right_layout.addLayout(images_hbox)
        
        right_layout.addSpacing(15)
        
        lbl_hint = QLabel("Наклеить электроды как показано\nна рисунке и подключить контакты")
        lbl_hint.setWordWrap(True)
        lbl_hint.setFont(QFont("Times New Roman", 11))
        right_layout.addWidget(lbl_hint)
        
        right_layout.addStretch()
        
        btn_next_layout = QHBoxLayout()
        btn_next_layout.addStretch()
        self.btn_next = QPushButton("Далее")
        self.btn_next.setFixedSize(110, 36)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet(
            "QPushButton { background: #2C2C2C; color: white; border-radius: 6px; "
            "font-weight: bold; font-size: 14px; } "
            "QPushButton:hover { background: #44CC29; }"
        )
        self.btn_next.clicked.connect(self._go_control)
        btn_next_layout.addWidget(self.btn_next)
        
        right_layout.addLayout(btn_next_layout)

    def _update_terminal_ui(self, status_conn, status_pulse, current_pulse):
        txt_conn = "OK" if status_conn == "OK" else "FAIL"
        lines = [
            f"Проверка сигнала . . . . . . . . . . . . . . . {txt_conn}",
            f"Проверка пульса . . . . . . . . . . . . . . . . {status_pulse}",
            f"Пульс . . . . . . . . . . . . . . . . . . . . . . . . . . . {current_pulse}"
        ]
        
        if txt_conn == "OK" and status_pulse == "OK" and current_pulse not in ["--", "ERR"]:
            lines.append("Для перехода в режим управления нажмите далее")
            
        self.lbl_term.setText("\n".join(lines))

    def _save_to_csv(self):
        th_val = self.edit_threshold.text().strip()
        norm_val = self.edit_normal.text().strip()
        
        if not th_val.isdigit() or not norm_val.isdigit():
            return QMessageBox.warning(self, "Ошибка", "Введите числовые значения пульса.")

        target_id = str(self.operator_row.get("id"))
        try:
            with open(self.csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                f_names = list(reader.fieldnames)
                if "pulse_threshold_critical" not in f_names:
                    f_names.append("pulse_threshold_critical")
                if "pulse_normal" not in f_names:
                    f_names.append("pulse_normal")
                if "current_pulse" not in f_names:
                    f_names.append("current_pulse")
                
                rows = list(reader)

            for row in rows:
                if row.get("id") == target_id:
                    row["pulse_threshold_critical"] = th_val
                    row["pulse_normal"] = norm_val
                    row["current_pulse"] = "0"
                    self.operator_row.update(row)
                    break

            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=f_names)
                writer.writeheader()
                writer.writerows(rows)
            
            QMessageBox.information(self, "Успех", "Данные пульса сохранены.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка CSV", f"Не удалось записать файл:\n{e}")

    def _go_instruction(self):
        self.close()
        from instruction_form import InstructionForm
        if not self.instr_window:
            self.instr_window = InstructionForm(self.operator_row)
        self.instr_window.show()
        
    def _go_control(self):
        self.close()
        from control_form import ControlForm
        if not self.control_window:
            self.control_window = ControlForm(self.operator_row)
        self.control_window.show()

    def closeEvent(self, event):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()
        super().closeEvent(event)