"""Standalone Windows shell: learning, provider settings and MCP setup."""

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from computer_tutor import __version__
from computer_tutor.storage import Settings, save_settings
from computer_tutor.theme import STYLE


def label(text, name=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    if primary:
        widget.setObjectName("primary")
    widget.clicked.connect(callback)
    return widget


class HomeWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Computer Tutor")
        self.setMinimumSize(740, 480)
        self.resize(980, 720)
        self.setStyleSheet(STYLE)
        root = QWidget()
        self.setCentralWidget(root)
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        navigation = QVBoxLayout(sidebar)
        navigation.setContentsMargins(18, 28, 18, 24)
        navigation.addWidget(label("computer\ntutor", "brand"))
        navigation.addSpacing(32)
        self.pages = QStackedWidget()
        self.pages.setStyleSheet("QStackedWidget { background: #101a21; }")
        group = QButtonGroup(self)
        self.nav_buttons = []
        for index, title in enumerate(["Lernen", "KI-Verbindung", "MCP-Agenten"]):
            nav = QPushButton(title)
            nav.setObjectName("nav")
            nav.setCheckable(True)
            nav.clicked.connect(lambda _checked=False, i=index: self.pages.setCurrentIndex(i))
            group.addButton(nav)
            navigation.addWidget(nav)
            self.nav_buttons.append(nav)
        self.pages.currentChanged.connect(lambda index: self.nav_buttons[index].setChecked(True))
        self.nav_buttons[0].setChecked(True)
        navigation.addStretch()
        navigation.addWidget(button("Demo entdecken", controller.start_demo))
        navigation.addWidget(label(f"Version {__version__}\nStrg+Alt+Esc: Stopp", "muted"))
        row.addWidget(sidebar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #101a21; }")
        scroll.setWidget(self.pages)
        row.addWidget(scroll, 1)
        self._learning_page()
        self._settings_page()
        self._mcp_page()
        self.statusBar().setStyleSheet("color: #9bb2b3; background: #101a21;")
        self.statusBar().showMessage("Bereit. Wähle ein Lernziel oder starte die Demo.")

    def page(self, title, subtitle):
        page = QWidget()
        page.setObjectName("page")
        page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 30, 34, 28)
        layout.setSpacing(16)
        layout.addWidget(label(title, "hero"))
        layout.addWidget(label(subtitle, "muted"))
        self.pages.addWidget(page)
        return layout

    def _learning_page(self):
        layout = self.page(
            "Lerne dein Programm.\nDirekt am Bildschirm.",
            "Ein Ziel, ein sichtbarer Hinweis, ein Schritt nach dem anderen.",
        )
        self.connection_status = label("Bereit für deine nächste Lektion", "status")
        layout.addWidget(self.connection_status)
        layout.addWidget(label("Was möchtest du lernen?", "section"))
        self.goal = QPlainTextEdit()
        self.goal.setPlaceholderText(
            "Zum Beispiel: Zeige mir, wie ich im geöffneten Programm ein PDF exportiere."
        )
        self.goal.setAccessibleName("Dein Lernziel")
        self.goal.setMaximumHeight(140)
        layout.addWidget(self.goal)
        monitor_row = QHBoxLayout()
        self.monitor_choice = QComboBox()
        self.monitor_choice.setAccessibleName("Bildschirm für das Tutorial")
        monitor_row.addWidget(self.monitor_choice, 1)
        monitor_row.addWidget(button("↻", self.reload_monitors))
        self.start = button("Lernen starten  →", self.start_lesson, True)
        monitor_row.addWidget(self.start)
        layout.addLayout(monitor_row)
        self.error = label("", "error")
        layout.addWidget(self.error)
        card = QFrame()
        card.setObjectName("card")
        body = QVBoxLayout(card)
        body.setContentsMargins(18, 18, 18, 18)
        body.addWidget(label("Du klickst. Dein Tutor erklärt.", "section"))
        body.addWidget(
            label(
                "Beim Starten und bei einem neuen Lernschritt wird dein ausgewählter Bildschirm "
                "an den eingestellten KI-Anbieter gesendet. Markierungen bleiben durchklickbar. "
                "Zurück zeigt frühere Erklärungen; Stopp beendet die Begleitung.",
                "muted",
            )
        )
        layout.addWidget(card)
        actions = QHBoxLayout()
        actions.addWidget(button("Lernleiste anzeigen", self.controller.show_dock))
        actions.addWidget(button("Tutorial öffnen…", self.open_tutorial))
        actions.addWidget(button("Speichern…", self.save_tutorial))
        layout.addLayout(actions)
        layout.addStretch()
        self.reload_monitors()

    def reload_monitors(self):
        previous = self.monitor_choice.currentData() or self.controller.settings.monitor_id
        self.monitor_choice.clear()
        for number, monitor in enumerate(self.controller.monitors(), 1):
            bounds = monitor["physical_bounds"] or monitor["logical_bounds"]
            self.monitor_choice.addItem(
                f"Bildschirm {number} · {bounds['width']} × {bounds['height']}"
                + (" · Hauptbildschirm" if monitor["primary"] else ""),
                monitor["id"],
            )
        index = self.monitor_choice.findData(previous)
        if index >= 0:
            self.monitor_choice.setCurrentIndex(index)

    def _settings_page(self):
        settings = self.controller.settings
        layout = self.page(
            "Deine KI-Verbindung", "Nutze einen Anbieter mit einer OpenAI-kompatiblen Vision-API."
        )
        form = QFormLayout()
        form.setSpacing(14)
        self.endpoint = QLineEdit(settings.endpoint)
        self.model = QLineEdit(settings.model)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText(
            "Sicher gespeichert" if settings.encrypted_api_key else "API-Key"
        )
        self.font_size = QSpinBox()
        self.font_size.setRange(12, 20)
        self.font_size.setValue(settings.font_size)
        form.addRow("API-Basisadresse", self.endpoint)
        form.addRow("Modell mit Bildfunktion", self.model)
        form.addRow("API-Key", self.api_key)
        form.addRow("Textgröße in der Lernleiste", self.font_size)
        layout.addLayout(form)
        layout.addWidget(
            label(
                "Der Schlüssel wird für dein Windows-Benutzerkonto verschlüsselt gespeichert. "
                "Ein lokaler Anbieter auf localhost darf ohne Schlüssel arbeiten. "
                "Die Nutzung eines Cloud-Anbieters kann API-Kosten verursachen.",
                "muted",
            )
        )
        self.sharing = QCheckBox("Bildschirmaufnahmen für diese KI-Verbindung erlauben")
        self.sharing.setChecked(settings.screen_sharing)
        layout.addWidget(self.sharing)
        self.endpoint.textEdited.connect(lambda _text: self.sharing.setChecked(False))
        layout.addWidget(
            label(
                "Es gibt keine dauernde Aufnahme. Bilder werden nur für angeforderte Lernschritte "
                "gesendet und von Computer Tutor nicht gespeichert. MCP-Agenten erhalten "
                "Screenshots ausschließlich über ihre eigenen Werkzeugaufrufe.",
                "muted",
            )
        )
        row = QHBoxLayout()
        row.addWidget(button("Einstellungen speichern", self.store_settings, True))
        row.addWidget(button("API-Key entfernen", self.remove_key))
        layout.addLayout(row)
        self.settings_message = label("", "muted")
        layout.addWidget(self.settings_message)
        layout.addStretch()

    def store_settings(self):
        try:
            old = self.controller.settings
            updated = Settings(
                endpoint=self.endpoint.text(),
                model=self.model.text().strip(),
                encrypted_api_key=(
                    old.encrypted_api_key
                    if self.endpoint.text().rstrip("/") == old.endpoint
                    else ""
                ),
                screen_sharing=self.sharing.isChecked(),
                font_size=self.font_size.value(),
                monitor_id=self.monitor_choice.currentData() or "",
            )
            key = self.api_key.text().strip()
            if key:
                updated.set_api_key(key)
            self.controller.stop()
            save_settings(updated)
            self.controller.settings = updated
            self.api_key.clear()
            self.api_key.setPlaceholderText(
                "Sicher gespeichert" if updated.encrypted_api_key else "API-Key"
            )
            self.settings_message.setText(
                "Gespeichert. Die Verbindung wird beim Lernstart verwendet."
            )
            self.controller.refresh()
        except Exception:
            self.settings_message.setText(
                "Speichern fehlgeschlagen. Adresse, Modell und Windows-Schlüsselspeicher prüfen."
            )

    def remove_key(self):
        self.controller.stop()
        self.controller.settings.encrypted_api_key = ""
        self.api_key.clear()
        self.api_key.setPlaceholderText("API-Key")
        save_settings(self.controller.settings)
        self.settings_message.setText("Der gespeicherte API-Key wurde entfernt.")

    def _mcp_page(self):
        layout = self.page(
            "Mit deinem Agenten lernen", "Vorhandene KI-Agenten verbinden sich lokal über MCP."
        )
        layout.addWidget(
            label(
                "Füge diese Konfiguration in deinen Windows-MCP-Client ein. Der MCP-Starter öffnet "
                "diese App bei Bedarf und verwendet die bereits laufende Instanz. Für MCP ist "
                "kein API-Key in Computer Tutor nötig.",
                "muted",
            )
        )
        if getattr(sys, "frozen", False):
            command = str(Path(sys.executable).with_name("computer-tutor-mcp.exe"))
            arguments = ["--mcp"]
        else:
            command, arguments = sys.executable, ["-m", "computer_tutor", "--mcp"]
        config = {"mcpServers": {"computer-tutor": {"command": command, "args": arguments}}}
        self.mcp_config = QPlainTextEdit(json.dumps(config, indent=2, ensure_ascii=False))
        self.mcp_config.setReadOnly(True)
        layout.addWidget(self.mcp_config)
        layout.addWidget(
            button(
                "Konfiguration kopieren",
                lambda: (
                    QApplication.clipboard().setText(self.mcp_config.toPlainText()),
                    self.statusBar().showMessage("MCP-Konfiguration kopiert.", 5000),
                ),
            )
        )
        layout.addWidget(
            label(
                "Maus und Tastatur bleiben gesperrt, bis du sie in der Lernleiste ausdrücklich "
                "freigibst. Strg+Alt+Esc sperrt die Eingaben sofort wieder. Beim Verlust der "
                "Agentenverbindung wird die Freigabe ebenfalls zurückgenommen.",
                "muted",
            )
        )
        layout.addStretch()

    def start_lesson(self):
        goal = self.goal.toPlainText().strip()
        if not 1 <= len(goal) <= 1000:
            self.error.setText("Bitte ein Lernziel mit höchstens 1000 Zeichen eingeben.")
            return
        try:
            self.controller.start_learning(goal, self.monitor_choice.currentData())
            self.error.clear()
        except Exception as error:
            self.error.setText(str(error))
            self.pages.setCurrentIndex(1)

    def open_tutorial(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Tutorial öffnen", "", "Tutorial (*.json)")
        if filename:
            try:
                path = Path(filename)
                if path.stat().st_size > 2_000_000:
                    raise ValueError("Datei zu groß")
                self.controller.import_tutorial(
                    path.read_text(encoding="utf-8"), self.monitor_choice.currentData()
                )
            except Exception:
                QMessageBox.warning(self, "Tutorial nicht geladen", "Keine gültige Tutorial-Datei.")

    def save_tutorial(self):
        tutorial = self.controller.state.tutorial
        if not tutorial:
            self.statusBar().showMessage("Noch kein Tutorial zum Speichern vorhanden.", 5000)
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Tutorial speichern", "tutorial.json", "Tutorial (*.json)"
        )
        if filename:
            try:
                Path(filename).write_text(tutorial.model_dump_json(indent=2), encoding="utf-8")
                self.statusBar().showMessage(
                    "Tutorial gespeichert (ohne Screenshots und Zugangsdaten).", 5000
                )
            except OSError:
                QMessageBox.warning(
                    self, "Speichern fehlgeschlagen", "Datei konnte nicht gespeichert werden."
                )

    def closeEvent(self, event):  # noqa: N802
        if self.controller.tray and self.controller.tray.isVisible():
            event.ignore()
            self.hide()
        else:
            self.controller.quit()
