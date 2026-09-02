import json
import unittest
from unittest.mock import patch

from tests._kivy_stubs import install as _install_kivy_stubs

_install_kivy_stubs()

from kbrd_dev import device_registration  # noqa: E402
from kbrd_dev.config import API_URL  # noqa: E402


class ImmediateThread:
    """Runs its target synchronously, so tests never juggle real threads."""

    def __init__(self, target=None, daemon=None):
        self._target = target

    def start(self):
        self._target()


class DeviceRegistrationTest(unittest.TestCase):
    def setUp(self):
        device_registration.Window.width = 1280
        device_registration.Window.height = 400
        patcher = patch(
            "kbrd_dev.device_registration.read_physical_size_mm",
            return_value=None,
        )
        self.read_physical_size_mm = patcher.start()
        self.addCleanup(patcher.stop)

    @patch("kbrd_dev.device_registration.urlopen")
    def test_register_once_posts_the_window_resolution(self, urlopen):
        device_registration._register_once()

        outbound = urlopen.call_args[0][0]
        self.assertEqual(outbound.full_url, f"{API_URL}/api/device/register")
        self.assertEqual(outbound.get_method(), "POST")
        self.assertEqual(
            json.loads(outbound.data), {"width": 1280, "height": 400}
        )

    @patch("kbrd_dev.device_registration.urlopen")
    def test_register_once_includes_the_physical_size_when_known(self, urlopen):
        self.read_physical_size_mm.return_value = (154, 85)

        device_registration._register_once()

        outbound = urlopen.call_args[0][0]
        self.assertEqual(
            json.loads(outbound.data),
            {"width": 1280, "height": 400, "width_mm": 154, "height_mm": 85},
        )

    @patch("kbrd_dev.device_registration.mark_startup_once")
    @patch("kbrd_dev.device_registration.urlopen", side_effect=OSError("offline"))
    def test_register_once_survives_an_unreachable_api(self, urlopen, mark):
        device_registration._register_once()

        mark.assert_called_once_with("device-registration-unavailable")

    @patch("kbrd_dev.device_registration.Thread", ImmediateThread)
    @patch("kbrd_dev.device_registration.urlopen")
    def test_start_registers_immediately(self, urlopen):
        device_registration.start_device_registration()

        self.assertEqual(urlopen.call_count, 1)


if __name__ == "__main__":
    unittest.main()
