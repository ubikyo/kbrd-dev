import unittest

from kbrd_dev.hid import HIDKeyboard


class HIDKeyboardTest(unittest.TestCase):
    def setUp(self):
        self.reports = []
        self.keyboard = HIDKeyboard(writer=self.reports.append)

    def test_ctrl_alt_delete(self):
        self.keyboard.press("combo", ["CTRL", "ALT", "DELETE"])
        self.assertEqual(
            self.reports[-1],
            bytes((0x05, 0, 0x4C, 0, 0, 0, 0, 0)),
        )
        self.keyboard.release("combo")
        self.assertEqual(self.reports[-1], bytes(8))

    def test_sources_are_combined_and_released_independently(self):
        self.keyboard.press("modifier", ["LEFT_CTRL"])
        self.keyboard.press("letter", ["C"])
        self.assertEqual(
            self.reports[-1],
            bytes((0x01, 0, 0x06, 0, 0, 0, 0, 0)),
        )
        self.keyboard.release("letter")
        self.assertEqual(
            self.reports[-1],
            bytes((0x01, 0, 0, 0, 0, 0, 0, 0)),
        )

    def test_six_key_limit_does_not_change_current_state(self):
        self.keyboard.press("first", ["A"])
        with self.assertRaises(ValueError):
            self.keyboard.press("overflow", list("BCDEFG"))
        self.keyboard.release("first")
        self.assertEqual(self.reports[-1], bytes(8))

    def test_unknown_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown HID key"):
            self.keyboard.press("invalid", ["NOT_A_KEY"])


if __name__ == "__main__":
    unittest.main()
