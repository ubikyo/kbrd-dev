# Logical display
LOGICAL_WIDTH = 1280
LOGICAL_HEIGHT = 800

# DRM / SDL
SDL_VIDEO_DRIVER = "kmsdrm"
SDL_KMSDRM_DEVICE_INDEX = "1"

# Touchscreen
TOUCH_DEVICE = "/dev/input/event4"

# Assets
ASSET_PATH = "/usr/share/kbrd"

PRIVATE_PATH = f"{ASSET_PATH}/private"
MEDIA_PATH = f"{ASSET_PATH}/media"
FONT_PATH = f"{ASSET_PATH}/fonts"

DEFAULT_IMAGE = f"{MEDIA_PATH}/image1.png"
DEFAULT_FONT = f"{FONT_PATH}/Inter_18pt-ExtraLight.ttf"