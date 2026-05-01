"""
MDF XML Parser

Parses both plain ``.mdf`` files (UTF-8 XML) and ``.mdfx`` bundle archives
(ZIP64) into an in-memory :class:`~mdf.model.document.MDFDocument` object
tree.

Namespace URIs used in MDF 0.1:
  default/core:  https://morphousdoc.org/ns/0.1
  print:         https://morphousdoc.org/ns/print/0.1
  sem:           https://morphousdoc.org/ns/semantics/0.1
  meta:          https://morphousdoc.org/ns/meta/0.1

The parser uses ``lxml.etree`` for robust namespace support and XML
validation.  It is intentionally lenient about unknown elements and
attributes — they are logged at DEBUG level and skipped so that forward-
compatible documents continue to load.

Usage::

    from mdf.parser import parse_file, parse_string

    doc = parse_file("design.mdf")
    doc = parse_file("bundle.mdfx")
    doc = parse_string(open("design.mdf").read())
"""

from __future__ import annotations

import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from lxml import etree

from mdf.model.document import (
    Canvas,
    CutLine,
    FoldLine,
    FontAsset,
    ICCProfileAsset,
    Layer,
    Manifest,
    MDFDocument,
    PrintIntent,
    PrintMarks,
    SpotColor,
)
from mdf.parser.unit_converter import UnitConversionError, parse_length, strip_units

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Namespace constants
# ---------------------------------------------------------------------------

NS_DEFAULT = "https://morphousdoc.org/ns/0.1"
NS_PRINT   = "https://morphousdoc.org/ns/print/0.1"
NS_SEM     = "https://morphousdoc.org/ns/semantics/0.1"
NS_META    = "https://morphousdoc.org/ns/meta/0.1"

# Clark-notation tag builders
_D = lambda local: f"{{{NS_DEFAULT}}}{local}"   # noqa: E731  default ns
_P = lambda local: f"{{{NS_PRINT}}}{local}"     # noqa: E731  print ns
_S = lambda local: f"{{{NS_SEM}}}{local}"       # noqa: E731  semantics ns
_M = lambda local: f"{{{NS_META}}}{local}"      # noqa: E731  meta ns


# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------

class MDFParseError(Exception):
    """Raised when an MDF document is structurally invalid and cannot be parsed."""


# ---------------------------------------------------------------------------
# Content element dataclasses
#
# The top-level model (mdf.model.document) defines Canvas/Layer/etc. but
# deliberately leaves Layer.elements as list[Any].  These dataclasses fill
# that list with typed, renderer-agnostic objects.
# ---------------------------------------------------------------------------

@dataclass
class ShapeElement:
    """A primitive SVG-style shape element (``<circle>``, ``<line>``, etc.)."""
    tag: str                              # local tag name: circle, rect, line, …
    id: Optional[str] = None
    path: Optional[str] = None           # 'd' / 'path' attribute if present
    fill: Optional[str] = None
    stroke: Optional[str] = None
    stroke_width: Optional[str] = None
    stroke_dasharray: Optional[str] = None
    attrs: dict[str, str] = field(default_factory=dict)  # all other bare attrs


@dataclass
class ImageElement:
    """An ``<image>`` element within a layer."""
    id: Optional[str] = None
    src: str = ""
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    clip_path: Optional[str] = None


@dataclass
class Group:
    """A ``<group>`` element containing nested content elements."""
    id: Optional[str] = None
    elements: list[Any] = field(default_factory=list)


@dataclass
class ReflowRegion:
    """A ``<reflow-region>`` element — defines the shape text flows inside."""
    shape: Optional[str] = None          # inline SVG path data
    shape_ref: Optional[str] = None      # ID ref, e.g. "canvas-boundary"
    padding: Optional[str] = None        # uniform padding (raw string kept for renderer)
    padding_top: Optional[str] = None
    padding_right: Optional[str] = None
    padding_bottom: Optional[str] = None
    padding_left: Optional[str] = None


@dataclass
class TextSpan:
    """An inline ``<span>`` element with optional style overrides."""
    text: str = ""
    font_ref: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    style: Optional[str] = None


