import json
import time
from threading import Thread
from urllib.error import URLError
from urllib.request import urlopen

from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import mm
from kivy.uix.floatlayout import FloatLayout

from kbrd_dev.config import API_URL
from kbrd_dev.layout_grid import (
    CellRect,
    division_cell_rect,
    division_outline,
    grid_rows,
    grid_size_mm,
    group_of,
    layout_row,
    max_items,
    merged_outline,
    pitch_mm,
)
from kbrd_dev.startup import mark_startup, mark_startup_once

BORDER_WIDTH = 1
# The physical screen's own outline — same white `--kbrd-border-alt` (see
# `theme.ts`) `<Display>`'s own unselected `<rect>` strokes it with.
SCREEN_OUTLINE_COLOR = (1, 1, 1, 1)
# `kbrd.layout-key`'s own outline — plain white for now (no fill), until
# Layer-mode content (Render/Invoke plugins) actually draws inside it.
KEY_BORDER_COLOR = (1, 1, 1, 1)

# Reference panel used until `/api/display` answers for the first time —
# same fallback kbrd-web's own `DEFAULT_LAYOUT_SETTINGS` uses.
DEFAULT_PHYSICAL_WIDTH_MM = 216
DEFAULT_PHYSICAL_HEIGHT_MM = 135
DEFAULT_UNIT_MM = 16
DEFAULT_GAP_MM = 3

REFRESH_INTERVAL_SECONDS = 5

# TEMPORARY — the real target is whichever layer KBRD-WEB actually has
# active (`GET /api/layer/active`); until that's wired back up, this shows
# one fixed layout by name instead (its first layer — ordered by name,
# then id — see `list_layers`), so there's something real and stable to
# look at on the device while the rest of Layer-mode rendering is built.
DEFAULT_LAYOUT_NAME = "Macbook Pro"

# A `kbrd.layout-space` cell/division still occupies its own place in the
# grid (nothing about its geometry differs from a `kbrd.layout-key` one —
# every row/merge/division computation above treats it exactly the same
# way) but draws nothing at all, unlike a key.
SPACE_PLUGIN_ID = "kbrd.layout-space"


def _rect_loop(x, y, width, height):
    return [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]


