import json
from threading import Thread
from urllib.error import URLError
from urllib.request import urlopen

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import mm
from kivy.uix.floatlayout import FloatLayout

from kbrd_dev.config import API_URL
from kbrd_dev.plugins import PluginRegistry
from kbrd_dev.ui.key import Key

BACKGROUND_REF = "__background__"


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
        self._plugins = []
        self._properties = []
        self._plugin_registry = PluginRegistry()
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
                f"{API_URL}/api/workspace/active",
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

        geometry = result.get("geometry")
        workspace = result.get("workspace")
        if not isinstance(geometry, dict):
            return
        layout = geometry.get("layout")
        unit = geometry.get("unit")
        plugins = workspace.get("plugins", []) if isinstance(workspace, dict) else []
        properties = (
            workspace.get("key_properties", [])
            if isinstance(workspace, dict)
            else []
        )
        if not isinstance(layout, dict) or unit not in ("mm", "px"):
            return
        if (
            layout == self._layout
            and unit == self._unit
            and plugins == self._plugins
            and properties == self._properties
        ):
            return

        self._layout = layout
        self._unit = unit
        self._plugins = plugins
        self._properties = properties
        self._rebuild_keys()

    def _rebuild_keys(self):
        for key in self._keys:
            self.remove_widget(key)
        self._keys.clear()

        plugins_by_key = {}
        for instance in self._plugins:
            plugins_by_key.setdefault(instance.get("key_ref"), []).append(instance)
        properties_by_key = {
            item.get("key_ref"): item.get("config", {})
            for item in self._properties
            if isinstance(item, dict)
        }

        background = Key(element_type="background")
        background.layout = {
            "is_background": True,
            "x": 0,
            "y": 0,
            "width": self._layout.get("width", 0),
            "height": self._layout.get("height", 0),
            "parts": [],
        }
        background.unit = self._unit
        background.ref = BACKGROUND_REF
        background.name = "Background"
        self._keys.append(background)
        self.add_widget(background)
        for instance in sorted(
            plugins_by_key.get(BACKGROUND_REF, []),
            key=lambda item: item.get("position", 0),
        ):
            self._plugin_registry.render(background, instance)

        for layout in self._layout.get("keys", []):
            key = Key(
                element_type=layout.get("type", "key"),
                parts=layout.get("parts"),
            )
            key.layout = layout
            key.unit = self._unit
            key.ref = layout.get("ref", "")
            key.name = layout.get("name", "")
            key.apply_style(properties_by_key.get(key.ref, {}))
            self._keys.append(key)
            self.add_widget(key)
            if key.element_type == "key":
                for instance in sorted(
                    plugins_by_key.get(key.ref, []),
                    key=lambda item: item.get("position", 0),
                ):
                    self._plugin_registry.render(key, instance)

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
            if layout.get("is_background"):
                key.size = self.size
                key.pos = self.pos
                continue
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
