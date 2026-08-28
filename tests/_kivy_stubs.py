"""Minimal fakes for the slice of Kivy that kbrd_dev imports at module load
time, so tests can exercise plain-Python logic without a real Kivy install.

Shared by every test module that needs to import kbrd_dev.plugins/ui.* —
`install()` is idempotent and always installs the *same* FakeClock/FakeEvent
classes, so it is safe to call from multiple test files regardless of pytest
collection order (whichever test module imports kbrd_dev first is the one
that "sticks", since Python only ever executes a module's imports once).
"""

import sys
from types import ModuleType


class FakeEvent:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class FakeClock:
    event = None

    @classmethod
    def schedule_once(cls, callback, delay=0):
        cls.event = FakeEvent()
        return cls.event

    @classmethod
    def schedule_interval(cls, callback, interval):
        return FakeEvent()


def _module(name, **attributes):
    module = sys.modules.get(name) or ModuleType(name)
    for attribute, value in attributes.items():
        setattr(module, attribute, value)
    sys.modules[name] = module
    return module


def install():
    _module("kivy")
    _module("kivy.clock", Clock=FakeClock)
    _module(
        "kivy.graphics",
        Color=object,
        Line=object,
        Mesh=object,
        RoundedRectangle=object,
        Rectangle=object,
    )
    _module("kivy.metrics", mm=lambda value: value)
    _module("kivy.uix")
    _module("kivy.uix.floatlayout", FloatLayout=object)
    _module("kivy.uix.widget", Widget=object)
    _module("kivy.uix.image", Image=object)
    _module("kivy.utils", get_color_from_hex=lambda value: [0, 0, 0, 0])
