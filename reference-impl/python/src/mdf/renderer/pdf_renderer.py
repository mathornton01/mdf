"""
MDF PDF Renderer
================

Converts a parsed :class:`~mdf.model.document.MDFDocument` to a PDF byte
stream using **reportlab**.

The PDF page dimensions exactly match the MDF canvas dimensions.  A thin
black rectangle is drawn around the canvas boundary so that the page edges
are always visible when the PDF is embedded or printed on larger media.

Usage::

    from mdf.parser import parse_file
    from mdf.renderer.pdf_renderer import render_pdf

    doc = parse_file("resume.mdf")
    pdf_bytes = render_pdf(doc)
    with open("resume.pdf", "wb") as f:
        f.write(pdf_bytes)

    # Proof mode overlays bleed/cut lines:
    pdf_bytes = render_pdf(doc, proof=True)

Dependencies
------------
- reportlab >= 4.0  (``pip install reportlab``)
"""

from __future__ import annotations

import io
import re
from typing import Any, Optional

from mdf.model.document import Canvas, Layer, MDFDocument
from mdf.renderer.svg_renderer import (
    _cmyk_to_rgb,
    _lab_to_rgb,
    _parse_color,
    _path_bbox,
)
from mdf.parser.unit_converter import parse_length

# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------

# All PDF coordinates are in points (1/72 inch).
_UNIT_TO_PT: dict[str, float] = {
    "mm": 72.0 / 25.4,
    "cm": 720.0 / 25.4,
    "in": 72.0,
    "pt": 1.0,
    "pc": 12.0,           # 1 pica = 12 pt
    "px": 72.0 / 96.0,   # CSS reference px = 1/96 inch
    "q":  72.0 / (25.4 * 4.0),  # quarter-mm
}


def _to_pt(value: float, units: str) -> float:
    """Convert a value in *units* to PDF points."""
    factor = _UNIT_TO_PT.get(units.lower().strip(), _UNIT_TO_PT["mm"])
    return value * factor


def _length_to_pt(raw: str, default_units: str = "mm") -> float:
    """Parse a length string (e.g. '10mm', '1in') to points."""
    try:
        val_mm = parse_length(raw, "mm")
        return val_mm * _UNIT_TO_PT["mm"]
    except Exception:
        try:
            return float(raw) * _UNIT_TO_PT.get(default_units, _UNIT_TO_PT["mm"])
        except (ValueError, TypeError):
            return 0.0


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

_HEX3_RE = re.compile(r"^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$")
_HEX6_RE = re.compile(r"^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$")
_HEX8_RE = re.compile(r"^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$")
_RGB_RE  = re.compile(r"rgb\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)", re.IGNORECASE)
_RGBA_RE = re.compile(r"rgba\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)", re.IGNORECASE)

# Known CSS named colors (subset sufficient for MDF documents)
_CSS_NAMED: dict[str, tuple[int, int, int]] = {
    "black":   (0, 0, 0),
    "white":   (255, 255, 255),
    "red":     (255, 0, 0),
    "green":   (0, 128, 0),
    "blue":    (0, 0, 255),
    "yellow":  (255, 255, 0),
    "cyan":    (0, 255, 255),
    "magenta": (255, 0, 255),
    "gray":    (128, 128, 128),
    "grey":    (128, 128, 128),
    "silver":  (192, 192, 192),
    "orange":  (255, 165, 0),
    "purple":  (128, 0, 128),
    "brown":   (165, 42, 42),
    "pink":    (255, 192, 203),
    "none":    None,   # type: ignore[assignment]
}


def _css_to_rgb(css: str) -> tuple[float, float, float] | None:
    """Convert a CSS color string to an (r, g, b) tuple with values in [0, 1].

    Returns None for 'none' / transparent.
    """
    if not css:
        return (0.0, 0.0, 0.0)
    css = css.strip()

    # none / transparent
    if css.lower() == "none":
        return None

    # #rrggbbaa
    m = _HEX8_RE.match(css)
    if m:
        r, g, b = int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)
        return r / 255.0, g / 255.0, b / 255.0

    # #rrggbb
    m = _HEX6_RE.match(css)
    if m:
        r, g, b = int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)
        return r / 255.0, g / 255.0, b / 255.0

    # #rgb
    m = _HEX3_RE.match(css)
    if m:
        r = int(m.group(1) * 2, 16)
        g = int(m.group(2) * 2, 16)
        b = int(m.group(3) * 2, 16)
        return r / 255.0, g / 255.0, b / 255.0

    # rgba(r, g, b, a)
    m = _RGBA_RE.match(css)
    if m:
        r, g, b = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if r > 1 or g > 1 or b > 1:
            return r / 255.0, g / 255.0, b / 255.0
        return r, g, b

    # rgb(r, g, b)
    m = _RGB_RE.match(css)
    if m:
        r, g, b = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if r > 1 or g > 1 or b > 1:
            return r / 255.0, g / 255.0, b / 255.0
        return r, g, b

    # named color
    named = _CSS_NAMED.get(css.lower())
    if named is not None:
        return named[0] / 255.0, named[1] / 255.0, named[2] / 255.0
    if css.lower() == "none":
        return None

    # default: black
    return (0.0, 0.0, 0.0)


