import json
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import urlopen

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import mm
from kivy.uix.floatlayout import FloatLayout

from kbrd_dev.config import API_URL
from kbrd_dev.ui.key import Key


KEY_HEIGHT_MM = 16
GAP_MM = 3
OUTER_MARGIN_MM = 20


@dataclass
class KeyLayout:
    x: float
    y: float
    width: float
    height: float
    parts: list


def generate_key_layout(geometry: list) -> tuple[list[KeyLayout], float, float]:
    """Convert API geometry into key rectangles expressed in millimetres."""
    keys = []
    group_x = 0.0
    keyboard_height = 0.0

    for group in geometry:
        rows = group.get("elements", [])
        group_width = 0.0
        group_height = max(0, len(rows) * (KEY_HEIGHT_MM + GAP_MM) - GAP_MM)

        for row_index, row in enumerate(rows):
            x = group_x
            y = row_index * (KEY_HEIGHT_MM + GAP_MM)

            for item in row:
                parts = item.get("parts") or []
                if parts:
                    width = max(float(part["width"]) for part in parts)
                    height = sum(float(part["height"]) for part in parts)
                else:
                    colspan = max(1, int(item.get("colspan", 0)))
                    rowspan = max(1, int(item.get("rowspan", 0)))
                    width = float(item.get("size", 0)) * colspan
                    width += GAP_MM * (colspan - 1)
                    height = KEY_HEIGHT_MM * rowspan + GAP_MM * (rowspan - 1)

                for _ in range(int(item.get("quantity", 1))):
                    if item.get("type", "key") == "key":
                        keys.append(KeyLayout(x, y, width, height, parts))

                    x += width + GAP_MM
                    group_width = max(group_width, x - group_x - GAP_MM)
                    group_height = max(group_height, y + height)

        group_x += group_width + float(group.get("gap", 0))
        keyboard_height = max(keyboard_height, group_height)

    if geometry:
        group_x -= float(geometry[-1].get("gap", 0))

    return keys, group_x, keyboard_height


class Keyboard(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.background = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_background, size=self._update_background)
        self.bind(size=self._layout_keys)

        self._geometry = self._load_first_geometry() or []
        self._keys = []
        self._keyboard_size = (0.0, 0.0)
        self._rebuild_geometry()

        self._refresh_event = Clock.schedule_interval(
            self._refresh_geometry,
            5,
        )

    def _load_first_geometry(self):
        try:
            with urlopen(f"{API_URL}/api/geometry", timeout=2) as response:
                geometries = json.load(response)
        except (OSError, URLError, json.JSONDecodeError):
            return None

        if not isinstance(geometries, list) or not geometries:
            return []

        first_geometry = geometries[0]
        if not isinstance(first_geometry, dict):
            return []

        geometry = first_geometry.get("geometry")
        return geometry if isinstance(geometry, list) else []

    def _rebuild_geometry(self):
        for key in self._keys:
            self.remove_widget(key)

        layouts, width, height = generate_key_layout(self._geometry)
        self._keyboard_size = (width, height)
        self._keys = []

        for layout in layouts:
            key = Key(parts=layout.parts)
            key.layout = layout
            self._keys.append(key)
            self.add_widget(key)

        self._layout_keys()

    def _refresh_geometry(self, *args):
        geometry = self._load_first_geometry()
        if geometry is None or geometry == self._geometry:
            return

        self._geometry = geometry
        self._rebuild_geometry()

    def _layout_keys(self, *args):
        keyboard_width, keyboard_height = self._keyboard_size
        if not keyboard_width or not keyboard_height:
            return

        available_width = max(0, self.width - 2 * mm(OUTER_MARGIN_MM))
        available_height = max(0, self.height - 2 * mm(OUTER_MARGIN_MM))
        scale = min(
            1,
            available_width / mm(keyboard_width),
            available_height / mm(keyboard_height),
        )
        origin_x = self.x + (self.width - mm(keyboard_width) * scale) / 2
        origin_y = self.y + (self.height - mm(keyboard_height) * scale) / 2

        for key in self._keys:
            layout = key.layout
            key.size = (mm(layout.width) * scale, mm(layout.height) * scale)
            key.pos = (
                origin_x + mm(layout.x) * scale,
                origin_y + mm(keyboard_height - layout.y - layout.height) * scale,
            )

    def on_parent(self, instance, parent):
        if parent is None and getattr(self, "_refresh_event", None):
            self._refresh_event.cancel()
            self._refresh_event = None

    def _update_background(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size
