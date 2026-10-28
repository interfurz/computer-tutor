"""Entry point for demo and MCP-hosted Windows sessions."""

import argparse
import contextlib
import logging
import os
import sys
import threading


def main():
    parser = argparse.ArgumentParser(description="Computer Tutor · Windows learning HUD")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mcp", action="store_true", help="Run the stdio MCP server and HUD")
    mode.add_argument("--demo", action="store_true", help="Show a three-step demo lesson")
    parser.add_argument("--allow-non-windows", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != "win32" and not args.allow_non_windows:
        parser.error("Computer Tutor targets Windows 10/11. See README for development checks.")

    # Keep stdout clean for the MCP JSON-RPC stream, including when launched as an .exe.
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from computer_tutor.bridge import GuiBridge
    from computer_tutor.controller import TutorController
    from computer_tutor.demo import demo_tutorial

    app = QApplication([sys.argv[0]])
    app.setApplicationName("Computer Tutor")
    app.setQuitOnLastWindowClosed(False)
    bridge = GuiBridge()
    controller = TutorController(app)
    if args.demo or not args.mcp:
        controller.load(demo_tutorial(controller.id_for(app.primaryScreen())))

    server_failed = threading.Event()
    server_done = threading.Event()
    if args.mcp:
        from computer_tutor.server import create_server

        server = create_server(bridge, controller)

        def run_server():
            try:
                server.run(transport="stdio")
            except Exception:
                logging.exception("MCP server stopped unexpectedly")
                server_failed.set()
            finally:
                server_done.set()

        thread = threading.Thread(target=run_server, name="mcp-stdio", daemon=True)
        thread.start()
        # EOF (client disconnected) also closes the HUD. Timer keeps all UI access on Qt.
        timer = QTimer()
        timer.timeout.connect(lambda: controller.quit() if server_done.is_set() else None)
        timer.start(200)

    result = app.exec()
    if args.mcp:
        # The stdio reader can remain blocked after a local close. Terminate this dedicated
        # process after Qt cleanup so the host observes EOF rather than a ghost MCP session.
        for stream in (sys.stdout, sys.stderr):
            with contextlib.suppress(OSError, ValueError):
                stream.flush()
        os._exit(1 if server_failed.is_set() else result)
    raise SystemExit(result)
