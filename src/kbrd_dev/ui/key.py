from enum import Enum

from kivy.graphics import Color, Line, Mesh, RoundedRectangle
from kivy.metrics import mm
from kivy.uix.widget import Widget


class KeyState(Enum):
    UP = "up"
    DOWN = "down"


class Key(Widget):
    RADIUS = mm(2)
    BORDER_WIDTH = 1

    def __init__(self, element_type="key", parts=None, **kwargs):
        super().__init__(**kwargs)

        if element_type not in ("key", "space"):
            raise ValueError("element_type must be 'key' or 'space'")

        self.element_type = element_type
        self.parts = parts or []
        self.size_hint = (None, None)
        self.state = KeyState.UP

        with self.canvas:
            self.background_color = Color(0, 0, 0, 1)
            self.background = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self.RADIUS],
            )
            self.composite_background = Color(0, 0, 0, 1)
            self.composite_shape = Mesh(
                vertices=[],
                indices=[0, 1, 2, 2, 3, 0, 4, 5, 6, 6, 7, 4],
                mode="triangles",
            )
            self.composite_border_color = Color(1, 1, 1, 0.5)
            self.composite_border = Line(
                close=True,
                width=self.BORDER_WIDTH,
            )
            self.border_color = Color(1, 1, 1, 0.5)
            self.border = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, self.RADIUS),
                width=self.BORDER_WIDTH,
            )

        self.bind(pos=self._update, size=self._update)
        self._update()

    def _update(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size
        self._update_composite()
        self.border.rounded_rectangle = (
            self.x,
            self.y,
            self.width,
            self.height,
            self.RADIUS,
        )
        visible = self.element_type == "key" and not self.parts
        self.background_color.a = 1 if visible else 0
        self.border_color.a = 0.5 if visible else 0

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
        self.composite_shape.vertices = self._rectangle_vertices(
            top_x,
            top_y,
            top_width,
            top_height,
        ) + self._rectangle_vertices(
            bottom_x,
            self.y,
            bottom_width,
            bottom_height,
        )
        self.composite_border.points = [
            top_x,
            self.top,
            top_x + top_width,
            self.top,
            top_x + top_width,
            self.y,
            bottom_x,
            self.y,
            bottom_x,
            self.y + bottom_height,
            top_x,
            self.y + bottom_height,
        ]
        self.composite_background.a = 1
        self.composite_border_color.a = 0.5

    @staticmethod
    def _rectangle_vertices(x, y, width, height):
        return [
            x, y, 0, 0,
            x + width, y, 0, 0,
            x + width, y + height, 0, 0,
            x, y + height, 0, 0,
        ]

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
        color = (
            (0, 1, 0, 1)
            if state == KeyState.DOWN
            else (0, 0, 0, 1)
        )
        if self.parts:
            self.background_color.rgba = (*color[:3], 0)
            self.composite_background.rgba = color
        else:
            self.background_color.rgba = color

    def on_touch_down(self, touch):
        if self.element_type == "key" and self._collide_key(*touch.pos):
            touch.grab(self)
            self._set_state(KeyState.DOWN)
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._set_state(KeyState.UP)
            return True
        return super().on_touch_up(touch)
