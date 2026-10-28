"""Standalone GUI and console MCP entry points sharing one authenticated local app."""

import argparse
import contextlib
import logging
import sys
import threading
import uuid

from computer_tutor import __version__


def run_mcp(allow_non_windows):
    from computer_tutor.ipc import DirectBridge, RemoteController, ensure_app
    from computer_tutor.server import create_server

    client = ensure_app(allow_non_windows)
    identifier = uuid.uuid4().hex
    client.call("connect_agent", identifier)
    finished = threading.Event()

    def heartbeat():
        while not finished.wait(3):
            try:
                client.call("connect_agent", identifier)
            except (ConnectionError, RuntimeError, OSError):
                return

    threading.Thread(target=heartbeat, name="tutor-heartbeat", daemon=True).start()
    try:
        create_server(DirectBridge(), RemoteController(client)).run(transport="stdio")
    finally:
        finished.set()
        with contextlib.suppress(Exception):
            client.call("disconnect_agent", identifier)


def main():
    parser = argparse.ArgumentParser(description="Computer Tutor · Lernen direkt am Bildschirm")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mcp", action="store_true", help="Lokalen stdio-MCP-Starter ausführen")
    mode.add_argument("--demo", action="store_true", help="Demo-Tutorial zeigen")
    mode.add_argument("--shutdown", action="store_true", help="Laufende App beenden")
    mode.add_argument("--background", action="store_true", help=argparse.SUPPRESS)
    mode.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--allow-non-windows", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != "win32" and not args.allow_non_windows:
        parser.error("Computer Tutor benötigt Windows 10/11.")

    from computer_tutor.storage import data_directory

    if args.mcp:
        logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
        run_mcp(args.allow_non_windows)
        return

    from computer_tutor.ipc import LocalClient

    if args.shutdown:
        with contextlib.suppress(ConnectionError):
            LocalClient().call("quit")
        return

    from logging.handlers import RotatingFileHandler

    handler = RotatingFileHandler(
        data_directory() / "app.log", maxBytes=500_000, backupCount=2, encoding="utf-8"
    )
    logging.basicConfig(handlers=[handler], level=logging.WARNING)

    from PySide6.QtCore import QLockFile, QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox

    from computer_tutor.bridge import GuiBridge
    from computer_tutor.controller import TutorController
    from computer_tutor.ipc import LocalServer
    from computer_tutor.theme import app_icon

    app = QApplication([sys.argv[0]])
    app.setApplicationName("Computer Tutor")
    app.setOrganizationName("ComputerTutor")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(False)
    lock = QLockFile(str(data_directory() / "app.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(3000):
        with contextlib.suppress(ConnectionError, RuntimeError):
            LocalClient().call("show_home")
        return
    bridge = GuiBridge()
    controller = TutorController(app)
    controller.setup_shell(bridge)
    server = LocalServer(bridge, controller)
    app.aboutToQuit.connect(server.close)

    def report_error(kind, error, traceback):
        logging.error("Unhandled application error", exc_info=(kind, error, traceback))
        controller.stop()
        QMessageBox.warning(
            controller.home,
            "Computer Tutor",
            "Ein Fehler ist aufgetreten. Bitte den Vorgang erneut versuchen. "
            "Technische Hinweise stehen in der lokalen app.log.",
        )

    sys.excepthook = report_error
    if args.demo:
        controller.start_demo()
    elif not args.background:
        controller.show_home()
    if args.smoke_test:
        QTimer.singleShot(250, controller.quit)
    result = app.exec()
    lock.unlock()
    raise SystemExit(result)