class Display(FloatLayout):
    """Draws the Factory grid — the same rows/cells/merges/divisions
    `<Display>` (kbrd-web/src/components/Display.tsx) lays out — onto the
    physical screen, using the exact same geometry math (`kbrd_dev.layout_grid`,
    a port of `utils/layout.ts`) so a layout looks identical here and in
    the web editor.

    For now this only draws each populated cell/division's own outline —
    a plain white border for whichever ones carry a `kbrd.layout-key`
    instance (a cell's `typeId`; see `GridCell`), nothing at all for a
    `kbrd.layout-space` one (it still occupies its own place in the grid —
    see `SPACE_PLUGIN_ID`) — plus the physical screen's own outline. No
    fill color, no Render/Invoke plugin content, no Layer-mode look, no
    text labels: this is purely about proving the grid computation itself
    is right before anything is drawn inside it — see
    `kbrd-dev/legacy/README.md` for the widget this replaces.

    Shows one fixed layout by name for now (`DEFAULT_LAYOUT_NAME`) rather
    than whichever layer KBRD-WEB actually has active — see that
    constant's own comment.
    """

    def __init__(self, **kwargs):
        mark_startup("display-init-start")
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.background = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_background, size=self._update_background)
        self.bind(pos=self._redraw, size=self._redraw)

        self._physical_width_mm = DEFAULT_PHYSICAL_WIDTH_MM
        self._physical_height_mm = DEFAULT_PHYSICAL_HEIGHT_MM
        self._unit_mm = DEFAULT_UNIT_MM
        self._gap_mm = DEFAULT_GAP_MM
        self._max_columns = None
        self._max_rows = None
        self._factory_layout = None
        # Every `Color`/`Line` instruction currently drawn, so a redraw can
        # clear them cheaply rather than rebuilding the whole canvas.
        self._shapes = []
        self._last_signature = None
        self._request_pending = False
        self._stopped = False

        self._refresh()
        self._refresh_event = Clock.schedule_interval(self._refresh, REFRESH_INTERVAL_SECONDS)
        mark_startup("display-init-complete")

    def _update_background(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size

    # -- polling -----------------------------------------------------------

    def _refresh(self, *args):
        if self._request_pending:
            return
        self._request_pending = True
        Thread(target=self._load, daemon=True).start()

    @staticmethod
    def _get_json(path):
        with urlopen(f"{API_URL}{path}", timeout=2) as response:
            return json.load(response)

    def _load(self):
        started = time.monotonic()
        mark_startup_once("api-request-start")
        display = layout = layer = None
        try:
            # The physical panel size lives on KBRD-API's own `display`
            # row (shared by every layout — see `api/display.py`).
            display = self._get_json("/api/display")
            # TEMPORARY — see `DEFAULT_LAYOUT_NAME`'s own comment: looks up
            # one fixed layout by name instead of `GET /api/layer/active`,
            # and takes its first layer (ordered by name, then id — see
            # `list_layers`) for `factory_layout`.
            layouts = self._get_json("/api/layout")
            if isinstance(layouts, list):
                layout = next(
                    (item for item in layouts if item.get("name") == DEFAULT_LAYOUT_NAME),
                    None,
                )
            if layout is not None:
                layers = self._get_json(f"/api/layout/{layout['id']}/layer")
                if isinstance(layers, list) and layers:
                    layer = layers[0]
        except (OSError, URLError, ValueError, KeyError) as error:
            display = layout = layer = None
            mark_startup_once(
                "api-unavailable",
                duration=f"{time.monotonic() - started:.3f}s",
                error=error.__class__.__name__,
            )
        else:
            mark_startup_once("api-ready", duration=f"{time.monotonic() - started:.3f}s")
        Clock.schedule_once(lambda *args: self._loaded(display, layout, layer))

    def _loaded(self, display, layout, layer):
        self._request_pending = False
        if self._stopped:
            return

        if isinstance(display, dict):
            self._physical_width_mm = display.get("physical_width_mm", self._physical_width_mm)
            self._physical_height_mm = display.get("physical_height_mm", self._physical_height_mm)

        if isinstance(layout, dict):
            self._unit_mm = layout.get("unit_mm", self._unit_mm)
            self._gap_mm = layout.get("gap_mm", self._gap_mm)
            self._max_columns = layout.get("max_columns")
            self._max_rows = layout.get("max_rows")
        self._factory_layout = layer.get("factory_layout") if isinstance(layer, dict) else None

        signature = (
            self._physical_width_mm,
            self._physical_height_mm,
            self._unit_mm,
            self._gap_mm,
            self._max_columns,
            self._max_rows,
            json.dumps(self._factory_layout, sort_keys=True),
        )
        if signature == self._last_signature:
            return
        self._last_signature = signature
        mark_startup_once("layout-ready")
        self._redraw()

    # -- geometry ------------------------------------------------------

    def _grid_items_y(self):
        computed = max_items(self._physical_height_mm, self._unit_mm, self._gap_mm)
        # KBRD-API always stores `max_rows`/`max_columns` as a float (see
        # `Layout._optional_positive_number`) — `int()` here is what lets
        # `grid_rows`' own `range(items_y)` accept the result below.
        return int(min(self._max_rows, computed)) if self._max_rows is not None else computed

    def _grid_items_x(self):
        computed = max_items(self._physical_width_mm, self._unit_mm, self._gap_mm)
        # Unlike `_grid_items_y`, this is *not* cast to `int`: `itemsX` only
        # ever feeds `grid_size_mm`'s own arithmetic (the centering
        # reference width), never a `range()`/array length, and
        # `max_columns` is routinely fractional — set to a row's own exact
        # Unit sum (14.5, 23.75…) so the reference footprint matches that
        # row's real width exactly (see kbrd-web's own `Display.tsx`:
        # `Math.min(maxColumns, computedItemsX)` never gets floored
        # either). Truncating it here previously made the centering
        # reference narrower than the actual row, which both shifted the
        # grid right and pushed its own trailing cells past the physical
        # panel's right edge, off-window — the "too much space on the
        # left, can't see the rightmost keys" bug on the Magic Keyboard /
        # Macbook Pro layouts.
        return min(self._max_columns, computed) if self._max_columns is not None else computed

    def _rows_and_cells(self):
        factory = self._factory_layout or {}
        cells = {int(cell_id): cell for cell_id, cell in (factory.get("cells") or {}).items()}
        row_overrides = {
            int(row): cell_ids for row, cell_ids in (factory.get("rowOverrides") or {}).items()
        }
        merge_groups = factory.get("mergeGroups") or []
        rows = grid_rows(self._grid_items_y(), row_overrides)
        return rows, cells, merge_groups

    def _division_loops(self, divide, parent_rect: CellRect):
        """Every populated division's own outline, within `parent_rect` —
        pure port of `LayoutCellDivision`'s own rendering pass, minus its
        border-dedup optimisation (each division still draws its own full
        dashed outline, so two adjacent baseline divisions' shared edge is
        drawn twice — a cosmetic difference from the web editor, not a
        geometry one; see `kbrd-dev`'s own follow-up notes)."""
        cols = divide.get("cols", 1)
        rows = divide.get("rows", 1)
        count = cols * rows
        division_cells = {
            int(cell_id): cell for cell_id, cell in (divide.get("cells") or {}).items()
        }
        merge_groups = divide.get("mergeGroups") or []

        loops = []
        drawn = set()
        for division_id in range(count):
            group = group_of(division_id, merge_groups)
            primary = min(group)
            if primary in drawn:
                continue
            drawn.add(primary)
            division_cell = division_cells.get(primary)
            if (
                not division_cell
                or not division_cell.get("typeId")
                or division_cell.get("typeId") == SPACE_PLUGIN_ID
            ):
                continue
            if len(group) > 1:
                loops.extend(division_outline(group, cols, rows, parent_rect).loops)
            else:
                rect = division_cell_rect(primary, cols, rows, parent_rect)
                loops.append(_rect_loop(rect.x, rect.y, rect.width, rect.height))
        return loops

    def _grid_shapes(self):
        """Every cell/division outline to draw, as closed loops of
        (x_mm, y_mm) points in the panel's own mm-space — row 0 at the
        top, same as kbrd-web's own SVG viewBox. Pure geometry, no Kivy
        involved, so it's testable on its own (see `tests/test_display.py`)."""
        rows, cells, merge_groups = self._rows_and_cells()
        items_x = self._grid_items_x()
        pitch = pitch_mm(self._unit_mm, self._gap_mm)

        raw_shapes = []
        for row_index, cell_ids in enumerate(rows):
            slots = {slot.id: slot for slot in layout_row(cell_ids, cells, self._unit_mm, self._gap_mm)}
            for cell_id in cell_ids:
                group = group_of(cell_id, merge_groups)
                primary = min(group)
                if primary != cell_id:
                    continue  # a merged cell only draws once, from its primary

                cell = cells.get(primary)
                if not cell or not cell.get("typeId"):
                    # No Layout plugin assigned (yet) — same as the row's
                    # own trailing empty space in the web editor: nothing
                    # to draw.
                    continue
                if cell.get("typeId") == SPACE_PLUGIN_ID:
                    # A space still occupies its slot (nothing above this
                    # skips it from `rows`/`layout_row`'s own math) — it
                    # just draws nothing.
                    continue

                if len(group) > 1:
                    raw_shapes.extend(merged_outline(group, rows, cells, self._unit_mm, self._gap_mm).loops)
                    continue

                slot = slots[primary]
                bounds = CellRect(slot.x, row_index * pitch, slot.width, self._unit_mm)
                divide = cell.get("divide")
                if divide:
                    raw_shapes.extend(self._division_loops(divide, bounds))
                else:
                    raw_shapes.append(_rect_loop(bounds.x, bounds.y, bounds.width, bounds.height))

        grid_offset_x = (
            self._physical_width_mm - grid_size_mm(items_x, self._unit_mm, self._gap_mm)
        ) / 2
        grid_offset_y = (
            self._physical_height_mm - grid_size_mm(len(rows), self._unit_mm, self._gap_mm)
        ) / 2
        return [
            [(grid_offset_x + x, grid_offset_y + y) for x, y in loop] for loop in raw_shapes
        ]

    # -- drawing -------------------------------------------------------

    def _clear_shapes(self):
        for instruction in self._shapes:
            self.canvas.after.remove(instruction)
        self._shapes = []

    def _flatten(self, points_mm, origin_x, origin_y):
        # `y` grows downward in mm-space (row 0 at the top) but upward in
        # Kivy's own window space — flipped per point here.
        flat = []
        for x_mm, y_mm in points_mm:
            flat.append(origin_x + mm(x_mm))
            flat.append(origin_y + mm(self._physical_height_mm - y_mm))
        return flat

    def _draw_outline(self, points_mm, origin_x, origin_y, color_rgba):
        flat = self._flatten(points_mm, origin_x, origin_y)
        color = Color(*color_rgba)
        line = Line(points=flat, close=True, width=BORDER_WIDTH)
        self.canvas.after.add(color)
        self.canvas.after.add(line)
        self._shapes.extend((color, line))

    def _redraw(self, *args):
        self._clear_shapes()
        if self._physical_width_mm <= 0 or self._physical_height_mm <= 0:
            return

        panel_width = mm(self._physical_width_mm)
        panel_height = mm(self._physical_height_mm)
        origin_x = self.x + (self.width - panel_width) / 2
        origin_y = self.y + (self.height - panel_height) / 2

        self._draw_outline(
            _rect_loop(0, 0, self._physical_width_mm, self._physical_height_mm),
            origin_x,
            origin_y,
            SCREEN_OUTLINE_COLOR,
        )
        for loop in self._grid_shapes():
            self._draw_outline(loop, origin_x, origin_y, KEY_BORDER_COLOR)

    def on_parent(self, instance, parent):
        if parent is not None:
            return
        self._stopped = True
        if getattr(self, "_refresh_event", None):
            self._refresh_event.cancel()
            self._refresh_event = None