@dataclass
class TextParagraph:
    """A ``<p>`` element inside a ``<text-block>``."""
    spans: list[TextSpan] = field(default_factory=list)
    font_ref: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None

    @property
    def plain_text(self) -> str:
        """Concatenated text of all child spans."""
        return "".join(s.text for s in self.spans)


@dataclass
class TextBlock:
    """A ``<text-block>`` element — shaped text container with reflow."""
    id: Optional[str] = None
    font_ref: Optional[str] = None
    size: Optional[str] = None
    leading: Optional[str] = None
    language: str = "und"
    text_align: str = "start"
    direction: str = "ltr"
    color: Optional[str] = None
    column_count: int = 1
    column_gap: Optional[str] = None
    reflow_region: Optional[ReflowRegion] = None
    paragraphs: list[TextParagraph] = field(default_factory=list)

    @property
    def plain_text(self) -> str:
        """All paragraph text joined with newlines."""
        return "\n".join(p.plain_text for p in self.paragraphs)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _local(el: etree._Element) -> str:
    """Return the local (namespace-stripped) tag name of *el*."""
    tag = el.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}", 1)[1]
    return str(tag)


def _ns_of(el: etree._Element) -> str:
    """Return the namespace URI of *el*, or empty string."""
    tag = el.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}", 1)[0][1:]
    return ""


def _get(el: etree._Element, local: str, ns: str = NS_DEFAULT,
         default: Optional[str] = None) -> Optional[str]:
    """Get an attribute by (namespace, local-name), falling back to bare name."""
    clark = f"{{{ns}}}{local}" if ns else local
    v = el.get(clark)
    if v is None:
        v = el.get(local)
    return v if v is not None else default


def _bool(el: etree._Element, local: str, ns: str = NS_DEFAULT,
          default: bool = False) -> bool:
    """Parse a boolean attribute (``"true"``/``"false"``)."""
    raw = _get(el, local, ns)
    if raw is None:
        return default
    return raw.strip().lower() in ("true", "1", "yes")


def _float(el: etree._Element, local: str, ns: str = NS_DEFAULT,
           default: float = 0.0) -> float:
    """Parse a float attribute, returning *default* on failure."""
    raw = _get(el, local, ns)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        log.debug("Expected float for %r, got %r; using %s", local, raw, default)
        return default


def _length(value: Optional[str], target_units: str = "mm",
            default: float = 0.0, context: str = "") -> float:
    """Parse a CSS/SVG length string into *target_units*.

    Returns *default* (with a debug-level log) if parsing fails.
    """
    if not value:
        return default
    try:
        return parse_length(value, target_units)
    except UnitConversionError as exc:
        log.debug("Could not parse length %r%s: %s", value,
                  f" ({context})" if context else "", exc)
        return default


def _child_text(parent: etree._Element, clark_tag: str) -> Optional[str]:
    """Return stripped text of the first matching child element, or None."""
    child = parent.find(clark_tag)
    if child is not None and child.text:
        return child.text.strip() or None
    return None


# ---------------------------------------------------------------------------
# Manifest parsing
# ---------------------------------------------------------------------------

def _parse_font_asset(el: etree._Element) -> FontAsset:
    """Parse a ``<font>`` asset element."""
    fid = el.get("id", "")
    if not fid:
        raise MDFParseError("<font> element missing required 'id' attribute")
    weight_raw = el.get("weight", "400")
    try:
        weight = int(weight_raw)
    except ValueError:
        log.debug("Non-integer font weight %r; defaulting to 400", weight_raw)
        weight = 400
    return FontAsset(
        id=fid,
        family=el.get("family", ""),
        weight=weight,
        style=el.get("style", "normal"),
        src=el.get("src", ""),
        format=el.get("format", "woff2"),
        embed=(el.get("embed", "false") or "").lower() in ("true", "1"),
    )


def _parse_icc_profile(el: etree._Element) -> ICCProfileAsset:
    """Parse an ``<icc-profile>`` asset element."""
    iid = el.get("id", "")
    if not iid:
        raise MDFParseError("<icc-profile> element missing required 'id' attribute")
    return ICCProfileAsset(id=iid, src=el.get("src", ""))


