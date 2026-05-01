"""
test_converter.py — Unit tests for pdf2mdf helper functions.

These tests work without an actual PDF or a real fitz installation.
Run with: python -m pytest test_converter.py -v
      or: python test_converter.py
"""

from __future__ import annotations

import sys
import types
import unittest

# ---------------------------------------------------------------------------
# Stub out fitz so the module can be imported without PyMuPDF installed.
# If fitz IS available, the real one is used (no harm done).
# ---------------------------------------------------------------------------

def _maybe_stub_fitz() -> None:
    if "fitz" not in sys.modules:
        stub = types.ModuleType("fitz")
        stub.TEXT_PRESERVE_WHITESPACE = 0
        stub.open = None  # type: ignore[assignment]

        class _Matrix:
            def __init__(self, *a, **kw): pass

        class _Rect:
            def __init__(self, *a, **kw):
                self.x0 = self.y0 = 0.0
                self.width = self.height = 100.0
                self.is_empty = False

        stub.Matrix = _Matrix  # type: ignore[attr-defined]
        stub.Rect = _Rect      # type: ignore[attr-defined]
        sys.modules["fitz"] = stub


_maybe_stub_fitz()

# Now safe to import
from pdf2mdf import (  # noqa: E402 — after stub setup
    bbox_to_path,
    color_to_mdf,
    detect_page_shape,
    font_weight_from_name,
    FontRegistry,
    make_boundary_path,
    merge_adjacent_blocks,
    pt_to_mm,
    rgb_to_cmyk,
    sanitize_id,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPtToMm(unittest.TestCase):
    def test_zero(self):
        self.assertAlmostEqual(pt_to_mm(0), 0.0)

    def test_one_point(self):
        # pt_to_mm rounds to 4 decimal places, so 1pt → 0.3528 mm
        self.assertAlmostEqual(pt_to_mm(1), 0.352778, places=3)

    def test_a4_width(self):
        # A4 width = 595.276 pt ≈ 210 mm
        result = pt_to_mm(595.276)
        self.assertAlmostEqual(result, 210.0, delta=0.1)

    def test_a4_height(self):
        # A4 height = 841.89 pt ≈ 297 mm
        result = pt_to_mm(841.89)
        self.assertAlmostEqual(result, 297.0, delta=0.1)

    def test_negative(self):
        self.assertAlmostEqual(pt_to_mm(-72), -72 * 0.352778, places=4)


class TestRgbToCmyk(unittest.TestCase):
    def test_black(self):
        c, m, y, k = rgb_to_cmyk(0.0, 0.0, 0.0)
        self.assertAlmostEqual(k, 1.0)
        self.assertAlmostEqual(c, 0.0)
        self.assertAlmostEqual(m, 0.0)
        self.assertAlmostEqual(y, 0.0)

    def test_white(self):
        c, m, y, k = rgb_to_cmyk(1.0, 1.0, 1.0)
        self.assertAlmostEqual(k, 0.0)
        self.assertAlmostEqual(c, 0.0)
        self.assertAlmostEqual(m, 0.0)
        self.assertAlmostEqual(y, 0.0)

    def test_red(self):
        c, m, y, k = rgb_to_cmyk(1.0, 0.0, 0.0)
        self.assertAlmostEqual(k, 0.0)
        self.assertAlmostEqual(c, 0.0)
        self.assertAlmostEqual(m, 1.0)
        self.assertAlmostEqual(y, 1.0)

    def test_green(self):
        c, m, y, k = rgb_to_cmyk(0.0, 1.0, 0.0)
        self.assertAlmostEqual(c, 1.0)
        self.assertAlmostEqual(m, 0.0)
        self.assertAlmostEqual(y, 1.0)
        self.assertAlmostEqual(k, 0.0)

    def test_blue(self):
        c, m, y, k = rgb_to_cmyk(0.0, 0.0, 1.0)
        self.assertAlmostEqual(c, 1.0)
        self.assertAlmostEqual(m, 1.0)
        self.assertAlmostEqual(y, 0.0)
        self.assertAlmostEqual(k, 0.0)

    def test_gray(self):
        c, m, y, k = rgb_to_cmyk(0.5, 0.5, 0.5)
        self.assertAlmostEqual(k, 0.5, places=4)
        self.assertAlmostEqual(c, 0.0, places=4)
        self.assertAlmostEqual(m, 0.0, places=4)
        self.assertAlmostEqual(y, 0.0, places=4)

    def test_clamp(self):
        # Should never produce values outside [0,1]
        for r, g, b in [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (0.3, 0.7, 0.1)]:
            c, m, y, k = rgb_to_cmyk(r, g, b)
            for val in (c, m, y, k):
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 1.0)


