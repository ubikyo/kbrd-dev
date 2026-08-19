import os

from kbrd_dev.config import (
    SDL_VIDEO_DRIVER,
    SDL_KMSDRM_DEVICE_INDEX,
    TOUCH_DEVICE,
)

os.environ["SDL_VIDEODRIVER"] = SDL_VIDEO_DRIVER
os.environ["SDL_KMSDRM_DEVICE_INDEX"] = SDL_KMSDRM_DEVICE_INDEX
os.environ["KIVY_NO_CONFIG"] = "1"

from kivy.config import Config

Config.remove_option("input", "%(name)s")
Config.remove_option("input", "mouse")

Config.set(
    "graphics",
    "rotation",
    "90",
)

Config.set(
    "input",
    "goodix",
    f"hidinput,{TOUCH_DEVICE},rotation=0,invert_x=0,invert_y=0",
)

from kivy.app import App as KivyApp
from kivy.core.window import Window

from kbrd_dev.ui.keyboard import Keyboard


class App(KivyApp):

    def build(self):
        Window.show_cursor = False
        return Keyboard()

def main():
    App().run()