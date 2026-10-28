"""Serialize MCP worker requests onto Qt's GUI thread."""

from concurrent.futures import Future, TimeoutError
from typing import Any

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot


class GuiBridge(QObject):
    requested = Signal(object, object)

    def __init__(self) -> None:
        super().__init__()
        self.requested.connect(self._run, Qt.ConnectionType.QueuedConnection)

    @Slot(object, object)
    def _run(self, function: Any, future: Future) -> None:
        if not future.set_running_or_notify_cancel():
            return
        try:
            future.set_result(function())
        except Exception as error:
            future.set_exception(error)

    def call(self, function: Any) -> Any:
        if QThread.currentThread() == self.thread():
            return function()
        future: Future = Future()
        self.requested.emit(function, future)
        try:
            return future.result(timeout=15)
        except TimeoutError:
            # A timed-out queued input must not execute later when the UI resumes.
            future.cancel()
            raise RuntimeError("The HUD did not respond. Check the Windows app.") from None
