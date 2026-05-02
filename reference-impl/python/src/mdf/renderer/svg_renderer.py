"""
MDF SVG Renderer

Converts a parsed MDFDocument to a self-contained SVG string.

SVG is the primary debug/preview renderer because:
- No C library dependencies (unlike Cairo)
- Opens in any browser
- Handles arbitrary shape boundaries natively via <clipPath>
- Preserves vector fidelity for any document unit

Usage::

    from mdf.parser import parse_file
    from mdf.renderer.svg_renderer import render_svg

    doc = parse_file("resume.mdf")
    svg = render_svg(doc)
    with open("resume.svg", "w") as f:
        f.write(svg)

    # Proof mode overlays bleed/cut/registration marks:
    svg_proof = render_svg(doc, proof=True)
"""

from __future__ import annotations

import html
import re
from typing import Any, Optional

from mdf.model.document import Canvas, Layer, MDFDocument


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_svg(doc: MDFDocument, proof: bool = False, canvas_index: int = 0) -> str:
    """
    Render a parsed MDFDocument to an SVG string.

    Parameters
    ----------
    doc:
        A fully parsed MDFDocument.
    proof:
        When True, overlays proof marks: bleed rectangle (dashed red),
        canvas boundary (dashed blue), cut lines (dashed green), and
        fold lines (dashed orange).
    canvas_index:
        Which canvas to render (0-based). Defaults to the first canvas.

    Returns
    -------
    str
        A well-formed SVG document as a UTF-8 string.

    Raises
    ------
    IndexError
        If canvas_index is out of range.
    ValueError
        If the document has no canvases.
    """
    if not doc.canvases:
        raise ValueError("Document has no canvases to render")
    if canvas_index >= len(doc.canvases):
        raise IndexError(
            f"canvas_index {canvas_index} out of range "
            f"(document has {len(doc.canvases)} canvas(es))"
        )

    canvas = doc.canvases[canvas_index]
    renderer = _SVGRenderer(doc, canvas, proof=proof)
    return renderer.render()


# ---------------------------------------------------------------------------
# Internal renderer
# ---------------------------------------------------------------------------


def _cmyk_to_rgb(c: float, m: float, y: float, k: float) -> tuple[int, int, int]:
    """Convert CMYK floats (0–1) to sRGB integers (0–255), simple device approximation."""
    r = 255.0 * (1.0 - c) * (1.0 - k)
    g = 255.0 * (1.0 - m) * (1.0 - k)
    b = 255.0 * (1.0 - y) * (1.0 - k)
    return int(round(r)), int(round(g)), int(round(b))


def _lab_to_rgb(L: float, a: float, b_val: float) -> tuple[int, int, int]:
    """
    Convert CIE L*a*b* to sRGB integers (0–255).

    Uses the D65 illuminant and sRGB primaries.  Values are clamped to the
    sRGB gamut after conversion; out-of-gamut Lab values are silently clipped.
    """
    # Lab → XYZ (D65)
    fy = (L + 16.0) / 116.0
    fx = a / 500.0 + fy
    fz = fy - b_val / 200.0

    def _f_inv(t: float) -> float:
        if t > 0.206897:
            return t ** 3
        return (t - 16.0 / 116.0) / 7.787

    x = _f_inv(fx) * 95.047
    y = _f_inv(fy) * 100.000
    z = _f_inv(fz) * 108.883

    # XYZ → linear sRGB
    x /= 100.0
    y /= 100.0
    z /= 100.0
    r_lin =  3.2406 * x - 1.5372 * y - 0.4986 * z
    g_lin = -0.9689 * x + 1.8758 * y + 0.0415 * z
    b_lin =  0.0557 * x - 0.2040 * y + 1.0570 * z

    # Gamma-encode (sRGB transfer function)
    def _gamma(c: float) -> float:
        c = max(0.0, min(1.0, c))
        if c <= 0.0031308:
            return 12.92 * c
        return 1.055 * (c ** (1.0 / 2.4)) - 0.055

    return (
        int(round(_gamma(r_lin) * 255.0)),
        int(round(_gamma(g_lin) * 255.0)),
        int(round(_gamma(b_lin) * 255.0)),
    )


