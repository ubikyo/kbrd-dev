import unittest
from unittest.mock import patch

from kbrd_dev import startup


class StartupMarkerTest(unittest.TestCase):
    def setUp(self):
        startup._marked.clear()

    @patch.object(startup.syslog, "openlog")
    @patch.object(startup.syslog, "syslog")
    @patch.object(startup.time, "monotonic", return_value=4.125)
    def test_marker_is_logged_once_with_kernel_uptime(
        self,
        monotonic,
        syslog_message,
        openlog,
    ):
        startup.mark_startup_once("window-first-frame", provider="kmsdrm")
        startup.mark_startup_once("window-first-frame", provider="kmsdrm")

        openlog.assert_called_once()
        syslog_message.assert_called_once_with(
            startup.syslog.LOG_INFO,
            "KBRD_STARTUP marker=window-first-frame "
            "uptime=4.125s provider=kmsdrm",
        )
        monotonic.assert_called_once()


if __name__ == "__main__":
    unittest.main()
