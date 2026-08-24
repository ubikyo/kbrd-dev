import json
from threading import Thread
from urllib.error import URLError
from urllib.request import urlopen

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import mm
from kivy.uix.floatlayout import FloatLayout

from kbrd_dev.config import API_URL
from kbrd_dev.ui.key import Key


class Keyboard(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.background = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_background, size=self._update_background)
        self.bind(size=self._layout_keys)

        self._layout = None
        self._unit = "mm"
        self._keys = []
        self._request_pending = False
        self._stopped = False
        self._refresh_geometry()
        self._refresh_event = Clock.schedule_interval(
            self._refresh_geometry,
            5,
        )

    def _refresh_geometry(self, *args):
        if self._request_pending:
            return

        self._request_pending = True
        Thread(target=self._load_geometry, daemon=True).start()

    def _load_geometry(self):
        try:
            with urlopen(
                f"{API_URL}/api/geometry/active",
                timeout=2,
            ) as response:
                result = json.load(response)
        except (OSError, URLError, json.JSONDecodeError):
            result = None

        Clock.schedule_once(
            lambda *args: self._geometry_loaded(result),
        )

    def _geometry_loaded(self, result):
        self._request_pending = False
        if self._stopped:
            return
        if not isinstance(result, dict):
            return

        layout = result.get("layout")
        unit = result.get("unit")
        if not isinstance(layout, dict) or unit not in ("mm", "px"):
            return
        if layout == self._layout and unit == self._unit:
            return

        self._layout = layout
        self._unit = unit
        self._rebuild_keys()

    def _rebuild_keys(self):
        for key in self._keys:
            self.remove_widget(key)
        self._keys.clear()

        for layout in self._layout.get("keys", []):
            key = Key(parts=layout.get("parts"))
            key.layout = layout
            key.ref = layout.get("ref", "")
            key.name = layout.get("name", "")
            self._keys.append(key)
            self.add_widget(key)

        self._layout_keys()

    def _pixels(self, value):
        return mm(value) if self._unit == "mm" else float(value)

    def _layout_keys(self, *args):
        if not self._layout:
            return

        keyboard_width = self._pixels(self._layout.get("width", 0))
        keyboard_height = self._pixels(self._layout.get("height", 0))
        if keyboard_width <= 0 or keyboard_height <= 0:
            return

        origin_x = self.x + (self.width - keyboard_width) / 2
        origin_y = self.y + (self.height - keyboard_height) / 2

        for key in self._keys:
            layout = key.layout
            width = self._pixels(layout["width"])
            height = self._pixels(layout["height"])
            key.size = (width, height)
            key.pos = (
                origin_x + self._pixels(layout["x"]),
                origin_y
                + keyboard_height
                - self._pixels(layout["y"])
                - height,
            )

    def on_parent(self, instance, parent):
        if parent is not None:
            return
        self._stopped = True
        if getattr(self, "_refresh_event", None):
            self._refresh_event.cancel()
            self._refresh_event = None

    def _update_background(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size
