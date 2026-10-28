"""Transparent annotation layer plus a separate, interactive lesson dock."""

import math

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from computer_tutor.models import Step

TEAL = QColor("#61e2c1")
INK = QColor("#101c23")


class DragHandle(QLabel):
    def __init__(self, dock):
        super().__init__("COMPUTER / TUTOR")
        self.dock = dock
        self.offset = None
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setToolTip("Ziehen zum Verschieben · Doppelklick setzt die Position zurück")

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - self.dock.pos()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self.offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            area = self.dock.controller.screen().availableGeometry()
            target = event.globalPosition().toPoint() - self.offset
            target.setX(max(area.left(), min(target.x(), area.right() - self.dock.width() + 1)))
            target.setY(max(area.top(), min(target.y(), area.bottom() - self.dock.height() + 1)))
            self.dock.user_position = True
            self.dock.move(target)

    def mouseReleaseEvent(self, _event):  # noqa: N802
        self.offset = None

    def mouseDoubleClickEvent(self, _event):  # noqa: N802
        self.dock.reset_position()
        self.dock.controller.refresh()


class AnnotationOverlay(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.step: Step | None = None
        self.panel_rect = QRectF()

    def paintEvent(self, _event):  # noqa: N802
        if self.step is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        targets = []
        for item in self.step.annotations:
            r = item.target
            targets.append(
                QRectF(
                    r.x * self.width(),
                    r.y * self.height(),
                    r.width * self.width(),
                    r.height * self.height(),
                )
            )

        if any(item.style == "spotlight" for item in self.step.annotations):
            mask = QPainterPath()
            mask.addRect(QRectF(self.rect()))
            for target in targets:
                cutout = QPainterPath()
                cutout.addRoundedRect(target.adjusted(-5, -5, 5, 5), 10, 10)
                mask = mask.subtracted(cutout)
            painter.fillPath(mask, QColor(4, 12, 19, 125))

        occupied = [self.panel_rect] if not self.panel_rect.isEmpty() else []
        for number, (item, target) in enumerate(
            zip(self.step.annotations, targets, strict=True), 1
        ):
            # A broad translucent outer line makes the target readable on light and dark apps.
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(9, 31, 31, 190), 7))
            painter.drawRoundedRect(target, 8, 8)
            painter.setPen(QPen(TEAL, 2))
            if item.style == "point":
                painter.drawEllipse(target.center(), 15, 15)
            else:
                painter.drawRoundedRect(target, 8, 8)

            font = QFont("Segoe UI", 10)
            painter.setFont(font)
            card_width = min(278, max(140, self.width() - 32))
            text_bounds = painter.fontMetrics().boundingRect(
                0,
                0,
                card_width - 44,
                1000,
                int(Qt.TextFlag.TextWordWrap),
                item.label,
            )
            card_height = text_bounds.height() + 28
            gap = 16
            candidates = {
                "below": QRectF(target.left(), target.bottom() + gap, card_width, card_height),
                "above": QRectF(
                    target.left(), target.top() - card_height - gap, card_width, card_height
                ),
                "right": QRectF(target.right() + gap, target.top(), card_width, card_height),
                "left": QRectF(
                    target.left() - card_width - gap, target.top(), card_width, card_height
                ),
            }
            order = ["below", "right", "above", "left"]
            if item.placement != "auto":
                order.remove(item.placement)
                order.insert(0, item.placement)

            def place(rect):
                rect = QRectF(rect)
                rect.moveLeft(max(12, min(rect.left(), self.width() - rect.width() - 12)))
                rect.moveTop(max(12, min(rect.top(), self.height() - rect.height() - 12)))
                return rect

            options = [place(candidates[key]) for key in order]

            def score(rect, target=target):
                # Prefer cards outside the target and the dock; avoid earlier cards as possible.
                overlaps = [rect.intersected(other) for other in [target, *occupied]]
                return sum(r.width() * r.height() for r in overlaps if not r.isEmpty())

            card = min(options, key=score)
            occupied.append(card)
            painter.setPen(QPen(TEAL, 1))
            painter.drawLine(target.center(), card.center())
            painter.setBrush(INK)
            painter.setPen(QPen(QColor("#41645f"), 1))
            painter.drawRoundedRect(card, 10, 10)
            badge = QPointF(card.left() + 20, card.top() + 22)
            painter.setBrush(TEAL)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(badge, 10, 10)
            painter.setPen(INK)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(
                QRectF(badge.x() - 10, badge.y() - 10, 20, 20),
                Qt.AlignmentFlag.AlignCenter,
                str(number),
            )
            painter.setFont(font)
            painter.setPen(QColor("#f3f8f5"))
            painter.drawText(
                card.adjusted(38, 14, -10, -14), int(Qt.TextFlag.TextWordWrap), item.label
            )
        painter.end()