class TestColorToMdf(unittest.TestCase):
    def test_none(self):
        self.assertEqual(color_to_mdf(None), "color(cmyk 0.000 0.000 0.000 1.000)")

    def test_zero_int(self):
        self.assertEqual(color_to_mdf(0), "color(cmyk 0.000 0.000 0.000 1.000)")

    def test_float_black(self):
        self.assertEqual(color_to_mdf(0.0), "color(cmyk 0.000 0.000 0.000 1.000)")

    def test_float_white(self):
        result = color_to_mdf(1.0)
        self.assertIn("0.000 0.000 0.000 0.000", result)

    def test_rgb_tuple_black(self):
        result = color_to_mdf((0.0, 0.0, 0.0))
        self.assertEqual(result, "color(cmyk 0.000 0.000 0.000 1.000)")

    def test_rgb_tuple_red(self):
        result = color_to_mdf((1.0, 0.0, 0.0))
        # red → C=0, M=1, Y=1, K=0
        self.assertIn("0.000 1.000 1.000 0.000", result)

    def test_cmyk_tuple(self):
        result = color_to_mdf((0.1, 0.2, 0.3, 0.4))
        self.assertIn("0.100 0.200 0.300 0.400", result)

    def test_single_element_tuple(self):
        result = color_to_mdf((0.0,))
        self.assertEqual(result, "color(cmyk 0.000 0.000 0.000 1.000)")

    def test_format_prefix(self):
        result = color_to_mdf((0.5, 0.5, 0.5))
        self.assertTrue(result.startswith("color(cmyk "))
        self.assertTrue(result.endswith(")"))

    def test_three_decimal_places(self):
        result = color_to_mdf((0.123456, 0.654321, 0.0))
        # Should have exactly 3 decimal places on each value
        import re
        # Extract CMYK values
        match = re.search(r"color\(cmyk ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)\)", result)
        self.assertIsNotNone(match)
        for i in range(1, 5):
            val_str = match.group(i)
            decimal_part = val_str.split(".")[-1]
            self.assertEqual(len(decimal_part), 3, f"Value {val_str} does not have 3 decimal places")


