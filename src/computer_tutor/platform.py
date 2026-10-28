"""Windows monitor geometry, global stop shortcut and bounded native input."""

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter


def physical_monitors() -> dict[str, tuple[int, int, int, int]]:
    """Match Qt's display device names to Win32 physical-pixel monitor rectangles."""
    if sys.platform != "win32":
        return {}

    class MonitorInfo(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("monitor", wintypes.RECT),
            ("work", wintypes.RECT),
            ("flags", wintypes.DWORD),
            ("device", wintypes.WCHAR * 32),
        ]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HANDLE,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    user32.EnumDisplayMonitors.argtypes = [
        wintypes.HDC,
        ctypes.c_void_p,
        callback_type,
        wintypes.LPARAM,
    ]
    user32.EnumDisplayMonitors.restype = wintypes.BOOL
    result = {}

    @callback_type
    def visit(handle, _hdc, _rect, _data):
        info = MonitorInfo()
        info.size = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(handle, ctypes.byref(info)):
            r = info.monitor
            result[info.device] = (r.left, r.top, r.right - r.left, r.bottom - r.top)
        return True

    if not user32.EnumDisplayMonitors(None, None, visit, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return result


class StopHotkey(QAbstractNativeEventFilter):
    ID = 0x4354

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.registered = False
        if sys.platform == "win32":
            self.registered = bool(
                ctypes.windll.user32.RegisterHotKey(
                    None,
                    self.ID,
                    0x0001 | 0x0002 | 0x4000,
                    0x1B,
                )
            )  # Alt + Ctrl + Escape, no repeat

    def nativeEventFilter(self, event_type, message):  # noqa: N802
        if sys.platform == "win32":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == self.ID:
                self.callback()
                return True, 0
        return False, 0

    def close(self):
        if self.registered:
            ctypes.windll.user32.UnregisterHotKey(None, self.ID)
            self.registered = False


class WindowsInput:
    """No shell execution. Permission is checked by the controller on every action."""

    KEYS = {
        "ctrl": 0x11,
        "alt": 0x12,
        "shift": 0x10,
        "win": 0x5B,
        "enter": 0x0D,
        "tab": 0x09,
        "escape": 0x1B,
        "space": 0x20,
        "backspace": 0x08,
        "delete": 0x2E,
        "home": 0x24,
        "end": 0x23,
        "left": 0x25,
        "up": 0x26,
        "right": 0x27,
        "down": 0x28,
        "pageup": 0x21,
        "pagedown": 0x22,
        **{chr(c).lower(): c for c in range(0x41, 0x5B)},
        **{str(i): 0x30 + i for i in range(10)},
        **{f"f{i}": 0x6F + i for i in range(1, 13)},
    }

    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("Desktop input is available only on Windows.")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        ulong_ptr = ctypes.c_size_t

        class Mouse(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("data", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("extra", ulong_ptr),
            ]

        class Keyboard(ctypes.Structure):
            _fields_ = [
                ("vk", wintypes.WORD),
                ("scan", wintypes.WORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("extra", ulong_ptr),
            ]

        class Payload(ctypes.Union):
            _fields_ = [("mouse", Mouse), ("keyboard", Keyboard)]

        class Input(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("payload", Payload)]

        self.Mouse, self.Keyboard, self.Input = Mouse, Keyboard, Input
        self.user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        self.user32.SendInput.restype = wintypes.UINT
        self.user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        self.user32.SetCursorPos.restype = wintypes.BOOL

    def _send(self, events):
        array = (self.Input * len(events))(*events)
        sent = self.user32.SendInput(len(events), array, ctypes.sizeof(self.Input))
        if sent != len(events):
            # Release every requested key on partial injection to avoid stuck modifiers.
            releases = [
                self.Input(
                    type=1,
                    payload=type(event.payload)(
                        keyboard=self.Keyboard(
                            vk=event.payload.keyboard.vk,
                            scan=event.payload.keyboard.scan,
                            flags=event.payload.keyboard.flags | 0x0002,
                        )
                    ),
                )
                for event in events
                if event.type == 1
            ]
            for event in events:
                if event.type == 0:
                    for down, up in ((0x0002, 0x0004), (0x0008, 0x0010)):
                        if event.payload.mouse.flags & down:
                            releases.append(self._mouse(up))
            if releases:
                release_array = (self.Input * len(releases))(*releases)
                self.user32.SendInput(len(releases), release_array, ctypes.sizeof(self.Input))
            raise RuntimeError("Windows blocked input (for example, an elevated target app).")

    def _key(self, vk=0, scan=0, flags=0):
        event = self.Input(type=1)
        event.payload.keyboard = self.Keyboard(vk=vk, scan=scan, flags=flags)
        return event

    def _mouse(self, flags, data=0):
        event = self.Input(type=0)
        event.payload.mouse = self.Mouse(flags=flags, data=data & 0xFFFFFFFF)
        return event

    def click(self, x: int, y: int, button: str):
        flags = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010)}
        down, up = flags[button]
        if not self.user32.SetCursorPos(x, y):
            raise ctypes.WinError(ctypes.get_last_error())
        self._send([self._mouse(down), self._mouse(up)])

    def type_text(self, text: str):
        encoded = text.encode("utf-16-le")
        events = []
        for index in range(0, len(encoded), 2):
            unit = int.from_bytes(encoded[index : index + 2], "little")
            events.extend(
                [self._key(scan=unit, flags=0x0004), self._key(scan=unit, flags=0x0004 | 0x0002)]
            )
        self._send(events)

    def hotkey(self, keys: list[str]):
        codes = [self.KEYS[key.lower()] for key in keys]
        extended = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2E, 0x5B}
        self._send(
            [self._key(vk=code, flags=1 if code in extended else 0) for code in codes]
            + [
                self._key(vk=code, flags=2 | (1 if code in extended else 0))
                for code in reversed(codes)
            ]
        )

    def scroll(self, ticks: int):
        self._send([self._mouse(0x0800, ticks * 120)])
