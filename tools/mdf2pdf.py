#!/usr/bin/env python3
"""
mdf2pdf — Convert an MDF document to PDF
=========================================

Converts an .mdf (or .mdfx) document to a PDF file.  The PDF page
dimensions exactly match the MDF canvas size, and a thin rectangle is
drawn around the boundary so that page edges are always visible.

Usage
-----
    python mdf2pdf.py input.mdf
    python mdf2pdf.py input.mdf -o output.pdf
    python mdf2pdf.py input.mdf --canvas 1
    python mdf2pdf.py input.mdf --proof
    python mdf2pdf.py input.mdf --border-width 1.0
    python mdf2pdf.py input.mdf --no-border

Dependencies
------------
    pip install reportlab

The MDF reference-impl package must be on the Python path.  If you are
running from the project root:

    cd /path/to/mdf/reference-impl/python
    pip install -e .
    python ../../tools/mdf2pdf.py ../../examples/basic/hello-world.mdf

Or activate the project venv first:

    source reference-impl/python/.venv/bin/activate
    python tools/mdf2pdf.py examples/basic/hello-world.mdf
"""

from __future__ import annotations

import argparse
import os
import sys

# ---------------------------------------------------------------------------
# Allow running this script from the project root without 'pip install -e .'
# by inserting the src/ directory on sys.path.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC  = os.path.join(_HERE, "..", "reference-impl", "python", "src")
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mdf2pdf",
        description=(
            "Convert an MDF document to PDF.  The PDF page matches the "
            "canvas dimensions exactly, with a thin rectangle drawn around "
            "the boundary."
        ),
    )
    p.add_argument("input", metavar="INPUT.mdf", help="Source MDF or MDFX file")
    p.add_argument(
        "-o", "--output",
        metavar="OUTPUT.pdf",
        default=None,
        help="Output PDF path (default: INPUT.pdf)",
    )
    p.add_argument(
        "--canvas",
        type=int,
        default=0,
        metavar="N",
        help="Canvas index to render, 0-based (default: 0)",
    )
    p.add_argument(
        "--proof",
        action="store_true",
        help="Overlay bleed, cut, and fold marks",
    )
    p.add_argument(
        "--border-width",
        type=float,
        default=0.5,
        metavar="PT",
        help="Border rectangle line width in PDF points (default: 0.5)",
    )
    p.add_argument(
        "--no-border",
        action="store_true",
        help="Do not draw the boundary rectangle",
    )
    p.add_argument(
        "--border-color",
        default="0,0,0",
        metavar="R,G,B",
        help=(
            "Border color as comma-separated RGB values in [0,1] "
            "(default: 0,0,0 = black)"
        ),
    )
    p.add_argument(
        "--all-canvases",
        action="store_true",
        help="Render all canvases, one PDF per canvas",
    )
    return p


def _parse_rgb(s: str) -> tuple[float, float, float]:
    """Parse 'R,G,B' string to (r, g, b) float tuple."""
    try:
        parts = [float(v.strip()) for v in s.split(",")]
        if len(parts) == 3:
            return (parts[0], parts[1], parts[2])
    except ValueError:
        pass
    print(f"Warning: cannot parse border color {s!r}; using black", file=sys.stderr)
    return (0.0, 0.0, 0.0)


def main() -> int:
    args = _build_parser().parse_args()

    # ---- Import MDF library ----
    try:
        from mdf.parser import parse_file, MDFParseError
        from mdf.renderer.pdf_renderer import render_pdf
    except ImportError as exc:
        print(
            f"Error: cannot import the MDF library.\n"
            f"  Run: pip install -e reference-impl/python\n"
            f"  Or:  source reference-impl/python/.venv/bin/activate\n\n"
            f"  Detail: {exc}",
            file=sys.stderr,
        )
        return 2

    # ---- Parse document ----
    try:
        doc = parse_file(args.input)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except MDFParseError as exc:
        print(f"Parse error: {exc}", file=sys.stderr)
        return 1

    border_color = _parse_rgb(args.border_color)
    border_width = 0.0 if args.no_border else args.border_width

    # ---- Determine which canvases to render ----
    if args.all_canvases:
        indices = list(range(len(doc.canvases)))
    else:
        if args.canvas >= len(doc.canvases):
            print(
                f"Error: canvas index {args.canvas} out of range "
                f"(document has {len(doc.canvases)} canvas(es)).",
                file=sys.stderr,
            )
            return 1
        indices = [args.canvas]

    base, _ = os.path.splitext(args.input)

    # ---- Render ----
    for idx in indices:
        if args.all_canvases:
            suffix = f"-canvas{idx}"
            out_path = f"{base}{suffix}.pdf"
        else:
            out_path = args.output or f"{base}.pdf"

        try:
            pdf_bytes = render_pdf(
                doc,
                proof=args.proof,
                canvas_index=idx,
                border_width_pt=border_width,
                border_color=border_color,
            )
        except ImportError as exc:
            print(
                f"Error: PDF rendering requires reportlab.\n"
                f"  pip install reportlab\n\n{exc}",
                file=sys.stderr,
            )
            return 2
        except (IndexError, ValueError) as exc:
            print(f"Render error: {exc}", file=sys.stderr)
            return 1

        try:
            with open(out_path, "wb") as fh:
                fh.write(pdf_bytes)
        except OSError as exc:
            print(f"Cannot write {out_path!r}: {exc}", file=sys.stderr)
            return 1

        canvas = doc.canvases[idx]
        size_str = f"{canvas.width:g}×{canvas.height:g} {canvas.units}"
        border_info = (
            f"  no border"
            if args.no_border
            else f"  border {border_width:.2g} pt"
        )
        proof_info = "  [proof]" if args.proof else ""
        print(f"✓  {out_path}  ({size_str}){border_info}{proof_info}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
