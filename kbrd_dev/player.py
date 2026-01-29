from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label


class Player(App):
    def __init__(self, api, **kwargs):
        super().__init__(**kwargs)
        self.api = api
        self.label = None
        self.last_value = None

    def build(self):
        Window.clearcolor = (0, 0, 0, 1)
        Window.fullscreen = True

        root = FloatLayout()
        self.label = Label(
            text="",
            color=(1, 1, 1, 1),
            font_size=60,
            halign="center",
            valign="middle",
            size_hint=(1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.label.bind(size=self._sync_text_size)
        root.add_widget(self.label)

        Clock.schedule_interval(self._tick, 1.0)
        self._tick(0)
        return root

    def _sync_text_size(self, *_):
        self.label.text_size = self.label.size

    def _tick(self, _dt):
        try:
            person = self.api.get_last_person()
            first_name = person.first_name if person else ""
        except Exception:
            first_name = ""

        if first_name != self.last_value:
            self.last_value = first_name
            self.label.text = first_name