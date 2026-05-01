#!/usr/bin/env python3
"""
pdf2mdf.py — PDF to MDF (Morphous Document Format) converter.

Usage:
    python pdf2mdf.py input.pdf [output.mdf | output_dir/]
        --page N        Convert only page N (1-based, default: all)
        --single        All pages in one .mdf file (outputs folder for now)
        --quality HIGH  Image extraction DPI (HIGH=150, default)
        --no-images     Skip image extraction
        --verbose       Print progress

MDF namespace: https://morphousdoc.org/ns/0.1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from xml.dom import minidom

# ---------------------------------------------------------------------------
# Dependency guard
# ---------------------------------------------------------------------------

try:
    import fitz  # PyMuPDF
except ImportError:
    print(
        "ERROR: PyMuPDF is not installed.\n"
        "Install it with:  pip install pymupdf\n"
        "Then re-run this script.",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PT_TO_MM = 0.352778  # 1 point = 0.352778 mm

# DPI options for image rendering
QUALITY_DPI = {
    "HIGH": 150,
    "MEDIUM": 96,
    "LOW": 72,
}

# MDF namespaces
NS_MDF = "https://morphousdoc.org/ns/0.1"
NS_PRINT = "https://morphousdoc.org/ns/print/0.1"
NS_SEM = "https://morphousdoc.org/ns/semantics/0.1"
NS_META = "https://morphousdoc.org/ns/meta/0.1"

# Known page shapes (dimensions in mm, tolerance ±2mm each side)
PAGE_SHAPES = [
    ("standard-a4",     210.0, 297.0),
    ("standard-a4-landscape", 297.0, 210.0),
    ("standard-a3",     297.0, 420.0),
    ("standard-a3-landscape", 420.0, 297.0),
    ("standard-a5",     148.0, 210.0),
    ("standard-letter", 215.9, 279.4),
    ("standard-letter-landscape", 279.4, 215.9),
    ("standard-legal",  215.9, 355.6),
    ("standard-tabloid", 279.4, 431.8),
]
SHAPE_TOLERANCE_MM = 2.0

# ---------------------------------------------------------------------------
# Helper functions (pure — easy to unit-test)
# ---------------------------------------------------------------------------

def pt_to_mm(pt: float) -> float:
    """Convert PDF points to millimetres."""
    return round(pt * PT_TO_MM, 4)


def rgb_to_cmyk(r: float, g: float, b: float) -> tuple[float, float, float, float]:
    """
    Convert RGB (0-1 floats) to CMYK (0-1 floats).
    Returns (C, M, Y, K).
    """
    k = 1.0 - max(r, g, b)
    if k >= 1.0:
        return 0.0, 0.0, 0.0, 1.0
    denom = 1.0 - k
    c = (1.0 - r - k) / denom
    m = (1.0 - g - k) / denom
    y = (1.0 - b - k) / denom
    return (
        max(0.0, min(1.0, c)),
        max(0.0, min(1.0, m)),
        max(0.0, min(1.0, y)),
        max(0.0, min(1.0, k)),
    )


def color_to_mdf(color: Any) -> str:
    """
    Convert a PyMuPDF color value to an MDF color string.

    PyMuPDF returns colors as:
      - None / 0       → black
      - int            → grayscale (0=black,1=white) or packed RGB
      - float          → grayscale
      - tuple of 1     → grayscale
      - tuple of 3     → RGB (0-1)
      - tuple of 4     → CMYK (0-1)
    """
    if color is None or color == 0:
        return "color(cmyk 0.000 0.000 0.000 1.000)"

    if isinstance(color, (int, float)):
        # Grayscale: 0=black, 1=white
        gray = float(color)
        # Guard: if it looks like a packed RGB int (>1), unpack it
        if isinstance(color, int) and color > 1:
            r = ((color >> 16) & 0xFF) / 255.0
            g = ((color >> 8) & 0xFF) / 255.0
            b = (color & 0xFF) / 255.0
            c, m, y, k = rgb_to_cmyk(r, g, b)
        else:
            # Pure gray: rgb = (gray, gray, gray)
            c, m, y, k = rgb_to_cmyk(gray, gray, gray)
        return f"color(cmyk {c:.3f} {m:.3f} {y:.3f} {k:.3f})"

    if isinstance(color, (tuple, list)):
        vals = tuple(float(v) for v in color)
        if len(vals) == 1:
            c, m, y, k = rgb_to_cmyk(vals[0], vals[0], vals[0])
        elif len(vals) == 3:
            c, m, y, k = rgb_to_cmyk(*vals)
        elif len(vals) == 4:
            c, m, y, k = vals  # already CMYK
        else:
            c, m, y, k = 0.0, 0.0, 0.0, 1.0
        return f"color(cmyk {c:.3f} {m:.3f} {y:.3f} {k:.3f})"

    return "color(cmyk 0.000 0.000 0.000 1.000)"


def sanitize_id(raw: str) -> str:
    """Return a valid XML id-safe string: lowercase, replace non-alnum with '-'."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()
    if not s or s[0].isdigit():
        s = "id-" + s
    return s or "id"