def _parse_spot_color(el: etree._Element) -> SpotColor:
    """Parse a ``<spot-color>`` asset element."""
    sid = el.get("id", "")
    if not sid:
        raise MDFParseError("<spot-color> element missing required 'id' attribute")
    cmyk_raw = el.get("cmyk", "0 0 0 1")
    try:
        parts = [float(v) for v in cmyk_raw.split()]
        cmyk: tuple[float, float, float, float] = tuple(parts[:4])  # type: ignore[assignment]
        if len(cmyk) < 4:
            raise ValueError
    except (ValueError, TypeError):
        cmyk = (0.0, 0.0, 0.0, 1.0)

    lab: Optional[tuple[float, float, float]] = None
    lab_raw = el.get("lab")
    if lab_raw:
        try:
            lp = [float(v) for v in lab_raw.split()]
            if len(lp) >= 3:
                lab = (lp[0], lp[1], lp[2])
        except (ValueError, TypeError):
            pass

    return SpotColor(
        id=sid,
        name=el.get("name", sid),
        cmyk_approximation=cmyk,
        lab=lab,
        plate_name=el.get("plate-name"),
    )


def _parse_print_intent(el: etree._Element) -> PrintIntent:
    """Parse a ``<print:intent>`` element."""
    substrate   = _child_text(el, _P("substrate")) or "coated"
    color_mode  = _child_text(el, _P("color-mode")) or "cmyk"
    press_type  = _child_text(el, _P("press-type"))

    res_el = el.find(_P("resolution"))
    resolution = "300dpi"
    if res_el is not None:
        resolution = res_el.get("target", "300dpi")

    icc_ref: Optional[str] = None
    icc_el = el.find(_P("icc-profile-ref"))
    if icc_el is not None:
        icc_ref = icc_el.get("ref") or (icc_el.text or "").strip() or None

    return PrintIntent(
        substrate=substrate,
        color_mode=color_mode,
        icc_profile_ref=icc_ref,
        resolution_target=resolution,
        press_type=press_type or None,
    )


def _parse_manifest(manifest_el: etree._Element) -> Manifest:
    """Parse the ``<manifest>`` element into a :class:`~mdf.model.document.Manifest`."""
    manifest = Manifest()

    manifest.title   = _child_text(manifest_el, _M("title"))
    manifest.author  = _child_text(manifest_el, _M("author"))
    manifest.created = _child_text(manifest_el, _M("created"))
    lang = _child_text(manifest_el, _M("language"))
    if lang:
        manifest.language = lang

    # <conformance level="print"/>
    conf_el = manifest_el.find(_D("conformance"))
    if conf_el is not None:
        level_str = (conf_el.get("level") or "1").lower()
        level_map = {"basic": 1, "1": 1, "print": 2, "2": 2, "full": 3, "3": 3}
        manifest.conformance_level = level_map.get(level_str, 1)

    # <assets> block
    assets_el = manifest_el.find(_D("assets"))
    if assets_el is not None:
        for child in assets_el:
            local_tag = _local(child)
            if local_tag == "font":
                try:
                    f = _parse_font_asset(child)
                    manifest.fonts[f.id] = f
                except MDFParseError as exc:
                    log.warning("Skipping malformed <font>: %s", exc)
            elif local_tag == "icc-profile":
                try:
                    icc = _parse_icc_profile(child)
                    manifest.icc_profiles[icc.id] = icc
                except MDFParseError as exc:
                    log.warning("Skipping malformed <icc-profile>: %s", exc)
            elif local_tag == "spot-color":
                try:
                    sc = _parse_spot_color(child)
                    manifest.spot_colors[sc.id] = sc
                except MDFParseError as exc:
                    log.warning("Skipping malformed <spot-color>: %s", exc)
            else:
                log.debug("Unknown asset element <%s>; skipping", local_tag)

    # <print:intent>
    intent_el = manifest_el.find(_P("intent"))
    if intent_el is not None:
        manifest.print_intent = _parse_print_intent(intent_el)

    return manifest


