"""
MDF Unit Converter

Converts CSS/SVG-style length strings (e.g. "210mm", "8.5in", "72pt", "96px")
to a target document unit.

All conversions go through millimetres as the canonical intermediate unit.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Conversion table: unit → millimetres
# ---------------------------------------------------------------------------

_TO_MM: dict[str, float] = {
    "mm": 1.0,
    "cm": 10.0,
    "in": 25.4,
    "pt": 25.4 / 72.0,     # 1 pt = 1/72 inch
    "pc": 25.4 / 6.0,      # 1 pica = 12 pt = 1/6 inch
    "px": 25.4 / 96.0,     # CSS reference px = 1/96 inch
    "q":  0.25,             # quarter-millimetre (CSS)
}

_FROM_MM: dict[str, float] = {unit: 1.0 / factor for unit, factor in _TO_MM.items()}

_LENGTH_RE = re.compile(
    r"^\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*"
    r"(mm|cm|in|pt|pc|px|q)?\s*$",
    re.IGNORECASE,
)


class UnitConversionError(ValueError):
    """Raised when a length string cannot be parsed or converted."""


def parse_length(value: str, target_units: str = "mm") -> float:
    """Parse a CSS/SVG length string and return its value in *target_units*.

    Parameters
    ----------
    value:
        A string like ``"210mm"``, ``"8.5in"``, ``"72pt"``, or a bare
        number (interpreted as already being in *target_units*).
    target_units:
        The unit to convert into.  Must be one of ``mm``, ``cm``, ``in``,
        ``pt``, ``pc``, ``px``, ``q``.  Defaults to ``"mm"``.

    Returns
    -------
    float
        The numeric value in *target_units*.

    Raises
    ------
    UnitConversionError
        If the string cannot be parsed or the unit is unrecognised.

    Examples
    --------
    >>> parse_length("210mm")
    210.0
    >>> parse_length("8.5in", "mm")
    215.9
    >>> parse_length("72pt", "mm")
    25.399999999999999
    >>> parse_length("100")        # bare number — stays in target unit
    100.0
    """
    target_units = target_units.lower().strip()
    if target_units not in _TO_MM:
        raise UnitConversionError(
            f"Unknown target unit {target_units!r}. "
            f"Supported: {', '.join(sorted(_TO_MM))}"
        )

    m = _LENGTH_RE.match(str(value).strip())
    if m is None:
        raise UnitConversionError(f"Cannot parse length value {value!r}")

    numeric = float(m.group(1))
    src_unit = (m.group(2) or "").lower()

    if not src_unit:
        # Bare number: assume it is already in target_units.
        return numeric

    src_unit = src_unit.lower()
    if src_unit not in _TO_MM:
        raise UnitConversionError(
            f"Unknown source unit {src_unit!r} in {value!r}. "
            f"Supported: {', '.join(sorted(_TO_MM))}"
        )

    if src_unit == target_units:
        return numeric

    # Convert: src → mm → target
    in_mm = numeric * _TO_MM[src_unit]
    return in_mm * _FROM_MM[target_units]


def strip_units(value: str) -> tuple[float, str]:
    """Split a length string into its numeric part and unit suffix.

    Returns
    -------
    (numeric, unit)
        *unit* is the lower-case suffix string, or ``""`` if the value is
        a bare number.

    Examples
    --------
    >>> strip_units("210mm")
    (210.0, 'mm')
    >>> strip_units("8.5in")
    (8.5, 'in')
    >>> strip_units("100")
    (100.0, '')
    """
    m = _LENGTH_RE.match(str(value).strip())
    if m is None:
        raise UnitConversionError(f"Cannot parse length value {value!r}")
    return float(m.group(1)), (m.group(2) or "").lower()
