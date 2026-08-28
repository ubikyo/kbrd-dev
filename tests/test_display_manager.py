import unittest
from unittest import mock

from tests._kivy_stubs import install as _install_kivy_stubs

_install_kivy_stubs()

from kbrd_dev.display_manager import DisplayManager
from kbrd_dev.render_spec import RenderSpec


class FakeWidget:
    def __init__(self):
        self.parent = None


class FakeKey:
    def __init__(self):
        self.children = []

    def add_widget(self, widget):
        widget.parent = self
        self.children.append(widget)

    def remove_widget(self, widget):
        widget.parent = None
        if widget in self.children:
            self.children.remove(widget)


def make_spec(**overrides):
    base = dict(kind="rect", x=0, y=0, width=10, height=10)
    base.update(overrides)
    return RenderSpec(**base)


class DisplayManagerTest(unittest.TestCase):
    def setUp(self):
        self.created = []
        self.updated = []

        def create(spec):
            widget = FakeWidget()
            self.created.append((widget, spec))
            return widget

        def update(widget, spec):
            self.updated.append((widget, spec))

        creators_patch = mock.patch.dict(
            "kbrd_dev.display_manager._CREATORS",
            {"rect": create, "image": create},
        )
        updaters_patch = mock.patch.dict(
            "kbrd_dev.display_manager._UPDATERS",
            {"rect": update, "image": update},
        )
        creators_patch.start()
        updaters_patch.start()
        self.addCleanup(creators_patch.stop)
        self.addCleanup(updaters_patch.stop)

        self.display = DisplayManager()
        self.key = FakeKey()

    def test_first_apply_creates_and_mounts_the_widget(self):
        self.display.apply(self.key, 1, make_spec())

        self.assertEqual(len(self.created), 1)
        self.assertEqual(self.updated, [])
        self.assertIn(self.created[0][0], self.key.children)

    def test_identical_spec_does_nothing(self):
        spec = make_spec()
        self.display.apply(self.key, 1, spec)

        # A value-equal but distinct RenderSpec instance, exactly what a
        # plugin recomputing its spec from unchanged config would return.
        self.display.apply(self.key, 1, RenderSpec(**vars(spec)))

        self.assertEqual(len(self.created), 1)
        self.assertEqual(self.updated, [])

    def test_changed_spec_same_kind_updates_in_place(self):
        self.display.apply(self.key, 1, make_spec(color="#ffffff"))

        self.display.apply(self.key, 1, make_spec(color="#ff0000"))

        self.assertEqual(len(self.created), 1)
        self.assertEqual(len(self.updated), 1)

    def test_changed_kind_replaces_the_widget(self):
        self.display.apply(self.key, 1, make_spec(kind="rect"))
        first_widget = self.created[0][0]

        self.display.apply(self.key, 1, make_spec(kind="image"))

        self.assertEqual(len(self.created), 2)
        self.assertNotIn(first_widget, self.key.children)

    def test_dispose_removes_the_widget(self):
        self.display.apply(self.key, 1, make_spec())
        widget = self.created[0][0]

        self.display.dispose(1)

        self.assertNotIn(widget, self.key.children)
        self.assertIsNone(widget.parent)

    def test_dispose_of_unknown_instance_is_a_no_op(self):
        self.display.dispose(999)  # must not raise

    def test_two_instances_on_the_same_key_are_independent(self):
        self.display.apply(self.key, 1, make_spec(color="#ffffff"))
        self.display.apply(self.key, 2, make_spec(color="#000000"))

        self.display.dispose(1)

        self.assertEqual(len(self.key.children), 1)


if __name__ == "__main__":
    unittest.main()