# Regex patterns for MDF color notations (§4.2)
# color(cmyk C M Y K)
_CMYK_RE = re.compile(
    r"color\(\s*cmyk\s+"
    r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)",
    re.IGNORECASE,
)

# color(gray L)  — §4.2.6 grayscale
_GRAY_RE = re.compile(
    r"color\(\s*gray\s+([\d.]+)\s*\)",
    re.IGNORECASE,
)

# color(lab L a b)  — §4.2.4 CIE L*a*b*
_LAB_RE = re.compile(
    r"color\(\s*lab\s+"
    r"([\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\)",
    re.IGNORECASE,
)

# spot(id) or spot(id, tint)  — §4.2.5 spot color reference
_SPOT_RE = re.compile(
    r"spot\(\s*([A-Za-z0-9_-]+)\s*(?:,\s*([\d.]+))?\s*\)",
    re.IGNORECASE,
)

# rgba(r, g, b, a) — §4.2.2 with alpha
_RGBA_RE = re.compile(
    r"rgba\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)",
    re.IGNORECASE,
)


def _parse_color(
    color_str: Optional[str],
    spot_colors: Optional[dict] = None,
) -> str:
    """
    Convert an MDF color value to a CSS/SVG color string.

    Handles all MDF color notations (§4.2):
    - ``color(cmyk C M Y K)``   → approximate sRGB conversion for screen display
    - ``color(gray L)``         → grayscale percentage converted to sRGB
    - ``color(lab L a b)``      → CIE L*a*b* converted to sRGB (D65)
    - ``spot(id[, tint])``      → look up the spot color's CMYK approximation,
                                   apply tint, convert to sRGB
    - ``#rrggbb`` / ``#rrggbbaa`` / ``#rgb`` → passed through (SVG handles these)
    - ``rgb(r, g, b)``          → passed through
    - ``rgba(r, g, b, a)``      → converted to ``rgba()`` with SVG-compatible syntax
    - ``hsl(h, s%, l%)``        → passed through
    - ``none``                  → passed through unchanged
    - Named CSS colors          → passed through unchanged
    - Unknown / empty           → falls back to ``black``

    Parameters
    ----------
    color_str:
        The raw MDF color attribute value.
    spot_colors:
        Optional dict mapping spot color ids to
        :class:`~mdf.model.document.SpotColor` objects, used to resolve
        ``spot()`` references.  When ``None``, spot colors are approximated
        as a neutral 50% gray.
    """
    if not color_str:
        return "black"
    color_str = color_str.strip()

    # ── color(cmyk C M Y K) ───────────────────────────────────────────────
    m = _CMYK_RE.match(color_str)
    if m:
        c, mg, y, k = (float(m.group(i)) for i in range(1, 5))
        r, g, b = _cmyk_to_rgb(c, mg, y, k)
        return f"rgb({r},{g},{b})"

    # ── color(gray L) ─────────────────────────────────────────────────────
    m = _GRAY_RE.match(color_str)
    if m:
        L = float(m.group(1))
        # L is in [0.0, 1.0]; 0.0 = black, 1.0 = white
        v = int(round(max(0.0, min(1.0, L)) * 255.0))
        return f"rgb({v},{v},{v})"

    # ── color(lab L a b) ──────────────────────────────────────────────────
    m = _LAB_RE.match(color_str)
    if m:
        L_val = float(m.group(1))
        a_val = float(m.group(2))
        b_val = float(m.group(3))
        r, g, b_out = _lab_to_rgb(L_val, a_val, b_val)
        return f"rgb({r},{g},{b_out})"

    # ── spot(id[, tint]) ──────────────────────────────────────────────────
    m = _SPOT_RE.match(color_str)
    if m:
        spot_id = m.group(1)
        tint = float(m.group(2)) if m.group(2) else 1.0
        tint = max(0.0, min(1.0, tint))

        if spot_colors and spot_id in spot_colors:
            sc = spot_colors[spot_id]
            c, mg, y, k = sc.cmyk_approximation
            # Apply tint: tint 0.0 = no ink (white on coated), 1.0 = full ink
            c, mg, y, k = c * tint, mg * tint, y * tint, k * tint
            r, g, b = _cmyk_to_rgb(c, mg, y, k)
            return f"rgb({r},{g},{b})"
        else:
            # Unknown spot color — render as a neutral warm gray so the
            # document is still visually coherent (not magenta).
            v = int(round((1.0 - tint * 0.7) * 255.0))
            return f"rgb({v},{v},{v})"

    # ── rgba(r, g, b, a) ─────────────────────────────────────────────────
    # MDF rgba uses floats in [0,255] for rgb and [0,1] for alpha.
    # CSS rgba() accepts the same syntax — pass through unchanged.
    m = _RGBA_RE.match(color_str)
    if m:
        # Normalise: if r/g/b > 1 they are 0–255 integers; keep as-is.
        return color_str  # CSS rgba() is identical syntax

    # ── CSS-compatible pass-through ──────────────────────────────────────
    lower = color_str.lower()
    if (
        lower == "none"
        or color_str.startswith("#")
        or lower.startswith("rgb")
        or lower.startswith("hsl")
    ):
        return color_str

    # Named CSS color or unknown — SVG/browser will handle it
    return color_str


