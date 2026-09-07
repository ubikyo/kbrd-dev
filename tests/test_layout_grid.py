"""Parity tests against kbrd-web/src/utils/layout.test.ts — same inputs,
same expected numbers, so `kbrd_dev.layout_grid` can be trusted to compute
a layout's disposition exactly the way the web editor's `<Display>` does.
Pure Python, no Kivy stubbing needed (see test_render_plugins.py's own
docstring for why that matters here too).
"""

import unittest

from kbrd_dev.layout_grid import (
    CellRect,
    cell_size_mm,
    default_grid_cell,
    division_cell_rect,
    division_outline,
    grid_rows,
    grid_size_mm,
    group_of,
    layout_row,
    max_items,
    merged_outline,
    pitch_mm,
    primary_of,
    row_of,
)


def cell_at(unit):
    return {**default_grid_cell(), "unit": unit, "typeId": "kbrd.layout-key"}


class PitchAndBudgetTest(unittest.TestCase):
    def test_pitch_is_the_unit_plus_the_gap(self):
        self.assertEqual(pitch_mm(16, 3), 19)

    def test_max_items_fits_as_many_items_as_the_gap_allows(self):
        self.assertEqual(max_items(100, 10, 0), 10)
        self.assertEqual(max_items(94, 10, 2), 8)
        self.assertEqual(max_items(106, 10, 2), 9)
        # KBRD's own reference panel (216x135mm, 19.05mm caps, 3mm gaps —
        # see kbrd_dev.config's calibration comment).
        self.assertEqual(max_items(216, 19.05, 3), 9)
        self.assertEqual(max_items(135, 19.05, 3), 6)

    def test_max_items_is_zero_when_there_is_nothing_to_fit(self):
        self.assertEqual(max_items(0, 10, 2), 0)
        self.assertEqual(max_items(100, 0, 0), 0)

    def test_grid_size_mm_is_the_footprint_max_items_fits_within(self):
        items = max_items(216, 19.05, 3)
        self.assertEqual(grid_size_mm(items, 19.05, 3), items * 19.05 + (items - 1) * 3)
        self.assertEqual(grid_size_mm(0, 16, 3), 0)

    def test_cell_size_mm_sizes_a_cell_by_pitches_not_a_raw_scale(self):
        # A 2U cell is 2 pitches minus the one trailing gap it doesn't
        # need past its own last pitch: 2*19 - 3 = 35, not 2*16 = 32.
        width, height = cell_size_mm(cell_at(2), 16, 3)
        self.assertEqual(width, 35)
        self.assertEqual(height, 16)


class GridRowsTest(unittest.TestCase):
    def test_gives_every_row_an_empty_cell_list_until_told_otherwise(self):
        self.assertEqual(grid_rows(3, {1: [5, 6]}), [[], [5, 6], []])

    def test_row_of_finds_which_row_holds_a_given_cell_id(self):
        rows = grid_rows(2, {0: [1, 2], 1: [3]})
        self.assertEqual(row_of(3, rows), 1)
        self.assertEqual(row_of(99, rows), -1)


class LayoutRowTest(unittest.TestCase):
    def test_places_cells_left_to_right_flush_at_the_row_origin(self):
        cells = {1: cell_at(1), 2: cell_at(0.5)}
        slots = layout_row([1, 2], cells, 16, 3)
        self.assertEqual(slots[0].x, 0)
        self.assertEqual(slots[0].width, 16)
        # Cell 2 starts right after cell 1's edge plus one gap: 16 + 3.
        self.assertEqual(slots[1].x, 19)
        self.assertEqual(slots[1].width, 0.5 * 19 - 3)

    def test_on_an_empty_row_returns_no_slots(self):
        self.assertEqual(layout_row([], {}, 16, 3), [])


class GroupOfTest(unittest.TestCase):
    def test_returns_a_singleton_for_an_unmerged_cell(self):
        self.assertEqual(group_of(5, [[1, 2]]), [5])

    def test_finds_the_group_a_merged_cell_belongs_to(self):
        self.assertEqual(group_of(2, [[1, 2, 3]]), [1, 2, 3])

    def test_primary_of_is_always_the_groups_smallest_index(self):
        self.assertEqual(primary_of(3, [[1, 2, 3]]), 1)
        self.assertEqual(primary_of(5, []), 5)


class MergedOutlineTest(unittest.TestCase):
    def test_same_row_cells_is_a_plain_rectangle(self):
        rows = grid_rows(1, {0: [1, 2]})
        cells = {1: cell_at(1), 2: cell_at(1)}
        outline = merged_outline([1, 2], rows, cells, 10, 3)
        self.assertEqual(outline.bounds, CellRect(0, 0, 23, 10))
        self.assertEqual(len(outline.loops), 1)
        self.assertEqual(
            set(outline.loops[0]), {(0, 0), (23, 0), (23, 10), (0, 10)}
        )

    def test_stacked_cells_close_the_gap_and_step_to_each_width(self):
        rows = grid_rows(2, {0: [1], 1: [2]})
        cells = {1: cell_at(1), 2: cell_at(0.75)}
        outline = merged_outline([1, 2], rows, cells, 10, 3)
        # Row 1's 0.75U cell is 0.75*13-3=6.75mm (pitch-based, see cell_size_mm).
        self.assertEqual(outline.bounds, CellRect(0, 0, 10, 23))
        self.assertEqual(len(outline.loops), 1)
        self.assertEqual(
            set(outline.loops[0]),
            {(0, 0), (10, 0), (10, 10), (6.75, 10), (6.75, 23), (0, 23)},
        )

    def test_doesnt_bleed_into_a_cell_left_out_of_the_merge(self):
        # A 3x3 grid, merging every cell except the centre one (E):
        #   A B C        A . .
        #   D E F   ->   D . F
        #   G H I        G H I
        rows = grid_rows(3, {0: [1, 2, 3], 1: [4, 5, 6], 2: [7, 8, 9]})
        cells = {cell_id: cell_at(1) for cell_id in range(1, 10)}
        group = [1, 4, 6, 7, 8, 9]  # A D F G H I — E, B, C left out

        outline = merged_outline(group, rows, cells, 10, 3)

        self.assertEqual(outline.bounds, CellRect(0, 0, 36, 36))
        # E's own rect (x13-23, y13-23) must stay outside every traced
        # loop: none of its four corners are ever a vertex.
        e_corners = {(13, 13), (23, 13), (13, 23), (23, 23)}
        traced_points = {point for loop in outline.loops for point in loop}
        self.assertEqual(traced_points & e_corners, set())
        # The merge wraps E on three sides but stays open on top (where B
        # sits) — one single closed loop, not one per member.
        self.assertEqual(len(outline.loops), 1)


class DivisionOutlineTest(unittest.TestCase):
    def test_division_cell_rect_splits_into_equal_gapless_shares(self):
        parent = CellRect(0, 0, 20, 10)
        self.assertEqual(division_cell_rect(0, 2, 1, parent), CellRect(0, 0, 10, 10))
        self.assertEqual(division_cell_rect(1, 2, 1, parent), CellRect(10, 0, 10, 10))

    def test_merged_2x1_divisions_is_one_seamless_rectangle(self):
        parent = CellRect(0, 0, 20, 10)
        outline = division_outline([0, 1], 2, 1, parent)
        self.assertEqual(outline.bounds, CellRect(0, 0, 20, 10))
        self.assertEqual(len(outline.loops), 1)
        self.assertEqual(
            set(outline.loops[0]), {(0, 0), (20, 0), (20, 10), (0, 10)}
        )


if __name__ == "__main__":
    unittest.main()
