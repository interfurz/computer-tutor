"""Authenticated per-user local IPC, connecting console MCP clients to one GUI app."""

import hashlib
import json
import os
import secrets
import subprocess
import sys
import threading
import time
from multiprocessing.connection import Client, Listener
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel

from computer_tutor.storage import atomic_write, data_directory, protect

ALLOWED = {
    "monitors",
    "monitor",
    "load",
    "replace_step",
    "navigate",
    "snapshot",
    "set_annotations_visible",
    "stop",
    "begin_capture",
    "end_capture",
    "capture_valid",
    "desktop_action",
    "show_home",
    "connect_agent",
    "disconnect_agent",
    "quit",
    "ping",
}


def address():
    digest = hashlib.sha256(str(data_directory().resolve()).encode()).hexdigest()[:20]
    if sys.platform == "win32":
        return rf"\\.\pipe\ComputerTutor-{digest}", "AF_PIPE"
    return str(data_directory() / "app.sock"), "AF_UNIX"


def token(create=False):
    path = data_directory() / "ipc.key"
    if path.exists():
        raw = bytes.fromhex(path.read_text(encoding="ascii"))
        return protect(raw, decrypt=True) if sys.platform == "win32" else raw
    if not create:
        raise ConnectionError("Computer Tutor ist noch nicht gestartet.")
    raw = secrets.token_bytes(32)
    protected = protect(raw) if sys.platform == "win32" else raw
    atomic_write(path, protected.hex())
    return raw


def encode(value):
    if isinstance(value, BaseModel):
        return value.model_dump()
    raise TypeError("Unsupported local RPC value")


class LocalClient:
    def call(self, method, *args, **kwargs):
        if method not in ALLOWED:
            raise ValueError("Unknown local method")
        location, family = address()
        try:
            with Client(location, family=family, authkey=token()) as connection:
                connection.send_bytes(
                    json.dumps(
                        {"method": method, "args": args, "kwargs": kwargs},
                        default=encode,
                    ).encode()
                )
                if not connection.poll(20):
                    raise TimeoutError("Die App antwortet nicht.")
                response = json.loads(connection.recv_bytes(4_000_000))
        except (OSError, EOFError) as error:
            raise ConnectionError(
                "Computer Tutor ist nicht erreichbar. Bitte die App öffnen."
            ) from error
        if "error" in response:
            raise RuntimeError(response["error"])
        return response["result"]


class RemoteController:
    def __init__(self, client):
        self.client = client
        self.state = SimpleNamespace(snapshot=lambda: client.call("snapshot"))

    def __getattr__(self, name):
        if name not in ALLOWED:
            raise AttributeError(name)
        return lambda *args, **kwargs: self.client.call(name, *args, **kwargs)


class DirectBridge:
    def call(self, function):
        return function()


class LocalServer:
    def __init__(self, bridge, controller):
        self.bridge, self.controller = bridge, controller
        location, family = address()
        if family == "AF_UNIX":
            Path(location).unlink(missing_ok=True)  # Caller holds the process lock.
        self.listener = Listener(location, family=family, authkey=token(create=True))
        self.closed = False
        threading.Thread(target=self.run, name="tutor-local-ipc", daemon=True).start()

    def run(self):
        while not self.closed:
            try:
                connection = self.listener.accept()
            except (OSError, EOFError):
                break
            except Exception:
                continue
            threading.Thread(target=self.handle, args=(connection,), daemon=True).start()

    def handle(self, connection):
        with connection:
            try:
                if not connection.poll(5):
                    return
                request = json.loads(connection.recv_bytes(2_000_000))
                method = request["method"]
                if method not in ALLOWED:
                    raise ValueError("Unknown local method")
                result = self.bridge.call(
                    lambda: self.controller.rpc(
                        method,
                        request.get("args", []),
                        request.get("kwargs", {}),
                    )
                )
                reply = {"result": result}
            except Exception as error:
                reply = {"error": str(error)}
            try:
                connection.send_bytes(json.dumps(reply).encode())
            except (OSError, EOFError):
                pass

    def close(self):
        self.closed = True
        self.listener.close()


def gui_command(*args):
    if getattr(sys, "frozen", False):
        gui = Path(sys.executable).with_name(
            "ComputerTutor.exe" if sys.platform == "win32" else "ComputerTutor"
        )
        return [str(gui), *args]
    return [sys.executable, "-m", "computer_tutor", *args]


def ensure_app(allow_non_windows=False):
    client = LocalClient()
    try:
        client.call("ping")
        return client
    except (ConnectionError, OSError):
        pass
    args = ["--background"]
    if allow_non_windows:
        args.append("--allow-non-windows")
    subprocess.Popen(
        gui_command(*args),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"},
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            client.call("ping")
            return client
        except (ConnectionError, OSError):
            time.sleep(0.1)
    raise RuntimeError("Computer Tutor konnte nicht gestartet werden. Bitte die App direkt öffnen.")
