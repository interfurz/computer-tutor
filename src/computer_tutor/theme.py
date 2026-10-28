from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

STYLE = """
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #e9f1ee; }
QMainWindow, QDialog { background: #101a21; }
QWidget#page { background: #101a21; }
QWidget#sidebar { background: #14232b; border-right: 1px solid #2a4148; }
QLabel#brand { color: #75e6c6; font-weight: 700; font-size: 18px; }
QLabel#hero { font-size: 30px; font-weight: 600; }
QLabel#muted { color: #9bb2b3; }
QLabel#status { color: #70dfc1; background: #1b3838; border-radius: 8px; padding: 8px; }
QLabel#section { font-size: 17px; font-weight: 600; }
QLabel#error { color: #ffb5a8; }
QFrame#card { background: #172931; border: 1px solid #2d454c; border-radius: 14px; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox { background: #0d181f; border: 1px solid
    #3b555e; border-radius: 7px; padding: 9px; selection-background-color: #36695d; }
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #70dfc1; }
QPushButton { background: #243b43; border: 1px solid #3c555e; border-radius: 8px;
    padding: 10px 16px; font-weight: 600; }
QPushButton:hover { background: #315059; }
QPushButton:disabled { color: #718989; background: #203038; }
QPushButton#primary { background: #75e6c6; border: 0; color: #102a25; }
QPushButton#primary:hover { background: #9ff4dc; }
QPushButton#primary:disabled { background: #325b53; color: #a3bcb7; }
QPushButton#nav { text-align: left; background: transparent; border: 0; padding: 12px; }
QPushButton#nav:checked { background: #28433f; color: #8bf1d3; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; }
QToolTip { background: #20363e; color: #f0f8f4; border: 1px solid #47645e; }
"""


def app_icon():
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#142a31"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(2, 2, 124, 124), 28, 28)
    painter.setPen(QColor("#75e6c6"))
    painter.setFont(QFont("Segoe UI", 55, QFont.Weight.DemiBold))
    painter.drawText(QRectF(0, -2, 128, 128), Qt.AlignmentFlag.AlignCenter, "t")
    painter.setBrush(QColor("#75e6c6"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(87, 87, 16, 16))
    painter.end()
    return QIcon(pixmap)
