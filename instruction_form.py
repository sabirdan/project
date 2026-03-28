from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont, QPixmap, QPainter, QBrush, QColor, QPolygon
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QVBoxLayout, QHBoxLayout
)


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
            points = [
                QPoint(self.width() // 2, 0),
                QPoint(0, self.height()),
                QPoint(self.width(), self.height())
            ]
            painter.drawPolygon(QPolygon(points))
            
        elif self.shape_type == "square":
            painter.drawRect(0, 0, self.width(), self.height())


class InstructionForm(QWidget):
    def __init__(self, operator_row: dict = None):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.operator_row = operator_row or {}
        self.analysis_form = None
        self.control_form = None

        self.W = 1000
        self.H = 450
        self.HEADER_H = 120
        self.SECTION_H = 44
        self.GRID_T = 4
        self.BODY_H = self.H - self.HEADER_H

        self.setFixedSize(self.W, self.H + 34)
        self.setWindowTitle("Инструкция и подключение")
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

    def _build_ui(self):
        col_one_w = self.W // 3
        left_body_w = col_one_w * 2
        right_body_w = self.W - col_one_w * 2

        menu_frame = QFrame(self.content_container)
        menu_frame.setGeometry(0, 0, col_one_w, self.HEADER_H)

        lbl_menu = QLabel("Меню управления", menu_frame)
        lbl_menu.setGeometry(0, 15, col_one_w, 30)
        lbl_menu.setAlignment(Qt.AlignCenter)
        lbl_menu.setFont(QFont("Times New Roman", 18))
        
        spacing = 8
        btn_h = 36
        btn_y = 65
        btn_w = (col_one_w - spacing * 2) // 3
        
        b_style = (
            "QPushButton { "
            "color: white; border-radius: 18px; "
            "font-family: 'Times New Roman'; font-size: 14px; font-weight: bold; "
            "}"
        )

        self.btn_instr = QPushButton("Инструкция", menu_frame)
        self.btn_instr.setGeometry(0, btn_y, btn_w, btn_h)
        self.btn_instr.setStyleSheet(
            b_style + "QPushButton { background-color: #44CC29; } "
            "QPushButton:hover { background-color: #45D44A; }"
        )

        self.btn_analysis = QPushButton("Анализ", menu_frame)
        self.btn_analysis.setGeometry(btn_w + spacing, btn_y, btn_w, btn_h)
        self.btn_analysis.setStyleSheet(
            b_style + "QPushButton { background-color: #8D3C7F; } "
            "QPushButton:hover { background-color: #9E4576; }"
        )
        self.btn_analysis.clicked.connect(self._open_analysis)

        self.btn_control = QPushButton("Управление", menu_frame)
        third_btn_w = col_one_w - (btn_w * 2 + spacing * 2)
        self.btn_control.setGeometry((btn_w + spacing) * 2, btn_y, third_btn_w, btn_h)
        self.btn_control.setStyleSheet(
            b_style + "QPushButton { background-color: #8D3C7F; } "
            "QPushButton:hover { background-color: #9E4576; }"
        )
        self.btn_control.clicked.connect(self._open_control)

        logo_frame = QFrame(self.content_container)
        logo_frame.setGeometry(col_one_w, 0, col_one_w, self.HEADER_H)
        logo_frame.setStyleSheet("background: #44CC29;")

        lbl_logo = QLabel("НейроБодр", logo_frame)
        lbl_logo.setGeometry(0, 10, col_one_w, 50)
        lbl_logo.setAlignment(Qt.AlignCenter)
        lbl_logo.setStyleSheet("color: white;")
        lbl_logo.setFont(QFont("Times New Roman", 20))

        line = QFrame(logo_frame)
        line.setGeometry(int(col_one_w * 0.2), 60, int(col_one_w * 0.6), 2)
        line.setStyleSheet("background-color: white;")

        desc_text = "Программа для мониторинга\nсостояния водителей"
        lbl_desc = QLabel(desc_text, logo_frame)
        lbl_desc.setGeometry(0, 65, col_one_w, 50)
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet("color: white;")
        lbl_desc.setFont(QFont("Times New Roman", 14))

        id_frame = QFrame(self.content_container)
        id_frame.setGeometry(col_one_w * 2, 0, right_body_w, self.HEADER_H)

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
        
        f_name = self.operator_row.get('first_name', '')
        l_name = self.operator_row.get('last_name', '')
        self.lbl_op_name = QLabel(f"{l_name} {f_name}", id_frame)
        self.lbl_op_name.setGeometry(150, 55, right_body_w - 120, 60)
        self.lbl_op_name.setFont(QFont("Times New Roman", 16)) 
        self.lbl_op_name.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self._section_header(self.content_container, "Инструкция", 0, self.HEADER_H, left_body_w)
        self._build_instruction_content(QFrame(self.content_container), left_body_w)

        self._section_header(self.content_container, "Вид подключения", left_body_w, self.HEADER_H, right_body_w)
        self._build_connection_content(QFrame(self.content_container), left_body_w, right_body_w)
        
        self._draw_grid(col_one_w, left_body_w)

    def _section_header(self, parent, text, x, y, w):
        h = QFrame(parent)
        h.setGeometry(x, y, w, self.SECTION_H)
        lbl = QLabel(text, h)
        lbl.setGeometry(0, 0, w, self.SECTION_H)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Times New Roman", 14, QFont.Bold))

    def _build_instruction_content(self, parent, w):
        parent.setGeometry(0, self.HEADER_H + self.SECTION_H, w, self.BODY_H - self.SECTION_H)
        text_w = w - 70
        
        data = [
            (
                "Зеленый индикатор на видео означает, хорошее состояние оператора.\n"
                "Оператор бодрствует. ЧСС в пределах нормы. 'Норма'", 
                45, "circle", "#7CE4D5"
            ),
            (
                "Желтый индикатор на видео означает 'Внимание' состояние\n"
                "оператора выходит за пределы нормы: Падение ЧСС ниже на 20%\n"
                "от нормы или повышение на 20%, но ниже критического порога.\n"
                "Веки закрыты дольше 4 секунд (микросон). Наклон вперед/вбок\n"
                "(эффект 'кивающей головы')", 
                100, "triangle", "#F9D849"
            ),
            (
                "Красный индикатор на видео означает, 'Критическое' состояние:\n"
                "ЧСС ниже на 30% от нормы или больше критического порога.\n"
                "Наклон головы вперед/вбок (дольше 7 секунд) веки закрыты", 
                90, "square", "#D0021B"
            )
        ]

        y_pos = 10
        for text, h, shape, color in data:
            lbl = QLabel(text, parent)
            lbl.setGeometry(60, y_pos, text_w, h)
            lbl.setWordWrap(True)
            lbl.setFont(QFont("Times New Roman", 11))
            
            icon = ShapeWidget(shape, color, parent)
            icon_y = y_pos + (h // 2) - 20
            icon.move(10, icon_y)
            
            y_pos += h + 15

    def _build_connection_content(self, parent, x_offset, w):
        parent.setGeometry(x_offset, self.HEADER_H + self.SECTION_H, w, self.BODY_H - self.SECTION_H)
        
        side_margin = 25
        gap = 20
        block_h = 150
        y_pos = 20
        block_w = (w - (side_margin * 2) - gap) // 2 
        
        for i, img in enumerate(["hand1.png", "hand2.png"]):
            box = QLabel(parent)
            box_x = side_margin + (block_w + gap) * i
            box.setGeometry(box_x, y_pos, block_w, block_h)
            
            pix = QPixmap(f"assets/{img}")
            box.setPixmap(pix.scaled(block_w, block_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            box.setAlignment(Qt.AlignCenter)
            
        hint_text = "Наклеить электроды как показано\nна рисунке и подключить контакты"
        lbl_hint = QLabel(hint_text, parent)
        lbl_hint.setGeometry(side_margin, y_pos + block_h + 15, w - (side_margin * 2), 60)
        lbl_hint.setWordWrap(True)
        lbl_hint.setFont(QFont("Times New Roman", 11))
        
        btn_next = QPushButton("Далее", parent)
        btn_x = w - 120 - side_margin
        btn_y = self.BODY_H - self.SECTION_H - 50
        btn_next.setGeometry(btn_x, btn_y, 110, 36)
        btn_next.setCursor(Qt.PointingHandCursor)
        btn_next.setStyleSheet("""
            QPushButton { 
                background-color: #2C2C2C; 
                color: #FFFFFF; 
                border-radius: 6px; 
                font-weight: bold; 
                font-family: 'Times New Roman'; 
                font-size: 14px; 
            } 
            QPushButton:hover { background-color: #44CC29; }
        """)
        btn_next.clicked.connect(self._open_analysis)

    def _draw_grid(self, col_w, left_body_w):
        for x in [col_w, col_w * 2]:
            sep = QFrame(self.content_container)
            sep.setGeometry(x - 2, 0, 4, self.HEADER_H)
            sep.setStyleSheet("background-color: #FFFFFF;")
            
        for y in [self.HEADER_H, self.HEADER_H + self.SECTION_H]:
            sep_h = QFrame(self.content_container)
            sep_h.setGeometry(0, y, self.W, 4)
            sep_h.setStyleSheet("background-color: #FFFFFF;")
            
        sep_v = QFrame(self.content_container)
        sep_v.setGeometry(left_body_w - 2, self.HEADER_H, 4, self.BODY_H)
        sep_v.setStyleSheet("background-color: #FFFFFF;")

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