def _blend_mode_to_css(blend_mode: str) -> str:
    """Map an MDF blend-mode identifier to its CSS mix-blend-mode value."""
    _MAP: dict[str, str] = {
        "normal":      "normal",
        "multiply":    "multiply",
        "screen":      "screen",
        "overlay":     "overlay",
        "darken":      "darken",
        "lighten":     "lighten",
        "color-dodge": "color-dodge",
        "color-burn":  "color-burn",
        "hard-light":  "hard-light",
        "soft-light":  "soft-light",
        "difference":  "difference",
        "exclusion":   "exclusion",
        "hue":         "hue",
        "saturation":  "saturation",
        "color":       "color",
        "luminosity":  "luminosity",
    }
    return _MAP.get(blend_mode.lower(), "normal")


def _esc(text: str) -> str:
    """XML-escape a string for embedding in SVG attribute values or text content."""
    return html.escape(text, quote=True)


class _SVGRenderer:
    """
    Stateful renderer that builds an SVG string for a single canvas.

    The output SVG structure::

        <svg viewBox="0 0 W H" ...>
          <defs>
            <clipPath id="boundary-clip">
              <path d="..." clip-rule="evenodd"/>
            </clipPath>
          </defs>
          <rect fill="white" .../>         <!-- background -->
          <g clip-path="url(#boundary-clip)">
            <g id="layer-..." style="..."> <!-- one per layer -->
              ...                          <!-- content elements -->
            </g>
          </g>
          <g id="proof-overlay">...</g>    <!-- only when proof=True -->
        </svg>
    """

    def __init__(self, doc: MDFDocument, canvas: Canvas, proof: bool = False) -> None:
        self._doc = doc
        self._canvas = canvas
        self._proof = proof
        self._lines: list[str] = []
        # Spot color lookup dict — populated once from the manifest
        self._spot_colors: dict = doc.manifest.spot_colors if doc.manifest.spot_colors else {}

    def _color(self, color_str: Optional[str]) -> str:
        """Resolve an MDF color string to a CSS color, using the document's spot colors."""
        return _parse_color(color_str, spot_colors=self._spot_colors)

    # ------------------------------------------------------------------
    # Top-level render
    # ------------------------------------------------------------------

    def render(self) -> str:
        """Build and return the complete SVG string."""
        canvas = self._canvas
        w = canvas.width
        h = canvas.height
        unit_suffix = self._svg_unit(canvas.units)

        title = _esc(self._doc.manifest.title or "MDF Document")

        self._lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        self._lines.append(
            f'<svg xmlns="http://www.w3.org/2000/svg"'
            f' xmlns:xlink="http://www.w3.org/1999/xlink"'
            f' viewBox="0 0 {w:g} {h:g}"'
            f' width="{w:g}{unit_suffix}"'
            f' height="{h:g}{unit_suffix}"'
            f' role="img"'
            f' aria-label="{title}">'
        )

        self._render_defs()
        self._render_background()
        self._render_layers()

        if self._proof:
            self._render_proof_overlay()

        self._lines.append("</svg>")
        return "\n".join(self._lines)

    # ------------------------------------------------------------------
    # <defs>
    # ------------------------------------------------------------------

    def _render_defs(self) -> None:
        """Emit <defs> with the boundary clipPath."""
        canvas = self._canvas
        self._lines.append("  <defs>")
        self._lines.append('    <clipPath id="boundary-clip">')
        self._lines.append(
            f'      <path d="{_esc(canvas.boundary_path)}" clip-rule="evenodd"/>'
        )
        self._lines.append("    </clipPath>")
        self._lines.append("  </defs>")

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    def _render_background(self) -> None:
        """Emit a white background rect covering the full canvas."""
        canvas = self._canvas
        self._lines.append(
            f'  <rect x="0" y="0"'
            f' width="{canvas.width:g}" height="{canvas.height:g}"'
            f' fill="white"/>'
        )

    # ------------------------------------------------------------------
    # Layer stack
    # ------------------------------------------------------------------

    def _render_layers(self) -> None:
        """Emit the clipped group containing all visible layers."""
        self._lines.append('  <g clip-path="url(#boundary-clip)">')
        for layer in self._canvas.layers:
            if not layer.visible and not self._proof:
                continue
            self._render_layer(layer)
        self._lines.append("  </g>")

    def _render_layer(self, layer: Layer) -> None:
        """Emit one <g> element representing a single layer."""
        blend_css = _blend_mode_to_css(layer.blend_mode)
        style_parts = [f"mix-blend-mode:{blend_css}"]
        if layer.opacity < 1.0:
            style_parts.append(f"opacity:{layer.opacity:g}")
        if not layer.visible:
            style_parts.append("display:none")
        style = ";".join(style_parts)

        id_attr = f' id="layer-{_esc(layer.id)}"' if layer.id else ""
        self._lines.append(f'    <g{id_attr} style="{style}">')

        for el in layer.elements:
            self._render_element(el, indent="      ")

        self._lines.append("    </g>")

    # ------------------------------------------------------------------
    # Content element dispatch
    # ------------------------------------------------------------------

    def _render_element(self, el: Any, indent: str = "      ") -> None:
        """Dispatch to the correct element renderer based on type."""
        # Import here to keep renderer independent of parser at module level
        from mdf.parser.mdf_parser import Group, ImageElement, ShapeElement, TextBlock

        if isinstance(el, ShapeElement):
            self._render_shape(el, indent)
        elif isinstance(el, ImageElement):
            self._render_image(el, indent)
        elif isinstance(el, TextBlock):
            self._render_text_block(el, indent)
        elif isinstance(el, Group):
            gid_attr = f' id="{_esc(el.id)}"' if el.id else ""
            self._lines.append(f"{indent}<g{gid_attr}>")
            for sub in el.elements:
                self._render_element(sub, indent + "  ")
            self._lines.append(f"{indent}</g>")

    # ------------------------------------------------------------------
    # Shape elements
    # ------------------------------------------------------------------

    def _render_shape(self, shape: Any, indent: str) -> None:
        """
        Render a ShapeElement as an SVG primitive.

        The lxml-based parser stores the most important style attributes
        (fill, stroke, stroke-width, etc.) on named fields as well as in
        the flat ``attrs`` dict.  We pull colour values through _parse_color
        so that CMYK notation is converted to RGB for screen display.
        """
        tag = shape.tag

        # Build the SVG attribute string from the flat attrs dict,
        # converting MDF colour expressions to SVG-compatible values.
        attrs = dict(shape.attrs)

        for colour_key in ("fill", "stroke", "color"):
            if colour_key in attrs:
                attrs[colour_key] = self._color(attrs[colour_key])

        # 'd' is used by SVG for <path>; MDF may also spell it 'path'
        if tag == "path" and "path" in attrs and "d" not in attrs:
            attrs["d"] = attrs.pop("path")

        attr_str = " ".join(f'{k}="{_esc(v)}"' for k, v in attrs.items())
        self._lines.append(f"{indent}<{tag} {attr_str}/>")

    # ------------------------------------------------------------------
    # Image elements
    # ------------------------------------------------------------------

    def _render_image(self, image: Any, indent: str) -> None:
        """Render an ImageElement as an SVG <image>."""
        parts: list[str] = []
        if image.x is not None:
            parts.append(f'x="{image.x:g}"')
        if image.y is not None:
            parts.append(f'y="{image.y:g}"')
        if image.width is not None:
            parts.append(f'width="{image.width:g}"')
        if image.height is not None:
            parts.append(f'height="{image.height:g}"')
        if image.src:
            parts.append(f'href="{_esc(image.src)}"')
        if image.clip_path:
            parts.append(f'clip-path="{_esc(image.clip_path)}"')
        self._lines.append(f"{indent}<image {' '.join(parts)}/>")

    # ------------------------------------------------------------------
    # Text blocks
    # ------------------------------------------------------------------

    def _render_text_block(self, block: Any, indent: str) -> None:
        """
        Render a TextBlock into SVG.

        Strategy:
        1. Resolve the text-placement rectangle (x, y, w, h).
        2. If the rectangle is valid, use <foreignObject> + HTML <div> for
           proper word wrapping and multi-paragraph layout.
        3. Fall back to bare SVG <text>/<tspan> centred on the canvas when
           no usable rectangle is available.
        """
        fill        = self._color(block.color)
        font_family = self._resolve_font_family(block.font_ref)
        font_size   = self._parse_size_to_px(block.size, default=12.0)
        line_height = self._parse_size_to_px(block.leading, default=font_size * 1.4)

        if not block.paragraphs:
            return

        x, y, w, h = self._resolve_text_placement(block)

        if w > 0 and h > 0:
            self._render_text_foreign_object(
                block, x, y, w, h,
                fill, font_family, font_size, line_height, indent,
            )
        else:
            # Fallback: centred SVG text
            cx = self._canvas.width / 2.0
            cy = self._canvas.height / 2.0
            self._render_text_svg_fallback(
                block, cx, cy,
                fill, font_family, font_size, line_height, indent,
            )

    def _render_text_foreign_object(
        self,
        block: Any,
        x: float, y: float, w: float, h: float,
        fill: str,
        font_family: str,
        font_size: float,
        line_height: float,
        indent: str,
    ) -> None:
        """Emit a <foreignObject> containing an HTML block for text rendering."""
        text_align = _normalize_text_align(block.text_align)

        self._lines.append(
            f'{indent}<foreignObject'
            f' x="{x:g}" y="{y:g}"'
            f' width="{w:g}" height="{h:g}"'
            f' overflow="visible">'
        )
        self._lines.append(
            f'{indent}  <body xmlns="http://www.w3.org/1999/xhtml"'
            f' style="margin:0;padding:0;">'
        )
        self._lines.append(
            f'{indent}  <div style="'
            f'font-family:{_esc(font_family)};'
            f'font-size:{font_size:.2f}px;'
            f'line-height:{line_height:.2f}px;'
            f'color:{fill};'
            f'text-align:{text_align};'
            f'width:{w:g}px;'
            f'overflow:hidden;">'
        )

        for para in block.paragraphs:
            self._render_paragraph_html(para, block, font_family, font_size, fill, indent)

        self._lines.append(f"{indent}  </div>")
        self._lines.append(f"{indent}  </body>")
        self._lines.append(f"{indent}</foreignObject>")

    def _render_paragraph_html(
        self,
        para: Any,
        block: Any,
        parent_font_family: str,
        parent_font_size: float,
        parent_fill: str,
        indent: str,
    ) -> None:
        """Emit one HTML <p> element for a TextParagraph."""
        para_fill   = self._color(para.color) if para.color else parent_fill
        para_family = self._resolve_font_family(para.font_ref) if para.font_ref else parent_font_family
        para_size   = self._parse_size_to_px(para.size) if para.size else parent_font_size

        self._lines.append(
            f'{indent}    <p style="'
            f'margin:0;padding:0;'
            f'font-family:{_esc(para_family)};'
            f'font-size:{para_size:.2f}px;'
            f'color:{para_fill};">'
        )

        for span in para.spans:
            # Normalise whitespace: collapse internal runs, strip edges
            raw_text = " ".join(span.text.split())
            if not raw_text:
                continue

            span_parts: list[str] = []
            if span.color:
                span_parts.append(f"color:{self._color(span.color)}")
            if span.font_ref:
                span_parts.append(f"font-family:{_esc(self._resolve_font_family(span.font_ref))}")
            if span.size:
                sz = self._parse_size_to_px(span.size)
                span_parts.append(f"font-size:{sz:.2f}px")

            text_content = _esc(raw_text)
            if span_parts:
                style = ";".join(span_parts)
                self._lines.append(
                    f'{indent}      <span style="{style}">{text_content}</span>'
                )
            else:
                self._lines.append(f"{indent}      {text_content}")

        self._lines.append(f"{indent}    </p>")

    def _render_text_svg_fallback(
        self,
        block: Any,
        cx: float, cy: float,
        fill: str,
        font_family: str,
        font_size: float,
        line_height: float,
        indent: str,
    ) -> None:
        """Fallback: render text as SVG <text> with <tspan> children."""
        text_anchor = {
            "left":    "start",
            "start":   "start",
            "center":  "middle",
            "right":   "end",
            "end":     "end",
            "justify": "start",
        }.get((block.text_align or "start").lower(), "start")

        self._lines.append(
            f'{indent}<text'
            f' x="{cx:g}" y="{cy:g}"'
            f' font-family="{_esc(font_family)}"'
            f' font-size="{font_size:.2f}"'
            f' fill="{fill}"'
            f' text-anchor="{text_anchor}">'
        )
        dy = 0.0
        for para in block.paragraphs:
            # Collapse internal whitespace for clean SVG output
            plain = " ".join(para.plain_text.split())
            if not plain:
                dy += line_height
                continue
            para_fill = self._color(para.color) if para.color else fill
            self._lines.append(
                f'{indent}  <tspan x="{cx:g}" dy="{dy:.2f}"'
                f' fill="{para_fill}">{_esc(plain)}</tspan>'
            )
            dy = line_height
        self._lines.append(f"{indent}</text>")

    # ------------------------------------------------------------------
    # Proof overlay
    # ------------------------------------------------------------------

    def _render_proof_overlay(self) -> None:
        """Emit the proof marks overlay group."""
        canvas = self._canvas
        self._lines.append('  <g id="proof-overlay" style="pointer-events:none">')

        # Bleed rectangle (dashed red)
        if canvas.bleed > 0:
            b = canvas.bleed
            self._lines.append(
                f'    <rect'
                f' x="{-b:g}" y="{-b:g}"'
                f' width="{canvas.width + 2 * b:g}" height="{canvas.height + 2 * b:g}"'
                f' fill="none"'
                f' stroke="red" stroke-width="0.5"'
                f' stroke-dasharray="3 3" opacity="0.7"/>'
            )

        # Canvas boundary (dashed blue)
        if canvas.boundary_path:
            self._lines.append(
                f'    <path d="{_esc(canvas.boundary_path)}"'
                f' fill="none"'
                f' stroke="blue" stroke-width="0.5"'
                f' stroke-dasharray="5 2" opacity="0.8"/>'
            )

        # Cut lines (dashed green)
        for cut in canvas.cut_lines:
            if cut.path:
                self._lines.append(
                    f'    <path d="{_esc(cut.path)}"'
                    f' fill="none"'
                    f' stroke="green" stroke-width="0.5"'
                    f' stroke-dasharray="4 2" opacity="0.8"/>'
                )

        # Fold lines (dashed orange)
        for fold in canvas.folds:
            if fold.path:
                self._lines.append(
                    f'    <path d="{_esc(fold.path)}"'
                    f' fill="none"'
                    f' stroke="orange" stroke-width="0.5"'
                    f' stroke-dasharray="6 2 1 2" opacity="0.8"/>'
                )

        # Registration crosshairs
        if canvas.marks and canvas.marks.registration_marks:
            self._render_registration_marks()

        self._lines.append("  </g>")

    def _render_registration_marks(self) -> None:
        """Emit simplified crosshair registration marks at each canvas corner."""
        canvas = self._canvas
        offset = canvas.marks.registration_offset if canvas.marks else 8.0
        arm = 5.0  # half-arm length in document units

        corners = [
            (-offset,              -offset),
            (canvas.width + offset, -offset),
            (canvas.width + offset,  canvas.height + offset),
            (-offset,               canvas.height + offset),
        ]
        for cx, cy in corners:
            self._lines.append(
                f'    <line'
                f' x1="{cx - arm:g}" y1="{cy:g}"'
                f' x2="{cx + arm:g}" y2="{cy:g}"'
                f' stroke="black" stroke-width="0.25" opacity="0.6"/>'
            )
            self._lines.append(
                f'    <line'
                f' x1="{cx:g}" y1="{cy - arm:g}"'
                f' x2="{cx:g}" y2="{cy + arm:g}"'
                f' stroke="black" stroke-width="0.25" opacity="0.6"/>'
            )
            self._lines.append(
                f'    <circle'
                f' cx="{cx:g}" cy="{cy:g}" r="{arm * 0.6:g}"'
                f' fill="none" stroke="black" stroke-width="0.25" opacity="0.6"/>'
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _svg_unit(self, units: str) -> str:
        """Return the SVG unit suffix for a document unit string."""
        _KNOWN = {"mm", "cm", "in", "pt", "pc", "px"}
        u = units.lower().strip()
        return u if u in _KNOWN else "mm"

    def _resolve_font_family(self, font_ref: Optional[str]) -> str:
        """Resolve a font-ref ID to a CSS font-family string."""
        if not font_ref:
            return "sans-serif"
        font = self._doc.manifest.fonts.get(font_ref)
        return font.family if font else "sans-serif"

    def _parse_size_to_px(self, size_str: Optional[str], default: float = 12.0) -> float:
        """
        Parse a CSS font-size string to screen pixels.

        Conversions used (96 dpi screen reference):
          1 pt = 1.333 px   (96 / 72)
          1 mm ≈ 3.779 px   (96 / 25.4)
        """
        if not size_str:
            return default
        s = size_str.strip()
        _PT_PX = 96.0 / 72.0
        _MM_PX = 96.0 / 25.4
        try:
            if s.endswith("pt"):
                return float(s[:-2]) * _PT_PX
            if s.endswith("px"):
                return float(s[:-2])
            if s.endswith("mm"):
                return float(s[:-2]) * _MM_PX
            if s.endswith("cm"):
                return float(s[:-2]) * _MM_PX * 10.0
            if s.endswith("em"):
                return float(s[:-2]) * default
            return float(s)
        except (ValueError, TypeError):
            return default

    def _resolve_text_placement(
        self, block: Any
    ) -> tuple[float, float, float, float]:
        """
        Return (x, y, width, height) in document units for a text block.

        Priority:
        1. reflow-region with ``shape-ref="canvas-boundary"`` → inset by padding.
        2. reflow-region with an explicit ``shape`` path → bbox of that path.
        3. No usable rectangle → return (0, 0, 0, 0) for SVG <text> fallback.
        """
        canvas = self._canvas
        region = getattr(block, "reflow_region", None)
        if region is None:
            return 0.0, 0.0, 0.0, 0.0

        # Parse padding values (stored as raw strings by the new parser)
        from mdf.parser.unit_converter import parse_length as _pl

        def _pad(raw: Optional[str], fallback: float = 0.0) -> float:
            if not raw:
                return fallback
            try:
                return _pl(raw, canvas.units)
            except Exception:
                try:
                    return float(raw)
                except (ValueError, TypeError):
                    return fallback

        # Uniform padding
        uniform = _pad(region.padding, 0.0)
        padding_top    = _pad(region.padding_top,    uniform)
        padding_right  = _pad(region.padding_right,  uniform)
        padding_bottom = _pad(region.padding_bottom, uniform)
        padding_left   = _pad(region.padding_left,   uniform)

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_text_align(align: str) -> str:
    """Map MDF text-align values to CSS text-align values."""
    _MAP = {
        "start":   "left",
        "end":     "right",
        "left":    "left",
        "right":   "right",
        "center":  "center",
        "justify": "justify",
    }
    return _MAP.get((align or "start").lower(), "left")


def _path_bbox(path_data: str) -> Optional[tuple[float, float, float, float]]:
    """
    Estimate the axis-aligned bounding box of an SVG path.

    Handles M, L, H, V, Z (and their lowercase relative equivalents) exactly.
    For curve commands (C, S, Q, T, A) the endpoint coordinate is recorded
    as a conservative approximation — this is accurate enough for rectangular
    reflow regions but may underestimate the true bounds of complex curves.

    Returns ``(x, y, width, height)`` or ``None`` if no coordinates found.
    """
    xs: list[float] = []
    ys: list[float] = []

    tokens = re.findall(
        r"[MLHVCSQTAZmlhvcsqtaz]"
        r"|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?",
        path_data,
    )

    cmd = ""
    i = 0
    cx, cy = 0.0, 0.0   # current pen position
    start_x, start_y = 0.0, 0.0  # for Z close-path

    def _num() -> Optional[float]:
        nonlocal i
        while i < len(tokens) and (tokens[i].isalpha() and len(tokens[i]) == 1):
            return None
        if i < len(tokens):
            try:
                v = float(tokens[i])
                i += 1
                return v
            except ValueError:
                return None
        return None

    while i < len(tokens):
        tok = tokens[i]
        if tok.isalpha():
            cmd = tok
            i += 1
            continue

        if cmd in ("M", "L"):
            x, y = _num(), _num()
            if x is None or y is None:
                break
            cx, cy = x, y
            xs.append(cx); ys.append(cy)
            if cmd == "M":
                start_x, start_y = cx, cy
                cmd = "L"
        elif cmd in ("m", "l"):
            dx, dy = _num(), _num()
            if dx is None or dy is None:
                break
            cx += dx; cy += dy
            xs.append(cx); ys.append(cy)
            if cmd == "m":
                start_x, start_y = cx, cy
                cmd = "l"
        elif cmd == "H":
            x = _num()
            if x is None:
                break
            cx = x; xs.append(cx)
        elif cmd == "h":
            dx = _num()
            if dx is None:
                break
            cx += dx; xs.append(cx)
        elif cmd == "V":
            y = _num()
            if y is None:
                break
            cy = y; ys.append(cy)
        elif cmd == "v":
            dy = _num()
            if dy is None:
                break
            cy += dy; ys.append(cy)
        elif cmd in ("C",):
            # 3 coord pairs: control1, control2, endpoint
            nums = [_num() for _ in range(6)]
            if any(n is None for n in nums):
                break
            for k in range(0, 6, 2):
                xs.append(nums[k])      # type: ignore[arg-type]
                ys.append(nums[k + 1])  # type: ignore[arg-type]
            cx, cy = nums[4], nums[5]  # type: ignore[assignment]
        elif cmd in ("c",):
            nums = [_num() for _ in range(6)]
            if any(n is None for n in nums):
                break
            cx += nums[4]; cy += nums[5]  # type: ignore[operator]
            xs.append(cx); ys.append(cy)
        elif cmd in ("S", "Q"):
            nums = [_num() for _ in range(4)]
            if any(n is None for n in nums):
                break
            cx, cy = nums[2], nums[3]  # type: ignore[assignment]
            xs.append(cx); ys.append(cy)
        elif cmd in ("s", "q"):
            nums = [_num() for _ in range(4)]
            if any(n is None for n in nums):
                break
            cx += nums[2]; cy += nums[3]  # type: ignore[operator]
            xs.append(cx); ys.append(cy)
        elif cmd in ("A",):
            # rx ry x-rot large-arc sweep x y
            nums = [_num() for _ in range(7)]
            if any(n is None for n in nums):
                break
            cx, cy = nums[5], nums[6]  # type: ignore[assignment]
            xs.append(cx); ys.append(cy)
        elif cmd in ("a",):
            nums = [_num() for _ in range(7)]
            if any(n is None for n in nums):
                break
            cx += nums[5]; cy += nums[6]  # type: ignore[operator]
            xs.append(cx); ys.append(cy)
        elif cmd in ("Z", "z"):
            cx, cy = start_x, start_y
            break
        else:
            i += 1  # unknown command token — skip

    if not xs or not ys:
        return None

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return min_x, min_y, max_x - min_x, max_y - min_y
