"""
MDF Document Model

Core dataclasses representing a parsed MDF document.
These are the in-memory representations after parsing; they are renderer-agnostic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MDFDocument:
    """Root document object. Corresponds to the <mdf> element."""
    version: str
    manifest: Manifest
    canvases: list[Canvas]  # 1 canvas for single-page, N for multi-page


@dataclass
class Manifest:
    """Document metadata and asset declarations. Corresponds to <manifest>."""
    title: Optional[str] = None
    author: Optional[str] = None
    created: Optional[str] = None
    language: str = "und"
    conformance_level: int = 1  # 1=basic, 2=print, 3=full
    fonts: dict[str, FontAsset] = field(default_factory=dict)
    icc_profiles: dict[str, ICCProfileAsset] = field(default_factory=dict)
    spot_colors: dict[str, SpotColor] = field(default_factory=dict)
    print_intent: Optional[PrintIntent] = None


@dataclass
class FontAsset:
    """A font asset declaration."""
    id: str
    family: str
    weight: int = 400
    style: str = "normal"
    src: str = ""
    format: str = "woff2"
    embed: bool = False


@dataclass
class ICCProfileAsset:
    """An ICC color profile asset declaration."""
    id: str
    src: str


@dataclass
class SpotColor:
    """A spot color declaration (Pantone, HKS, custom)."""
    id: str
    name: str
    cmyk_approximation: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    lab: Optional[tuple[float, float, float]] = None
    plate_name: Optional[str] = None


@dataclass
class PrintIntent:
    """Print production intent declaration."""
    substrate: str = "coated"
    color_mode: str = "cmyk"
    icc_profile_ref: Optional[str] = None
    resolution_target: str = "300dpi"
    press_type: Optional[str] = None


@dataclass
class Canvas:
    """
    The root geometric container of an MDF document.
    Corresponds to the <canvas> element.

    The boundary_path is the defining innovation of MDF: it's an SVG path
    that defines the actual shape of the document. For a circle, it's a
    circular arc path. For a die-cut sticker, it's the exact cut outline.
    """
    id: Optional[str]
    width: float
    height: float
    units: str
    boundary_path: str       # SVG path data string
    layers: list[Layer] = field(default_factory=list)

    # Print production
    die_cut: bool = False
    die_cut_type: str = "cut"
    bleed: float = 0.0       # in same units as width/height
    cut_lines: list[CutLine] = field(default_factory=list)
    marks: Optional[PrintMarks] = None
    folds: list[FoldLine] = field(default_factory=list)

    # Semantics
    shape_type: Optional[str] = None
    shape_meaning: Optional[str] = None
    shape_meaning_iri: Optional[str] = None


@dataclass
class CutLine:
    """A named cut line within the canvas (for multi-cut documents like sticker sheets)."""
    id: str
    path: str
    cut_type: str = "cut"  # cut, kiss-cut, score, perforate, crease


@dataclass
class PrintMarks:
    """Print production marks (registration, crop, color bar)."""
    registration_marks: bool = False
    registration_style: str = "crosshair"
    registration_offset: float = 8.0
    crop_marks: bool = False
    crop_mark_length: float = 5.0
    crop_mark_weight: float = 0.25
    crop_mark_offset: float = 3.0
    color_bar: bool = False


@dataclass
class FoldLine:
    """A fold line definition for multi-panel documents."""
    id: str
    path: str
    fold_type: str = "valley"  # valley, mountain, score-only
    angle: float = 180.0


@dataclass
class Layer:
    """
    A compositing layer within the canvas.
    Corresponds to the <layer> element.
    """
    id: Optional[str]
    blend_mode: str = "normal"
    opacity: float = 1.0
    visible: bool = True
    lock: bool = False
    print_role: Optional[str] = None  # e.g. "registration-marks"
    visible_in_render: bool = True
    elements: list = field(default_factory=list)  # TextBlock, Image, Shape, etc.
