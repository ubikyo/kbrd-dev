import json
from threading import Thread
from urllib.error import URLError
from urllib.request import Request, urlopen

from kivy.clock import Clock
from kivy.core.window import Window

from kbrd_dev.config import API_URL
from kbrd_dev.edid import read_physical_size_mm
from kbrd_dev.startup import mark_startup_once

# Same heartbeat cadence as KBRD-Agent's own registration loop, so a
# registration going quiet expires well before KBRD-API's
# `Device.REGISTRATION_TTL_SECONDS`.
REGISTRATION_INTERVAL_SECONDS = 10
_REQUEST_TIMEOUT_SECONDS = 2


def start_device_registration():
    """Report this unit's screen resolution to KBRD-API so KBRD-WEB can
    preview layouts at the connected display's aspect ratio (see
    `kbrd_api.api.device.Device`). Registers immediately, then keeps
    re-registering on an interval — the network call runs off the Kivy
    thread so a slow/unreachable KBRD-API never stalls the UI.
    """

    def register(*args):
        Thread(target=_register_once, daemon=True).start()

    register()
    Clock.schedule_interval(register, REGISTRATION_INTERVAL_SECONDS)


def _register_once():
    payload = {"width": Window.width, "height": Window.height}
    size_mm = read_physical_size_mm()
    if size_mm is not None:
        payload["width_mm"], payload["height_mm"] = size_mm
    body = json.dumps(payload).encode()
    outbound = Request(
        f"{API_URL}/api/device/register",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(outbound, timeout=_REQUEST_TIMEOUT_SECONDS):
            pass
    except (OSError, URLError):
        mark_startup_once("device-registration-unavailable")