# ---------------------------------------------------------------------------
# Print-geometry helpers
# ---------------------------------------------------------------------------

def _parse_print_marks(marks_el: etree._Element) -> PrintMarks:
    """Parse a ``<print:marks>`` element."""
    pm = PrintMarks()

    reg_el = marks_el.find(_P("registration-marks"))
    if reg_el is not None:
        pm.registration_marks = True
        pm.registration_style = reg_el.get("style", "crosshair")
        pm.registration_offset = _length(reg_el.get("offset", "8mm"),
                                          context="registration offset", default=8.0)

    crop_el = marks_el.find(_P("crop-marks"))
    if crop_el is not None:
        pm.crop_marks = True
        pm.crop_mark_length = _length(crop_el.get("length", "5mm"), default=5.0,
                                       context="crop-mark length")
        # weight is a line thickness — keep it in pt for the renderer
        pm.crop_mark_weight = _length(crop_el.get("weight", "0.25pt"), "pt", 0.25,
                                       "crop-mark weight")
        pm.crop_mark_offset = _length(crop_el.get("offset", "3mm"), default=3.0,
                                       context="crop-mark offset")

    if marks_el.find(_P("color-bar")) is not None:
        pm.color_bar = True

    return pm


# ---------------------------------------------------------------------------
# Canvas parsing
# ---------------------------------------------------------------------------

def _parse_canvas(canvas_el: etree._Element) -> Canvas:
    """Parse a ``<canvas>`` element into a :class:`~mdf.model.document.Canvas`."""
    units = canvas_el.get("units", "mm")

    # ---- required: width / height ----------------------------------------
    def _dim(attr: str) -> float:
        raw = canvas_el.get(attr)
        if raw is None:
            raise MDFParseError(
                f"<canvas> is missing required attribute '{attr}'"
            )
        try:
            numeric, src_unit = strip_units(raw)
        except UnitConversionError as exc:
            raise MDFParseError(
                f"<canvas> attribute '{attr}' = {raw!r} cannot be parsed: {exc}"
            ) from exc
        # If the embedded unit differs from the canvas unit, convert.
        if src_unit and src_unit != units:
            return parse_length(raw, units)
        return numeric

    width  = _dim("width")
    height = _dim("height")

    # ---- required: boundary path -----------------------------------------
    boundary = canvas_el.get("boundary")
    if not boundary:
        # Fall back to a full-canvas rectangle so we can still parse the rest.
        boundary = f"M 0,0 L {width},0 L {width},{height} L 0,{height} Z"
        log.warning("<canvas> missing 'boundary' attribute; defaulting to bounding-box rectangle")

    canvas = Canvas(
        id=canvas_el.get("id"),
        width=width,
        height=height,
        units=units,
        boundary_path=boundary,
    )

    # ---- print namespace attributes --------------------------------------
    canvas.die_cut = _bool(canvas_el, "die-cut", NS_PRINT)
    canvas.die_cut_type = (
        _get(canvas_el, "die-cut-type", NS_PRINT) or "cut"
    )
    bleed_raw = _get(canvas_el, "bleed", NS_PRINT)
    if bleed_raw:
        canvas.bleed = _length(bleed_raw, units, context="bleed")

    # ---- semantics namespace attributes ---------------------------------
    canvas.shape_type        = _get(canvas_el, "shape-type", NS_SEM)
    canvas.shape_meaning     = _get(canvas_el, "shape-meaning", NS_SEM)
    canvas.shape_meaning_iri = _get(canvas_el, "shape-meaning-iri", NS_SEM)

    # ---- child elements -------------------------------------------------
    for child in canvas_el:
        local_tag = _local(child)
        child_ns  = _ns_of(child)

        if local_tag == "marks" and child_ns == NS_PRINT:
            canvas.marks = _parse_print_marks(child)
        elif local_tag == "cut-line":
            cid  = child.get("id", "")
            path = child.get("path") or child.get("d", "")
            canvas.cut_lines.append(CutLine(
                id=cid,
                path=path,
                cut_type=child.get("type", "cut"),
            ))
        elif local_tag == "fold":
            canvas.folds.append(FoldLine(
                id=child.get("id", ""),
                path=child.get("path") or child.get("d", ""),
                fold_type=child.get("type", "valley"),
                angle=_float(child, "angle", default=180.0, ns=""),
            ))
        elif local_tag == "layers" and child_ns == NS_DEFAULT:
            for layer_el in child:
                if _local(layer_el) == "layer":
                    canvas.layers.append(_parse_layer(layer_el))
        elif local_tag == "layer" and child_ns == NS_DEFAULT:
            # Tolerate <layer> as direct <canvas> children (non-standard)
            canvas.layers.append(_parse_layer(child))
        # All other children (including unknown namespaces) are silently ignored.

    return canvas


