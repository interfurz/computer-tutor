"""Per-user settings and Windows DPAPI encryption; never persist plaintext API keys."""

import base64
import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


def data_directory() -> Path:
    override = os.environ.get("COMPUTER_TUTOR_DATA_DIR")
    root = (
        Path(override)
        if override
        else (
            Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "ComputerTutor"
        )
    )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def protect(data: bytes, decrypt=False) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("Das sichere Speichern von Zugangsdaten benötigt Windows.")

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), buffer)
    target = Blob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.c_wchar_p,
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(Blob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.POINTER(ctypes.c_wchar_p),
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(Blob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        success = crypt32.CryptUnprotectData(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            1,
            ctypes.byref(target),
        )
    else:
        success = crypt32.CryptProtectData(
            ctypes.byref(source),
            "Computer Tutor",
            None,
            None,
            None,
            1,
            ctypes.byref(target),
        )
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel32.LocalFree(target.data)


class Settings(BaseModel):
    endpoint: str = "https://api.openai.com/v1"
    model: str = Field(default="gpt-4.1-mini", min_length=1, max_length=200)
    encrypted_api_key: str = ""
    screen_sharing: bool = False
    monitor_id: str = ""
    font_size: int = Field(default=13, ge=12, le=20)

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value):
        parsed = urlparse(value.strip())
        if (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or not parsed.hostname
        ):
            raise ValueError("Eine API-Basisadresse ohne Zugangsdaten oder Parameter eingeben.")
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
            raise ValueError("Die API-Adresse muss HTTPS verwenden (lokal ist HTTP erlaubt).")
        return value.strip().rstrip("/")

    def api_key(self) -> str:
        if not self.encrypted_api_key:
            return ""
        return protect(base64.b64decode(self.encrypted_api_key), decrypt=True).decode("utf-8")

    def set_api_key(self, key: str):
        self.encrypted_api_key = base64.b64encode(protect(key.encode("utf-8"))).decode("ascii")


def load_settings() -> Settings:
    path = data_directory() / "settings.json"
    if not path.exists():
        return Settings()
    try:
        return Settings.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        # Preserve the original file for recovery, without logging credentials or its contents.
        return Settings()


def save_settings(settings: Settings):
    atomic_write(data_directory() / "settings.json", settings.model_dump_json(indent=2))


def atomic_write(path: Path, content: str):
    import tempfile

    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tutor-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
