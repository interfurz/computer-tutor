import contextlib
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_data_directory(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("COMPUTER_TUTOR_DATA_DIR", str(tmp_path_factory.mktemp("ct")))
    yield
    from computer_tutor.ipc import LocalClient

    with contextlib.suppress(Exception):
        LocalClient().call("quit")
