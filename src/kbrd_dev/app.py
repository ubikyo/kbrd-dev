import os

from kbrd_dev.startup import mark_startup

mark_startup("process-start")

from kbrd_dev.config import (
    SDL_VIDEO_DRIVER,
    SDL_KMSDRM_DEVICE_INDEX,
    TOUCH_DEVICE,
    PIXELS_PER_CM,
)

os.environ["SDL_VIDEODRIVER"] = SDL_VIDEO_DRIVER
os.environ["SDL_KMSDRM_DEVICE_INDEX"] = SDL_KMSDRM_DEVICE_INDEX
os.environ["KIVY_NO_CONFIG"] = "1"
os.environ["KIVY_DPI"] = str(PIXELS_PER_CM * 2.54)

from kivy.config import Config

Config.remove_option("input", "%(name)s")
Config.remove_option("input", "mouse")

Config.set(
    "graphics",
    "rotation",
    "90",
)

# Hide the SDL cursor as soon as the window is created. Setting Window.show_cursor
# in App.build() happens after window initialization and lets the arrow flash
# briefly while switching from the FBV splash screen to KBRD-DEV.
Config.set(
    "graphics",
    "show_cursor",
    "0",
)

Config.set(
    "input",
    "goodix",
    f"hidinput,{TOUCH_DEVICE},rotation=0,invert_x=0,invert_y=0",
)

from kivy.app import App as KivyApp
from kivy.core.window import Window

from kbrd_dev.device_registration import start_device_registration
from kbrd_dev.ui.keyboard import Keyboard

mark_startup(
    "window-created",
    provider=Window.__class__.__name__,
    size=f"{Window.width}x{Window.height}",
)


class App(KivyApp):
    def build(self):
        mark_startup("app-build-start")
        # Keep the runtime setting as a safeguard for alternate window providers.
        Window.show_cursor = False
        Window.bind(on_flip=self._mark_first_flip)
        start_device_registration()
        keyboard = Keyboard()
        mark_startup("app-build-complete")
        return keyboard

    def _mark_first_flip(self, *args):
        Window.unbind(on_flip=self._mark_first_flip)
        mark_startup("window-first-frame")


def main() -> None:
    App().run()
