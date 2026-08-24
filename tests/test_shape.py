import unittest

from kbrd_dev.ui.shape import rounded_polygon, triangulate


class ShapeTest(unittest.TestCase):
    def test_rounds_and_triangulates_enter_key(self):
        outline = rounded_polygon([
            (0, 36),
            (16, 36),
            (16, 0),
            (5, 0),
            (5, 19),
            (0, 19),
        ], radius=2)
        triangles = triangulate(outline)

        self.assertEqual(len(outline), 30)
        self.assertEqual(len(triangles), (len(outline) - 2) * 3)
        self.assertTrue(all(0 <= index < len(outline) for index in triangles))


if __name__ == "__main__":
    unittest.main()