def font_weight_from_name(name: str) -> tuple[str, int, bool]:
    """
    Parse a PDF font name into (clean_family, weight, italic).

    PDF fonts may look like:
        ABCDEF+Helvetica-BoldOblique
        TimesNewRoman,Bold
        Arial-Regular
    """
    # Strip subset prefix (e.g. ABCDEF+)
    name = re.sub(r"^[A-Z]{6}\+", "", name)
    # Normalise separators
    name = name.replace(",", "-")

    italic = False
    weight = 400

    # Check for style suffixes (case-insensitive)
    lower = name.lower()
    if any(s in lower for s in ("italic", "oblique", "slanted")):
        italic = True
    if any(s in lower for s in ("black", "ultra", "extrablack")):
        weight = 900
    elif any(s in lower for s in ("extrabold", "ultrabold", "heavy")):
        weight = 800
    elif any(s in lower for s in ("semibold", "demibold")):
        # Must be checked before plain "bold" since "semibold" contains "bold"
        weight = 600
    elif "bold" in lower:
        weight = 700
    elif "medium" in lower:
        weight = 500
    elif "light" in lower:
        weight = 300
    elif "thin" in lower or "hairline" in lower:
        weight = 100

    # Strip all known style tokens to get the family name
    tokens_to_strip = [
        "extrablack", "ultrabold", "extrabold", "semibold", "demibold",
        "black", "ultra", "heavy", "bold", "medium", "regular", "normal",
        "light", "thin", "hairline", "italic", "oblique", "slanted",
    ]
    # Work on the base name (after last + stripping)
    parts = re.split(r"[-_ ]+", name)
    clean_parts = []
    for part in parts:
        if part.lower() not in tokens_to_strip:
            clean_parts.append(part)
    family = " ".join(clean_parts).strip() or name.split("-")[0]
    return family, weight, italic


def make_boundary_path(width_mm: float, height_mm: float) -> str:
    """Return the rectangular MDF boundary path string."""
    w = round(width_mm, 4)
    h = round(height_mm, 4)
    return f"M 0,0 L {w},0 L {w},{h} L 0,{h} Z"


def bbox_to_path(x0: float, y0: float, x1: float, y1: float) -> str:
    """Convert a bounding box (in mm) to an MDF SVG-style path."""
    return (
        f"M {x0:.4f},{y0:.4f} "
        f"L {x1:.4f},{y0:.4f} "
        f"L {x1:.4f},{y1:.4f} "
        f"L {x0:.4f},{y1:.4f} Z"
    )


def detect_page_shape(width_mm: float, height_mm: float) -> str:
    """Return the sem:shape-meaning for the given page dimensions."""
    for name, w, h in PAGE_SHAPES:
        if abs(width_mm - w) <= SHAPE_TOLERANCE_MM and abs(height_mm - h) <= SHAPE_TOLERANCE_MM:
            return name
    return "custom"


def _pt_bbox_to_mm(bbox: tuple) -> tuple[float, float, float, float]:
    """Convert a fitz.Rect / 4-tuple of points to mm values."""
    x0, y0, x1, y1 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    return pt_to_mm(x0), pt_to_mm(y0), pt_to_mm(x1), pt_to_mm(y1)


