import atexit
import os
from threading import RLock


MODIFIERS = {
    "LEFT_CTRL": 0x01,
    "LEFT_SHIFT": 0x02,
    "LEFT_ALT": 0x04,
    "LEFT_META": 0x08,
    "RIGHT_CTRL": 0x10,
    "RIGHT_SHIFT": 0x20,
    "RIGHT_ALT": 0x40,
    "RIGHT_META": 0x80,
}

ALIASES = {
    "CTRL": "LEFT_CTRL",
    "CONTROL": "LEFT_CTRL",
    "SHIFT": "LEFT_SHIFT",
    "ALT": "LEFT_ALT",
    "META": "LEFT_META",
    "SUPER": "LEFT_META",
    "WIN": "LEFT_META",
    "CMD": "LEFT_META",
    "DEL": "DELETE",
    "ESC": "ESCAPE",
    "RETURN": "ENTER",
    "PGUP": "PAGE_UP",
    "PGDN": "PAGE_DOWN",
}

KEY_CODES = {
    **{chr(ord("A") + index): 0x04 + index for index in range(26)},
    **{
        value: 0x1E + index
        for index, value in enumerate(("1", "2", "3", "4", "5", "6", "7", "8", "9", "0"))
    },
    "ENTER": 0x28,
    "ESCAPE": 0x29,
    "BACKSPACE": 0x2A,
    "TAB": 0x2B,
    "SPACE": 0x2C,
    "MINUS": 0x2D,
    "EQUAL": 0x2E,
    "LEFT_BRACKET": 0x2F,
    "RIGHT_BRACKET": 0x30,
    "BACKSLASH": 0x31,
    "SEMICOLON": 0x33,
    "APOSTROPHE": 0x34,
    "GRAVE": 0x35,
    "COMMA": 0x36,
    "PERIOD": 0x37,
    "SLASH": 0x38,
    "CAPS_LOCK": 0x39,
    **{f"F{index}": 0x39 + index for index in range(1, 13)},
    "PRINT_SCREEN": 0x46,
    "SCROLL_LOCK": 0x47,
    "PAUSE": 0x48,
    "INSERT": 0x49,
    "HOME": 0x4A,
    "PAGE_UP": 0x4B,
    "DELETE": 0x4C,
    "END": 0x4D,
    "PAGE_DOWN": 0x4E,
    "RIGHT": 0x4F,
    "LEFT": 0x50,
    "DOWN": 0x51,
    "UP": 0x52,
    "NUM_LOCK": 0x53,
}


def normalize_key(value):
    name = str(value).strip().upper().replace("-", "_").replace(" ", "_")
    return ALIASES.get(name, name)


class HIDKeyboard:
    REPORT_SIZE = 8
    MAX_KEYS = 6

    def __init__(self, device_path="/dev/hidg0", writer=None):
        self.device_path = device_path
        self._writer = writer
        self._fd = None
        self._states = {}
        self._last_report = None
        self._lock = RLock()

    @staticmethod
    def _keys_state(keys):
        modifiers = 0
        codes = set()
        for raw_key in keys:
            key = normalize_key(raw_key)
            if key in MODIFIERS:
                modifiers |= MODIFIERS[key]
            elif key in KEY_CODES:
                codes.add(KEY_CODES[key])
            else:
                raise ValueError(f"unknown HID key: {raw_key}")
        return modifiers, frozenset(codes)

    def _report(self, states=None):
        modifiers = 0
        codes = set()
        for state_modifiers, state_codes in (states or self._states).values():
            modifiers |= state_modifiers
            codes.update(state_codes)
        if len(codes) > self.MAX_KEYS:
            raise ValueError("a HID keyboard report supports at most 6 keys")
        ordered = sorted(codes)
        return bytes((modifiers, 0, *ordered, *([0] * (self.MAX_KEYS - len(ordered)))))

    def press(self, source, keys):
        state = self._keys_state(keys)
        with self._lock:
            states = {**self._states, source: state}
            report = self._report(states)
            self._states = states
            self._emit(report)

    def release(self, source):
        with self._lock:
            if source not in self._states:
                return
            del self._states[source]
            self._emit(self._report())

    def reset(self):
        with self._lock:
            self._states.clear()
            self._emit(bytes(self.REPORT_SIZE), force=True)

    def close(self):
        with self._lock:
            self.reset()
            self._close_device()

    def _emit(self, report, force=False):
        if not force and report == self._last_report:
            return
        self._last_report = report
        if self._writer is not None:
            self._writer(report)
            return
        try:
            if self._fd is None:
                self._fd = os.open(
                    self.device_path,
                    os.O_RDWR | os.O_NONBLOCK,
                )
            if os.write(self._fd, report) != self.REPORT_SIZE:
                self._close_device()
        except OSError:
            self._close_device()

    def _close_device(self):
        if self._fd is None:
            return
        try:
            os.close(self._fd)
        except OSError:
            pass
        self._fd = None


keyboard = HIDKeyboard()
atexit.register(keyboard.close)
