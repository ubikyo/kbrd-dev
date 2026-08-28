import syslog
import time
from threading import Lock


_marked = set()
_lock = Lock()


def mark_startup(marker, **fields):
    """Write a boot marker using the same monotonic clock as kernel uptime."""
    details = " ".join(f"{name}={value}" for name, value in fields.items())
    message = f"KBRD_STARTUP marker={marker} uptime={time.monotonic():.3f}s"
    if details:
        message = f"{message} {details}"
    try:
        syslog.openlog("kbrd-dev", syslog.LOG_PID, syslog.LOG_DAEMON)
        syslog.syslog(syslog.LOG_INFO, message)
    except (OSError, RuntimeError):
        # Startup instrumentation must never prevent the keyboard from running.
        pass


def mark_startup_once(marker, **fields):
    """Write a marker only for its first occurrence in this process."""
    with _lock:
        if marker in _marked:
            return
        _marked.add(marker)
    mark_startup(marker, **fields)