def _mdf_color_to_rgb(
    color_str: Optional[str],
    spot_colors: Optional[dict] = None,
) -> tuple[float, float, float] | None:
    """Convert an MDF color string to an (r, g, b) tuple in [0, 1], or None."""
    css = _parse_color(color_str, spot_colors=spot_colors)
    return _css_to_rgb(css)


# ---------------------------------------------------------------------------
# SVG path → reportlab path
# ---------------------------------------------------------------------------

def _apply_svg_path(rl_path: Any, path_data: str) -> None:
    """
    Parse SVG path data and apply the commands to a reportlab path object.

    Supported commands: M, m, L, l, H, h, V, v, C, c, S, s, Q, q, A, a, Z, z.
    The coordinate system is SVG (Y-down), so the caller is responsible for
    applying a coordinate transform before drawing.
    """
    tokens = re.findall(
        r"[MLHVCSQTAZmlhvcsqtaz]"
        r"|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?",
        path_data,
    )

    cmd = "M"
    i = 0
    cx, cy = 0.0, 0.0
    start_x, start_y = 0.0, 0.0

    def _nums(n: int) -> list[float]:
        nonlocal i
        result: list[float] = []
        while len(result) < n and i < len(tokens):
            tok = tokens[i]
            if tok.isalpha():
                break
            try:
                result.append(float(tok))
                i += 1
            except ValueError:
                i += 1
        return result

    while i < len(tokens):
        tok = tokens[i]
        if tok.isalpha():
            cmd = tok
            i += 1
            continue

        if cmd == "M":
            ns = _nums(2)
            if len(ns) < 2:
                break
            cx, cy = ns[0], ns[1]
            start_x, start_y = cx, cy
            rl_path.moveTo(cx, cy)
            cmd = "L"

        elif cmd == "m":
            ns = _nums(2)
            if len(ns) < 2:
                break
            cx += ns[0]; cy += ns[1]
            start_x, start_y = cx, cy
            rl_path.moveTo(cx, cy)
            cmd = "l"

        elif cmd == "L":
            ns = _nums(2)
            if len(ns) < 2:
                break
            cx, cy = ns[0], ns[1]
            rl_path.lineTo(cx, cy)

        elif cmd == "l":
            ns = _nums(2)
            if len(ns) < 2:
                break
            cx += ns[0]; cy += ns[1]
            rl_path.lineTo(cx, cy)

        elif cmd == "H":
            ns = _nums(1)
            if not ns:
                break
            cx = ns[0]
            rl_path.lineTo(cx, cy)

        elif cmd == "h":
            ns = _nums(1)
            if not ns:
                break
            cx += ns[0]
            rl_path.lineTo(cx, cy)

        elif cmd == "V":
            ns = _nums(1)
            if not ns:
                break
            cy = ns[0]
            rl_path.lineTo(cx, cy)

        elif cmd == "v":
            ns = _nums(1)
            if not ns:
                break
            cy += ns[0]
            rl_path.lineTo(cx, cy)

        elif cmd == "C":
            ns = _nums(6)
            if len(ns) < 6:
                break
            rl_path.curveTo(ns[0], ns[1], ns[2], ns[3], ns[4], ns[5])
            cx, cy = ns[4], ns[5]

        elif cmd == "c":
            ns = _nums(6)
            if len(ns) < 6:
                break
            rl_path.curveTo(
                cx + ns[0], cy + ns[1],
                cx + ns[2], cy + ns[3],
                cx + ns[4], cy + ns[5],
            )
            cx += ns[4]; cy += ns[5]

        elif cmd == "S":
            ns = _nums(4)
            if len(ns) < 4:
                break
            rl_path.curveTo(cx, cy, ns[0], ns[1], ns[2], ns[3])
            cx, cy = ns[2], ns[3]

        elif cmd == "s":
            ns = _nums(4)
            if len(ns) < 4:
                break
            rl_path.curveTo(
                cx, cy,
                cx + ns[0], cy + ns[1],
                cx + ns[2], cy + ns[3],
            )
            cx += ns[2]; cy += ns[3]

        elif cmd == "Q":
            # Quadratic → cubic approximation
            ns = _nums(4)
            if len(ns) < 4:
                break
            x1 = cx + 2 / 3 * (ns[0] - cx)
            y1 = cy + 2 / 3 * (ns[1] - cy)
            x2 = ns[2] + 2 / 3 * (ns[0] - ns[2])
            y2 = ns[3] + 2 / 3 * (ns[1] - ns[3])
            rl_path.curveTo(x1, y1, x2, y2, ns[2], ns[3])
            cx, cy = ns[2], ns[3]

        elif cmd == "q":
            ns = _nums(4)
            if len(ns) < 4:
                break
            ax, ay = cx + ns[0], cy + ns[1]
            ex, ey = cx + ns[2], cy + ns[3]
            x1 = cx + 2 / 3 * (ax - cx)
            y1 = cy + 2 / 3 * (ay - cy)
            x2 = ex + 2 / 3 * (ax - ex)
            y2 = ey + 2 / 3 * (ay - ey)
            rl_path.curveTo(x1, y1, x2, y2, ex, ey)
            cx, cy = ex, ey

        elif cmd in ("A", "a"):
            # Arc: approximate by moving to endpoint (full arc support requires
            # Bezier decomposition — this keeps the tool functional for now)
            ns = _nums(7)
            if len(ns) < 7:
                break
            if cmd == "A":
                cx, cy = ns[5], ns[6]
            else:
                cx += ns[5]; cy += ns[6]
            rl_path.lineTo(cx, cy)

        elif cmd in ("Z", "z"):
            rl_path.close()
            cx, cy = start_x, start_y

        else:
            i += 1  # unknown — skip


