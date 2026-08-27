import sys
from types import ModuleType
import unittest


class FakeEvent:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class FakeClock:
    event = None

    @classmethod
    def schedule_once(cls, callback, delay):
        cls.event = FakeEvent()
        return cls.event


if "kivy.clock" not in sys.modules:
    kivy = ModuleType("kivy")
    kivy_clock = ModuleType("kivy.clock")
    kivy_clock.Clock = FakeClock
    sys.modules["kivy"] = kivy
    sys.modules["kivy.clock"] = kivy_clock

from kbrd_dev.plugins import PluginRegistry


class FakeKey:
    def __init__(self):
        self.callbacks = {}

    def bind(self, **callbacks):
        self.callbacks.update(callbacks)


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


if __name__ == "__main__":
    unittest.main()
