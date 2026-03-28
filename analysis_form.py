import os
import csv
import time
import serial
import collections
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QLineEdit, 
    QMessageBox, QVBoxLayout, QHBoxLayout
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
        self.HEADER_H = 120
        self.SECTION_H = 44
        self.GRID_T = 4
        self.BODY_H = self.H - self.HEADER_H

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
        self.content_container.setFixedSize(self.W, self.H)
        main_layout.addWidget(self.content_container)

        self._build_ui()
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

    def _build_ui(self):
        col_w = self.W // 3
        left_w = (self.W // 3) * 2
        right_w = self.W - left_w

        menu_frame = QFrame(self.content_container)
        menu_frame.setGeometry(0, 0, col_w, self.HEADER_H)
        
        lbl_menu = QLabel("Меню управления", menu_frame)
        lbl_menu.setGeometry(0, 15, col_w, 30)
        lbl_menu.setAlignment(Qt.AlignCenter)
        lbl_menu.setFont(QFont("Times New Roman", 18))

        btn_w = (col_w - 16) // 3
        b_style = (
            "color: white; border-radius: 18px; "
            "font-family: 'Times New Roman'; font-size: 14px; font-weight: bold;"
        )

        self.btn_instr = QPushButton("Инструкция", menu_frame)
        self.btn_instr.setGeometry(0, 65, btn_w, 36)
        self.btn_instr.setStyleSheet(
            f"QPushButton {{ background-color: #8D3C7F; {b_style} }} "
            f"QPushButton:hover {{ background-color: #9E4576; }}"
        )
        self.btn_instr.clicked.connect(self._go_instruction)

        self.btn_analysis = QPushButton("Анализ", menu_frame)
        self.btn_analysis.setGeometry(btn_w + 8, 65, btn_w, 36)
        self.btn_analysis.setStyleSheet(
            f"QPushButton {{ background-color: #44CC29; {b_style} }} "
            f"QPushButton:hover {{ background-color: #45D44A; }}"
        )

        self.btn_control = QPushButton("Управление", menu_frame)
        self.btn_control.setGeometry((btn_w + 8) * 2, 65, col_w - (btn_w + 8) * 2, 36)
        self.btn_control.setStyleSheet(
            f"QPushButton {{ background-color: #8D3C7F; {b_style} }} "
            f"QPushButton:hover {{ background-color: #9E4576; }}"
        )
        self.btn_control.clicked.connect(self._go_control)

        logo_frame = QFrame(self.content_container)
        logo_frame.setGeometry(col_w, 0, col_w, self.HEADER_H)
        logo_frame.setStyleSheet("background: #44CC29;")
        
        lbl_logo = QLabel("НейроБодр", logo_frame)
        lbl_logo.setGeometry(0, 10, col_w, 50)
        lbl_logo.setAlignment(Qt.AlignCenter)
        lbl_logo.setStyleSheet("color: white;")
        lbl_logo.setFont(QFont("Times New Roman", 20))

        line = QFrame(logo_frame)
        line.setGeometry(int(col_w * 0.2), 60, int(col_w * 0.6), 2)
        line.setStyleSheet("background-color: white;")

        lbl_desc = QLabel("Программа для мониторинга\nсостояния водителей", logo_frame)
        lbl_desc.setGeometry(0, 65, col_w, 50)
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet("color: white;")
        lbl_desc.setFont(QFont("Times New Roman", 14))

        id_frame = QFrame(self.content_container)
        id_frame.setGeometry(col_w * 2, 0, right_w, self.HEADER_H)
        
        lbl_id_title = QLabel("Идентификация", id_frame)
        lbl_id_title.setGeometry(0, 5, right_w, 35)
        lbl_id_title.setAlignment(Qt.AlignCenter)
        lbl_id_title.setFont(QFont("Times New Roman", 14))

        id_sep = QFrame(id_frame)
        id_sep.setGeometry(0, 45, right_w, self.GRID_T)
        id_sep.setStyleSheet("background-color: white;")

        lbl_op_status = QLabel("Оператор\nопределен:", id_frame)
        lbl_op_status.setGeometry(20, 55, 110, 60)
        lbl_op_status.setFont(QFont("Times New Roman", 14))
        
        self.lbl_op_name = QLabel("", id_frame)
        self.lbl_op_name.setGeometry(150, 55, right_w - 160, 60)
        self.lbl_op_name.setFont(QFont("Times New Roman", 16))

        self._section_header(self.content_container, "Анализ оператора", 0, self.HEADER_H, left_w)
        self._build_analysis_content(QFrame(self.content_container), left_w)

        self._section_header(self.content_container, "Вид подключения", left_w, self.HEADER_H, right_w)
        self._build_connection_content(QFrame(self.content_container), left_w, right_w)

        self._draw_grid(col_w, left_w)

    def _section_header(self, parent, text, x, y, w):
        h = QFrame(parent)
        h.setGeometry(x, y, w, self.SECTION_H)
        lbl = QLabel(text, h)
        lbl.setGeometry(0, 0, w, self.SECTION_H)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Times New Roman", 14))

    def _build_analysis_content(self, parent, w):
        parent.setGeometry(0, self.HEADER_H + self.SECTION_H, w, self.BODY_H - self.SECTION_H)
        
        lbl_p1 = QLabel("Укажите порог вашего пульса", parent)
        lbl_p1.setGeometry(20, 15, 280, 35)
        lbl_p1.setFont(QFont("Times New Roman", 12))
        
        self.edit_threshold = QLineEdit(parent)
        self.edit_threshold.setGeometry(305, 15, 200, 35)
        self.edit_threshold.setStyleSheet("background: white; padding-left: 5px;")
        self.edit_threshold.setFont(QFont("Times New Roman", 14))
        
        lbl_p2 = QLabel("Укажите норму вашего пульса", parent)
        lbl_p2.setGeometry(20, 53, 280, 35)
        lbl_p2.setFont(QFont("Times New Roman", 12))
        
        self.edit_normal = QLineEdit(parent)
        self.edit_normal.setGeometry(305, 53, 200, 35)
        self.edit_normal.setStyleSheet("background: white; padding-left: 5px;")
        self.edit_normal.setFont(QFont("Times New Roman", 14))

        btn_save = QPushButton("Записать", parent)
        btn_save.setGeometry(525, 30, 110, 40) 
        btn_save.setStyleSheet(
            "QPushButton { background: #2C2C2C; color: white; border-radius: 6px; "
            "font-weight: bold; font-size: 14px; } "
            "QPushButton:hover { background: #44CC29; }"
        )
        btn_save.clicked.connect(self._save_to_csv)

        line_sep = QFrame(parent)
        line_sep.setGeometry(0, 95, w, self.GRID_T)
        line_sep.setStyleSheet("background-color: white;")

        lbl_term_title = QLabel("Терминальный блок информации", parent)
        lbl_term_title.setGeometry(0, 105, w, 30)
        lbl_term_title.setAlignment(Qt.AlignCenter)
        lbl_term_title.setFont(QFont("Times New Roman", 14))

        term_box = QFrame(parent)
        term_box.setGeometry(20, 140, w - 40, 125)
        term_box.setStyleSheet("background-color: black;")

        self.lbl_term = QLabel("", term_box)
        self.lbl_term.setGeometry(20, 10, w - 80, 105)
        self.lbl_term.setStyleSheet("color: white; background: transparent;")
        self.lbl_term.setFont(QFont("Times New Roman", 11))
        self._update_terminal_ui("WAIT", "WAIT", "--")

    def _build_connection_content(self, parent, x_offset, w):
        parent.setGeometry(x_offset, self.HEADER_H + self.SECTION_H, w, self.BODY_H - self.SECTION_H)
        block_w = (w - 70) // 2 
        
        for i, img_name in enumerate(["hand1.png", "hand2.png"]):
            box = QLabel(parent)
            box.setGeometry(25 + (block_w + 20) * i, 20, block_w, 150)
            img_path = f"assets/{img_name}"
            box.setPixmap(QPixmap(img_path).scaled(block_w, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            box.setAlignment(Qt.AlignCenter)

        lbl_hint = QLabel(
            "Наклеить электроды как показано\nна рисунке и подключить контакты", 
            parent
        )
        lbl_hint.setGeometry(25, 180, w - 50, 50)
        lbl_hint.setWordWrap(True)
        lbl_hint.setFont(QFont("Times New Roman", 11))

        self.btn_next = QPushButton("Далее", parent)
        self.btn_next.setGeometry(w - 145, 230, 110, 36)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet(
            "QPushButton { background: #2C2C2C; color: white; border-radius: 6px; "
            "font-weight: bold; font-size: 14px; } "
            "QPushButton:hover { background: #44CC29; }"
        )
        self.btn_next.clicked.connect(self._go_control)

    def _draw_grid(self, col_w, left_w):
        for x in [col_w, col_w * 2]:
            sep = QFrame(self.content_container)
            sep.setGeometry(x - 2, 0, 4, self.HEADER_H)
            sep.setStyleSheet("background-color: white;")
            
        for y in [self.HEADER_H, self.HEADER_H + self.SECTION_H]:
            sep = QFrame(self.content_container)
            sep.setGeometry(0, y, self.W, 4)
            sep.setStyleSheet("background-color: white;")
            
        sep_v = QFrame(self.content_container)
        sep_v.setGeometry(left_w - 2, self.HEADER_H, 4, self.BODY_H)
        sep_v.setStyleSheet("background-color: white;")

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