# ---------------------------------------------------------------------------
# PDF renderer
# ---------------------------------------------------------------------------

def render_pdf(
    doc: MDFDocument,
    proof: bool = False,
    canvas_index: int = 0,
    border_width_pt: float = 0.5,
    border_color: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bytes:
    """
    Render a parsed :class:`~mdf.model.document.MDFDocument` to a PDF byte stream.

    The PDF page dimensions exactly match the MDF canvas dimensions.  A thin
    rectangle is drawn around the canvas boundary so page edges are visible.

    Parameters
    ----------
    doc:
        A fully parsed MDFDocument.
    proof:
        When True, overlays bleed (red dashed), cut (green dashed), and fold
        (orange dashed) marks.
    canvas_index:
        Which canvas to render, 0-based.
    border_width_pt:
        Line width of the boundary rectangle, in PDF points.  Default 0.5 pt.
    border_color:
        Border rectangle color as (r, g, b) in [0, 1].  Default black.

    Returns
    -------
    bytes
        A complete PDF document as bytes.

    Raises
    ------
    ImportError
        If reportlab is not installed.
    IndexError
        If canvas_index is out of range.
    ValueError
        If the document has no canvases.
    """
    try:
        from reportlab.pdfgen import canvas as rl_canvas_module
        from reportlab.lib.colors import Color
    except ImportError as exc:
        raise ImportError(
            "PDF rendering requires reportlab. Install it with:\n"
            "  pip install reportlab"
        ) from exc

    if not doc.canvases:
        raise ValueError("Document has no canvases to render")
    if canvas_index >= len(doc.canvases):
        raise IndexError(
            f"canvas_index {canvas_index} out of range "
            f"(document has {len(doc.canvases)} canvas(es))"
        )

    canvas = doc.canvases[canvas_index]
    renderer = _PDFRenderer(doc, canvas, proof=proof,
                            border_width_pt=border_width_pt,
                            border_color=border_color)
    return renderer.render()


# ---------------------------------------------------------------------------
# Internal renderer class
# ---------------------------------------------------------------------------

class _PDFRenderer:
    """
    Stateful renderer that produces a PDF byte stream for a single canvas.

    Coordinate system notes
    -----------------------
    * MDF / SVG: origin top-left, Y increases downward.
    * PDF / reportlab: origin bottom-left, Y increases upward.

    Every Y coordinate is flipped via ``_y(y_mdf)`` = page_height_pt - y_mdf_pt.
    """

    def __init__(
        self,
        doc: MDFDocument,
        canvas: Canvas,
        proof: bool = False,
        border_width_pt: float = 0.5,
        border_color: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> None:
        self._doc = doc
        self._canvas = canvas
        self._proof = proof
        self._border_width_pt = border_width_pt
        self._border_color = border_color
        self._spot_colors: dict = doc.manifest.spot_colors or {}

        # Canvas dimensions in PDF points
        self._w_pt = _to_pt(canvas.width,  canvas.units)
        self._h_pt = _to_pt(canvas.height, canvas.units)
        # Scale factor: document units → PDF points
        self._scale = _UNIT_TO_PT.get(canvas.units.lower().strip(), _UNIT_TO_PT["mm"])

    # ------------------------------------------------------------------
    # Coordinate helpers (MDF top-left → PDF bottom-left)
    # ------------------------------------------------------------------

    def _x(self, x_doc: float) -> float:
        """Convert x in document units to PDF points (x is the same direction)."""
        return x_doc * self._scale

    def _y(self, y_doc: float) -> float:
        """Convert y in document units to PDF points, flipping the axis."""
        return self._h_pt - (y_doc * self._scale)

    def _pt(self, value: float) -> float:
        """Convert a scalar document-unit value to PDF points."""
        return value * self._scale

    # ------------------------------------------------------------------
    # Top-level render
    # ------------------------------------------------------------------

    def render(self) -> bytes:
        """Build and return the complete PDF as bytes."""
        from reportlab.pdfgen import canvas as rl_canvas_module
        from reportlab.lib.colors import Color

        buf = io.BytesIO()
        c = rl_canvas_module.Canvas(
            buf,
            pagesize=(self._w_pt, self._h_pt),
        )

        title = self._doc.manifest.title or "MDF Document"
        c.setTitle(title)
        if self._doc.manifest.author:
            c.setAuthor(self._doc.manifest.author)
        c.setSubject("Morphous Document Format (MDF)")

        # Draw white background
        c.setFillColorRGB(1.0, 1.0, 1.0)
        c.rect(0, 0, self._w_pt, self._h_pt, fill=1, stroke=0)

        # Render all visible layers
        self._render_layers(c)

        # Proof overlay
        if self._proof:
            self._render_proof_overlay(c)

        # Boundary rectangle — always on top
        self._render_boundary_rect(c)

        c.save()
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Boundary rectangle
    # ------------------------------------------------------------------

    def _render_boundary_rect(self, c: Any) -> None:
        """
        Draw a thin rectangle around the canvas boundary.

        For a rectangular canvas this is simply a stroke rect at the page
        edges.  For non-rectangular shapes the bounding-box rectangle is
        drawn so the page boundary is always clearly visible.
        """
        from reportlab.lib.colors import Color
        r, g, b = self._border_color
        c.setStrokeColorRGB(r, g, b)
        c.setLineWidth(self._border_width_pt)
        c.setFillColorRGB(1.0, 1.0, 1.0)  # no fill

        half = self._border_width_pt / 2.0
        c.rect(
            half,            # x
            half,            # y (PDF: bottom)
            self._w_pt - self._border_width_pt,
            self._h_pt - self._border_width_pt,
            fill=0,
            stroke=1,
        )

    # ------------------------------------------------------------------
    # Layer stack
    # ------------------------------------------------------------------

    def _render_layers(self, c: Any) -> None:
        """Render all visible layers."""
        for layer in self._canvas.layers:
            if not layer.visible and not self._proof:
                continue
            self._render_layer(c, layer)

    def _render_layer(self, c: Any, layer: Layer) -> None:
        """Render one layer's content elements."""
        if not layer.visible and not self._proof:
            return

        # Apply layer opacity by saving/restoring graphics state
        if layer.opacity < 1.0:
            c.saveState()
            # reportlab does not have direct group opacity, but we can set
            # the transparency on subsequent drawing calls
            # We approximate with setFillAlpha / setStrokeAlpha
            try:
                c.setFillAlpha(layer.opacity)
                c.setStrokeAlpha(layer.opacity)
            except AttributeError:
                pass  # older reportlab versions

        for el in layer.elements:
            self._render_element(c, el)

        if layer.opacity < 1.0:
            c.restoreState()

    # ------------------------------------------------------------------
    # Content element dispatch
    # ------------------------------------------------------------------

    def _render_element(self, c: Any, el: Any) -> None:
        from mdf.parser.mdf_parser import Group, ImageElement, ShapeElement, TextBlock

        if isinstance(el, ShapeElement):
            self._render_shape(c, el)
        elif isinstance(el, ImageElement):
            self._render_image(c, el)
        elif isinstance(el, TextBlock):
            self._render_text_block(c, el)
        elif isinstance(el, Group):
            for sub in el.elements:
                self._render_element(c, sub)

    # ------------------------------------------------------------------
    # Shape rendering
    # ------------------------------------------------------------------

    def _color_rgb(self, color_str: Optional[str]) -> tuple[float, float, float] | None:
        """Convert an MDF color string to (r, g, b) in [0,1], or None."""
        return _mdf_color_to_rgb(color_str, spot_colors=self._spot_colors)

    def _set_fill(self, c: Any, color_str: Optional[str]) -> bool:
        """Set fill color. Returns True if fill should be applied."""
        rgb = self._color_rgb(color_str)
        if rgb is None:
            return False
        c.setFillColorRGB(rgb[0], rgb[1], rgb[2])
        return True

    def _set_stroke(
        self,
        c: Any,
        color_str: Optional[str],
        width_str: Optional[str] = None,
    ) -> bool:
        """Set stroke color and optionally line width. Returns True if stroke should be applied."""
        if not color_str or color_str.lower() == "none":
            return False
        rgb = self._color_rgb(color_str)
        if rgb is None:
            return False
        c.setStrokeColorRGB(rgb[0], rgb[1], rgb[2])
        if width_str:
            try:
                w_pt = _length_to_pt(width_str, self._canvas.units)
            except Exception:
                try:
                    w_pt = float(width_str) * self._scale
                except (ValueError, TypeError):
                    w_pt = 0.5
            c.setLineWidth(max(0.0, w_pt))
        else:
            c.setLineWidth(0.5)
        return True

    def _render_shape(self, c: Any, shape: Any) -> None:
        """Render a primitive shape element."""
        tag = shape.tag
        attrs = shape.attrs

        has_fill   = self._set_fill(c, attrs.get("fill"))
        has_stroke = self._set_stroke(c, attrs.get("stroke"), attrs.get("stroke-width"))

        fill_flag   = 1 if has_fill   else 0
        stroke_flag = 1 if has_stroke else 0

        if not fill_flag and not stroke_flag:
            # Invisible element — nothing to draw, but set a default
            fill_flag = 1
            c.setFillColorRGB(0, 0, 0)

        c.saveState()

        if tag == "rect":
            self._render_rect(c, attrs, fill_flag, stroke_flag)
        elif tag == "circle":
            self._render_circle(c, attrs, fill_flag, stroke_flag)
        elif tag == "ellipse":
            self._render_ellipse(c, attrs, fill_flag, stroke_flag)
        elif tag == "line":
            self._render_line(c, attrs)
        elif tag in ("path", "shape"):
            self._render_path_el(c, attrs, fill_flag, stroke_flag)
        elif tag in ("polygon", "polyline"):
            self._render_poly(c, tag, attrs, fill_flag, stroke_flag)
        else:
            pass  # unknown primitive — skip

        c.restoreState()

    def _render_rect(self, c: Any, attrs: dict, fill: int, stroke: int) -> None:
        x = float(attrs.get("x", 0))
        y = float(attrs.get("y", 0))
        w = float(attrs.get("width", 0))
        h = float(attrs.get("height", 0))

        rx_raw = attrs.get("rx")
        ry_raw = attrs.get("ry")

        x_pt = self._x(x)
        # PDF rect: y is the bottom-left corner
        y_pt = self._y(y + h)
        w_pt = self._pt(w)
        h_pt = self._pt(h)

        if rx_raw or ry_raw:
            # Rounded rect via bezier path
            rx = self._pt(float(rx_raw or ry_raw or 0))
            ry = self._pt(float(ry_raw or rx_raw or 0))
            c.roundRect(x_pt, y_pt, w_pt, h_pt, min(rx, ry), fill=fill, stroke=stroke)
        else:
            c.rect(x_pt, y_pt, w_pt, h_pt, fill=fill, stroke=stroke)

    def _render_circle(self, c: Any, attrs: dict, fill: int, stroke: int) -> None:
        cx = float(attrs.get("cx", 0))
        cy = float(attrs.get("cy", 0))
        r  = float(attrs.get("r", 0))

        cx_pt = self._x(cx)
        cy_pt = self._y(cy)
        r_pt  = self._pt(r)

        c.circle(cx_pt, cy_pt, r_pt, fill=fill, stroke=stroke)

    def _render_ellipse(self, c: Any, attrs: dict, fill: int, stroke: int) -> None:
        cx = float(attrs.get("cx", 0))
        cy = float(attrs.get("cy", 0))
        rx = float(attrs.get("rx", 0))
        ry = float(attrs.get("ry", 0))

        cx_pt = self._x(cx)
        cy_pt = self._y(cy)
        rx_pt = self._pt(rx)
        ry_pt = self._pt(ry)

        c.ellipse(
            cx_pt - rx_pt, cy_pt - ry_pt,
            cx_pt + rx_pt, cy_pt + ry_pt,
            fill=fill, stroke=stroke,
        )

    def _render_line(self, c: Any, attrs: dict) -> None:
        x1 = float(attrs.get("x1", 0))
        y1 = float(attrs.get("y1", 0))
        x2 = float(attrs.get("x2", 0))
        y2 = float(attrs.get("y2", 0))

        stroke_col = attrs.get("stroke")
        width_raw  = attrs.get("stroke-width")
        if not self._set_stroke(c, stroke_col, width_raw):
            c.setStrokeColorRGB(0, 0, 0)
            c.setLineWidth(0.5)

        c.line(self._x(x1), self._y(y1), self._x(x2), self._y(y2))

    def _render_path_el(self, c: Any, attrs: dict, fill: int, stroke: int) -> None:
        d = attrs.get("d") or attrs.get("path", "")
        if not d:
            return

        # Build path in SVG (Y-down) coordinates, then transform to PDF (Y-up)
        p = c.beginPath()
        _apply_svg_path_pdf(p, d, self._w_pt, self._h_pt, self._scale)
        c.drawPath(p, fill=fill, stroke=stroke)

    def _render_poly(self, c: Any, tag: str, attrs: dict, fill: int, stroke: int) -> None:
        points_raw = attrs.get("points", "")
        nums = [float(v) for v in re.findall(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?", points_raw)]
        if len(nums) < 4:
            return

        p = c.beginPath()
        p.moveTo(self._x(nums[0]), self._y(nums[1]))
        for k in range(2, len(nums) - 1, 2):
            p.lineTo(self._x(nums[k]), self._y(nums[k + 1]))
        if tag == "polygon":
            p.close()
        c.drawPath(p, fill=fill, stroke=stroke)

    # ------------------------------------------------------------------
    # Image rendering
    # ------------------------------------------------------------------

    def _render_image(self, c: Any, image: Any) -> None:
        src = image.src or ""
        if not src or src.startswith("mdfx:") or src.startswith("fonts/"):
            return  # embedded assets not available in plain .mdf files

        x  = image.x  or 0.0
        y  = image.y  or 0.0
        w  = image.width  or self._canvas.width
        h  = image.height or self._canvas.height

        x_pt = self._x(x)
        w_pt = self._pt(w)
        h_pt = self._pt(h)
        # PDF image y: top-left of image in PDF coords
        y_pt = self._y(y) - h_pt  # PDF origin is bottom-left of image

        try:
            c.drawImage(src, x_pt, y_pt, width=w_pt, height=h_pt, preserveAspectRatio=True)
        except Exception:
            pass  # image not found or unsupported format — skip silently

    # ------------------------------------------------------------------
    # Text block rendering
    # ------------------------------------------------------------------

    def _render_text_block(self, c: Any, block: Any) -> None:
        if not block.paragraphs:
            return

        # Resolve placement
        x, y, w, h = self._resolve_text_placement(block)
        if w <= 0 or h <= 0:
            # Fallback: centred on canvas
            x = 0.0
            y = 0.0
            w = self._canvas.width
            h = self._canvas.height

        font_size_pt = self._parse_size_to_pt(block.size, 12.0)
        leading_pt   = self._parse_size_to_pt(block.leading, font_size_pt * 1.4)

        fill_rgb = self._color_rgb(block.color) or (0.0, 0.0, 0.0)
        c.setFillColorRGB(*fill_rgb)

        # Text alignment
        align = (block.text_align or "start").lower()

        x_pt  = self._x(x)
        # Start from top of the region; each line steps down
        y_start_pt = self._y(y)

        text_obj = c.beginText()
        text_obj.setFont("Helvetica", font_size_pt)
        text_obj.setLeading(leading_pt)
        text_obj.setFillColorRGB(*fill_rgb)

        # Position: PDF text y is the baseline, so shift down by leading
        text_obj.setTextOrigin(x_pt, y_start_pt - leading_pt)

        for para in block.paragraphs:
            plain = " ".join(para.plain_text.split())
            if not plain:
                text_obj.textLine("")
                continue

            if align in ("center", "middle"):
                text_width = c.stringWidth(plain, "Helvetica", font_size_pt)
                region_w_pt = self._pt(w)
                offset = max(0.0, (region_w_pt - text_width) / 2.0)
                text_obj.setTextOrigin(x_pt + offset, text_obj.getY())
                text_obj.textLine(plain)
                text_obj.setTextOrigin(x_pt, text_obj.getY())
            elif align in ("right", "end"):
                text_width = c.stringWidth(plain, "Helvetica", font_size_pt)
                region_w_pt = self._pt(w)
                offset = max(0.0, region_w_pt - text_width)
                text_obj.setTextOrigin(x_pt + offset, text_obj.getY())
                text_obj.textLine(plain)
                text_obj.setTextOrigin(x_pt, text_obj.getY())
            else:
                text_obj.textLine(plain)

            # Stop if we exceed the text box height
            if self._y(y) - text_obj.getY() > self._pt(h):
                break

        c.drawText(text_obj)

    def _resolve_text_placement(
        self, block: Any
    ) -> tuple[float, float, float, float]:
        """Return (x, y, width, height) in document units for a text block."""
        canvas = self._canvas
        region = getattr(block, "reflow_region", None)
        if region is None:
            return 0.0, 0.0, 0.0, 0.0

        def _pad(raw: Optional[str], fallback: float = 0.0) -> float:
            if not raw:
                return fallback
            try:
                return parse_length(raw, canvas.units)
            except Exception:
                try:
                    return float(raw)
                except (ValueError, TypeError):
                    return fallback

        uniform       = _pad(region.padding, 0.0)
        padding_top   = _pad(region.padding_top,    uniform)
        padding_right = _pad(region.padding_right,  uniform)
        padding_bottom = _pad(region.padding_bottom, uniform)
        padding_left  = _pad(region.padding_left,   uniform)

        if region.shape_ref == "canvas-boundary":
            x = padding_left
            y = padding_top
            w = canvas.width  - padding_left - padding_right
            h = canvas.height - padding_top  - padding_bottom
            return x, y, max(w, 0.0), max(h, 0.0)

        if region.shape:
            bbox = _path_bbox(region.shape)
            if bbox:
                bx, by, bw, bh = bbox
                x = bx + padding_left
                y = by + padding_top
                w = bw - padding_left - padding_right
                h = bh - padding_top  - padding_bottom
                return x, y, max(w, 0.0), max(h, 0.0)

        return 0.0, 0.0, 0.0, 0.0

    def _parse_size_to_pt(self, size_str: Optional[str], default: float = 12.0) -> float:
        """Parse a CSS font-size string to PDF points."""
        if not size_str:
            return default
        s = size_str.strip()
        try:
            if s.endswith("pt"):
                return float(s[:-2])
            if s.endswith("px"):
                return float(s[:-2]) * (72.0 / 96.0)
            if s.endswith("mm"):
                return float(s[:-2]) * (72.0 / 25.4)
            if s.endswith("cm"):
                return float(s[:-2]) * (720.0 / 25.4)
            if s.endswith("in"):
                return float(s[:-2]) * 72.0
            if s.endswith("em"):
                return float(s[:-2]) * default
            return float(s)
        except (ValueError, TypeError):
            return default

    # ------------------------------------------------------------------
    # Proof overlay
    # ------------------------------------------------------------------

    def _render_proof_overlay(self, c: Any) -> None:
        """Render proof marks (bleed, cuts, folds) as coloured dashed lines."""
        canvas = self._canvas

        c.saveState()

        # Bleed rectangle (red dashed)
        if canvas.bleed > 0:
            b_pt = self._pt(canvas.bleed)
            c.setStrokeColorRGB(1.0, 0.0, 0.0)
            c.setLineWidth(0.5)
            c.setDash([3, 3])
            c.rect(
                -b_pt, -b_pt,
                self._w_pt + 2 * b_pt,
                self._h_pt + 2 * b_pt,
                fill=0, stroke=1,
            )

        # Cut lines (green dashed)
        for cut in canvas.cut_lines:
            if cut.path:
                c.setStrokeColorRGB(0.0, 0.6, 0.0)
                c.setLineWidth(0.5)
                c.setDash([4, 2])
                p = c.beginPath()
                _apply_svg_path_pdf(p, cut.path, self._w_pt, self._h_pt, self._scale)
                c.drawPath(p, fill=0, stroke=1)

        # Fold lines (orange dashed)
        for fold in canvas.folds:
            if fold.path:
                c.setStrokeColorRGB(1.0, 0.6, 0.0)
                c.setLineWidth(0.5)
                c.setDash([6, 2, 1, 2])
                p = c.beginPath()
                _apply_svg_path_pdf(p, fold.path, self._w_pt, self._h_pt, self._scale)
                c.drawPath(p, fill=0, stroke=1)

        c.restoreState()


# ---------------------------------------------------------------------------
# PDF coordinate-space path helper
# ---------------------------------------------------------------------------

def _apply_svg_path_pdf(
    rl_path: Any,
    path_data: str,
    page_h_pt: float,
    page_h_doc: float,  # kept for signature compatibility; unused (we use direct transform)
    scale: float,
) -> None:
    """
    Parse SVG path data and apply it to a reportlab path, converting from
    SVG (Y-down, document units) to PDF (Y-up, points) coordinates.

    Parameters
    ----------
    rl_path:
        A reportlab path object (from ``canvas.beginPath()``).
    path_data:
        SVG ``d`` attribute string.
    page_h_pt:
        Page height in PDF points (used to flip the Y axis).
    page_h_doc:
        (Unused — kept for API symmetry.)
    scale:
        Document-unit-to-point scale factor.
    """
    def _sx(v: float) -> float:
        return v * scale

    def _sy(v: float) -> float:
        return page_h_pt - v * scale

    tokens = re.findall(
        r"[MLHVCSQTAZmlhvcsqtaz]"
        r"|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?",
        path_data,
    )

    cmd = "M"
    i = 0
    cx, cy = 0.0, 0.0
    start_x, start_y = 0.0, 0.0

    def _nums(n: int) -> list[float]:
        nonlocal i
        result: list[float] = []
        while len(result) < n and i < len(tokens):
            tok = tokens[i]
            if tok.isalpha():
                break
            try:
                result.append(float(tok))
                i += 1
            except ValueError:
                i += 1
        return result

    while i < len(tokens):
        tok = tokens[i]
        if tok.isalpha():
            cmd = tok
            i += 1
            continue

        if cmd == "M":
            ns = _nums(2)
            if len(ns) < 2:
                break
            cx, cy = ns[0], ns[1]
            start_x, start_y = cx, cy
            rl_path.moveTo(_sx(cx), _sy(cy))
            cmd = "L"

        elif cmd == "m":
            ns = _nums(2)
            if len(ns) < 2:
                break
            cx += ns[0]; cy += ns[1]
            start_x, start_y = cx, cy
            rl_path.moveTo(_sx(cx), _sy(cy))
            cmd = "l"

        elif cmd == "L":
            ns = _nums(2)
            if len(ns) < 2:
                break
            cx, cy = ns[0], ns[1]
            rl_path.lineTo(_sx(cx), _sy(cy))

        elif cmd == "l":
            ns = _nums(2)
            if len(ns) < 2:
                break
            cx += ns[0]; cy += ns[1]
            rl_path.lineTo(_sx(cx), _sy(cy))

        elif cmd == "H":
            ns = _nums(1)
            if not ns:
                break
            cx = ns[0]
            rl_path.lineTo(_sx(cx), _sy(cy))

        elif cmd == "h":
            ns = _nums(1)
            if not ns:
                break
            cx += ns[0]
            rl_path.lineTo(_sx(cx), _sy(cy))

        elif cmd == "V":
            ns = _nums(1)
            if not ns:
                break
            cy = ns[0]
            rl_path.lineTo(_sx(cx), _sy(cy))

        elif cmd == "v":
            ns = _nums(1)
            if not ns:
                break
            cy += ns[0]
            rl_path.lineTo(_sx(cx), _sy(cy))

        elif cmd == "C":
            ns = _nums(6)
            if len(ns) < 6:
                break
            rl_path.curveTo(
                _sx(ns[0]), _sy(ns[1]),
                _sx(ns[2]), _sy(ns[3]),
                _sx(ns[4]), _sy(ns[5]),
            )
            cx, cy = ns[4], ns[5]

        elif cmd == "c":
            ns = _nums(6)
            if len(ns) < 6:
                break
            rl_path.curveTo(
                _sx(cx + ns[0]), _sy(cy + ns[1]),
                _sx(cx + ns[2]), _sy(cy + ns[3]),
                _sx(cx + ns[4]), _sy(cy + ns[5]),
            )
            cx += ns[4]; cy += ns[5]

        elif cmd == "S":
            ns = _nums(4)
            if len(ns) < 4:
                break
            rl_path.curveTo(
                _sx(cx), _sy(cy),
                _sx(ns[0]), _sy(ns[1]),
                _sx(ns[2]), _sy(ns[3]),
            )
            cx, cy = ns[2], ns[3]

        elif cmd == "s":
            ns = _nums(4)
            if len(ns) < 4:
                break
            rl_path.curveTo(
                _sx(cx), _sy(cy),
                _sx(cx + ns[0]), _sy(cy + ns[1]),
                _sx(cx + ns[2]), _sy(cy + ns[3]),
            )
            cx += ns[2]; cy += ns[3]

        elif cmd == "Q":
            ns = _nums(4)
            if len(ns) < 4:
                break
            ax, ay = ns[0], ns[1]
            ex, ey = ns[2], ns[3]
            x1 = cx + 2 / 3 * (ax - cx)
            y1 = cy + 2 / 3 * (ay - cy)
            x2 = ex + 2 / 3 * (ax - ex)
            y2 = ey + 2 / 3 * (ay - ey)
            rl_path.curveTo(_sx(x1), _sy(y1), _sx(x2), _sy(y2), _sx(ex), _sy(ey))
            cx, cy = ex, ey

        elif cmd == "q":
            ns = _nums(4)
            if len(ns) < 4:
                break
            ax, ay = cx + ns[0], cy + ns[1]
            ex, ey = cx + ns[2], cy + ns[3]
            x1 = cx + 2 / 3 * (ax - cx)
            y1 = cy + 2 / 3 * (ay - cy)
            x2 = ex + 2 / 3 * (ax - ex)
            y2 = ey + 2 / 3 * (ay - ey)
            rl_path.curveTo(_sx(x1), _sy(y1), _sx(x2), _sy(y2), _sx(ex), _sy(ey))
            cx, cy = ex, ey

        elif cmd in ("A", "a"):
            ns = _nums(7)
            if len(ns) < 7:
                break
            if cmd == "A":
                cx, cy = ns[5], ns[6]
            else:
                cx += ns[5]; cy += ns[6]
            rl_path.lineTo(_sx(cx), _sy(cy))

        elif cmd in ("Z", "z"):
            rl_path.close()
            cx, cy = start_x, start_y

        else:
            i += 1
