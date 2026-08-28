"""Migrated plugin renderers (render-rectangle, render-image) return a
`RenderSpec` and are pure Python — no Kivy stubbing needed to test them,
unlike the still-legacy plugins in test_plugins.py.
"""

import importlib.util
import unittest
from pathlib import Path

PLUGINS_SRC = Path(__file__).resolve().parents[2] / "kbrd-plugins" / "src"


def _load_renderer(plugin_dir):
    path = PLUGINS_SRC / plugin_dir / "dev" / "renderer.py"
    spec = importlib.util.spec_from_file_location(
        f"test_{plugin_dir.replace('-', '_')}_renderer", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render


class FakeKey:
    def __init__(self, x=0, y=0, width=100, height=40):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y + self.height


class RenderRectangleTest(unittest.TestCase):
    render = staticmethod(_load_renderer("render-rectangle"))

    def test_default_config_centers_a_half_size_rectangle(self):
        key = FakeKey(x=10, y=20, width=100, height=40)

        spec = self.render(key, {})

        self.assertEqual(spec.kind, "rect")
        self.assertEqual(spec.color, "#ffffff")
        self.assertEqual((spec.width, spec.height), (50, 20))
        self.assertEqual(spec.x, 10 + (100 - 50) / 2)
        self.assertEqual(spec.y, 20 + (40 - 20) / 2)

    def test_left_top_alignment(self):
        key = FakeKey(x=10, y=20, width=100, height=40)

        spec = self.render(
            key, {"horizontalPosition": "left", "verticalPosition": "top"}
        )

        self.assertEqual(spec.x, 10)
        self.assertEqual(spec.y, key.top - spec.height)

    def test_size_is_clamped_between_5_and_100_percent(self):
        key = FakeKey(width=100, height=40)

        spec = self.render(key, {"width": 0, "height": 500})

        self.assertEqual((spec.width, spec.height), (5, 40))

    def test_same_config_produces_an_equal_spec(self):
        key = FakeKey()
        config = {"width": 30, "height": 60, "color": "#ff0000"}

        self.assertEqual(self.render(key, config), self.render(key, config))


class RenderImageTest(unittest.TestCase):
    render = staticmethod(_load_renderer("render-image"))

    def test_no_media_is_hidden(self):
        spec = self.render(FakeKey(), {})

        self.assertFalse(spec.visible)

    def test_full_size_fills_the_key_regardless_of_alignment(self):
        key = FakeKey(x=5, y=5, width=80, height=30)

        spec = self.render(
            key, {"media": "photo.png", "horizontalPosition": "right"}
        )

        self.assertTrue(spec.visible)
        self.assertEqual((spec.x, spec.y), (5, 5))
        self.assertEqual((spec.width, spec.height), (80, 30))
        self.assertTrue(spec.source.endswith("photo.png"))

    def test_partial_size_is_aligned_within_the_key(self):
        key = FakeKey(x=0, y=0, width=100, height=100)

        spec = self.render(
            key,
            {
                "media": "icon.png",
                "fullSize": False,
                "size": 50,
                "horizontalPosition": "left",
                "verticalPosition": "bottom",
            },
        )

        self.assertEqual((spec.width, spec.height), (50, 50))
        self.assertEqual((spec.x, spec.y), (0, 0))

    def test_path_traversal_in_media_name_is_rejected(self):
        spec = self.render(FakeKey(), {"media": "../secrets.png"})

        self.assertFalse(spec.visible)


if __name__ == "__main__":
    unittest.main()