class LessonDock(QWidget):
    def __init__(self, controller):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.controller = controller
        self.user_position = False
        self.compact = False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("Computer Tutor")
        self.setStyleSheet("""
            QWidget { color: #f3f6f4; font-family: 'Segoe UI'; font-size: 13px; }
            QFrame#surface { background: #111e25; border: 1px solid #36514f;
                              border-radius: 16px; }
            QLabel#eyebrow { color: #6de4c4; font-size: 10px; font-weight: 700;
                              letter-spacing: 2px; }
            QLabel#title { font-size: 21px; font-weight: 600; }
            QLabel#meta { color: #a1b7b6; font-size: 11px; }
            QPlainTextEdit { background: transparent; border: none; color: #cbd9d6;
                             font-size: 13px; selection-background-color: #315d55; }
            QPushButton { background: #20343b; border: 1px solid #3a5156;
                          border-radius: 8px; padding: 8px 14px; font-weight: 600; }
            QPushButton:hover { background: #2d494e; }
            QPushButton:disabled { color: #607876; background: #1a2b32; }
            QPushButton#next { background: #69e2c1; color: #102923; border: none; }
            QPushButton#next:hover { background: #91f2d7; }
            QPushButton#next:disabled { background: #304c47; color: #90a9a4; }
            QPushButton#stop { color: #ffb5a8; padding: 5px 10px; font-size: 11px; }
            QCheckBox { color: #aabfbb; font-size: 11px; spacing: 6px; }
            QCheckBox::indicator { width: 15px; height: 15px; }
            QScrollBar:vertical { width: 7px; background: transparent; }
            QScrollBar::handle:vertical { background: #49635f; border-radius: 3px; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        surface = QFrame()
        surface.setObjectName("surface")
        outer.addWidget(surface)
        layout = QVBoxLayout(surface)
        layout.setContentsMargins(22, 17, 22, 17)
        layout.setSpacing(10)
        top = QHBoxLayout()
        eyebrow = DragHandle(self)
        eyebrow.setObjectName("eyebrow")
        top.addWidget(eyebrow)
        top.addStretch()
        self.visibility = QPushButton("Hinweise ausblenden")
        self.visibility.setAccessibleName("Markierungen ein- oder ausblenden")
        self.visibility.clicked.connect(controller.toggle_annotations)
        top.addWidget(self.visibility)
        home = QPushButton("⌂")
        home.setAccessibleName("Startfenster öffnen")
        home.clicked.connect(controller.show_home)
        top.addWidget(home)
        self.collapse = QPushButton("−")
        self.collapse.setAccessibleName("Lernleiste ein- oder ausklappen")
        self.collapse.clicked.connect(self.toggle_compact)
        top.addWidget(self.collapse)
        close = QPushButton("×")
        close.setAccessibleName("Lernleiste ausblenden und pausieren")
        close.setToolTip("Pausieren und zum Tray ausblenden")
        close.clicked.connect(controller.hide_dock)
        top.addWidget(close)
        layout.addLayout(top)
        self.meta = QLabel()
        self.meta.setObjectName("meta")
        self.meta.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.meta)
        self.title = QLabel()
        self.title.setObjectName("title")
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.explanation = QPlainTextEdit()
        self.explanation.setReadOnly(True)
        self.explanation.setAccessibleName("Ausführliche Erklärung des aktuellen Lernschritts")
        self.explanation.setMinimumHeight(65)
        layout.addWidget(self.explanation, 1)
        self.session_message = QLabel()
        self.session_message.setTextFormat(Qt.TextFormat.PlainText)
        self.session_message.setWordWrap(True)
        self.session_message.setObjectName("meta")
        layout.addWidget(self.session_message)
        self.retry = QPushButton("Erneut versuchen")
        self.retry.clicked.connect(controller._generate)
        self.retry.hide()
        layout.addWidget(self.retry)
        navigation = QHBoxLayout()
        self.previous = QPushButton("←  Zurück")
        self.previous.setAccessibleName("Vorheriger Lernschritt")
        self.previous.clicked.connect(lambda: controller.navigate_user("previous"))
        navigation.addWidget(self.previous)
        self.counter = QLabel()
        self.counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        navigation.addWidget(self.counter, 1)
        self.next = QPushButton("Weiter  →")
        self.next.setObjectName("next")
        self.next.setAccessibleName("Nächster Lernschritt")
        self.next.clicked.connect(lambda: controller.navigate_user("next"))
        navigation.addWidget(self.next)
        layout.addLayout(navigation)
        bottom = QHBoxLayout()
        self.permission = QCheckBox("Agent darf Maus & Tastatur steuern")
        self.permission.toggled.connect(controller.set_control)
        bottom.addWidget(self.permission)
        bottom.addStretch()
        stop = QPushButton("■  Stopp")
        stop.setObjectName("stop")
        stop.setToolTip("Steuerung sperren und Hinweise ausblenden · Strg+Alt+Esc")
        stop.clicked.connect(controller.stop)
        bottom.addWidget(stop)
        layout.addLayout(bottom)

    def render(self, state, screen, hotkey_available):
        step = state.step
        width = min(660, screen.availableGeometry().width() - 32)
        height = (
            210 if self.compact else min(390, math.floor(screen.availableGeometry().height() * 0.7))
        )
        self.resize(max(320, width), max(190 if self.compact else 310, height))
        area = screen.availableGeometry()
        if not self.user_position:
            x = area.x() + (area.width() - self.width()) // 2
            options = [QPoint(x, area.bottom() - self.height() - 15), QPoint(x, area.top() + 15)]
            targets = []
            if step:
                for annotation in step.annotations:
                    r = annotation.target
                    geometry = screen.geometry()
                    targets.append(
                        QRectF(
                            geometry.x() + r.x * geometry.width(),
                            geometry.y() + r.y * geometry.height(),
                            r.width * geometry.width(),
                            r.height * geometry.height(),
                        )
                    )

            def overlap(point):
                panel = QRectF(point.x(), point.y(), self.width(), self.height())
                return sum(
                    panel.intersected(t).width() * panel.intersected(t).height()
                    for t in targets
                    if panel.intersects(t)
                )

            self.move(min(options, key=overlap))
        self.title.setText(step.title if step else "Was möchtest du lernen?")
        text = (
            step.explanation
            if step
            else (
                "Verbinde einen MCP-Agenten mit Computer Tutor. Er kann dir Programme erklären, "
                "Schaltflächen markieren und dich Schritt für Schritt begleiten.\n\n"
                "Du bedienst den Computer selbst. Wenn du möchtest, kannst du unten zusätzlich "
                "die Steuerung durch den Agenten erlauben."
            )
        )
        if text != self.explanation.toPlainText():
            self.explanation.setPlainText(text)
        title = state.tutorial.title if state.tutorial else "Bereit für deinen Agenten"
        shortcut = "Strg+Alt+Esc: Stopp" if hotkey_available else "Stopp-Hotkey nicht verfügbar"
        self.meta.setToolTip(f"{title}  ·  {shortcut}")
        self.meta.setText(
            self.meta.fontMetrics().elidedText(
                f"{title}  ·  {shortcut}",
                Qt.TextElideMode.ElideRight,
                self.width() - 44,
            )
        )
        count = len(state.tutorial.steps) if state.tutorial else 0
        self.counter.setText(f"{state.step_index + 1} / {count}" if count else "Noch kein Tutorial")
        self.previous.setEnabled(count > 0 and state.step_index > 0)
        self.next.setEnabled(count > 0 and state.step_index < count - 1)
        self.visibility.setText(
            "Hinweise ausblenden" if state.annotations_visible else "Hinweise einblenden"
        )
        self.permission.blockSignals(True)
        self.permission.setChecked(state.control_enabled)
        self.permission.blockSignals(False)

    def reset_position(self):
        self.user_position = False

    def toggle_compact(self):
        self.compact = not self.compact
        self.explanation.setVisible(not self.compact)
        self.meta.setVisible(not self.compact)
        self.collapse.setText("+" if self.compact else "−")
        self.controller.refresh()

    def apply_text_size(self, size):
        self.explanation.setStyleSheet(f"font-size: {size}px;")

    def update_session(self, controller):
        self.session_message.setText(controller.message)
        self.retry.setVisible(controller.generation_error and not controller.busy)
        if controller.lesson_mode == "direct":
            if controller.state.step is None:
                self.title.setText(
                    "Dein Tutor schaut auf den Bildschirm …"
                    if controller.busy
                    else "Noch kein Lernschritt"
                )
                self.explanation.setPlainText(
                    "Die KI erstellt eine Erklärung aus deinem aktuellen Bildschirm. "
                    "Du kannst die Anfrage jederzeit mit Stopp abbrechen."
                )
            self.permission.setVisible(False)
            self.next.setEnabled(
                not controller.busy
                and controller.state.step is not None
                and (
                    not controller.lesson_done
                    or controller.state.step_index < len(controller.state.tutorial.steps) - 1
                )
            )
            if controller.busy:
                self.next.setText("Wird erstellt …")
            else:
                self.next.setText("Weiter  →")
        else:
            self.permission.setVisible(True)
            self.next.setText("Weiter  →")
        self.previous.setEnabled(self.previous.isEnabled() and not controller.busy)

    def moveEvent(self, event):  # noqa: N802
        super().moveEvent(event)
        if hasattr(self.controller, "dock"):
            self.controller.overlay.panel_rect = QRectF(
                self.geometry().translated(-self.controller.screen().geometry().topLeft())
            )
            self.controller.overlay.update()
