"""Port of KBRD-WEB's grid geometry math (`kbrd-web/src/utils/layout.ts`) —
the exact same arithmetic `<Display>` uses to lay the Factory grid (rows of
`GridCell`s, merges, divisions) out onto the physical screen. Keeping this
byte-for-byte identical to the web editor's own computation is the whole
point: whatever a layout looks like while it's being built in KBRD-WEB is
what has to show up on KBRD-DEV.

Only the *layout* math is ported here — everything in `utils/layout.ts`
that exists purely to support editing (adding/removing/moving cells,
merge/divide mutations, copy/paste, drag/resize helpers…) has no
equivalent on the device, which only ever reads an already-built
`factory_layout` and draws it. `mergedOutline`/`divisionOutline` are
ported without the SVG-path serialization their JS originals build
(`tracePolygon`/`pathFromLoop`) — the device draws point lists straight to
a Kivy `Line`, never an SVG `<path d="...">` string — and without the
`evenodd`-fill / `labelBounds` concerns, both specific to filling a shape
or centering text, neither of which applies here (every shape drawn today
is stroke-only, with no label — see `kbrd_dev.ui.display`).
"""

from dataclasses import dataclass

# Same floor `MIN_UNIT` in `types/layout.ts` gives a cell's own Unit — used
# here only as `defaultGridCell`'s own fallback, for a cell id a row
# references that `cells` doesn't actually have an entry for (shouldn't
# normally happen, but `layoutRow`'s own JS falls back the same way).
MIN_UNIT = 0.25

_EPS = 1e-6


def default_grid_cell(unit: float = MIN_UNIT) -> dict:
    return {
        "typeId": None,
        "typeConfig": {},
        "pluginIds": [],
        "keyRef": None,
        "unit": unit,
    }


def pitch_mm(unit_mm: float, gap_mm: float) -> float:
    """Centre-to-centre spacing between two adjacent items."""
    return unit_mm + gap_mm


