from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLineEdit
from utils import COLOR_BTN_BG, COLOR_GREEN

def create_line_edit(height=52, font_size=24, padding=12):
    le = QLineEdit()
    le.setFixedHeight(height)
    le.setFont(QFont("Times New Roman", font_size))
    le.setStyleSheet(f"background-color: white; border: none; padding-left: {padding}px;")
    return le

def get_btn_style():
    return f"""
        QPushButton {{ 
            background-color: {COLOR_BTN_BG}; 
            color: white; 
            border-radius: 8px; 
            font-family: "Times New Roman"; 
            font-size: 14px; 
            font-weight: 600; 
        }} 
        QPushButton:hover {{ background-color: {COLOR_GREEN}; }}
    """