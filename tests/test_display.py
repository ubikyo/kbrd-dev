import unittest

from tests._kivy_stubs import install as _install_kivy_stubs

_install_kivy_stubs()

from kbrd_dev.ui.display import Display  # noqa: E402


def make_display(
    physical_width_mm=100,
    physical_height_mm=50,
    unit_mm=10,
    gap_mm=2,
    max_columns=None,
    max_rows=None,
    factory_layout=None,
):
    display = Display.__new__(Display)
    display._physical_width_mm = physical_width_mm
    display._physical_height_mm = physical_height_mm
    display._unit_mm = unit_mm
    display._gap_mm = gap_mm
    display._max_columns = max_columns
    display._max_rows = max_rows
    display._factory_layout = factory_layout
    return display


def grid_cell(unit=1, type_id="kbrd.layout-key", divide=None):
    cell = {"typeId": type_id, "typeConfig": {}, "pluginIds": [], "keyRef": "k", "unit": unit}
    if divide is not None:
        cell["divide"] = divide
    return cell


class RowsAndCellsTest(unittest.TestCase):
    def test_parses_factory_layout_with_string_keys_like_json_does(self):
        display = make_display(
            factory_layout={
                "rowOverrides": {"0": [1, 2]},
                "cells": {"1": grid_cell(1), "2": grid_cell(1)},
                "mergeGroups": [],
            },
        )
        rows, cells, merge_groups = display._rows_and_cells()
        self.assertEqual(rows[0], [1, 2])
        self.assertIn(1, cells)
        self.assertEqual(merge_groups, [])

    def test_no_factory_layout_means_an_empty_grid(self):
        display = make_display(factory_layout=None)
        rows, cells, merge_groups = display._rows_and_cells()
        self.assertTrue(all(row == [] for row in rows))
        self.assertEqual(cells, {})


class GridItemsTest(unittest.TestCase):
    def test_grid_items_y_is_clamped_to_max_rows(self):
        # 50mm panel, 10mm caps, 2mm gaps -> pitch 12 -> floor(52/12) = 4.
        display = make_display(max_rows=2)
        self.assertEqual(display._grid_items_y(), 2)

    def test_grid_items_y_falls_back_to_the_computed_max_without_an_override(self):
        display = make_display(max_rows=None)
        self.assertEqual(display._grid_items_y(), 4)

    def test_grid_items_x_is_clamped_to_max_columns(self):
        # 100mm panel, same pitch -> floor(102/12) = 8.
        display = make_display(max_columns=3)
        self.assertEqual(display._grid_items_x(), 3)

    def test_max_rows_comes_back_as_a_float_from_kbrd_api_but_grid_items_y_is_an_int(self):
        # `Layout._optional_positive_number` always stores/returns these as
        # a float — `range()` (in `layout_grid.grid_rows`) rejects one, so
        # `_grid_items_y` must hand back a plain `int`.
        display = make_display(max_rows=2.0)
        self.assertEqual(display._grid_items_y(), 2)
        self.assertIsInstance(display._grid_items_y(), int)

    def test_grid_items_x_stays_fractional_like_kbrd_web_own_itemsX(self):
        # Unlike `_grid_items_y`, `_grid_items_x` only ever feeds
        # `grid_size_mm`'s arithmetic (never a `range()`) — a fractional
        # `max_columns` (set to a row's own exact Unit sum, e.g. 14.5) must
        # come through unrounded, or the centering reference footprint no
        # longer matches that row's real width (see `GridShapesTest`'s own
        # regression test below).
        display = make_display(max_columns=3.5)
        self.assertEqual(display._grid_items_x(), 3.5)


