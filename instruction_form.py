import os
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QFrame


class InstructionForm(QWidget):
    def __init__(self, operator_row: dict = None):
        super().__init__()
        
        self.operator_row = operator_row if operator_row else {}
        self.analysis_form = None
        self.control_form = None

        self.W = 1000
        self.H = 450
        self.HEADER_H = 120
        self.BODY_H = self.H - self.HEADER_H
        self.SECTION_H = 44
        self.GRID_T = 4

        self.setFixedSize(self.W, self.H)
        self.setWindowTitle("Инструкция и подключение")
        self.setStyleSheet("background-color: #D9D9D9;")

        self._build_ui()

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
        lbl_menu.setFont(QFont("Times New Roman", 18, QFont.Normal))

        spacing = 8
        btn_h = 36
        btn_y = 65
        
        total_width_for_buttons = col_one_w - (spacing * 2)
        btn_w = total_width_for_buttons // 3

        base_style = """
            QPushButton {
                color: white; 
                border: none;
                border-radius: 18px; 
                font-family: "Times New Roman"; 
                font-size: 14px; 
                font-weight: bold;
            }
        """
        green_style = base_style + "QPushButton { background-color: #35C43A; } QPushButton:hover { background-color: #45D44A; }"
        purple_style = base_style + "QPushButton { background-color: #8E3566; } QPushButton:hover { background-color: #9E4576; }"

        self.btn_instr = QPushButton("Инструкция", menu_frame)
        self.btn_instr.setGeometry(0, btn_y, btn_w, btn_h)
        self.btn_instr.setStyleSheet(green_style)

        self.btn_analysis = QPushButton("Анализ", menu_frame)
        self.btn_analysis.setGeometry(btn_w + spacing, btn_y, btn_w, btn_h)
        self.btn_analysis.setStyleSheet(purple_style)
        self.btn_analysis.clicked.connect(self._open_analysis)

        btn_3_w = col_one_w - (btn_w * 2 + spacing * 2)
        self.btn_control = QPushButton("Управление", menu_frame)
        self.btn_control.setGeometry((btn_w + spacing) * 2, btn_y, btn_3_w, btn_h)
        self.btn_control.setStyleSheet(purple_style)
        self.btn_control.clicked.connect(self._open_control)

        logo_frame = QFrame(self)
        logo_frame.setGeometry(col_one_w, 0, col_one_w, self.HEADER_H)
        logo_frame.setStyleSheet("background: #35C43A; border: none;")

        lbl_logo = QLabel("НейроБодр", logo_frame)
        lbl_logo.setGeometry(0, 10, col_one_w, 50)
        lbl_logo.setAlignment(Qt.AlignCenter)
        lbl_logo.setStyleSheet("color: white;")
        lbl_logo.setFont(QFont("Times New Roman", 20, QFont.Normal))
        
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
        lbl_id_title.setFont(QFont("Times New Roman", 14, QFont.Normal))

        id_sep = QFrame(id_frame)
        id_sep.setGeometry(0, 45, right_body_w, self.GRID_T)
        id_sep.setStyleSheet("background-color: white;")

        lbl_op_status = QLabel("Оператор\nопределен:", id_frame)
        lbl_op_status.setGeometry(20, 55, 110, 60)
        lbl_op_status.setFont(QFont("Times New Roman", 14))
        
        f_name = self.operator_row.get("first_name", "")
        l_name = self.operator_row.get("last_name", "")
        full_name = f"{l_name} {f_name}"

        self.lbl_op_name = QLabel(full_name, id_frame)
        self.lbl_op_name.setGeometry(150, 55, right_body_w - 120, 60)
        self.lbl_op_name.setFont(QFont("Times New Roman", 16, QFont.Normal)) 
        self.lbl_op_name.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        instr_header = QFrame(self)
        instr_header.setGeometry(0, self.HEADER_H, left_body_w, self.SECTION_H)
        instr_header.setStyleSheet("background-color: #D9D9D9;")
        
        lbl_instr_h = QLabel("Инструкция", instr_header)
        lbl_instr_h.setGeometry(0, 0, left_body_w, self.SECTION_H)
        lbl_instr_h.setAlignment(Qt.AlignCenter)
        lbl_instr_h.setFont(QFont("Times New Roman", 14, QFont.Normal))

        instr_body = QFrame(self)
        instr_body.setGeometry(0, self.HEADER_H + self.SECTION_H, left_body_w, self.BODY_H - self.SECTION_H)
        instr_body.setStyleSheet("background: transparent;")

        self._build_instruction_content(instr_body, left_body_w)

        conn_header = QFrame(self)
        conn_header.setGeometry(left_body_w, self.HEADER_H, right_body_w, self.SECTION_H)
        conn_header.setStyleSheet("background-color: #D9D9D9;")

        lbl_conn_h = QLabel("Вид подключения", conn_header)
        lbl_conn_h.setGeometry(0, 0, right_body_w, self.SECTION_H)
        lbl_conn_h.setAlignment(Qt.AlignCenter)
        lbl_conn_h.setFont(QFont("Times New Roman", 14, QFont.Normal))

        conn_body = QFrame(self)
        conn_body.setGeometry(left_body_w, self.HEADER_H + self.SECTION_H, right_body_w, self.BODY_H - self.SECTION_H)
        conn_body.setStyleSheet("background: transparent;")

        self._build_connection_content(conn_body, right_body_w)

        self._draw_grid(col_one_w, left_body_w)

    def _build_instruction_content(self, parent, w):
        margin_left = 60
        text_w = w - margin_left - 10
        y_pos = 10
        icon_h = 40
        
        txt_green = ("Зеленый индикатор на видео означает, хорошее состояние оператора. "
                     "Оператор бодрствует. ЧСС в пределах нормы. 'Норма'")
        lbl_t1 = QLabel(txt_green, parent)
        h_t1 = 45 
        lbl_t1.setGeometry(margin_left, y_pos, text_w, h_t1)
        lbl_t1.setWordWrap(True)
        lbl_t1.setFont(QFont("Times New Roman", 11))
        lbl_t1.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        y_icon_1 = int(y_pos + (h_t1 / 2) - (icon_h / 2))
        icon_green = QLabel(parent)
        icon_green.setGeometry(10, y_icon_1, 40, 40)
        icon_green.setStyleSheet("background-color: #07D40B; border: 2px solid #0000FF;")

        y_pos = y_pos + h_t1 + 15 

        txt_yellow = ("Желтый индикатор на видео означает 'Внимание' состояние оператора выходит за пределы нормы:\n"
                      "Падение ЧСС ниже 50 уд./мин или выше не более 90 уд./мин\n"
                      "Веки закрыты дольше 3 секунд (микросон).\n"
                      "Наклон вперед/вбок (эффект 'кивающей головы')")
        lbl_t2 = QLabel(txt_yellow, parent)
        h_t2 = 100 
        lbl_t2.setGeometry(margin_left, y_pos, text_w, h_t2)
        lbl_t2.setWordWrap(True)
        lbl_t2.setFont(QFont("Times New Roman", 11))
        lbl_t2.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        y_icon_2 = int(y_pos + (h_t2 / 2) - (icon_h / 2))
        icon_yellow = QLabel(parent)
        icon_yellow.setGeometry(10, y_icon_2, 40, 40)
        icon_yellow.setStyleSheet("background-color: #FFFC00; border: 2px solid #0000FF;")

        y_pos = y_pos + h_t2 + 10

        txt_red = ("Красный индикатор на видео означает, 'Критическое' состояние:\n"
                   "ЧСС 38–42 уд./мин в минуту и ниже\n"
                   "ЧСС больше 100–130 ударов\n"
                   "Наклон головы вперед/вбок (дольше 4 секунд) веки закрыты")
        lbl_t3 = QLabel(txt_red, parent)
        h_t3 = 90
        lbl_t3.setGeometry(margin_left, y_pos, text_w, h_t3)
        lbl_t3.setWordWrap(True)
        lbl_t3.setFont(QFont("Times New Roman", 11))
        lbl_t3.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        y_icon_3 = int(y_pos + (h_t3 / 2) - (icon_h / 2))
        icon_red = QLabel(parent)
        icon_red.setGeometry(10, y_icon_3, 40, 40)
        icon_red.setStyleSheet("background-color: #D0021B; border: 2px solid #0000FF;")

    def _build_connection_content(self, parent, w):
        side_margin = 25
        gap = 20
        block_h = 150
        y_pos = 20

        block_w = (w - (side_margin * 2) - gap) // 2 
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        img1_path = os.path.join(base_dir, "assets", "hand1.png")
        img2_path = os.path.join(base_dir, "assets", "hand2.png")

        box1 = QLabel(parent)
        box1.setGeometry(side_margin, y_pos, block_w, block_h)
        box1.setAlignment(Qt.AlignCenter)
        pixmap1 = QPixmap(img1_path)
        box1.setPixmap(pixmap1.scaled(block_w, block_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        box2 = QLabel(parent)
        box2.setGeometry(side_margin + block_w + gap, y_pos, block_w, block_h)
        box2.setAlignment(Qt.AlignCenter)
        pixmap2 = QPixmap(img2_path)
        box2.setPixmap(pixmap2.scaled(block_w, block_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        lbl_hint = QLabel("Наклеить электроды как показано\nна рисунке и подключить контакты", parent)
        lbl_hint.setGeometry(side_margin, y_pos + block_h + 15, w - (side_margin * 2), 60)
        lbl_hint.setWordWrap(True)
        lbl_hint.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        lbl_hint.setFont(QFont("Times New Roman", 11))

        btn_next = QPushButton("Далее", parent)
        btn_next.setGeometry(w - 120 - side_margin, self.BODY_H - self.SECTION_H - 50, 110, 36)
        btn_next.setCursor(Qt.PointingHandCursor)
        btn_next.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2C; color: #FFFFFF; border: none; font-weight: bold;
                border-radius: 6px; font-family: "Times New Roman"; font-size: 14px;
            }
            QPushButton:hover { background-color: #3A3A3A; }
            QPushButton:pressed { background-color: #1F1F1F; }
        """)
        btn_next.clicked.connect(self._open_analysis)

    def _draw_grid(self, col_w, left_body_w):
        sep1 = QFrame(self)
        sep1.setGeometry(col_w - self.GRID_T // 2, 0, self.GRID_T, self.HEADER_H)
        sep1.setStyleSheet("background-color: #FFFFFF; border: none;")
        sep1.raise_()

        sep2 = QFrame(self)
        sep2.setGeometry(col_w * 2 - self.GRID_T // 2, 0, self.GRID_T, self.HEADER_H)
        sep2.setStyleSheet("background-color: #FFFFFF; border: none;")
        sep2.raise_()

        sep_h_main = QFrame(self)
        sep_h_main.setGeometry(0, self.HEADER_H, self.W, self.GRID_T)
        sep_h_main.setStyleSheet("background-color: #FFFFFF; border: none;")
        sep_h_main.raise_()

        sep_h_sub = QFrame(self)
        sep_h_sub.setGeometry(0, self.HEADER_H + self.SECTION_H, self.W, self.GRID_T)
        sep_h_sub.setStyleSheet("background-color: #FFFFFF; border: none;")
        sep_h_sub.raise_()

        sep_body_v = QFrame(self)
        sep_body_v.setGeometry(left_body_w - self.GRID_T // 2, self.HEADER_H, self.GRID_T, self.BODY_H)
        sep_body_v.setStyleSheet("background-color: #FFFFFF; border: none;")
        sep_body_v.raise_()

    def _open_control(self):
        from control_form import ControlForm 
        
        if self.control_form is None:
            self.control_form = ControlForm(self.operator_row)
            
        self.control_form.show()
        self.hide()

    def _open_analysis(self):
        from analysis_form import AnalysisForm 
        
        if self.analysis_form is None:
            self.analysis_form = AnalysisForm(self.operator_row)
            
        self.analysis_form.show()
        self.hide()