# ---------------------------------------------------------------------------
# Layer parsing
# ---------------------------------------------------------------------------

def _parse_layer(layer_el: etree._Element) -> Layer:
    """Parse a ``<layer>`` element."""
    opacity_raw = layer_el.get("opacity", "1")
    try:
        opacity = float(opacity_raw)
    except ValueError:
        log.debug("Invalid opacity %r; defaulting to 1.0", opacity_raw)
        opacity = 1.0

    layer = Layer(
        id=layer_el.get("id"),
        blend_mode=layer_el.get("blend-mode", "normal"),
        opacity=opacity,
        visible=(layer_el.get("visible", "true") or "true").lower() not in ("false", "0"),
        lock=(layer_el.get("lock", "false") or "false").lower() in ("true", "1"),
        print_role=_get(layer_el, "print-role", NS_PRINT),
        visible_in_render=(
            (layer_el.get("visible-in-render", "true") or "true").lower()
            not in ("false", "0")
        ),
    )

    layer.elements = _parse_content_children(layer_el)
    return layer


# ---------------------------------------------------------------------------
# Content element parsing
# ---------------------------------------------------------------------------

_PRIMITIVE_SHAPES = frozenset({
    "shape", "circle", "ellipse", "rect", "line",
    "polyline", "polygon", "path",
})


def _parse_content_children(parent: etree._Element) -> list[Any]:
    """Return a list of parsed content elements from *parent*'s children."""
    result: list[Any] = []
    for child in parent:
        child_ns  = _ns_of(child)
        local_tag = _local(child)

        # Only process elements in the default MDF namespace (or bare names)
        if child_ns and child_ns != NS_DEFAULT:
            log.debug("Skipping element in foreign namespace <%s>", child.tag)
            continue

        if local_tag == "text-block":
            result.append(_parse_text_block(child))
        elif local_tag == "image":
            result.append(_parse_image(child))
        elif local_tag == "group":
            result.append(_parse_group(child))
        elif local_tag in _PRIMITIVE_SHAPES:
            result.append(_parse_shape_element(child, local_tag))
        else:
            log.debug("Unknown content element <%s>; skipping", local_tag)

    return result


def _parse_shape_element(el: etree._Element, local_tag: str) -> ShapeElement:
    """Parse a primitive shape element (``<circle>``, ``<line>``, etc.)."""
    # Collect all plain (non-namespaced) attributes
    flat: dict[str, str] = {}
    for k, v in el.attrib.items():
        if k.startswith("{"):
            ns_uri, bare = k[1:].split("}", 1)
            if ns_uri == NS_DEFAULT:
                flat[bare] = v
            # else skip foreign-namespace attributes
        else:
            flat[k] = v

    return ShapeElement(
        tag=local_tag,
        id=flat.get("id"),
        path=flat.get("d") or flat.get("path"),
        fill=flat.get("fill"),
        stroke=flat.get("stroke"),
        stroke_width=flat.get("stroke-width"),
        stroke_dasharray=flat.get("stroke-dasharray"),
        attrs=flat,
    )


def _parse_image(el: etree._Element) -> ImageElement:
    """Parse an ``<image>`` element."""
    def _opt_float(attr: str) -> Optional[float]:
        raw = el.get(attr)
        if raw is None:
            return None
        try:
            numeric, _ = strip_units(raw)
            return numeric
        except UnitConversionError:
            return None

    return ImageElement(
        id=el.get("id"),
        src=el.get("src", ""),
        x=_opt_float("x"),
        y=_opt_float("y"),
        width=_opt_float("width"),
        height=_opt_float("height"),
        clip_path=el.get("clip-path"),
    )


