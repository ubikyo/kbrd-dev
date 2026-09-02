import tempfile
import unittest
from pathlib import Path

from kbrd_dev.edid import read_physical_size_mm


def _make_edid(width_cm: int, height_cm: int) -> bytes:
    edid = bytearray(128)
    edid[21] = width_cm
    edid[22] = height_cm
    return bytes(edid)


class ReadPhysicalSizeMmTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.drm_root = Path(self._tmp.name)

    def _add_connector(self, name, status, edid: bytes | None = None):
        connector = self.drm_root / name
        connector.mkdir()
        (connector / "status").write_text(f"{status}\n")
        if edid is not None:
            (connector / "edid").write_bytes(edid)

    def test_returns_none_when_nothing_is_connected(self):
        self._add_connector("card1-HDMI-A-1", "disconnected")

        self.assertIsNone(read_physical_size_mm(self.drm_root))

    def test_reads_the_size_of_the_connected_connector(self):
        self._add_connector("card1-HDMI-A-1", "disconnected")
        self._add_connector(
            "card1-DSI-1", "connected", _make_edid(width_cm=15, height_cm=7)
        )

        self.assertEqual(read_physical_size_mm(self.drm_root), (150, 70))

    def test_zero_size_in_the_edid_is_treated_as_unknown(self):
        self._add_connector(
            "card1-HDMI-A-1", "connected", _make_edid(width_cm=0, height_cm=0)
        )

        self.assertIsNone(read_physical_size_mm(self.drm_root))

    def test_missing_edid_file_is_treated_as_unknown(self):
        self._add_connector("card1-HDMI-A-1", "connected")

        self.assertIsNone(read_physical_size_mm(self.drm_root))

    def test_truncated_edid_is_treated_as_unknown(self):
        connector = self.drm_root / "card1-HDMI-A-1"
        connector.mkdir()
        (connector / "status").write_text("connected\n")
        (connector / "edid").write_bytes(bytes(10))

        self.assertIsNone(read_physical_size_mm(self.drm_root))


if __name__ == "__main__":
    unittest.main()
