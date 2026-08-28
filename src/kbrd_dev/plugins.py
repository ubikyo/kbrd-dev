import importlib.util
import json
import os
from pathlib import Path

from kivy.clock import Clock

from kbrd_dev.display_manager import DisplayManager
from kbrd_dev.render_spec import RenderSpec


def _plugin_roots():
    configured = os.environ.get("KBRD_PLUGIN_PATH")
    if configured:
        yield Path(configured)
    yield Path("/usr/share/kbrd/plugins")
    yield Path(__file__).resolve().parents[3] / "kbrd-plugins" / "src"


class PluginRegistry:
    def __init__(self):
        self._renderers = {}
        self._controllers = {}
        self._display = DisplayManager()
        self._load()

    def _load(self):
        for root in _plugin_roots():
            if not root.is_dir():
                continue
            for manifest_path in root.glob("*/plugin.json"):
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    plugin_id = manifest["id"]
                    renderer_path = manifest_path.parent / "dev" / "renderer.py"
                    controller_path = manifest_path.parent / "dev" / "controller.py"
                    if renderer_path.is_file() and plugin_id not in self._renderers:
                        module = self._module(
                            f"kbrd_renderer_{plugin_id.replace('.', '_')}",
                            renderer_path,
                        )
                        self._renderers[plugin_id] = module.render
                    if (
                        controller_path.is_file()
                        and plugin_id not in self._controllers
                    ):
                        module = self._module(
                            f"kbrd_controller_{plugin_id.replace('.', '_')}",
                            controller_path,
                        )
                        self._controllers[plugin_id] = module.Controller
                except Exception:
                    continue

    @staticmethod
    def _module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def render(self, key, instance):
        if not instance.get("enabled", True):
            return
        instance_id = instance.get("id")
        plugin_id = instance.get("plugin_id")
        config = instance.get("config") or {}
        renderer = self._renderers.get(plugin_id)
        up_config = {
            name: value
            for name, value in config.items()
            if name != "down"
        }
        raw_down = config.get("down")
        down = raw_down if isinstance(raw_down, dict) else {}
        enabled = down.get("enabled")
        if not isinstance(enabled, bool):
            enabled = down.get("inherited", True) is False
        down_config = down.get("config")
        if not isinstance(down_config, dict):
            down_config = up_config
        try:
            delay = max(0, float(down.get("delay", 0))) / 1000
        except (TypeError, ValueError):
            delay = 0

        if renderer:
            current_widget = [None]
            scheduled = [None]
            pressed = [False]

            def draw(state_config):
                widget = current_widget[0]
                update = getattr(widget, "kbrd_update", None)
                if callable(update):
                    update(state_config)
                    return

                result = renderer(key, state_config)
                if isinstance(result, RenderSpec):
                    # Declarative plugin: DisplayManager owns the actual
                    # Kivy widget and only touches it if `result` actually
                    # differs from what it mounted last.
                    current_widget[0] = self._display.apply(
                        key, instance_id, result
                    )
                    return

                # Legacy plugin: `result` is a raw Kivy widget it manages
                # itself (e.g. it already called `key.add_widget()`).
                parent = getattr(widget, "parent", None)
                if parent is not None:
                    parent.remove_widget(widget)
                current_widget[0] = result

            def show_up(*args):
                scheduled[0] = None
                if not pressed[0]:
                    draw(up_config)

            def resync(*args):
                # A declarative spec embeds the key's own geometry, so it
                # must be recomputed whenever `key` moves/resizes — notably
                # on first mount, since `render()` runs before `Keyboard`
                # has positioned the key. Legacy plugins already resync
                # themselves via their own pos/size binding; re-triggering
                # `draw()` here is a harmless extra `kbrd_update()` call for
                # them.
                draw(down_config if pressed[0] else up_config)

            def press(*args):
                pressed[0] = True
                if not enabled:
                    return
                if scheduled[0] is not None:
                    scheduled[0].cancel()
                    scheduled[0] = None
                draw(down_config)

            def release(*args):
                pressed[0] = False
                if scheduled[0] is not None:
                    scheduled[0].cancel()
                    scheduled[0] = None
                if enabled:
                    if delay > 0:
                        scheduled[0] = Clock.schedule_once(show_up, delay)
                    else:
                        show_up()

            def dispose_renderer():
                if scheduled[0] is not None:
                    scheduled[0].cancel()
                    scheduled[0] = None
                widget = current_widget[0]
                dispose = getattr(widget, "kbrd_dispose", None)
                if callable(dispose):
                    dispose()
                self._display.dispose(instance_id)
                current_widget[0] = None

            draw(up_config)
            key.bind(pos=resync, size=resync)
            renderer_disposers = getattr(key, "kbrd_renderer_disposers", None)
            if renderer_disposers is None:
                renderer_disposers = []
                key.kbrd_renderer_disposers = renderer_disposers
            renderer_disposers.append(dispose_renderer)
            key.bind(on_press=press, on_release=release)
        controller_class = self._controllers.get(plugin_id)
        if controller_class:
            controller = controller_class(up_config)
            controllers = getattr(key, "kbrd_controllers", None)
            if controllers is None:
                controllers = []
                key.kbrd_controllers = controllers
            controllers.append(controller)
            key.bind(
                on_press=lambda pressed_key: controller.on_press(pressed_key),
                on_release=lambda released_key: controller.on_release(
                    released_key
                ),
            )

    @staticmethod
    def release(key):
        for dispose in getattr(key, "kbrd_renderer_disposers", []):
            dispose()
        key.kbrd_renderer_disposers = []
        for controller in getattr(key, "kbrd_controllers", []):
            dispose = getattr(controller, "dispose", None)
            if callable(dispose):
                dispose()
        key.kbrd_controllers = []