def _parse_group(el: etree._Element) -> Group:
    """Parse a ``<group>`` element, recursively parsing its children."""
    return Group(
        id=el.get("id"),
        elements=_parse_content_children(el),
    )


def _collect_text(el: etree._Element) -> str:
    """Flatten all text and tail content of *el* and its descendants."""
    parts: list[str] = []
    if el.text:
        parts.append(el.text)
    for child in el:
        parts.append(_collect_text(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _parse_span(el: etree._Element) -> TextSpan:
    """Parse a ``<span>`` element."""
    return TextSpan(
        text=_collect_text(el),
        font_ref=el.get("font-ref"),
        size=el.get("size"),
        color=el.get("color"),
        style=el.get("style"),
    )


def _parse_paragraph(el: etree._Element) -> TextParagraph:
    """Parse a ``<p>`` element with optional inline ``<span>`` children."""
    para = TextParagraph(
        font_ref=el.get("font-ref"),
        size=el.get("size"),
        color=el.get("color"),
    )

    # Text that precedes the first child element
    if el.text and el.text.strip():
        para.spans.append(TextSpan(
            text=el.text,
            font_ref=el.get("font-ref"),
            size=el.get("size"),
            color=el.get("color"),
        ))

    for child in el:
        if _local(child) == "span":
            span = _parse_span(child)
            if span.text:
                para.spans.append(span)
        # Tail text (text between the end of this child and the next sibling)
        if child.tail:
            para.spans.append(TextSpan(text=child.tail))

    # Paragraph with no child elements: direct text content
    if not para.spans:
        full_text = _collect_text(el)
        if full_text.strip():
            para.spans.append(TextSpan(
                text=full_text,
                font_ref=el.get("font-ref"),
                size=el.get("size"),
                color=el.get("color"),
            ))

    return para


def _parse_reflow_region(el: etree._Element) -> ReflowRegion:
    """Parse a ``<reflow-region>`` element."""
    return ReflowRegion(
        shape=el.get("shape"),
        shape_ref=el.get("shape-ref"),
        padding=el.get("padding"),
        padding_top=el.get("padding-top"),
        padding_right=el.get("padding-right"),
        padding_bottom=el.get("padding-bottom"),
        padding_left=el.get("padding-left"),
    )


def _parse_text_block(el: etree._Element) -> TextBlock:
    """Parse a ``<text-block>`` element and its child paragraphs."""
    col_count_raw = el.get("column-count", "1")
    try:
        col_count = int(col_count_raw)
    except ValueError:
        col_count = 1

    tb = TextBlock(
        id=el.get("id"),
        font_ref=el.get("font-ref"),
        size=el.get("size"),
        leading=el.get("leading"),
        language=el.get("language", "und"),
        text_align=el.get("text-align", "start"),
        direction=el.get("direction", "ltr"),
        color=el.get("color"),
        column_count=col_count,
        column_gap=el.get("column-gap"),
    )

    for child in el:
        local_tag = _local(child)
        if local_tag == "reflow-region":
            tb.reflow_region = _parse_reflow_region(child)
        elif local_tag == "p":
            tb.paragraphs.append(_parse_paragraph(child))
        # <overflow> and other known-but-unneeded children are silently ignored.

    return tb


# ---------------------------------------------------------------------------
# Top-level XML document parsing
# ---------------------------------------------------------------------------

def _parse_xml_root(root: etree._Element) -> MDFDocument:
    """Build an :class:`MDFDocument` from an already-parsed lxml root element."""
    if _local(root) != "mdf":
        raise MDFParseError(
            f"Root element must be <mdf> in the MDF namespace; got <{root.tag}>"
        )

    version = root.get("version")
    if not version:
        raise MDFParseError("<mdf> root element is missing required 'version' attribute")

    # --- Manifest ---
    manifest_el = root.find(_D("manifest"))
    if manifest_el is None:
        raise MDFParseError("<manifest> element not found — document is invalid")
    manifest = _parse_manifest(manifest_el)

    # --- Canvas(es) ---
    canvases: list[Canvas] = []

    # Single-canvas: <canvas> is a direct child of <mdf>
    single = root.find(_D("canvas"))
    if single is not None:
        canvases.append(_parse_canvas(single))

    # Multi-canvas: <document><canvas/>…</document>
    doc_el = root.find(_D("document"))
    if doc_el is not None:
        for canvas_el in doc_el.findall(_D("canvas")):
            canvases.append(_parse_canvas(canvas_el))

    if not canvases:
        raise MDFParseError(
            "MDF document must contain at least one <canvas> element "
            "(either directly in <mdf> or inside a <document> wrapper)"
        )

    return MDFDocument(version=version, manifest=manifest, canvases=canvases)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_string(xml: str | bytes) -> MDFDocument:
    """Parse an MDF XML document from a string or bytes.

    Parameters
    ----------
    xml:
        A UTF-8 string or bytes containing a complete, well-formed MDF
        XML document.

    Returns
    -------
    MDFDocument

    Raises
    ------
    MDFParseError
        If *xml* is not well-formed XML or is structurally invalid MDF.
    """
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    try:
        root = etree.fromstring(xml)
    except etree.XMLSyntaxError as exc:
        raise MDFParseError(f"XML syntax error: {exc}") from exc
    return _parse_xml_root(root)


def parse_file(path: str | Path) -> MDFDocument:
    """Parse an MDF document from a file path.

    Accepts both plain ``.mdf`` files (UTF-8 XML) and ``.mdfx`` bundle
    archives (ZIP64 containing ``document.mdf``).

    Parameters
    ----------
    path:
        Path to a ``.mdf`` or ``.mdfx`` file.

    Returns
    -------
    MDFDocument

    Raises
    ------
    MDFParseError
        If the file cannot be read, is not valid MDF, or a bundle is
        missing its ``document.mdf`` entry.
    FileNotFoundError
        If *path* does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"MDF file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".mdfx":
        return _parse_mdfx_bundle(path)
    if suffix == ".mdf":
        return _parse_plain_mdf(path)

    # Unknown extension: probe for ZIP magic
    if zipfile.is_zipfile(path):
        return _parse_mdfx_bundle(path)
    return _parse_plain_mdf(path)


# ---------------------------------------------------------------------------
# File-type specific helpers (not part of the public API)
# ---------------------------------------------------------------------------

def _parse_plain_mdf(path: Path) -> MDFDocument:
    """Read and parse a plain UTF-8 ``.mdf`` XML file."""
    try:
        xml_bytes = path.read_bytes()
    except OSError as exc:
        raise MDFParseError(f"Cannot read {path}: {exc}") from exc

    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        raise MDFParseError(f"XML syntax error in {path}: {exc}") from exc

    return _parse_xml_root(root)


def _parse_mdfx_bundle(path: Path) -> MDFDocument:
    """Open a ``.mdfx`` ZIP64 bundle and parse the embedded ``document.mdf``."""
    if not zipfile.is_zipfile(path):
        raise MDFParseError(
            f"{path} does not appear to be a valid ZIP/MDFX archive"
        )

    try:
        with zipfile.ZipFile(path, "r", allowZip64=True) as zf:
            names = zf.namelist()
            entry = "document.mdf"
            if entry not in names:
                # Fallback: find any .mdf entry
                candidates = [n for n in names if n.endswith(".mdf")]
                if not candidates:
                    raise MDFParseError(
                        f"MDFX bundle {path} contains no .mdf document entry "
                        f"(entries found: {names!r})"
                    )
                entry = candidates[0]
                log.warning(
                    "MDFX bundle has no 'document.mdf'; using %r instead", entry
                )
            xml_bytes = zf.read(entry)
    except zipfile.BadZipFile as exc:
        raise MDFParseError(f"Cannot open MDFX bundle {path}: {exc}") from exc

    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        raise MDFParseError(
            f"XML syntax error in '{entry}' inside {path}: {exc}"
        ) from exc

    return _parse_xml_root(root)
