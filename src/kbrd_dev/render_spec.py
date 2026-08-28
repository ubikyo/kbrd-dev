from dataclasses import dataclass


@dataclass(frozen=True)
class RenderSpec:
    """Declarative description of one piece of visual content a plugin
    wants displayed inside a key.

    A migrated plugin's `dev/renderer.py` returns one of these from
    `render(key, config)` instead of building/mounting a Kivy widget itself
    — `DisplayManager` is the only code that turns it into real widgets,
    and only touches Kivy when the spec it receives actually differs (by
    value) from the one it mounted last. Plugins that have not migrated yet
    keep returning a raw Kivy widget, which `PluginRegistry` still mounts
    exactly as before; both are accepted transparently on the same key.

    `x`/`y`/`width`/`height` are absolute window pixels, the same space
    `key.x/y/width/height` already live in — plugins keep computing their
    own placement (it is plugin-specific), only *widget management* moves
    to `DisplayManager`. Only `kind`s whose geometry a plugin can compute
    in pure Python are covered here (`rect`, `image`): a piece of content
    whose size depends on Kivy actually measuring it — e.g. text under
    precise (x %, y %) placement, which needs the rendered glyph box before
    it can be positioned — still needs a two-phase, Kivy-aware step and is
    intentionally left on the legacy raw-widget path for now (see
    `render-label`'s `dev/renderer.py`).

    `z` is the plugin's requested stacking position among the specs it
    returns. Today every migrated plugin returns exactly one spec, and
    ordering between *different* plugin instances on the same key is
    already governed by their `position` (the same field the web editor's
    drag-to-reorder writes) — `DisplayManager` mounts/updates instances in
    that same order, so `z` is not yet used to reorder widgets. It is kept
    on the spec so a plugin returning several overlapping pieces of content
    at once has a documented way to state their order once that lands.
    """

    kind: str  # "rect" | "image"
    x: float
    y: float
    width: float
    height: float
    z: int = 0
    visible: bool = True

    # kind == "rect"
    color: str = "#ffffff"

    # kind == "image"
    source: str = ""
