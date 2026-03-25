import os
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont, QPixmap, QPainter, QBrush, QColor, QPolygon
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QFrame, QVBoxLayout, QHBoxLayout

class ShapeWidget(QWidget):
    def __init__(self, shape_type, color, parent=None):
        super().__init__(parent)
        self.shape_type = shape_type
        self.color = color
        self.setFixedSize(40, 40)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(self.color)))
        if self.shape_type == "circle":
            painter.drawEllipse(0, 0, self.width(), self.height())
        elif self.shape_type == "triangle":
            points = [QPoint(self.width() // 2, 0), QPoint(0, self.height()), QPoint(self.width(), self.height())]
            painter.drawPolygon(QPolygon(points))
        elif self.shape_type == "square":
            painter.drawRect(0, 0, self.width(), self.height())

class InstructionForm(QWidget):
    def __init__(self, operator_row: dict = None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.operator_row = operator_row if operator_row else {}
        self.analysis_form = None
        self.control_form = None

        self.W = 1000
        self.H = 450
        self.HEADER_H = 120
        self.BODY_H = self.H - self.HEADER_H
        self.SECTION_H = 44
        self.GRID_T = 4

        self.setFixedSize(self.W, self.H + 34)
        self.setWindowTitle("Инструкция и подключение")
        self.setStyleSheet("background-color: #D9D9D9;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.top_grey_area = QWidget(self)
        self.top_grey_area.setFixedHeight(30)
        self.top_grey_area.setStyleSheet("background-color: #D9D9D9; border: none;")
        
        top_layout = QHBoxLayout(self.top_grey_area)
        top_layout.setContentsMargins(0, 0, 5, 0)
        top_layout.setSpacing(0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("×", self.top_grey_area)
        self.btn_close.setFixedSize(45, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                color: #FF0000; 
                background: transparent; 
                border: none; 
                font-size: 36px; 
                font-weight: bold;
            }
        """)
        self.btn_close.clicked.connect(self.close)
        top_layout.addWidget(self.btn_close)
        main_layout.addWidget(self.top_grey_area)

        self.top_white_line = QWidget(self)
        self.top_white_line.setFixedHeight(4)
        self.top_white_line.setStyleSheet("background-color: #FFFFFF; border: none;")
        main_layout.addWidget(self.top_white_line)

        self.content_container = QWidget(self)
        self.content_container.setFixedSize(self.W, self.H)
        main_layout.addWidget(self.content_container)

        self._build_ui()

    def _build_ui(self):
        col_one_w = self.W // 3
        left_body_w = col_one_w * 2
        right_body_w = self.W - left_body_w

        menu_frame = QFrame(self.content_container)
        menu_frame.setGeometry(0, 0, col_one_w, self.HEADER_H)
        menu_frame.setStyleSheet("background: #D9D9D9; border: none;")

        lbl_menu = QLabel("Меню управления", menu_frame)
        lbl_menu.setGeometry(0, 15, col_one_w, 30)
        lbl_menu.setAlignment(Qt.AlignCenter)
        lbl_menu.setFont(QFont("Times New Roman", 18, QFont.Normal))
        spacing, btn_h, btn_y = 8, 36, 65
        total_width_for_buttons = col_one_w - (spacing * 2)
        btn_w = total_width_for_buttons // 3
        base_style = "QPushButton { color: white; border: none; border-radius: 18px; font-family: 'Times New Roman'; font-size: 14px; font-weight: bold; }"
        green_style = base_style + "QPushButton { background-color: #44CC29; } QPushButton:hover { background-color: #45D44A; }"
        purple_style = base_style + "QPushButton { background-color: #8D3C7F; } QPushButton:hover { background-color: #9E4576; }"

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

        logo_frame = QFrame(self.content_container)
        logo_frame.setGeometry(col_one_w, 0, col_one_w, self.HEADER_H)
        logo_frame.setStyleSheet("background: #44CC29; border: none;")

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

        id_frame = QFrame(self.content_container)
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
        f_name, l_name = self.operator_row.get("first_name", ""), self.operator_row.get("last_name", "")
        self.lbl_op_name = QLabel(f"{l_name} {f_name}", id_frame)
        self.lbl_op_name.setGeometry(150, 55, right_body_w - 120, 60)
        self.lbl_op_name.setFont(QFont("Times New Roman", 16, QFont.Normal)) 
        self.lbl_op_name.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        instr_header = QFrame(self.content_container)
        instr_header.setGeometry(0, self.HEADER_H, left_body_w, self.SECTION_H)
        instr_header.setStyleSheet("background-color: #D9D9D9;")

        lbl_instr_h = QLabel("Инструкция", instr_header)
        lbl_instr_h.setGeometry(0, 0, left_body_w, self.SECTION_H)
        lbl_instr_h.setAlignment(Qt.AlignCenter)
        lbl_instr_h.setFont(QFont("Times New Roman", 14, QFont.Normal))

        instr_body = QFrame(self.content_container)
        instr_body.setGeometry(0, self.HEADER_H + self.SECTION_H, left_body_w, self.BODY_H - self.SECTION_H)
        self._build_instruction_content(instr_body, left_body_w)

        conn_header = QFrame(self.content_container)
        conn_header.setGeometry(left_body_w, self.HEADER_H, right_body_w, self.SECTION_H)

        lbl_conn_h = QLabel("Вид подключения", conn_header)
        lbl_conn_h.setGeometry(0, 0, right_body_w, self.SECTION_H)
        lbl_conn_h.setAlignment(Qt.AlignCenter)
        lbl_conn_h.setFont(QFont("Times New Roman", 14, QFont.Normal))

        conn_body = QFrame(self.content_container)
        conn_body.setGeometry(left_body_w, self.HEADER_H + self.SECTION_H, right_body_w, self.BODY_H - self.SECTION_H)
        self._build_connection_content(conn_body, right_body_w)
        
        self._draw_grid(col_one_w, left_body_w)

    def _build_instruction_content(self, parent, w):
        margin_left, y_pos, icon_h = 60, 10, 40
        text_w = w - margin_left - 10
        
        lbl_t1 = QLabel("Зеленый индикатор на видео означает, хорошее состояние оператора.\nОператор бодрствует. ЧСС в пределах нормы. 'Норма'", parent)
        lbl_t1.setGeometry(margin_left, y_pos, text_w, 45)
        lbl_t1.setWordWrap(True)
        lbl_t1.setFont(QFont("Times New Roman", 11))
        icon_green = ShapeWidget("circle", "#7CE4D5", parent)
        icon_green.move(10, y_pos + (45 // 2) - (icon_h // 2))

        y_pos += 60
        lbl_t2 = QLabel("Желтый индикатор на видео означает 'Внимание' состояние\nоператора выходит за пределы нормы: Падение ЧСС ниже на 20%\nот нормы или повышение на 20%, но ниже критического порога.\nВеки закрыты дольше 4 секунд (микросон). Наклон вперед/вбок\n(эффект 'кивающей головы')", parent)
        lbl_t2.setGeometry(margin_left, y_pos, text_w, 100)
        lbl_t2.setWordWrap(True)
        lbl_t2.setFont(QFont("Times New Roman", 11))
        icon_yellow = ShapeWidget("triangle", "#F9D849", parent)
        icon_yellow.move(10, y_pos + (100 // 2) - (icon_h // 2))

        y_pos += 110
        lbl_t3 = QLabel("Красный индикатор на видео означает, 'Критическое' состояние:\nЧСС ниже на 30% от нормы или больше критического порога.\nНаклон головы вперед/вбок (дольше 7 секунд) веки закрыты", parent)
        lbl_t3.setGeometry(margin_left, y_pos, text_w, 90)
        lbl_t3.setWordWrap(True)
        lbl_t3.setFont(QFont("Times New Roman", 11))
        icon_red = ShapeWidget("square", "#D0021B", parent)
        icon_red.move(10, y_pos + (90 // 2) - (icon_h // 2))

    def _build_connection_content(self, parent, w):
        side_margin, gap, block_h, y_pos = 25, 20, 150, 20
        block_w = (w - (side_margin * 2) - gap) // 2 
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        for i, img in enumerate(["hand1.png", "hand2.png"]):
            box = QLabel(parent)
            box.setGeometry(side_margin + (block_w + gap) * i, y_pos, block_w, block_h)
            pixmap = QPixmap(os.path.join(base_dir, "assets", img))
            box.setPixmap(pixmap.scaled(block_w, block_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            box.setAlignment(Qt.AlignCenter)
            
        lbl_hint = QLabel("Наклеить электроды как показано\nна рисунке и подключить контакты", parent)
        lbl_hint.setGeometry(side_margin, y_pos + block_h + 15, w - (side_margin * 2), 60)
        lbl_hint.setWordWrap(True)
        lbl_hint.setFont(QFont("Times New Roman", 11))
        
        btn_next = QPushButton("Далее", parent)
        btn_next.setGeometry(w - 120 - side_margin, self.BODY_H - self.SECTION_H - 50, 110, 36)
        btn_next.setCursor(Qt.PointingHandCursor)
        btn_next.setStyleSheet("QPushButton { background-color: #2C2C2C; color: #FFFFFF; border: none; font-weight: bold; border-radius: 6px; font-family: 'Times New Roman'; font-size: 14px; } QPushButton:hover { background-color: #44CC29; }")
        btn_next.clicked.connect(self._open_analysis)

    def _draw_grid(self, col_w, left_body_w):
        for x in [col_w, col_w * 2]:
            sep = QFrame(self.content_container)
            sep.setGeometry(x - self.GRID_T // 2, 0, self.GRID_T, self.HEADER_H)
            sep.setStyleSheet("background-color: #FFFFFF; border: none;")
            
        sep_h1 = QFrame(self.content_container)
        sep_h1.setGeometry(0, self.HEADER_H, self.W, self.GRID_T)
        sep_h1.setStyleSheet("background-color: #FFFFFF; border: none;")
        
        sep_h2 = QFrame(self.content_container)
        sep_h2.setGeometry(0, self.HEADER_H + self.SECTION_H, self.W, self.GRID_T)
        sep_h2.setStyleSheet("background-color: #FFFFFF; border: none;")
        
        sep_v = QFrame(self.content_container)
        sep_v.setGeometry(left_body_w - self.GRID_T // 2, self.HEADER_H, self.GRID_T, self.BODY_H)
        sep_v.setStyleSheet("background-color: #FFFFFF; border: none;")

    def _open_control(self):
        from control_form import ControlForm 
        if self.control_form is None: self.control_form = ControlForm(self.operator_row)
        self.control_form.show()
        self.hide()

    def _open_analysis(self):
        from analysis_form import AnalysisForm 
        if self.analysis_form is None: self.analysis_form = AnalysisForm(self.operator_row)
        self.analysis_form.show()
        self.hide()