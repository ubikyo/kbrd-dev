import json
import time
from threading import Thread
from urllib.error import URLError
from urllib.request import urlopen

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import mm
from kivy.uix.floatlayout import FloatLayout

from kbrd_dev.config import API_URL
from kbrd_dev.plugins import PluginRegistry
from kbrd_dev.startup import mark_startup, mark_startup_once
from kbrd_dev.ui.key import Key

BACKGROUND_REF = "__background__"


def _group_plugins_by_key(plugins):
    grouped = {}
    for instance in plugins:
        grouped.setdefault(instance.get("key_ref"), []).append(instance)
    return grouped


def _group_properties_by_key(properties):
    return {
        item.get("key_ref"): item.get("config", {})
        for item in properties
        if isinstance(item, dict)
    }


class Keyboard(FloatLayout):
    def __init__(self, **kwargs):
        mark_startup("keyboard-init-start")
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
        mark_startup("plugin-load-start")
        self._plugin_registry = PluginRegistry()
        mark_startup("plugin-load-complete")
        self._keys_by_ref = {}
        self._request_pending = False
        self._stopped = False
        self._refresh_geometry()
        self._refresh_event = Clock.schedule_interval(
            self._refresh_geometry,
            5,
        )
        mark_startup("keyboard-init-complete")

    def _refresh_geometry(self, *args):
        if self._request_pending:
            return

        self._request_pending = True
        Thread(target=self._load_geometry, daemon=True).start()

    def _load_geometry(self):
        started = time.monotonic()
        mark_startup_once("api-request-start")
        try:
            with urlopen(
                f"{API_URL}/api/workspace/active",
                timeout=2,
            ) as response:
                result = json.load(response)
        except (OSError, URLError, json.JSONDecodeError) as error:
            result = None
            mark_startup_once(
                "api-unavailable",
                duration=f"{time.monotonic() - started:.3f}s",
                error=error.__class__.__name__,
            )
        else:
            mark_startup_once(
                "api-ready",
                duration=f"{time.monotonic() - started:.3f}s",
            )

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
        mark_startup_once(
            "geometry-ready",
            keys=len(layout.get("keys", [])),
            plugins=len(plugins),
        )
        if (
            layout == self._layout
            and unit == self._unit
            and plugins == self._plugins
            and properties == self._properties
        ):
            return

        if layout != self._layout or unit != self._unit:
            self._layout = layout
            self._unit = unit
            self._plugins = plugins
            self._properties = properties
            self._rebuild_keys()
            return

        self._reconcile_keys(plugins, properties)

    def _mount_key(self, ref, is_background, layout_entry, plugins_by_key, properties_by_key):
        """Create a fresh `Key` widget for `ref` (releasing/removing any
        existing one first) and render its plugin instances onto it.

        Recreating the widget rather than patching an existing one in place
        keeps its lifetime simple: whatever a plugin renderer binds to
        `key` (pos/size listeners, canvas instructions) cannot accumulate
        across repeated edits of the same key, since every edit gets a
        brand new `Key` object — exactly as a full `_rebuild_keys()` already
        did for every key before this method existed. "space" elements
        never render plugins, matching the original behaviour.
        """
        existing = self._keys_by_ref.pop(ref, None)
        if existing is not None:
            self._plugin_registry.release(existing)
            self.remove_widget(existing)

        if is_background:
            key = Key(element_type="background")
            key.layout = {
                "is_background": True,
                "x": 0,
                "y": 0,
                "width": self._layout.get("width", 0),
                "height": self._layout.get("height", 0),
                "parts": [],
            }
            key.name = "Background"
        else:
            key = Key(
                element_type=layout_entry.get("type", "key"),
                parts=layout_entry.get("parts"),
            )
            key.layout = layout_entry
            key.name = layout_entry.get("name", "")
        key.unit = self._unit
        key.ref = ref
        self._keys_by_ref[ref] = key
        self.add_widget(key)

        if not is_background:
            key.apply_style(properties_by_key.get(ref, {}))
        if is_background or key.element_type == "key":
            for instance in sorted(
                plugins_by_key.get(ref, []),
                key=lambda item: item.get("position", 0),
            ):
                self._plugin_registry.render(key, instance)
        return key

    def _reconcile_keys(self, plugins, properties):
        """Recreate only the keys whose plugins/properties actually
        changed, leaving every other key's widgets (videos included)
        untouched. Only valid when `self._layout`/`self._unit` are
        unchanged — geometry changes still go through `_rebuild_keys()`."""
        old_plugins_by_key = _group_plugins_by_key(self._plugins)
        old_properties_by_key = _group_properties_by_key(self._properties)
        new_plugins_by_key = _group_plugins_by_key(plugins)
        new_properties_by_key = _group_properties_by_key(properties)

        layout_by_ref = {
            layout.get("ref", ""): layout
            for layout in self._layout.get("keys", [])
        }
        changed = False
        for ref in (BACKGROUND_REF, *layout_by_ref):
            if (
                new_plugins_by_key.get(ref, []) == old_plugins_by_key.get(ref, [])
                and new_properties_by_key.get(ref)
                == old_properties_by_key.get(ref)
            ):
                continue

            if ref != BACKGROUND_REF and ref not in self._keys_by_ref:
                # Defensive: every ref in an unchanged layout should already
                # have a Key widget. If not, fall back to a full rebuild.
                self._plugins = plugins
                self._properties = properties
                self._rebuild_keys()
                return

            self._mount_key(
                ref,
                ref == BACKGROUND_REF,
                layout_by_ref.get(ref),
                new_plugins_by_key,
                new_properties_by_key,
            )
            changed = True

        self._plugins = plugins
        self._properties = properties
        if changed:
            # Geometry is unchanged, so this is a cheap pure reposition —
            # not a rebuild — but the key(s) just recreated above start out
            # at Kivy's default pos/size and need it.
            self._layout_keys()

    def _rebuild_keys(self):
        mark_startup_once("keyboard-rebuild-start")
        for key in self._keys_by_ref.values():
            self._plugin_registry.release(key)
            self.remove_widget(key)
        self._keys_by_ref = {}

        plugins_by_key = _group_plugins_by_key(self._plugins)
        properties_by_key = _group_properties_by_key(self._properties)

        self._mount_key(BACKGROUND_REF, True, None, plugins_by_key, properties_by_key)
        for layout in self._layout.get("keys", []):
            self._mount_key(
                layout.get("ref", ""),
                False,
                layout,
                plugins_by_key,
                properties_by_key,
            )

        self._layout_keys()
        mark_startup_once(
            "keyboard-rebuild-complete", widgets=len(self._keys_by_ref)
        )
        Clock.schedule_once(self._mark_keyboard_first_frame)

    def _mark_keyboard_first_frame(self, *args):
        # A zero-delay callback runs after the next frame has been rendered.
        mark_startup_once("keyboard-first-frame")

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

        for key in self._keys_by_ref.values():
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
        for key in self._keys_by_ref.values():
            self._plugin_registry.release(key)

    def _update_background(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size
