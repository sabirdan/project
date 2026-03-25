import os
import csv
import time
import serial
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QLineEdit, QMessageBox
)

import collections


class SerialWorker(QObject):
    data_received = pyqtSignal(str, str, str)

    def __init__(self, port="COM5", baud=9600):
        super().__init__()
        self.port = port
        self.baud = baud
        self.running = True
        self.ser = None
        
        self.filter_size = 10
        self.raw_buffer = collections.deque(maxlen=self.filter_size)
        self.threshold_on = 650
        self.threshold_off = 500
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
                        
                        current_time = time.time()
                        
                        if not self.is_peak:
                            if filtered_val > self.threshold_on:
                                duration = current_time - last_peak_time
                                if duration > 0.3:
                                    bpm = int(60 / duration)
                                    if 40 < bpm < 180:
                                        beats.append(bpm)
                                        if len(beats) > 8: beats.pop(0)
                                    
                                    last_peak_time = current_time
                                    self.is_peak = True
                        else:
                            if filtered_val < self.threshold_off:
                                self.is_peak = False
                        
                        avg_bpm = int(sum(beats) / len(beats)) if beats else 0
                        pulse_str = str(avg_bpm) if avg_bpm > 0 else "--"
                        status_pulse = "OK" if avg_bpm > 0 else "Поиск..."
                        
                        self.data_received.emit("OK", status_pulse, pulse_str)
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
        
        self.operator_row = operator_row if operator_row else {}
        self.csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'operators_db.csv'))

        self.instr_window = None
        self.control_window = None
        self.control_window = None

        self.W = 1000
        self.H = 450
        self.HEADER_H = 120
        self.BODY_H = self.H - self.HEADER_H
        self.SECTION_H = 44 
        self.GRID_T = 4     

        self.setFixedSize(self.W, self.H)
        self.setWindowTitle("Анализ оператора")
        self.setStyleSheet("background-color: #D9D9D9;")

        self._build_ui()
        self._fill_data()

        self.thread = QThread()
        self.worker = SerialWorker(port="COM5")
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.data_received.connect(self._update_terminal_ui)
        self.thread.start()

    def _fill_data(self):
        f_name = self.operator_row.get("first_name", "")
        l_name = self.operator_row.get("last_name", "")
        self.lbl_op_name.setText(f"{l_name} {f_name}")
        
        if self.operator_row.get("pulse_threshold_critical"):
            self.edit_threshold.setText(self.operator_row.get("pulse_threshold_critical"))
        if self.operator_row.get("pulse_normal"):
            self.edit_normal.setText(self.operator_row.get("pulse_normal"))

    def _build_ui(self):
        col_one_w = self.W // 3 
        left_body_w = col_one_w * 2
        right_body_w = self.W - left_body_w

        menu_frame = QFrame(self)
        menu_frame.setGeometry(0, 0, col_one_w, self.HEADER_H)
        menu_frame.setStyleSheet("background: #D9D9D9; border: none;")
        
        lbl_menu = QLabel("Меню управления", menu_frame)
        lbl_menu.setGeometry(0, 15, col_one_w, 30)
        lbl_menu.setAlignment(Qt.AlignCenter)
        lbl_menu.setFont(QFont("Times New Roman", 18))

        spacing = 8
        btn_h = 36
        btn_y = 65
        total_btn_w = col_one_w - (spacing * 2)
        btn_w = total_btn_w // 3

        base_style = "color: white; border: none; border-radius: 18px; font-family: 'Times New Roman'; font-size: 14px; font-weight: bold;"
        green_style = f"QPushButton {{ background-color: #44CC29; {base_style} }} QPushButton:hover {{ background-color: #45D44A; }}"
        purple_style = f"QPushButton {{ background-color: #8D3C7F; {base_style} }} QPushButton:hover {{ background-color: #9E4576; }}"

        self.btn_instr = QPushButton("Инструкция", menu_frame)
        self.btn_instr.setGeometry(0, btn_y, btn_w, btn_h)
        self.btn_instr.setStyleSheet(purple_style)
        self.btn_instr.clicked.connect(self._go_instruction)

        self.btn_analysis = QPushButton("Анализ", menu_frame)
        self.btn_analysis.setGeometry(btn_w + spacing, btn_y, btn_w, btn_h)
        self.btn_analysis.setStyleSheet(green_style)

        self.btn_control = QPushButton("Управление", menu_frame)
        self.btn_control.setGeometry((btn_w + spacing) * 2, btn_y, col_one_w - (btn_w + spacing) * 2, btn_h)
        self.btn_control.setStyleSheet(purple_style)
        self.btn_control.clicked.connect(self._go_control)

        logo_frame = QFrame(self)
        logo_frame.setGeometry(col_one_w, 0, col_one_w, self.HEADER_H)
        logo_frame.setStyleSheet("background: #44CC29; border: none;")
        
        lbl_logo = QLabel("НейроБодр", logo_frame)
        lbl_logo.setGeometry(0, 10, col_one_w, 50)
        lbl_logo.setAlignment(Qt.AlignCenter)
        lbl_logo.setStyleSheet("color: white;")
        lbl_logo.setFont(QFont("Times New Roman", 20))
        
        line = QFrame(logo_frame)
        line.setGeometry(int(col_one_w * 0.2), 60, int(col_one_w * 0.6), 2)
        line.setStyleSheet("background-color: white;")

        lbl_desc = QLabel("Программа для мониторинга\nсостояния водителей", logo_frame)
        lbl_desc.setGeometry(0, 65, col_one_w, 50)
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet("color: white;")
        lbl_desc.setFont(QFont("Times New Roman", 14))

        id_frame = QFrame(self)
        id_frame.setGeometry(col_one_w * 2, 0, right_body_w, self.HEADER_H)
        id_frame.setStyleSheet("background: #D9D9D9; border: none;")
        
        lbl_id_title = QLabel("Идентификация", id_frame)
        lbl_id_title.setGeometry(0, 5, right_body_w, 35)
        lbl_id_title.setAlignment(Qt.AlignCenter)
        lbl_id_title.setFont(QFont("Times New Roman", 14))

        id_sep = QFrame(id_frame)
        id_sep.setGeometry(0, 45, right_body_w, self.GRID_T)
        id_sep.setStyleSheet("background-color: white;")

        lbl_op_status = QLabel("Оператор\nопределен:", id_frame)
        lbl_op_status.setGeometry(20, 55, 110, 60)
        lbl_op_status.setFont(QFont("Times New Roman", 14))
        
        self.lbl_op_name = QLabel("", id_frame)
        self.lbl_op_name.setGeometry(150, 55, right_body_w - 160, 60)
        self.lbl_op_name.setFont(QFont("Times New Roman", 16))
        self.lbl_op_name.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        analys_header = QFrame(self)
        analys_header.setGeometry(0, self.HEADER_H, left_body_w, self.SECTION_H)
        analys_header.setStyleSheet("background: #D9D9D9; border: none;")
        
        lbl_analys_h = QLabel("Анализ оператора", analys_header)
        lbl_analys_h.setGeometry(0, 0, left_body_w, self.SECTION_H)
        lbl_analys_h.setAlignment(Qt.AlignCenter)
        lbl_analys_h.setFont(QFont("Times New Roman", 14))

        analys_body = QFrame(self)
        analys_body.setGeometry(0, self.HEADER_H + self.SECTION_H, left_body_w, self.BODY_H - self.SECTION_H)
        analys_body.setStyleSheet("background: transparent;")
        self._build_analysis_content(analys_body, left_body_w)

        conn_header = QFrame(self)
        conn_header.setGeometry(left_body_w, self.HEADER_H, right_body_w, self.SECTION_H)
        conn_header.setStyleSheet("background: #D9D9D9; border: none;")
        
        lbl_conn_h = QLabel("Вид подключения", conn_header)
        lbl_conn_h.setGeometry(0, 0, right_body_w, self.SECTION_H)
        lbl_conn_h.setAlignment(Qt.AlignCenter)
        lbl_conn_h.setFont(QFont("Times New Roman", 14))

        conn_body = QFrame(self)
        conn_body.setGeometry(left_body_w, self.HEADER_H + self.SECTION_H, right_body_w, self.BODY_H - self.SECTION_H)
        conn_body.setStyleSheet("background: transparent;")
        self._build_connection_content(conn_body, right_body_w)

        self._draw_grid(col_one_w, left_body_w)

    def _build_analysis_content(self, parent, w):
        content_margin = 20  
        input_y = 15
        input_h = 35
        input_w = 200
        gap_v = 38           
        
        edit_x = content_margin + 285 
        
        input_font = QFont("Times New Roman", 14)

        lbl_p1 = QLabel("Укажите порог вашего пульса", parent)
        lbl_p1.setGeometry(content_margin, input_y, 280, input_h)
        lbl_p1.setFont(QFont("Times New Roman", 12))
        
        self.edit_threshold = QLineEdit("", parent)
        self.edit_threshold.setGeometry(edit_x, input_y, input_w, input_h)
        self.edit_threshold.setStyleSheet("background: white; border-radius: 0px; padding-left: 5px;")
        self.edit_threshold.setFont(input_font)
        
        lbl_p2 = QLabel("Укажите норму вашего пульса", parent)
        lbl_p2.setGeometry(content_margin, input_y + gap_v, 280, input_h)
        lbl_p2.setFont(QFont("Times New Roman", 12))
        
        self.edit_normal = QLineEdit("", parent)
        self.edit_normal.setGeometry(edit_x, input_y + gap_v, input_w, input_h)
        self.edit_normal.setStyleSheet("background: white; border-radius: 0px; padding-left: 5px;")
        self.edit_normal.setFont(input_font)

        btn_save = QPushButton("Записать", parent)
        btn_save.setGeometry(edit_x + input_w + 20, input_y + 15, 110, 40) 
        btn_save.setStyleSheet("""
            QPushButton { 
                background: #2C2C2C; color: white; border-radius: 6px; font-weight: bold; font-size: 14px;
            } 
            QPushButton:hover { background: #44CC29; }
        """)
        btn_save.clicked.connect(self._save_to_csv)

        line_sep = QFrame(parent)
        line_sep.setGeometry(0, 95, w, self.GRID_T)
        line_sep.setStyleSheet("background-color: white; border: none;")

        lbl_term_title = QLabel("Терминальный блок информации", parent)
        lbl_term_title.setGeometry(0, 105, w, 30)
        lbl_term_title.setAlignment(Qt.AlignCenter)
        lbl_term_title.setFont(QFont("Times New Roman", 14))

        terminal_box = QFrame(parent)
        terminal_box.setGeometry(content_margin, 140, w - (content_margin * 2), 125)
        terminal_box.setStyleSheet("background-color: black; border-radius: 0px;")

        self.lbl_term = QLabel("", terminal_box)
        self.lbl_term.setGeometry(20, 10, w - 80, 105)
        self.lbl_term.setStyleSheet("color: white; background: transparent;")
        self.lbl_term.setFont(QFont("Times New Roman", 11))
        self._update_terminal_ui("WAIT", "WAIT", "--")

    def _build_connection_content(self, parent, w):
        side_margin = 25
        gap = 20
        block_h = 150
        y_pos = 20
        block_w = (w - (side_margin * 2) - gap) // 2 

        box1 = QLabel("1 пример", parent)
        box1.setGeometry(side_margin, y_pos, block_w, block_h)
        box1.setStyleSheet("background-color: white; border: none; border-radius: 0px;")
        box1.setAlignment(Qt.AlignCenter)

        box2 = QLabel("2 пример", parent)
        box2.setGeometry(side_margin + block_w + gap, y_pos, block_w, block_h)
        box2.setStyleSheet("background-color: white; border: none; border-radius: 0px;")
        box2.setAlignment(Qt.AlignCenter)

        lbl_hint = QLabel("Наклеить электроды как показано\nна рисунке и подключить контакты", parent)
        lbl_hint.setGeometry(side_margin, y_pos + block_h + 10, w - (side_margin * 2), 50)
        lbl_hint.setWordWrap(True)
        lbl_hint.setFont(QFont("Times New Roman", 11))

        self.btn_next = QPushButton("Далее", parent)
        self.btn_next.setGeometry(w - 120 - side_margin, 230, 110, 36)
        self.btn_next.setStyleSheet("""
            QPushButton { background: #2C2C2C; color: white; border-radius: 6px; font-weight: bold; font-size: 14px;}
            QPushButton:hover { background: #44CC29; }
        """)
        self.btn_next.clicked.connect(self._go_control)

    def _draw_grid(self, col_w, left_body_w):
        for x in [col_w, col_w * 2]:
            sep = QFrame(self)
            sep.setGeometry(x - self.GRID_T // 2, 0, self.GRID_T, self.HEADER_H)
            sep.setStyleSheet("background-color: white;")
        
        sep_h1 = QFrame(self)
        sep_h1.setGeometry(0, self.HEADER_H, self.W, self.GRID_T)
        sep_h1.setStyleSheet("background-color: white;")

        sep_h2 = QFrame(self)
        sep_h2.setGeometry(0, self.HEADER_H + self.SECTION_H, self.W, self.GRID_T)
        sep_h2.setStyleSheet("background-color: white;")

        sep_v = QFrame(self)
        sep_v.setGeometry(left_body_w - self.GRID_T // 2, self.HEADER_H, self.GRID_T, self.BODY_H)
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
            
        term_text = "\n".join(lines)
        self.lbl_term.setText(term_text)

    def _save_to_csv(self):
        th_val = self.edit_threshold.text().strip()
        norm_val = self.edit_normal.text().strip()

        if not th_val.isdigit() or not norm_val.isdigit():
            QMessageBox.warning(self, "Ошибка", "Введите числовые значения пульса.")
            return

        target_id = str(self.operator_row.get("id"))
        updated_rows = []
        header = []
        
        new_columns = ["pulse_threshold_critical", "pulse_normal", "current_pulse"]

        try:
            with open(self.csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                
                for col in new_columns:
                    if col not in header:
                        header.append(col)
                
                for row in reader:
                    row_data = dict(zip(header[:len(row)], row))
                    
                    if row_data.get("id") == target_id:
                        row_data["pulse_threshold_critical"] = th_val
                        row_data["pulse_normal"] = norm_val
                        row_data["current_pulse"] = "0"
                        
                        self.operator_row.update(row_data)
                    
                    new_row = [row_data.get(h, "") for h in header]
                    updated_rows.append(new_row)

            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(updated_rows)

            QMessageBox.information(self, "Успех", "Данные пульса сохранены.")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка CSV", f"Не удалось записать файл:\n{e}")

    def _go_instruction(self):
        if self.worker:
            self.worker.stop()
        if self.thread:
            self.thread.quit()
            self.thread.wait()

        from instruction_form import InstructionForm

        if not self.instr_window:
            self.instr_window = InstructionForm(self.operator_row)
        self.instr_window.show()
        
        self.close()
        
    def _go_control(self):
        if self.worker:
            self.worker.stop()
        if self.thread:
            self.thread.quit()
            self.thread.wait()

        from control_form import ControlForm
        if not self.control_window:
            self.control_window = ControlForm(self.operator_row)
        
        self.control_window.show()
        
        self.close()

    def closeEvent(self, event):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()
        super().closeEvent(event)