# ---------------------------------------------------------------------------
# Font registry
# ---------------------------------------------------------------------------

class FontRegistry:
    """Tracks unique fonts and assigns stable IDs for the <assets> section."""

    def __init__(self) -> None:
        self._fonts: dict[str, str] = {}  # key → font-id
        self._counter = 0
        # Always register a fallback
        self._ensure("Helvetica", 400)

    def _make_key(self, family: str, weight: int) -> str:
        return f"{family.lower()}::{weight}"

    def _ensure(self, family: str, weight: int) -> str:
        key = self._make_key(family, weight)
        if key not in self._fonts:
            fid = f"font-{self._counter}"
            self._fonts[key] = fid
            self._counter += 1
        return self._fonts[key]

    def register(self, family: str, weight: int) -> str:
        return self._ensure(family, weight)

    def get_id(self, family: str, weight: int) -> str:
        return self._ensure(family, weight)

    def all_fonts(self) -> list[dict]:
        """Return list of font dicts for rendering into <assets>."""
        result = []
        for key, fid in self._fonts.items():
            family, weight_str = key.split("::")
            # Capitalise family
            family_display = " ".join(w.capitalize() for w in family.split())
            result.append({
                "id": fid,
                "family": family_display,
                "weight": weight_str,
            })
        return sorted(result, key=lambda f: int(f["id"].split("-")[1]))

    @property
    def fallback_id(self) -> str:
        return self._fonts[self._make_key("Helvetica", 400)]


# ---------------------------------------------------------------------------
# Block merging
# ---------------------------------------------------------------------------

def _should_merge(block_a: dict, block_b: dict, tolerance_pt: float = 2.0) -> bool:
    """
    Return True if two text blocks are vertically adjacent enough to merge.
    Blocks must also overlap horizontally.
    """
    ax0, ay0, ax1, ay1 = block_a["bbox"]
    bx0, by0, bx1, by1 = block_b["bbox"]

    # Vertical proximity: bottom of A is within tolerance of top of B
    vertical_gap = by0 - ay1
    if not (-tolerance_pt <= vertical_gap <= tolerance_pt):
        return False

    # Horizontal overlap
    overlap_start = max(ax0, bx0)
    overlap_end = min(ax1, bx1)
    return overlap_end > overlap_start


def merge_adjacent_blocks(blocks: list[dict]) -> list[dict]:
    """
    Greedily merge text blocks that are visually adjacent (bboxes overlap
    vertically within 2pt and share horizontal space).
    """
    if not blocks:
        return blocks

    merged = [blocks[0]]
    for block in blocks[1:]:
        prev = merged[-1]
        if _should_merge(prev, block):
            # Extend prev bbox to cover both
            px0, py0, px1, py1 = prev["bbox"]
            bx0, by0, bx1, by1 = block["bbox"]
            prev["bbox"] = (
                min(px0, bx0), min(py0, by0),
                max(px1, bx1), max(py1, by1),
            )
            prev["lines"].extend(block.get("lines", []))
        else:
            merged.append(block)
    return merged


# ---------------------------------------------------------------------------
# XML building helpers
# ---------------------------------------------------------------------------

def _set(el: ET.Element, **attrs: str) -> None:
    for k, v in attrs.items():
        el.set(k, v)


def _sub(parent: ET.Element, tag: str, **attrs: str) -> ET.Element:
    el = ET.SubElement(parent, tag)
    for k, v in attrs.items():
        el.set(k, v)
    return el


def _qn(ns: str, local: str) -> str:
    return f"{{{ns}}}{local}"


# ---------------------------------------------------------------------------
# Page converter
# ---------------------------------------------------------------------------

