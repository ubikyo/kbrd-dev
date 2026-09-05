import unittest
from unittest import mock

from tests._kivy_stubs import install as _install_kivy_stubs

# kbrd_dev.ui.keyboard (and, transitively, kbrd_dev.ui.key) only need Kivy
# names to *exist* at import time: every test below drives Keyboard via
# `Keyboard.__new__()` and replaces `Key` with a fake, so real widgets,
# canvas instructions and layout code never execute.
_install_kivy_stubs()

from kbrd_dev.ui.keyboard import BACKGROUND_REF, Keyboard  # noqa: E402


class FakeKey:
    def __init__(self, element_type="key", parts=None):
        self.element_type = element_type
        self.parts = parts
        self.ref = None
        self.name = None
        self.unit = None
        self.layout = None
        self.style_calls = []

    def apply_style(self, config):
        self.style_calls.append(config)


class FakeRegistry:
    def __init__(self):
        self.released = []
        self.rendered = []

    def release(self, key):
        self.released.append(key)

    def render(self, key, instance):
        self.rendered.append((key, instance["id"]))


def make_keyboard(layout, plugins, properties):
    keyboard = Keyboard.__new__(Keyboard)
    keyboard._layout = layout
    keyboard._unit = "mm"
    keyboard._plugins = plugins
    keyboard._properties = properties
    keyboard._plugin_registry = FakeRegistry()
    keyboard._keys_by_ref = {}
    keyboard._added_widgets = []
    keyboard._removed_widgets = []
    keyboard._layout_calls = 0
    keyboard.add_widget = keyboard._added_widgets.append
    keyboard.remove_widget = keyboard._removed_widgets.append
    keyboard._layout_keys = lambda *a: setattr(
        keyboard, "_layout_calls", keyboard._layout_calls + 1
    )
    return keyboard


def _key_ids(mapping):
    return {ref: id(key) for ref, key in mapping.items()}


class ReconcileKeysTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("kbrd_dev.ui.keyboard.Key", FakeKey)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.layout = {
            "width": 100,
            "height": 50,
            "keys": [{"ref": "A", "type": "key"}, {"ref": "B", "type": "key"}],
        }
        self.plugins = [
            {"id": 1, "key_ref": "A", "position": 0},
            {"id": 2, "key_ref": "B", "position": 0},
        ]
        self.properties = [{"key_ref": "A", "config": {"x": 1}}]
        self.keyboard = make_keyboard(self.layout, self.plugins, self.properties)
        self.keyboard._rebuild_keys()
        # Reset call-tracking accumulated by the initial full build so each
        # test only sees what `_reconcile_keys` itself does.
        self.keyboard._plugin_registry = FakeRegistry()
        self.keyboard._added_widgets = []
        self.keyboard._removed_widgets = []
        self.keyboard._layout_calls = 0

    def test_unchanged_keys_are_left_untouched(self):
        before = _key_ids(self.keyboard._keys_by_ref)

        self.keyboard._reconcile_keys(list(self.plugins), list(self.properties))

        self.assertEqual(_key_ids(self.keyboard._keys_by_ref), before)
        self.assertEqual(self.keyboard._plugin_registry.released, [])
        self.assertEqual(self.keyboard._plugin_registry.rendered, [])
        self.assertEqual(self.keyboard._removed_widgets, [])
        self.assertEqual(self.keyboard._layout_calls, 0)

    def test_only_the_key_with_changed_plugins_is_recreated(self):
        before = _key_ids(self.keyboard._keys_by_ref)
        new_plugins = [
            {"id": 1, "key_ref": "A", "position": 0},
            {"id": 3, "key_ref": "B", "position": 0},  # id changed for B
        ]

        self.keyboard._reconcile_keys(new_plugins, list(self.properties))

        after = _key_ids(self.keyboard._keys_by_ref)
        self.assertEqual(after["A"], before["A"])  # untouched
        self.assertNotEqual(after["B"], before["B"])  # recreated
        self.assertEqual(
            self.keyboard._plugin_registry.rendered,
            [(self.keyboard._keys_by_ref["B"], 3)],
        )
        self.assertEqual(self.keyboard._plugins, new_plugins)
        self.assertEqual(self.keyboard._layout_calls, 1)

    def test_changed_property_recreates_that_key_and_applies_style(self):
        before = _key_ids(self.keyboard._keys_by_ref)
        new_properties = [{"key_ref": "A", "config": {"x": 2}}]

        self.keyboard._reconcile_keys(list(self.plugins), new_properties)

        after = _key_ids(self.keyboard._keys_by_ref)
        self.assertNotEqual(after["A"], before["A"])
        self.assertEqual(after["B"], before["B"])
        self.assertEqual(
            self.keyboard._keys_by_ref["A"].style_calls, [{"x": 2}]
        )

    def test_space_elements_never_render_plugins(self):
        layout = {
            "width": 10,
            "height": 10,
            "keys": [{"ref": "S", "type": "space"}],
        }
        keyboard = make_keyboard(layout, [], [])
        keyboard._rebuild_keys()
        keyboard._plugin_registry = FakeRegistry()

        keyboard._reconcile_keys([{"id": 9, "key_ref": "S", "position": 0}], [])

        self.assertEqual(keyboard._plugin_registry.rendered, [])
        # A space still gets its style re-applied even without plugins.
        self.assertEqual(keyboard._keys_by_ref["S"].style_calls, [{}])

    def test_missing_key_widget_falls_back_to_full_rebuild(self):
        rebuilt = []
        self.keyboard._rebuild_keys = lambda: rebuilt.append(True)
        del self.keyboard._keys_by_ref["B"]
        new_plugins = [
            {"id": 1, "key_ref": "A", "position": 0},
            {"id": 4, "key_ref": "B", "position": 0},
        ]

        self.keyboard._reconcile_keys(new_plugins, list(self.properties))

        self.assertEqual(rebuilt, [True])
        self.assertEqual(self.keyboard._plugins, new_plugins)


class RebuildKeysTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("kbrd_dev.ui.keyboard.Key", FakeKey)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_background_and_keys_are_mounted_in_order(self):
        layout = {
            "width": 10,
            "height": 10,
            "keys": [{"ref": "A", "type": "key"}, {"ref": "S", "type": "space"}],
        }
        plugins = [{"id": 1, "key_ref": "A", "position": 0}]
        keyboard = make_keyboard(layout, plugins, [])

        keyboard._rebuild_keys()

        self.assertEqual(
            set(keyboard._keys_by_ref), {BACKGROUND_REF, "A", "S"}
        )
        self.assertEqual(len(keyboard._added_widgets), 3)
        self.assertEqual(
            keyboard._plugin_registry.rendered,
            [(keyboard._keys_by_ref["A"], 1)],
        )
        self.assertEqual(keyboard._layout_calls, 1)


class LayoutLoadedRoutingTest(unittest.TestCase):
    def make(self):
        keyboard = Keyboard.__new__(Keyboard)
        keyboard._stopped = False
        keyboard._layout = {"width": 1, "height": 1, "keys": []}
        keyboard._unit = "mm"
        keyboard._plugins = []
        keyboard._properties = []
        keyboard._rebuild_calls = []
        keyboard._reconcile_calls = []
        keyboard._rebuild_keys = lambda: keyboard._rebuild_calls.append(True)
        keyboard._reconcile_keys = lambda plugins, properties: (
            keyboard._reconcile_calls.append((plugins, properties))
        )
        return keyboard

    def test_layout_change_triggers_full_rebuild(self):
        keyboard = self.make()
        new_layout = {"width": 2, "height": 1, "keys": []}

        keyboard._layout_loaded({
            "layout": {"layout": new_layout, "unit": "mm"},
            "layer": {"plugins": [], "key_properties": []},
        })

        self.assertEqual(keyboard._rebuild_calls, [True])
        self.assertEqual(keyboard._reconcile_calls, [])
        self.assertEqual(keyboard._layout, new_layout)

    def test_plugin_only_change_triggers_reconcile_not_rebuild(self):
        keyboard = self.make()
        new_plugins = [{"id": 1, "key_ref": "A"}]

        keyboard._layout_loaded({
            "layout": {"layout": keyboard._layout, "unit": "mm"},
            "layer": {"plugins": new_plugins, "key_properties": []},
        })

        self.assertEqual(keyboard._rebuild_calls, [])
        self.assertEqual(keyboard._reconcile_calls, [(new_plugins, [])])

    def test_no_change_does_nothing(self):
        keyboard = self.make()

        keyboard._layout_loaded({
            "layout": {"layout": keyboard._layout, "unit": "mm"},
            "layer": {"plugins": [], "key_properties": []},
        })

        self.assertEqual(keyboard._rebuild_calls, [])
        self.assertEqual(keyboard._reconcile_calls, [])


if __name__ == "__main__":
    unittest.main()