def max_items(physical_mm: float, unit_mm: float, gap_mm: float) -> int:
    """How many `unit_mm`-sized items fit along `physical_mm`, spaced
    `gap_mm` apart — see `maxItems`'s own docstring for the formula."""
    pitch = pitch_mm(unit_mm, gap_mm)
    if pitch <= 0 or physical_mm <= 0:
        return 0
    return max(0, int((physical_mm + gap_mm) // pitch))


def grid_size_mm(items: int, unit_mm: float, gap_mm: float) -> float:
    """Reference footprint of `items` 1U slots laid out with `gap_mm`
    between them — used to centre the grid within the physical panel."""
    return items * unit_mm + (items - 1) * gap_mm if items > 0 else 0


def cell_size_mm(cell: dict, unit_mm: float, gap_mm: float) -> tuple[float, float]:
    """A cell's own physical footprint — see `cellSizeMm`'s own docstring
    on why a `cell.unit`-U cell isn't simply `unit * unit_mm` wide."""
    width = cell["unit"] * pitch_mm(unit_mm, gap_mm) - gap_mm
    return width, unit_mm


def grid_rows(items_y: int, row_overrides: dict[int, list[int]]) -> list[list[int]]:
    """`items_y` rows, each an ordered list of cell ids — empty until a
    plugin is actually dropped on that row (see `GridCell`'s own
    docstring: there is no "default cell")."""
    return [row_overrides.get(row, []) for row in range(items_y)]


def row_of(cell_id: int, rows: list[list[int]]) -> int:
    """Which row of `rows` holds cell `cell_id`, or -1 if none does."""
    for index, cell_ids in enumerate(rows):
        if cell_id in cell_ids:
            return index
    return -1


@dataclass(frozen=True)
class RowSlot:
    id: int
    x: float
    width: float


def layout_row(
    cell_ids: list[int],
    cells: dict[int, dict],
    unit_mm: float,
    gap_mm: float,
) -> list[RowSlot]:
    """Lays a row's actual cells out left to right as a plain flow,
    starting flush at the row's own local origin — see `layoutRow`'s own
    docstring for why a gap only ever sits *between* two consecutive
    cells."""
    slots: list[RowSlot] = []
    x = 0.0
    for cell_id in cell_ids:
        cell = cells.get(cell_id) or default_grid_cell()
        width, _ = cell_size_mm(cell, unit_mm, gap_mm)
        if slots:
            x += gap_mm
        slots.append(RowSlot(id=cell_id, x=x, width=width))
        x += width
    return slots


def group_of(index: int, groups: list[list[int]]) -> list[int]:
    """The merge group `index` belongs to, or the singleton `[index]` if
    it hasn't been merged with anything."""
    for group in groups:
        if index in group:
            return group
    return [index]


def primary_of(index: int, groups: list[list[int]]) -> int:
    """The index whose `GridCell` a merged group is shown through — its
    smallest member, so it's stable regardless of merge order."""
    return min(group_of(index, groups))


@dataclass(frozen=True)
class CellRect:
    x: float
    y: float
    width: float
    height: float


# -- merged/division outlines ------------------------------------------


def _row_spans(
    cell_ids: list[int],
    group: set[int],
    cells: dict[int, dict],
    unit_mm: float,
    gap_mm: float,
    y: float,
    height: float,
) -> list[CellRect]:
    """Collapses one row's cells into a rect per maximal run of
    *consecutive* group members — see `rowSpans`'s own docstring on why a
    non-member cell breaks the run rather than being bridged over."""
    spans: list[CellRect] = []
    run_start: float | None = None
    run_end = 0.0
    for slot in layout_row(cell_ids, cells, unit_mm, gap_mm):
        if slot.id in group:
            if run_start is None:
                run_start = slot.x
            run_end = slot.x + slot.width
        elif run_start is not None:
            spans.append(CellRect(run_start, y, run_end - run_start, height))
            run_start = None
    if run_start is not None:
        spans.append(CellRect(run_start, y, run_end - run_start, height))
    return spans


def _bounding_box(rects: list[CellRect]) -> CellRect:
    x = min(rect.x for rect in rects)
    y = min(rect.y for rect in rects)
    right = max(rect.x + rect.width for rect in rects)
    bottom = max(rect.y + rect.height for rect in rects)
    return CellRect(x, y, right - x, bottom - y)


Point = tuple[float, float]


def _trace_polygon(rects: list[CellRect]) -> list[list[Point]]:
    """Traces the outline of the union of `rects` as one or more closed
    loops, by rasterising the elementary cells their edges cut the plane
    into — a direct port of `tracePolygon`'s own algorithm. A loop wrapped
    all the way around a rect left out of the union (see
    `mergedOutline`'s "doesn't bleed into a cell left out of the merge"
    case) comes out as its own separate loop, same as the JS version's own
    inner subpath — nothing extra needed here to treat it as a hole, since
    every shape this draws is stroked, never filled (no `evenodd` fill
    rule to worry about)."""
    if not rects:
        return []

    xs = sorted({value for rect in rects for value in (rect.x, rect.x + rect.width)})
    ys = sorted({value for rect in rects for value in (rect.y, rect.y + rect.height)})
    cols = len(xs) - 1
    row_count = len(ys) - 1

    def covered(mid_x: float, mid_y: float) -> bool:
        return any(
            rect.x < mid_x < rect.x + rect.width and rect.y < mid_y < rect.y + rect.height
            for rect in rects
        )

    filled = [
        [covered((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2) for i in range(cols)]
        for j in range(row_count)
    ]

    def is_filled(j: int, i: int) -> bool:
        return 0 <= j < row_count and 0 <= i < cols and filled[j][i]

    edges: list[tuple[Point, Point]] = []
    for j in range(row_count):
        for i in range(cols):
            if not filled[j][i]:
                continue
            x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
            if not is_filled(j - 1, i):
                edges.append(((x0, y0), (x1, y0)))
            if not is_filled(j, i + 1):
                edges.append(((x1, y0), (x1, y1)))
            if not is_filled(j + 1, i):
                edges.append(((x1, y1), (x0, y1)))
            if not is_filled(j, i - 1):
                edges.append(((x0, y1), (x0, y0)))

    by_start: dict[Point, list[int]] = {}
    for index, edge in enumerate(edges):
        by_start.setdefault(edge[0], []).append(index)

    used = [False] * len(edges)
    loops: list[list[Point]] = []
    for start in range(len(edges)):
        if used[start]:
            continue
        loop: list[Point] = []
        current = start
        while True:
            used[current] = True
            loop.append(edges[current][0])
            candidates = by_start.get(edges[current][1], [])
            following = next((candidate for candidate in candidates if not used[candidate]), None)
            if following is None:
                break
            current = following
        loops.append(_simplify_loop(loop))

    return loops


def _near(a: float, b: float) -> bool:
    return abs(a - b) < _EPS


def _simplify_loop(loop: list[Point]) -> list[Point]:
    """Drops every point that doesn't actually turn a corner — the raster
    in `_trace_polygon` walks one elementary cell at a time, so a straight
    run of several is chopped into that many collinear points. Port of
    `pathFromLoop`'s own corner-filtering, minus the SVG path string it
    then serializes those corners into."""
    n = len(loop)
    if n < 3:
        return loop

    def direction(a: Point, b: Point) -> str:
        return "H" if _near(a[1], b[1]) else "V"

    return [
        point
        for i, point in enumerate(loop)
        if direction(loop[i - 1], point) != direction(point, loop[(i + 1) % n])
    ]


@dataclass(frozen=True)
class Outline:
    loops: list[list[Point]]
    bounds: CellRect


def merged_outline(
    group: list[int],
    rows: list[list[int]],
    cells: dict[int, dict],
    unit_mm: float,
    gap_mm: float,
) -> Outline:
    """The outline of a merged group — a plain rectangle when every member
    sits on the same row, a stepped/L shape when they're stacked across
    rows with a different width each, or any more irregular shape a less
    regular merge forms. See `mergedOutline`'s own docstring for the full
    reasoning (row spans, then bridging the gap between physically
    adjacent rows over whatever column range their spans actually share)."""
    group_set = set(group)
    pitch = pitch_mm(unit_mm, gap_mm)
    row_indexes = sorted({row_of(cell_id, rows) for cell_id in group})

    spans_by_row = {
        row: _row_spans(
            rows[row] if row != -1 else [],
            group_set,
            cells,
            unit_mm,
            gap_mm,
            row * pitch,
            unit_mm,
        )
        for row in row_indexes
    }
    rects = [span for spans in spans_by_row.values() for span in spans]

    for i in range(len(row_indexes) - 1):
        row_a, row_b = row_indexes[i], row_indexes[i + 1]
        if row_b != row_a + 1:
            continue  # not physically adjacent — nothing to bridge
        bridge_top = row_a * pitch + unit_mm
        bridge_bottom = row_b * pitch
        for a in spans_by_row.get(row_a, []):
            for b in spans_by_row.get(row_b, []):
                x = max(a.x, b.x)
                right = min(a.x + a.width, b.x + b.width)
                if right > x + _EPS:
                    rects.append(CellRect(x, bridge_top, right - x, bridge_bottom - bridge_top))

    return Outline(loops=_trace_polygon(rects), bounds=_bounding_box(rects))


def division_cell_rect(division_id: int, cols: int, rows: int, parent_rect: CellRect) -> CellRect:
    """A division's own rect within its parent cell's rect: `parent_rect`
    split into `cols` x `rows` equal shares, `division_id` row-major, no
    gap between any of them."""
    width = parent_rect.width / cols
    height = parent_rect.height / rows
    col = division_id % cols
    row = division_id // cols
    return CellRect(
        x=parent_rect.x + col * width,
        y=parent_rect.y + row * height,
        width=width,
        height=height,
    )


def division_outline(group: list[int], cols: int, rows: int, parent_rect: CellRect) -> Outline:
    """Same shape as `merged_outline`, over a division grid's own uniform,
    gap-less rects instead — no gap-bridging step needed since touching
    divisions already touch exactly."""
    rects = [division_cell_rect(division_id, cols, rows, parent_rect) for division_id in group]
    return Outline(loops=_trace_polygon(rects), bounds=_bounding_box(rects))