class PageConverter:
    """Converts a single fitz.Page into an MDF <canvas> XML element."""

    def __init__(
        self,
        page: "fitz.Page",
        page_number: int,
        font_registry: FontRegistry,
        output_dir: Path,
        include_images: bool = True,
        image_dpi: int = 150,
        verbose: bool = False,
    ) -> None:
        self.page = page
        self.page_number = page_number
        self.font_registry = font_registry
        self.output_dir = output_dir
        self.include_images = include_images
        self.image_dpi = image_dpi
        self.verbose = verbose
        self._block_counter = 0
        self._image_counter = 0

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [page {self.page_number}] {msg}")

    def _next_block_id(self) -> str:
        bid = f"block-{self._block_counter}"
        self._block_counter += 1
        return bid

    def _next_image_id(self) -> str:
        iid = f"img-{self._image_counter}"
        self._image_counter += 1
        return iid

    def convert(self) -> ET.Element:
        rect = self.page.rect
        width_mm = pt_to_mm(rect.width)
        height_mm = pt_to_mm(rect.height)
        boundary = make_boundary_path(width_mm, height_mm)
        shape_meaning = detect_page_shape(width_mm, height_mm)

        canvas = ET.Element("canvas")
        _set(
            canvas,
            width=str(round(width_mm, 4)),
            height=str(round(height_mm, 4)),
            units="mm",
            boundary=boundary,
            **{_qn(NS_SEM, "shape-type"): "polygon"},
            **{_qn(NS_SEM, "shape-meaning"): shape_meaning},
        )

        layers_el = _sub(canvas, "layers")
        layer_el = _sub(layers_el, "layer", id="content", **{"blend-mode": "normal"})

        self._add_text(layer_el, width_mm, height_mm)
        if self.include_images:
            self._add_images(layer_el)

        return canvas

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    def _add_text(self, layer_el: ET.Element, page_w_mm: float, page_h_mm: float) -> None:
        try:
            text_dict = self.page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        except Exception as exc:
            self._log(f"Warning: could not extract text: {exc}")
            return

        raw_blocks = [b for b in text_dict.get("blocks", []) if b.get("type") == 0]
        if not raw_blocks:
            return

        # Sort blocks top-to-bottom, then left-to-right
        raw_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))

        # Merge adjacent blocks
        merged = merge_adjacent_blocks(raw_blocks)
        self._log(f"Text blocks: {len(raw_blocks)} raw → {len(merged)} after merge")

        for block in merged:
            self._render_text_block(layer_el, block)

    def _render_text_block(self, layer_el: ET.Element, block: dict) -> None:
        lines = block.get("lines", [])
        if not lines:
            return

        # Collect all spans to determine dominant font/size/color/align for the block
        all_spans = [span for line in lines for span in line.get("spans", [])]
        all_spans = [s for s in all_spans if s.get("text", "").strip()]
        if not all_spans:
            return

        # Pick dominant font attributes from first non-empty span
        dominant = all_spans[0]
        raw_font = dominant.get("font", "Helvetica")
        family, weight, _italic = font_weight_from_name(raw_font)
        font_size_pt = dominant.get("size", 12.0)
        raw_color = dominant.get("color", 0)
        color_str = color_to_mdf(raw_color)
        font_ref = self.font_registry.register(family, weight)

        # Block bounding box in mm
        bx0, by0, bx1, by1 = _pt_bbox_to_mm(block["bbox"])

        block_id = self._next_block_id()
        size_str = f"{round(font_size_pt, 2)}pt"
        leading_str = f"{round(font_size_pt * 1.2, 2)}pt"

        tb = _sub(
            layer_el, "text-block",
            id=block_id,
            **{"font-ref": font_ref},
            size=size_str,
            leading=leading_str,
            **{"text-align": "left"},
            color=color_str,
        )

        # Reflow region = block's bounding box (with zero padding)
        region_path = bbox_to_path(bx0, by0, bx1, by1)
        _sub(tb, "reflow-region", shape=region_path, padding="0")

        # Lines → <p> elements
        span_counters: dict[str, int] = {}
        for line in lines:
            spans = line.get("spans", [])
            non_empty = [s for s in spans if s.get("text", "")]
            if not non_empty:
                continue

            p_el = _sub(tb, "p")
            for span in non_empty:
                text_val = span.get("text", "")
                if not text_val:
                    continue
                # Zero-area check
                sx0, sy0, sx1, sy1 = span.get("bbox", (0, 0, 0, 0))
                if abs(sx1 - sx0) < 0.001 and abs(sy1 - sy0) < 0.001:
                    continue

                s_raw_font = span.get("font", raw_font)
                s_family, s_weight, s_italic = font_weight_from_name(s_raw_font)
                s_font_ref = self.font_registry.register(s_family, s_weight)
                s_size = span.get("size", font_size_pt)
                s_color_str = color_to_mdf(span.get("color", raw_color))

                # Create a unique span id
                key = f"{block_id}"
                span_counters[key] = span_counters.get(key, 0)
                span_id = f"span-{self._block_counter - 1}-{span_counters[key]}"
                span_counters[key] += 1

                span_attrs: dict[str, str] = {
                    "id": span_id,
                    "font-ref": s_font_ref,
                    "size": f"{round(s_size, 2)}pt",
                    "color": s_color_str,
                }
                if s_italic:
                    span_attrs["style"] = "italic"

                span_el = _sub(p_el, "span", **span_attrs)
                span_el.text = text_val

    # ------------------------------------------------------------------
    # Image extraction
    # ------------------------------------------------------------------

    def _add_images(self, layer_el: ET.Element) -> None:
        images_dir = self.output_dir / "images"

        try:
            image_list = self.page.get_images(full=True)
        except Exception as exc:
            self._log(f"Warning: could not list images: {exc}")
            return

        if not image_list:
            return

        images_dir.mkdir(parents=True, exist_ok=True)
        self._log(f"Extracting {len(image_list)} image(s)")

        doc = self.page.parent  # the fitz.Document

        for img_info in image_list:
            xref = img_info[0]
            iid = self._next_image_id()
            filename = f"page-{self.page_number}-{iid}.jpg"
            img_path = images_dir / filename
            rel_path = f"images/{filename}"

            # Get image bounding box on page
            try:
                bbox = self.page.get_image_bbox(img_info)
            except Exception:
                bbox = None

            if bbox is None or bbox.is_empty:
                self._log(f"Skipping image {xref}: no valid bbox")
                continue

            # Extract and save image
            try:
                base_image = doc.extract_image(xref)
                img_bytes = base_image["image"]
                img_ext = base_image.get("ext", "jpeg").lower()

                # Save as JPEG (convert if needed via fitz)
                if img_ext in ("jpeg", "jpg"):
                    with open(img_path, "wb") as f:
                        f.write(img_bytes)
                else:
                    # Re-render via pixmap for format conversion
                    clip_rect = fitz.Rect(bbox)
                    mat = fitz.Matrix(self.image_dpi / 72.0, self.image_dpi / 72.0)
                    pix = self.page.get_pixmap(matrix=mat, clip=clip_rect)
                    pix.save(str(img_path))

                self._log(f"Saved image: {rel_path}")
            except Exception as exc:
                self._log(f"Warning: could not extract image xref={xref}: {exc}")
                continue

            # Convert bbox pts → mm
            ix0 = pt_to_mm(bbox.x0)
            iy0 = pt_to_mm(bbox.y0)
            iw = pt_to_mm(bbox.width)
            ih = pt_to_mm(bbox.height)

            _sub(
                layer_el, "image",
                src=rel_path,
                x=str(round(ix0, 4)),
                y=str(round(iy0, 4)),
                width=str(round(iw, 4)),
                height=str(round(ih, 4)),
            )