class GridShapesTest(unittest.TestCase):
    def test_a_single_plain_cell_draws_one_rectangle_offset_to_centre(self):
        display = make_display(
            physical_width_mm=100,
            physical_height_mm=50,
            unit_mm=10,
            gap_mm=2,
            max_rows=1,
            max_columns=1,
            factory_layout={
                "rowOverrides": {"0": [1]},
                "cells": {"1": grid_cell(1)},
                "mergeGroups": [],
            },
        )
        shapes = display._grid_shapes()
        self.assertEqual(len(shapes), 1)
        # A 1U cell (10mm) centred in a 100mm-wide, 1-row-tall panel: 45mm
        # of margin on each side.
        self.assertEqual(set(shapes[0]), {(45, 20), (55, 20), (55, 30), (45, 30)})

    def test_an_untyped_cell_draws_nothing(self):
        display = make_display(
            factory_layout={
                "rowOverrides": {"0": [1]},
                "cells": {"1": grid_cell(1, type_id=None)},
                "mergeGroups": [],
            },
        )
        self.assertEqual(display._grid_shapes(), [])

    def test_a_merged_group_draws_its_outline_once(self):
        display = make_display(
            physical_width_mm=100,
            physical_height_mm=50,
            unit_mm=10,
            gap_mm=2,
            max_rows=1,
            factory_layout={
                "rowOverrides": {"0": [1, 2]},
                "cells": {"1": grid_cell(1), "2": grid_cell(1)},
                "mergeGroups": [[1, 2]],
            },
        )
        shapes = display._grid_shapes()
        self.assertEqual(len(shapes), 1)

    def test_a_divided_cell_draws_each_populated_division(self):
        divide = {
            "cols": 2,
            "rows": 1,
            "cells": {
                "0": grid_cell(type_id="kbrd.layout-key"),
                "1": grid_cell(type_id=None),
            },
            "mergeGroups": [],
        }
        display = make_display(
            physical_width_mm=100,
            physical_height_mm=50,
            unit_mm=10,
            gap_mm=2,
            max_rows=1,
            factory_layout={
                "rowOverrides": {"0": [1]},
                "cells": {"1": grid_cell(1, divide=divide)},
                "mergeGroups": [],
            },
        )
        shapes = display._grid_shapes()
        # Division 1 has no `typeId` — only division 0 draws, same as an
        # untyped top-level cell drawing nothing.
        self.assertEqual(len(shapes), 1)

    def test_a_space_still_takes_its_slot_but_draws_nothing(self):
        # A key right after a space must sit exactly where the space's own
        # width pushes it — the space just never gets its own shape.
        display = make_display(
            physical_width_mm=100,
            physical_height_mm=50,
            unit_mm=10,
            gap_mm=2,
            max_rows=1,
            factory_layout={
                "rowOverrides": {"0": [1, 2]},
                "cells": {
                    "1": grid_cell(1, type_id="kbrd.layout-space"),
                    "2": grid_cell(1),
                },
                "mergeGroups": [],
            },
        )
        shapes = display._grid_shapes()
        self.assertEqual(len(shapes), 1)
        xs = [x for x, _ in shapes[0]]
        # Cell 2 starts at 12mm (cell 1's 10mm width + the 2mm gap) within
        # the grid's own local space. No `max_columns` override here, so
        # the centering reference is the full computed 8 items
        # (`grid_size_mm(8, 10, 2)` = 94mm), a 3mm margin either side.
        self.assertEqual(min(xs), 3 + 12)

    def test_a_row_whose_units_exactly_fill_max_columns_isnt_clipped(self):
        # Regression test for the real "Macbook Pro"/"Magic keyboard"
        # layouts: `max_columns` set to a row's own exact Unit sum (14.5U
        # here, mirroring the real 13mm-cap/1mm-gap Macbook Pro layout)
        # must produce a centering reference that matches the row's real
        # width exactly — truncating it to `14` previously shifted the
        # whole row right and pushed its last cell off the physical panel.
        unit_mm, gap_mm = 13, 1
        cells = {"1": grid_cell(1.5)}
        for cell_id in range(2, 15):
            cells[str(cell_id)] = grid_cell(1)
        display = make_display(
            physical_width_mm=216,
            physical_height_mm=135,
            unit_mm=unit_mm,
            gap_mm=gap_mm,
            max_rows=6,
            max_columns=14.5,
            factory_layout={
                "rowOverrides": {"0": list(range(1, 15))},
                "cells": cells,
                "mergeGroups": [],
            },
        )
        shapes = display._grid_shapes()
        all_x = [x for loop in shapes for x, _ in loop]
        # The row's real content is exactly 202mm wide (14.5U at this
        # pitch) — centred in a 216mm panel, that's a 7mm margin on each
        # side, and nothing past `216 - 7 = 209mm`.
        self.assertAlmostEqual(min(all_x), 7)
        self.assertAlmostEqual(max(all_x), 209)


if __name__ == "__main__":
    unittest.main()
