from enum import Enum

from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import mm
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from kbrd_dev.config import DEFAULT_FONT


class KeyState(Enum):
    UP = "up"
    DOWN = "down"
    RELEASED = "released"


class Key(Widget):
    SIZE = mm(19)
    RADIUS = mm(2)
    BORDER_WIDTH = 1

    POSITIONS = (
        "TL", "TC", "TR",
        "ML", "MC", "MR",
        "BL", "BC", "BR",
    )

    FONT_SIZES = {
        1: mm(3.0),
        2: mm(3.5),
        3: mm(4.0),
        4: mm(5.0),
    }

    IMAGE_SIZES = {
        1: 0.25,
        2: 0.40,
        3: 0.55,
        4: 0.70,
    }

    def __init__(self, padding=mm(1.5), **kwargs):
        super().__init__(**kwargs)

        self.size_hint = (None, None)
        self.size = (self.SIZE, self.SIZE)

        self.padding = padding
        self.state = KeyState.UP

        self._elements = {}

        with self.canvas:
            self.background_color = Color(0, 0, 0, 1)

            self.background = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self.RADIUS],
            )

            self.border_color = Color(1, 1, 1, 0.5)

            self.border = Line(
                rounded_rectangle=(
                    self.x,
                    self.y,
                    self.width,
                    self.height,
                    self.RADIUS,
                ),
                width=self.BORDER_WIDTH,
            )

        self.bind(
            pos=self._update,
            size=self._update,
        )

        self._update()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_text(self, position, text, size=2):
        self._validate(position, size)
        self.remove(position)

        label = Label(
            text=text,
            font_name=DEFAULT_FONT,
            font_size=self.FONT_SIZES[size],
            color=(1, 1, 1, 1),
            halign=self._horizontal_alignment(position),
            valign=self._vertical_alignment(position),
        )

        self._elements[position] = {
            "widget": label,
            "type": "text",
            "size": size,
        }

        self.add_widget(label)
        self._update()

        return self

    def set_image(self, position, source, size=2):
        self._validate(position, size)
        self.remove(position)

        image = Image(
            source=source,
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(None, None),
        )

        self._elements[position] = {
            "widget": image,
            "type": "image",
            "size": size,
        }

        self.add_widget(image)
        self._update()

        return self

    def remove(self, position):
        element = self._elements.pop(position, None)

        if element:
            self.remove_widget(element["widget"])

        return self

    def clear(self):
        for position in list(self._elements):
            self.remove(position)

        return self

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _update(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size
        self.background.radius = [self.RADIUS]

        self.border.rounded_rectangle = (
            self.x,
            self.y,
            self.width,
            self.height,
            self.RADIUS,
        )

        for position, element in self._elements.items():
            self._position_element(position, element)

    def _position_element(self, position, element):
        widget = element["widget"]

        left = self.x + self.padding
        right = self.right - self.padding
        bottom = self.y + self.padding
        top = self.top - self.padding

        available_width = right - left
        available_height = top - bottom

        if element["type"] == "text":
            widget.pos = (left, bottom)
            widget.size = (
                available_width,
                available_height,
            )
            widget.text_size = widget.size
            return

        scale = self.IMAGE_SIZES[element["size"]]

        width = available_width * scale
        height = available_height * scale

        widget.size = (width, height)

        widget.pos = (
            self._aligned_x(position, left, right, width),
            self._aligned_y(position, bottom, top, height),
        )

    # ------------------------------------------------------------------
    # Alignment
    # ------------------------------------------------------------------

    @staticmethod
    def _horizontal_alignment(position):
        return {
            "L": "left",
            "C": "center",
            "R": "right",
        }[position[1]]

    @staticmethod
    def _vertical_alignment(position):
        return {
            "T": "top",
            "M": "middle",
            "B": "bottom",
        }[position[0]]

    @staticmethod
    def _aligned_x(position, left, right, width):
        column = position[1]

        if column == "L":
            return left

        if column == "R":
            return right - width

        return left + ((right - left - width) / 2)

    @staticmethod
    def _aligned_y(position, bottom, top, height):
        row = position[0]

        if row == "B":
            return bottom

        if row == "T":
            return top - height

        return bottom + ((top - bottom - height) / 2)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def _set_state(self, state):
        self.state = state

        if state == KeyState.DOWN:
            self.background_color.rgba = (0, 1, 0, 1)

            for element in self._elements.values():
                if element["type"] == "text":
                    element["widget"].color = (1, 1, 1, 1)

        else:
            self.background_color.rgba = (0, 0, 0, 1)

            for element in self._elements.values():
                if element["type"] == "text":
                    element["widget"].color = (1, 1, 1, 1)

    # ------------------------------------------------------------------
    # Touch
    # ------------------------------------------------------------------

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)

            self._set_state(KeyState.DOWN)
            self.on_key_down()

            return True

        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)

            self._set_state(KeyState.RELEASED)
            self.on_key_released()

            self._set_state(KeyState.UP)
            self.on_key_up()

            return True

        return super().on_touch_up(touch)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_key_down(self):
        pass

    def on_key_released(self):
        pass

    def on_key_up(self):
        pass

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self, position, size):
        if position not in self.POSITIONS:
            raise ValueError(
                f"Invalid position: {position}. "
                f"Expected one of {self.POSITIONS}"
            )

        if size not in (1, 2, 3, 4):
            raise ValueError("size must be between 1 and 4")