# ---------------------------------------------------------------------------
# Document-level converter
# ---------------------------------------------------------------------------

class PDFtoMDFConverter:
    """Top-level converter: opens a PDF and drives per-page conversion."""

    def __init__(
        self,
        pdf_path: Path,
        output_path: Path,
        page_number: int | None = None,
        include_images: bool = True,
        image_dpi: int = 150,
        verbose: bool = False,
    ) -> None:
        self.pdf_path = pdf_path
        self.output_path = output_path
        self.page_number = page_number  # 1-based, None = all
        self.include_images = include_images
        self.image_dpi = image_dpi
        self.verbose = verbose

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[pdf2mdf] {msg}")

    def convert(self) -> None:
        self._log(f"Opening: {self.pdf_path}")
        try:
            doc = fitz.open(str(self.pdf_path))
        except Exception as exc:
            print(f"ERROR: Cannot open PDF '{self.pdf_path}': {exc}", file=sys.stderr)
            sys.exit(1)

        total_pages = doc.page_count
        self._log(f"PDF has {total_pages} page(s)")

        # Determine which pages to convert
        if self.page_number is not None:
            if self.page_number < 1 or self.page_number > total_pages:
                print(
                    f"ERROR: Page {self.page_number} out of range (1–{total_pages})",
                    file=sys.stderr,
                )
                sys.exit(1)
            page_indices = [self.page_number - 1]
        else:
            page_indices = list(range(total_pages))

        # Decide output mode
        output_str = str(self.output_path)
        is_single_mdf = output_str.endswith(".mdf")

        if is_single_mdf and len(page_indices) > 1:
            print(
                f"WARNING: Input has {total_pages} pages but output is a single .mdf file. "
                f"Converting only page 1.",
                file=sys.stderr,
            )
            page_indices = [0]

        if is_single_mdf:
            self._convert_single_mdf(doc, page_indices, self.output_path)
        else:
            self._convert_folder(doc, page_indices, self.output_path)

        doc.close()
        self._log("Done.")

    # ------------------------------------------------------------------
    # Single .mdf output (one page)
    # ------------------------------------------------------------------

    def _convert_single_mdf(
        self,
        doc: "fitz.Document",
        page_indices: list[int],
        out_path: Path,
    ) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        images_dir = out_path.parent

        font_reg = FontRegistry()
        page_idx = page_indices[0]
        page = doc[page_idx]
        page_num = page_idx + 1

        self._log(f"Converting page {page_num} → {out_path}")
        converter = PageConverter(
            page=page,
            page_number=page_num,
            font_registry=font_reg,
            output_dir=out_path.parent,
            include_images=self.include_images,
            image_dpi=self.image_dpi,
            verbose=self.verbose,
        )
        canvas_el = converter.convert()

        root = self._build_mdf_root(doc, font_reg)
        root.append(canvas_el)

        xml_str = self._serialize(root)
        out_path.write_text(xml_str, encoding="utf-8")
        self._log(f"Written: {out_path}")

    # ------------------------------------------------------------------
    # Multi-page folder output
    # ------------------------------------------------------------------

    def _convert_folder(
        self,
        doc: "fitz.Document",
        page_indices: list[int],
        out_dir: Path,
    ) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_entries = []

        for page_idx in page_indices:
            page_num = page_idx + 1
            page_filename = f"page-{page_num}.mdf"
            page_out = out_dir / page_filename

            self._log(f"Converting page {page_num} → {page_out}")

            font_reg = FontRegistry()
            page = doc[page_idx]

            converter = PageConverter(
                page=page,
                page_number=page_num,
                font_registry=font_reg,
                output_dir=out_dir,
                include_images=self.include_images,
                image_dpi=self.image_dpi,
                verbose=self.verbose,
            )
            canvas_el = converter.convert()

            root = self._build_mdf_root(doc, font_reg)
            root.append(canvas_el)

            xml_str = self._serialize(root)
            page_out.write_text(xml_str, encoding="utf-8")
            self._log(f"Written: {page_out}")

            manifest_entries.append({
                "page": page_num,
                "file": page_filename,
            })

        # Write manifest.json
        manifest = {
            "source": str(self.pdf_path.name),
            "total_pages": len(manifest_entries),
            "converted": datetime.now(timezone.utc).isoformat(),
            "pages": manifest_entries,
        }
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._log(f"Written manifest: {manifest_path}")

    # ------------------------------------------------------------------
    # XML construction helpers
    # ------------------------------------------------------------------

    def _build_mdf_root(self, doc: "fitz.Document", font_reg: FontRegistry) -> ET.Element:
        """Build the root <mdf> element with <manifest>."""
        # Register namespace prefixes
        ET.register_namespace("", NS_MDF)
        ET.register_namespace("print", NS_PRINT)
        ET.register_namespace("sem", NS_SEM)
        ET.register_namespace("meta", NS_META)

        # Register namespace prefixes so ET emits them correctly.
        # Do NOT manually set xmlns:* attributes — that causes duplicates.
        ET.register_namespace("", NS_MDF)
        ET.register_namespace("print", NS_PRINT)
        ET.register_namespace("sem", NS_SEM)
        ET.register_namespace("meta", NS_META)

        root = ET.Element(
            _qn(NS_MDF, "mdf"),
            version="0.1",
        )
        # Force xmlns:print onto the root element by setting a placeholder attribute
        # in the print namespace (removed after serialisation by string cleanup).
        # This ensures the namespace declaration appears at document level.
        root.set(_qn(NS_PRINT, "_placeholder"), "1")

        manifest_el = _sub(root, "manifest")

        # Metadata
        metadata = doc.metadata or {}
        title = metadata.get("title") or f"Converted from {self.pdf_path.name}"
        author = metadata.get("author") or "Unknown"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        title_el = ET.SubElement(manifest_el, _qn(NS_META, "title"))
        title_el.text = title
        author_el = ET.SubElement(manifest_el, _qn(NS_META, "author"))
        author_el.text = author
        created_el = ET.SubElement(manifest_el, _qn(NS_META, "created"))
        created_el.text = now_iso
        lang_el = ET.SubElement(manifest_el, _qn(NS_META, "language"))
        lang_el.text = "en-US"

        _sub(manifest_el, "conformance", level="screen")

        # Assets
        assets_el = _sub(manifest_el, "assets")
        for font_info in font_reg.all_fonts():
            _sub(
                assets_el, "font",
                id=font_info["id"],
                family=font_info["family"],
                weight=font_info["weight"],
                src="",
                embed="false",
            )

        return root

    @staticmethod
    def _serialize(root: ET.Element) -> str:
        """Serialize the XML tree to a pretty-printed UTF-8 string."""
        raw = ET.tostring(root, encoding="unicode", xml_declaration=False)
        # Strip the placeholder attribute used to force xmlns:print onto root
        raw = re.sub(r'\s*print:_placeholder="1"', "", raw)
        dom = minidom.parseString(raw)
        pretty = dom.toprettyxml(indent="  ", encoding=None)
        # minidom adds its own XML declaration; replace/ensure correct one
        lines = pretty.split("\n")
        # Remove the minidom declaration line (first line)
        if lines and lines[0].startswith("<?xml"):
            lines = lines[1:]
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf2mdf",
        description="Convert PDF files to MDF (Morphous Document Format).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pdf2mdf.py document.pdf                     # Outputs document_mdf/
  python pdf2mdf.py document.pdf output.mdf          # Single page → one file
  python pdf2mdf.py document.pdf output_dir/         # Multi-page folder
  python pdf2mdf.py document.pdf --page 3            # Only page 3
  python pdf2mdf.py document.pdf --no-images         # Skip image extraction
  python pdf2mdf.py document.pdf --verbose           # Print progress
