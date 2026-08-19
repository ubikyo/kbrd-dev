from kivy.graphics import Color, Rectangle
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout

from kbrd_dev.ui.key import Key


class Keyboard(AnchorLayout):

    SPACING = 5

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.anchor_x = "center"
        self.anchor_y = "center"

        # Fond de l'écran
        with self.canvas.before:
            Color(0, 0, 0, 1)

            self.background = Rectangle(
                pos=self.pos,
                size=self.size,
            )

        self.bind(
            pos=self._update_background,
            size=self._update_background,
        )

        # Conteneur des touches
        self.keys = GridLayout(
            cols=3,
            spacing=self.SPACING,
            padding=0,
            size_hint=(None, None),
        )

        self.keys.bind(
            minimum_width=self.keys.setter("width"),
            minimum_height=self.keys.setter("height"),
        )

        self.add_widget(self.keys)

        self._create_keys()

    def _create_keys(self):

        # --------------------------------------------------------------
        # Key 1
        # --------------------------------------------------------------

        key = self.add_key()

        key.set_text("TL", "ESC", size=1)
        key.set_text("MC", "1", size=4)

        # --------------------------------------------------------------
        # Key 2
        # --------------------------------------------------------------

        key = self.add_key()

        key.set_text("TL", "F1", size=1)
        key.set_text("MC", "A", size=4)
        key.set_text("BR", "Shift", size=1)

        # --------------------------------------------------------------
        # Key 3
        # --------------------------------------------------------------

        key = self.add_key()

        key.set_text("TC", "Volume", size=1)
        key.set_text("ML", "-", size=2)
        key.set_text("MC", "VOL", size=3)
        key.set_text("MR", "+", size=2)
        key.set_text("BC", "Mute", size=1)

        # --------------------------------------------------------------
        # Key 4
        # --------------------------------------------------------------

        key = self.add_key()

        key.set_text("TL", "Home", size=1)
        key.set_text("TR", "PgUp", size=1)
        key.set_text("MC", "↑", size=4)
        key.set_text("BL", "End", size=1)
        key.set_text("BR", "PgDn", size=1)

        # --------------------------------------------------------------
        # Key 5 - démonstration des 9 positions
        # --------------------------------------------------------------

        key = self.add_key()

        key.set_text("TL", "TL", size=1)
        key.set_text("TC", "TC", size=1)
        key.set_text("TR", "TR", size=1)

        key.set_text("ML", "ML", size=1)
        key.set_text("MC", "MC", size=2)
        key.set_text("MR", "MR", size=1)

        key.set_text("BL", "BL", size=1)
        key.set_text("BC", "BC", size=1)
        key.set_text("BR", "BR", size=1)

        # --------------------------------------------------------------
        # Key 6
        # --------------------------------------------------------------

        key = self.add_key()

        key.set_text("TC", "Media", size=1)
        key.set_text("MC", "▶", size=4)
        key.set_text("BC", "Play", size=1)

    def add_key(self):
        key = Key()
        self.keys.add_widget(key)

        return key

    def _update_background(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size