from enum import Enum

from kivy.graphics import Color, Line, Mesh, RoundedRectangle
from kivy.metrics import mm
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex

from kbrd_dev.ui.shape import rounded_polygon, triangulate


class KeyState(Enum):
    UP = "up"
    DOWN = "down"


class Key(Widget):
    # Match the 2 px radius used by the SVG renderer in KBRD-WEB.
    RADIUS = 2
    BORDER_WIDTH = 1
    DEFAULT_STYLE = {
        "keyMode": "momentary",
        "borderEnabled": True,
        "downEnabled": False,
        "upBorderEnabled": True,
        "downBorderEnabled": True,
        "upBorderColor": "#808080",
        "downBorderColor": "#ffffff",
        "upBorderWidth": 1,
        "downBorderWidth": 1,
        "upBackgroundColor": "#00000000",
        "downBackgroundColor": "#00000000",
    }

    def __init__(self, element_type="key", parts=None, **kwargs):
        super().__init__(**kwargs)

        if element_type not in ("key", "space", "background"):
            raise ValueError("invalid element_type")

        self.element_type = element_type
        self.parts = parts or []
        self.size_hint = (None, None)
        self.state = KeyState.UP
        self.key_style = dict(self.DEFAULT_STYLE)
        self.register_event_type("on_press")
        self.register_event_type("on_release")

        # The key fill is always behind plugin widgets.
        with self.canvas.before:
            self.background_color = Color(0, 0, 0, 0)
            self.background = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self.RADIUS],
            )
            self.composite_background = Color(0, 0, 0, 0)
            self.composite_shape = Mesh(
                vertices=[],
                indices=[],
                mode="triangles",
            )

        # Plugin widgets are children of Key. canvas.after guarantees that the
        # key outline remains visible above every plugin, including images.
        with self.canvas.after:
            self.composite_border_color = Color(1, 1, 1, 0.5)
            self.composite_border = Line(
                close=True,
                width=self.BORDER_WIDTH,
                dash_length=4 if self.element_type == "space" else 1,
                dash_offset=4 if self.element_type == "space" else 0,
            )
            self.border_color = Color(1, 1, 1, 0.5)
            self.border = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, self.RADIUS),
                width=self.BORDER_WIDTH,
                dash_length=4 if self.element_type == "space" else 1,
                dash_offset=4 if self.element_type == "space" else 0,
            )

        self.bind(pos=self._update, size=self._update)
        self._update()

    def _update(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size
        self._update_composite()
        self.border.rounded_rectangle = (
            self.x + self.border.width / 2,
            self.y + self.border.width / 2,
            max(0, self.width - self.border.width),
            max(0, self.height - self.border.width),
            self.RADIUS,
        )
        self._apply_visual_state()

    def _update_composite(self):
        if not self.parts:
            self.composite_background.a = 0
            self.composite_border_color.a = 0
            return

        top, bottom = self.parts[0], self.parts[-1]
        top_width = mm(top["width"])
        bottom_width = mm(bottom["width"])
        top_width *= self.width / mm(self._parts_width())
        bottom_width *= self.width / mm(self._parts_width())
        top_height = mm(top["height"])
        bottom_height = mm(bottom["height"])
        top_height *= self.height / mm(self._parts_height())
        bottom_height *= self.height / mm(self._parts_height())
        top_x = self._part_x(top, top_width)
        bottom_x = self._part_x(bottom, bottom_width)
        top_y = self.y + self.height - top_height
        outline = rounded_polygon([
            (top_x, self.top),
            (top_x + top_width, self.top),
            (top_x + top_width, self.y),
            (bottom_x, self.y),
            (bottom_x, self.y + bottom_height),
            (top_x, self.y + bottom_height),
        ], self.RADIUS)
        self.composite_shape.vertices = [
            component
            for point in outline
            for component in (*point, 0, 0)
        ]
        self.composite_shape.indices = triangulate(outline)
        self.composite_border.points = [value for point in outline for value in point]
        self._apply_visual_state()

    @staticmethod
    def _color(value, fallback):
        try:
            return get_color_from_hex(value)
        except (AttributeError, TypeError, ValueError):
            return get_color_from_hex(fallback)

    def apply_style(self, config):
        if isinstance(config, dict):
            self.key_style = {**self.DEFAULT_STYLE, **config}
            if "borderEnabled" in config:
                if "upBorderEnabled" not in config:
                    self.key_style["upBorderEnabled"] = config["borderEnabled"]
                if "downBorderEnabled" not in config:
                    self.key_style["downBorderEnabled"] = config["borderEnabled"]
            if "borderWidth" in config:
                if "upBorderWidth" not in config:
                    self.key_style["upBorderWidth"] = config["borderWidth"]
                if "downBorderWidth" not in config:
                    self.key_style["downBorderWidth"] = config["borderWidth"]
        else:
            self.key_style = dict(self.DEFAULT_STYLE)
        try:
            prefix = self._visual_prefix()
            legacy_width = self.key_style.get("borderWidth", 1)
            width = max(
                1,
                min(
                    4,
                    float(
                        self.key_style.get(f"{prefix}BorderWidth", legacy_width)
                    ),
                ),
            )
        except (TypeError, ValueError):
            width = self.BORDER_WIDTH
        if self.element_type == "space":
            width = self.BORDER_WIDTH
        self.border.width = width
        self.composite_border.width = width
        self._update()

    def _apply_visual_state(self):
        visible = self.element_type == "key"
        prefix = self._visual_prefix()
        background = self._color(
            self.key_style.get(f"{prefix}BackgroundColor"),
            self.DEFAULT_STYLE[f"{prefix}BackgroundColor"],
        )
        border = self._color(
            self.key_style.get(f"{prefix}BorderColor"),
            self.DEFAULT_STYLE[f"{prefix}BorderColor"],
        )
        border_enabled = self.key_style.get(
            f"{prefix}BorderEnabled",
            self.key_style.get("borderEnabled", True),
        )
        if not border_enabled:
            border[3] = 0
        if not visible:
            background[3] = 0
            border[3] = 0
        self.background_color.rgba = (
            background if not self.parts else (*background[:3], 0)
        )
        self.composite_background.rgba = (
            background if self.parts else (*background[:3], 0)
        )
        self.border_color.rgba = border if not self.parts else (*border[:3], 0)
        self.composite_border_color.rgba = (
            border if self.parts else (*border[:3], 0)
        )

    def _visual_prefix(self):
        return (
            "down"
            if self.state == KeyState.DOWN
            and self.key_style.get("downEnabled", False)
            else "up"
        )

    def _is_toggle(self):
        return self.key_style.get("keyMode") == "toggle"

    def _part_x(self, part, width):
        align = part.get("align", "right")
        if align == "left":
            return self.x
        if align == "center":
            return self.x + (self.width - width) / 2
        return self.x + self.width - width

    def _parts_width(self):
        return max(part["width"] for part in self.parts)

    def _parts_height(self):
        return sum(part["height"] for part in self.parts)

    def _collide_key(self, x, y):
        if not self.parts:
            return self.collide_point(x, y)

        part_y = self.top
        width_scale = self.width / mm(self._parts_width())
        height_scale = self.height / mm(self._parts_height())
        for part in self.parts:
            width = mm(part["width"]) * width_scale
            height = mm(part["height"]) * height_scale
            part_y -= height
            part_x = self._part_x(part, width)
            if (
                part_x <= x <= part_x + width
                and part_y <= y <= part_y + height
            ):
                return True

        return False

    def _set_state(self, state):
        self.state = state
        self.apply_style(self.key_style)
        self._apply_visual_state()

    def on_touch_down(self, touch):
        if self.element_type == "key" and self._collide_key(*touch.pos):
            touch.grab(self)
            if self._is_toggle() and self.state == KeyState.DOWN:
                self._set_state(KeyState.UP)
                self.dispatch("on_release")
            else:
                self._set_state(KeyState.DOWN)
                self.dispatch("on_press")
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if not self._is_toggle():
                self._set_state(KeyState.UP)
                self.dispatch("on_release")
            return True
        return super().on_touch_up(touch)

    def on_press(self):
        pass

    def on_release(self):
        pass