""",
    )
    parser.add_argument("input", metavar="INPUT.pdf", help="Path to input PDF file")
    parser.add_argument(
        "output",
        metavar="OUTPUT",
        nargs="?",
        default=None,
        help="Output .mdf file or directory (default: <input_stem>_mdf/)",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=None,
        metavar="N",
        help="Convert only page N (1-based)",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="(Future) Put all pages in one .mdf; currently outputs a folder",
    )
    parser.add_argument(
        "--quality",
        choices=list(QUALITY_DPI.keys()),
        default="HIGH",
        help="Image extraction quality / DPI (default: HIGH=150dpi)",
    )
    parser.add_argument(
        "--no-images",
        dest="no_images",
        action="store_true",
        help="Skip image extraction",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print conversion progress",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    pdf_path = Path(args.input).expanduser().resolve()
    if not pdf_path.exists():
        print(f"ERROR: Input file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    if not pdf_path.suffix.lower() == ".pdf":
        print(f"WARNING: Input file does not have a .pdf extension: {pdf_path}", file=sys.stderr)

    # Determine output path
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        output_path = pdf_path.parent / (pdf_path.stem + "_mdf")

    dpi = QUALITY_DPI.get(args.quality, 150)

    if args.single and args.verbose:
        print(
            "NOTE: --single is a planned feature; output will be a folder (one file per page).",
            file=sys.stderr,
        )

    converter = PDFtoMDFConverter(
        pdf_path=pdf_path,
        output_path=output_path,
        page_number=args.page,
        include_images=not args.no_images,
        image_dpi=dpi,
        verbose=args.verbose,
    )
    converter.convert()


if __name__ == "__main__":
    main()