class TestSanitizeId(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(sanitize_id("hello"), "hello")

    def test_spaces_become_dashes(self):
        self.assertEqual(sanitize_id("hello world"), "hello-world")

    def test_special_chars(self):
        self.assertEqual(sanitize_id("block#1!"), "block-1")

    def test_leading_digit(self):
        result = sanitize_id("0block")
        self.assertFalse(result[0].isdigit())

    def test_empty(self):
        result = sanitize_id("")
        self.assertTrue(len(result) > 0)

    def test_uppercase_lowercased(self):
        self.assertEqual(sanitize_id("BLOCK"), "block")

    def test_multiple_separators_collapsed(self):
        self.assertEqual(sanitize_id("a---b"), "a-b")


class TestFontWeightFromName(unittest.TestCase):
    def test_plain_helvetica(self):
        family, weight, italic = font_weight_from_name("Helvetica")
        self.assertEqual(family, "Helvetica")
        self.assertEqual(weight, 400)
        self.assertFalse(italic)

    def test_bold(self):
        family, weight, italic = font_weight_from_name("Arial-Bold")
        self.assertEqual(weight, 700)
        self.assertFalse(italic)

    def test_bold_italic(self):
        family, weight, italic = font_weight_from_name("Times-BoldItalic")
        self.assertEqual(weight, 700)
        self.assertTrue(italic)

    def test_light(self):
        family, weight, italic = font_weight_from_name("Roboto-Light")
        self.assertEqual(weight, 300)

    def test_subset_prefix_stripped(self):
        family, weight, italic = font_weight_from_name("ABCDEF+Helvetica")
        self.assertEqual(family, "Helvetica")

    def test_subset_prefix_with_style(self):
        family, weight, italic = font_weight_from_name("XYZABC+TimesNewRoman-BoldOblique")
        self.assertEqual(weight, 700)
        self.assertTrue(italic)
        self.assertNotIn("XYZABC", family)

    def test_oblique_is_italic(self):
        _, _, italic = font_weight_from_name("Helvetica-Oblique")
        self.assertTrue(italic)

    def test_regular_stripped(self):
        family, weight, italic = font_weight_from_name("Arial-Regular")
        self.assertEqual(weight, 400)
        # "Regular" should be stripped from family
        self.assertNotIn("Regular", family)

    def test_semibold(self):
        _, weight, _ = font_weight_from_name("Roboto-SemiBold")
        self.assertEqual(weight, 600)

    def test_thin(self):
        _, weight, _ = font_weight_from_name("Roboto-Thin")
        self.assertEqual(weight, 100)

    def test_black(self):
        _, weight, _ = font_weight_from_name("Futura-Black")
        self.assertEqual(weight, 900)


class TestMakeBoundaryPath(unittest.TestCase):
    def test_a4(self):
        path = make_boundary_path(210.0, 297.0)
        self.assertIn("M 0,0", path)
        self.assertIn("L 210.0,0", path)
        self.assertIn("L 210.0,297.0", path)
        self.assertIn("L 0,297.0", path)
        self.assertIn("Z", path)

    def test_symmetric(self):
        path = make_boundary_path(100.0, 100.0)
        self.assertIn("L 100.0,100.0", path)

    def test_zero_dimensions(self):
        path = make_boundary_path(0.0, 0.0)
        self.assertIn("M 0,0", path)

    def test_fractional(self):
        path = make_boundary_path(215.9, 279.4)
        self.assertIn("215.9", path)
        self.assertIn("279.4", path)


class TestColorToMdfFormat(unittest.TestCase):
    """Verify the exact output format of color_to_mdf."""

    def test_output_format(self):
        result = color_to_mdf((0.0, 0.0, 0.0))
        self.assertEqual(result, "color(cmyk 0.000 0.000 0.000 1.000)")

    def test_output_format_white(self):
        result = color_to_mdf((1.0, 1.0, 1.0))
        self.assertEqual(result, "color(cmyk 0.000 0.000 0.000 0.000)")


class TestBboxToPath(unittest.TestCase):
    def test_basic(self):
        path = bbox_to_path(10.0, 20.0, 100.0, 200.0)
        self.assertIn("M 10.0000,20.0000", path)
        self.assertIn("L 100.0000,20.0000", path)
        self.assertIn("L 100.0000,200.0000", path)
        self.assertIn("L 10.0000,200.0000", path)
        self.assertIn("Z", path)

    def test_zero_origin(self):
        path = bbox_to_path(0.0, 0.0, 50.0, 50.0)
        self.assertIn("M 0.0000,0.0000", path)

    def test_fractional_coords(self):
        path = bbox_to_path(1.2345, 6.7890, 11.2345, 16.7890)
        self.assertIn("1.2345", path)
        self.assertIn("6.7890", path)


class TestDetectPageShape(unittest.TestCase):
    def test_a4(self):
        self.assertEqual(detect_page_shape(210.0, 297.0), "standard-a4")

    def test_a4_tolerance(self):
        # Within 2mm tolerance
        self.assertEqual(detect_page_shape(210.5, 296.5), "standard-a4")

    def test_letter(self):
        self.assertEqual(detect_page_shape(215.9, 279.4), "standard-letter")

    def test_a3(self):
        self.assertEqual(detect_page_shape(297.0, 420.0), "standard-a3")

    def test_custom(self):
        self.assertEqual(detect_page_shape(300.0, 400.0), "custom")

    def test_a4_landscape(self):
        self.assertEqual(detect_page_shape(297.0, 210.0), "standard-a4-landscape")

    def test_outside_tolerance(self):
        # 215mm × 297mm — close to A4 width but not within 2mm
        self.assertEqual(detect_page_shape(215.0, 297.0), "custom")


class TestFontRegistry(unittest.TestCase):
    def test_initial_fallback(self):
        reg = FontRegistry()
        fid = reg.get_id("Helvetica", 400)
        self.assertEqual(fid, "font-0")

    def test_register_new(self):
        reg = FontRegistry()
        fid = reg.register("Arial", 700)
        self.assertIsNotNone(fid)
        self.assertTrue(fid.startswith("font-"))

    def test_same_font_same_id(self):
        reg = FontRegistry()
        id1 = reg.register("Arial", 400)
        id2 = reg.register("Arial", 400)
        self.assertEqual(id1, id2)

    def test_different_weight_different_id(self):
        reg = FontRegistry()
        id1 = reg.register("Arial", 400)
        id2 = reg.register("Arial", 700)
        self.assertNotEqual(id1, id2)

    def test_all_fonts_sorted(self):
        reg = FontRegistry()
        reg.register("Times", 400)
        reg.register("Courier", 700)
        fonts = reg.all_fonts()
        ids = [int(f["id"].split("-")[1]) for f in fonts]
        self.assertEqual(ids, sorted(ids))

    def test_all_fonts_includes_family(self):
        reg = FontRegistry()
        reg.register("Times New Roman", 400)
        fonts = reg.all_fonts()
        families = [f["family"] for f in fonts]
        # Should have capitalised form
        self.assertTrue(any("Times" in fam for fam in families))

    def test_fallback_id_property(self):
        reg = FontRegistry()
        self.assertEqual(reg.fallback_id, "font-0")


class TestMergeAdjacentBlocks(unittest.TestCase):
    def _make_block(self, x0, y0, x1, y1, text="hello"):
        return {
            "bbox": (x0, y0, x1, y1),
            "type": 0,
            "lines": [{"spans": [{"text": text, "bbox": (x0, y0, x1, y1)}]}],
        }

    def test_empty(self):
        self.assertEqual(merge_adjacent_blocks([]), [])

    def test_single(self):
        block = self._make_block(0, 0, 100, 20)
        result = merge_adjacent_blocks([block])
        self.assertEqual(len(result), 1)

    def test_adjacent_merged(self):
        b1 = self._make_block(0, 0, 100, 20)
        b2 = self._make_block(0, 20, 100, 40)  # exactly touching
        result = merge_adjacent_blocks([b1, b2])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["bbox"][3], 40)  # y1 extended

    def test_within_tolerance_merged(self):
        b1 = self._make_block(0, 0, 100, 20)
        b2 = self._make_block(0, 21.5, 100, 40)  # 1.5pt gap → within 2pt
        result = merge_adjacent_blocks([b1, b2])
        self.assertEqual(len(result), 1)

    def test_too_far_not_merged(self):
        b1 = self._make_block(0, 0, 100, 20)
        b2 = self._make_block(0, 30, 100, 50)  # 10pt gap
        result = merge_adjacent_blocks([b1, b2])
        self.assertEqual(len(result), 2)

    def test_no_horizontal_overlap_not_merged(self):
        b1 = self._make_block(0, 0, 50, 20)
        b2 = self._make_block(60, 20, 110, 40)  # no horizontal overlap
        result = merge_adjacent_blocks([b1, b2])
        self.assertEqual(len(result), 2)

    def test_lines_combined(self):
        b1 = self._make_block(0, 0, 100, 20, "line1")
        b2 = self._make_block(0, 20, 100, 40, "line2")
        result = merge_adjacent_blocks([b1, b2])
        self.assertEqual(len(result[0]["lines"]), 2)

    def test_bbox_union_correct(self):
        b1 = self._make_block(10, 0, 80, 20)
        b2 = self._make_block(0, 20, 100, 40)
        result = merge_adjacent_blocks([b1, b2])
        rx0, ry0, rx1, ry1 = result[0]["bbox"]
        self.assertEqual(rx0, 0)   # min of 10, 0
        self.assertEqual(rx1, 100)  # max of 80, 100
        self.assertEqual(ry0, 0)
        self.assertEqual(ry1, 40)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
