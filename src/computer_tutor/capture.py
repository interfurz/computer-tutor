"""Reusable HUD-free capture for local AI and MCP clients."""

import threading
import time

import mss
import mss.tools


class ScreenCapture:
    def __init__(self, bridge, controller):
        self.bridge = bridge
        self.controller = controller
        self.lock = threading.Lock()

    def capture(self, monitor_id):
        with self.lock:
            monitor = self.bridge.call(lambda: self.controller.begin_capture(monitor_id))
            lease = monitor.pop("capture_token", None)
            try:
                time.sleep(0.15)
                bounds = monitor["physical_bounds"]
                with mss.mss() as capture:
                    shot = capture.grab(bounds)
                    png = mss.tools.to_png(shot.rgb, shot.size)
                if self.bridge.call(lambda: self.controller.monitor(monitor_id)) != monitor:
                    raise RuntimeError("Bildschirmanordnung geändert. Bitte erneut aufnehmen.")
                if lease and not self.bridge.call(lambda: self.controller.capture_valid(lease)):
                    raise RuntimeError("Bildschirmaufnahme abgelaufen. Bitte erneut aufnehmen.")
                metadata = {
                    "monitor_id": monitor_id,
                    "width": shot.width,
                    "height": shot.height,
                    "physical_bounds": bounds,
                    "coordinate_space": "monitor_normalized",
                }
                return metadata, png
            finally:
                self.bridge.call(lambda: self.controller.end_capture(lease))
