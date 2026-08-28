import unittest
from unittest import mock

from tests._kivy_stubs import FakeClock, install as _install_kivy_stubs

_install_kivy_stubs()

from kbrd_dev.display_manager import DisplayManager
from kbrd_dev.plugins import PluginRegistry
from kbrd_dev.render_spec import RenderSpec


class FakeKey:
    def __init__(self):
        self.callbacks = {}
        self.children = []

    def bind(self, **callbacks):
        self.callbacks.update(callbacks)

    def add_widget(self, widget):
        widget.parent = self
        self.children.append(widget)

    def remove_widget(self, widget):
        widget.parent = None
        if widget in self.children:
            self.children.remove(widget)


class FakeRenderer:
    def __init__(self, config):
        self.config = config
        self.parent = None
        self.disposed = False

    def kbrd_update(self, config):
        self.config = config

    def kbrd_dispose(self):
        self.disposed = True


class PluginRegistryTest(unittest.TestCase):
    def test_release_cancels_delayed_renderer_and_disposes_widget(self):
        registry = PluginRegistry.__new__(PluginRegistry)
        registry._display = DisplayManager()
        widgets = []

        def render(key, config):
            widget = FakeRenderer(config)
            widgets.append(widget)
            return widget

        registry._renderers = {"test.renderer": render}
        registry._controllers = {}
        key = FakeKey()
        registry.render(key, {
            "plugin_id": "test.renderer",
            "config": {
                "value": "up",
                "down": {
                    "enabled": True,
                    "delay": 100,
                    "config": {"value": "down"},
                },
            },
        })

        key.callbacks["on_press"]()
        key.callbacks["on_release"]()
        event = FakeClock.event
        PluginRegistry.release(key)

        self.assertTrue(event.cancelled)
        self.assertTrue(widgets[0].disposed)
        self.assertEqual(key.kbrd_renderer_disposers, [])


class DeclarativeAndLegacyCoexistTest(unittest.TestCase):
    def test_declarative_and_legacy_instances_on_the_same_key(self):
        registry = PluginRegistry.__new__(PluginRegistry)
        registry._display = DisplayManager()
        legacy_widgets = []

        def legacy_render(key, config):
            widget = FakeRenderer(config)
            legacy_widgets.append(widget)
            key.add_widget(widget)
            return widget

        def declarative_render(key, config):
            return RenderSpec(kind="rect", x=0, y=0, width=1, height=1)

        registry._renderers = {
            "legacy": legacy_render,
            "declarative": declarative_render,
        }
        registry._controllers = {}
        key = FakeKey()

        with mock.patch.dict(
            "kbrd_dev.display_manager._CREATORS",
            {"rect": lambda spec: FakeRenderer({})},
        ), mock.patch.dict(
            "kbrd_dev.display_manager._UPDATERS", {"rect": lambda widget, spec: None}
        ):
            registry.render(key, {"id": 1, "plugin_id": "legacy", "config": {}})
            registry.render(
                key, {"id": 2, "plugin_id": "declarative", "config": {}}
            )
            self.assertEqual(len(key.children), 2)

            PluginRegistry.release(key)

        # The legacy widget is only disposed (as it always was) — the whole
        # `key` is expected to be discarded by the caller, taking it along.
        self.assertTrue(legacy_widgets[0].disposed)
        # The declarative widget is actively unmounted by DisplayManager.
        self.assertEqual(key.children, [legacy_widgets[0]])


if __name__ == "__main__":
    unittest.main()
