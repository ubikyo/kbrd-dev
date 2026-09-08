from kivy.graphics import Color, Line, Rectangle
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex

from kbrd_dev.render_spec import RenderSpec

# How long a dash and the gap after it are, per border style — the device
# side of `BORDER_DASHES` in the web `Border` control, which draws the
# same three styles as SVG dash patterns. `None` is the solid line: no
# pattern at all.
_BORDER_DASHES = {"dashed": (4, 3), "dotted": (1, 2)}


class _Mounted:
    __slots__ = ("key", "spec", "widget")

    def __init__(self, key, spec, widget):
        self.key = key
        self.spec = spec
        self.widget = widget


def _create_rect(spec):
    widget = Widget(size_hint=(None, None))
    with widget.canvas:
        color = Color(1, 1, 1, 1)
        rectangle = Rectangle()
        # The outline is its own colour + line, drawn after the fill so it
        # sits on top of it. Both exist from the start whether or not this
        # spec asks for a border: a canvas instruction added later would
        # have to be re-created on every change of mind, and an invisible
        # line costs nothing (see `_update_rect`, which switches it off
        # through its alpha).
        border_color = Color(1, 1, 1, 0)
        border = Line(width=1)
    widget.kbrd_color = color
    widget.kbrd_rectangle = rectangle
    widget.kbrd_border_color = border_color
    widget.kbrd_border = border
    _update_rect(widget, spec)
    return widget


def _update_rect(widget, spec):
    widget.opacity = 1 if spec.visible else 0
    widget.pos = (spec.x, spec.y)
    widget.size = (spec.width, spec.height)
    widget.kbrd_rectangle.pos = widget.pos
    widget.kbrd_rectangle.size = widget.size
    widget.kbrd_color.rgba = get_color_from_hex(spec.color)
    _update_border(widget, spec)


def _update_border(widget, spec):
    border = widget.kbrd_border
    if spec.border_width <= 0:
        # Nothing to draw: the line is left where it is and simply made
        # fully transparent, so switching a border back on is one alpha
        # away rather than a rebuilt canvas.
        widget.kbrd_border_color.rgba = (0, 0, 0, 0)
        return
    widget.kbrd_border_color.rgba = get_color_from_hex(spec.border_color)
    border.width = spec.border_width
    # Inset by half the line's own width: Kivy centres a stroke on its
    # path, so a wide border on the rectangle's exact bounds would hang
    # half of itself outside the shape it outlines.
    half = spec.border_width / 2
    border.rectangle = (
        spec.x + half,
        spec.y + half,
        max(0, spec.width - spec.border_width),
        max(0, spec.height - spec.border_width),
    )
    dash = _BORDER_DASHES.get(spec.border_style)
    # Kivy only dashes a 1px line, so a thicker one comes out solid — the
    # pattern is still set, so it starts dashing the moment the width
    # allows it.
    border.dash_length, border.dash_offset = dash if dash else (1, 0)


def _create_image(spec):
    widget = Image(allow_stretch=True, keep_ratio=True)
    _update_image(widget, spec)
    return widget


def _update_image(widget, spec):
    if not spec.visible:
        widget.size = (0, 0)
        widget.opacity = 0
        return
    widget.opacity = 1
    widget.size = (spec.width, spec.height)
    widget.pos = (spec.x, spec.y)
    if widget.source != spec.source:
        widget.source = spec.source
        widget.reload()


_CREATORS = {"rect": _create_rect, "image": _create_image}
_UPDATERS = {"rect": _update_rect, "image": _update_image}


class DisplayManager:
    """Owns every Kivy widget mounted from a declarative `RenderSpec`.

    Keyed by plugin-instance id (globally unique — see `key_plugin.id` in
    KBRD-API): `apply()` creates the widget the first time a spec is seen
    for an instance, updates it in place when the spec changes but keeps
    the same `kind`, replaces it if the `kind` itself changes, and does
    nothing at all — no Kivy call whatsoever — when the new spec is
    identical (by value) to the one last applied. This is what makes
    editing one static element on screen cheap regardless of how many
    other elements (rectangles, images, live video widgets managed outside
    this class) are mounted elsewhere.
    """

    def __init__(self):
        self._mounted = {}

    def apply(self, key, instance_id, spec: RenderSpec) -> RenderSpec:
        mounted = self._mounted.get(instance_id)
        if mounted is not None and mounted.key is key and mounted.spec == spec:
            return spec

        if (
            mounted is None
            or mounted.key is not key
            or mounted.spec.kind != spec.kind
        ):
            if mounted is not None:
                self._unmount(instance_id)
            widget = _CREATORS[spec.kind](spec)
            key.add_widget(widget)
            self._mounted[instance_id] = _Mounted(key, spec, widget)
            return spec

        _UPDATERS[spec.kind](mounted.widget, spec)
        mounted.spec = spec
        return spec

    def dispose(self, instance_id):
        self._unmount(instance_id)

    def _unmount(self, instance_id):
        mounted = self._mounted.pop(instance_id, None)
        if mounted is None:
            return
        parent = mounted.widget.parent
        if parent is not None:
            parent.remove_widget(mounted.widget)
