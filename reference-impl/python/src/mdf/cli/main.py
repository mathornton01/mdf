"""
MDF CLI — mdf command-line tool

Commands:
  mdf render <file.mdf>   — render to SVG or PNG
  mdf validate <file.mdf> — validate against spec requirements
  mdf pack <dir/>         — pack a directory into .mdfx bundle
  mdf unpack <file.mdfx>  — unpack .mdfx bundle to directory
  mdf info <file.mdf>     — print document metadata
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import click

from mdf.parser import MDFParseError, parse_file
from mdf.renderer.svg_renderer import render_svg
from mdf.renderer.pdf_renderer import render_pdf


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version="0.1.0", prog_name="mdf")
def cli() -> None:
    """MDF — Morphous Document Format tools."""


# ---------------------------------------------------------------------------
# mdf render
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", default=None, help="Output file path")
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(["png", "svg", "pdf"]),
    default="svg",
    help="Output format (default: svg)",
)
@click.option("--dpi", default=150, help="Resolution for raster output (default: 150)")
@click.option("--proof", is_flag=True, help="Show bleed and marks in output")
@click.option(
    "--canvas",
    "canvas_index",
    default=0,
    help="Which canvas to render, 0-based (default: 0)",
)
def render(
    input_file: str,
    output: Optional[str],
    output_format: str,
    dpi: int,
    proof: bool,
    canvas_index: int,
) -> None:
    """Render an MDF document to SVG or PNG."""
    # ---- Parse the document ----
    try:
        doc = parse_file(input_file)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except MDFParseError as exc:
        click.echo(f"Parse error: {exc}", err=True)
        sys.exit(1)

    # ---- Determine output path ----
    if output is None:
        base = os.path.splitext(input_file)[0]
        output = f"{base}.{output_format}"

    # ---- Render ----
    if output_format == "svg":
        _render_svg(doc, output, proof=proof, canvas_index=canvas_index)

    elif output_format == "png":
        _render_png(doc, output, proof=proof, dpi=dpi, canvas_index=canvas_index)

    elif output_format == "pdf":
        _render_pdf(doc, output, proof=proof, canvas_index=canvas_index)


def _render_svg(
    doc: object,
    output_path: str,
    proof: bool = False,
    canvas_index: int = 0,
) -> None:
    """Render to SVG and write to output_path."""
    try:
        svg = render_svg(doc, proof=proof, canvas_index=canvas_index)  # type: ignore[arg-type]
    except (IndexError, ValueError) as exc:
        click.echo(f"Render error: {exc}", err=True)
        sys.exit(1)

    try:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(svg)
    except OSError as exc:
        click.echo(f"Cannot write output file {output_path!r}: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Rendered SVG → {output_path}")


def _render_png(
    doc: object,
    output_path: str,
    proof: bool = False,
    dpi: int = 150,
    canvas_index: int = 0,
) -> None:
    """Render to PNG via cairosvg (optional dependency)."""
    try:
        import cairosvg  # type: ignore[import]
    except ImportError:
        click.echo(
            "PNG output requires cairosvg. Install it with:\n"
            "  pip install cairosvg\n"
            "Alternatively, render to SVG (--format svg) and convert externally.",
            err=True,
        )
        sys.exit(1)

    try:
        svg = render_svg(doc, proof=proof, canvas_index=canvas_index)  # type: ignore[arg-type]
    except (IndexError, ValueError) as exc:
        click.echo(f"Render error: {exc}", err=True)
        sys.exit(1)

    # cairosvg works in pixels; convert dpi to a scale factor
    # SVG dimensions are in document units (mm by default); at 96 dpi base,
    # scale = dpi / 96 gives the right physical size.
    scale = dpi / 96.0

    try:
        cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            write_to=output_path,
            scale=scale,
        )
    except Exception as exc:
        click.echo(f"cairosvg error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Rendered PNG ({dpi} dpi) → {output_path}")


def _render_pdf(
    doc: object,
    output_path: str,
    proof: bool = False,
    canvas_index: int = 0,
) -> None:
    """Render to PDF using reportlab and write to output_path."""
    try:
        pdf_bytes = render_pdf(doc, proof=proof, canvas_index=canvas_index)  # type: ignore[arg-type]
    except ImportError as exc:
        click.echo(
            f"PDF output requires reportlab. Install it with:\n"
            f"  pip install reportlab\n\n{exc}",
            err=True,
        )
        sys.exit(1)
    except (IndexError, ValueError) as exc:
        click.echo(f"Render error: {exc}", err=True)
        sys.exit(1)

    try:
        with open(output_path, "wb") as fh:
            fh.write(pdf_bytes)
    except OSError as exc:
        click.echo(f"Cannot write output file {output_path!r}: {exc}", err=True)
        sys.exit(1)

    canvas = doc.canvases[canvas_index]  # type: ignore[union-attr]
    click.echo(
        f"Rendered PDF ({canvas.width:g}×{canvas.height:g} {canvas.units}) → {output_path}"
    )


# ---------------------------------------------------------------------------
# mdf validate
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--level",
    type=click.Choice(["1", "2", "3"]),
    default=None,
    help="Conformance level to validate against (default: use level declared in document)",
)
def validate(input_file: str, level: Optional[str]) -> None:
    """Validate an MDF document against the spec requirements."""
    # ---- Parse ----
    try:
        doc = parse_file(input_file)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except MDFParseError as exc:
        click.echo(f"  INVALID — parse error: {exc}", err=True)
        sys.exit(1)

    errors: list[str] = []
    warnings: list[str] = []

    manifest = doc.manifest
    target_level = int(level) if level else manifest.conformance_level

    # ---- Level 1 checks (basic) ----
    if not doc.canvases:
        errors.append("Document must contain at least one <canvas> element")

    for idx, canvas in enumerate(doc.canvases):
        label = f"Canvas[{idx}]"

        if canvas.width <= 0:
            errors.append(f"{label}: width must be > 0 (got {canvas.width})")
        if canvas.height <= 0:
            errors.append(f"{label}: height must be > 0 (got {canvas.height})")
        if not canvas.boundary_path:
            errors.append(f"{label}: boundary path is empty")
        if not canvas.units:
            warnings.append(f"{label}: units not specified, defaulting to mm")
        if not canvas.layers:
            warnings.append(f"{label}: canvas has no layers")

    # ---- Level 2 checks (print) ----
    if target_level >= 2:
        if manifest.print_intent is None:
            errors.append(
                "Level 2 (print) conformance requires a <print:intent> in the manifest"
            )
        for idx, canvas in enumerate(doc.canvases):
            label = f"Canvas[{idx}]"
            if canvas.die_cut and canvas.bleed <= 0:
                warnings.append(
                    f"{label}: die-cut document has no bleed specified — "
                    "print shops typically require ≥3mm bleed"
                )

    # ---- Level 3 checks (full) ----
    if target_level >= 3:
        if not manifest.fonts:
            warnings.append(
                "Level 3 (full) documents should embed fonts in the manifest"
            )

    # ---- Report ----
    if errors:
        click.echo(f"  INVALID — {len(errors)} error(s) found:")
        for err in errors:
            click.echo(f"    ✗ {err}")
        if warnings:
            click.echo(f"  {len(warnings)} warning(s):")
            for w in warnings:
                click.echo(f"    ! {w}")
        sys.exit(1)
    else:
        level_names = {1: "Basic", 2: "Print", 3: "Full"}
        level_name = level_names.get(target_level, f"Level {target_level}")
        click.echo(
            f"  Valid MDF Level {target_level} ({level_name}) document"
        )
        if warnings:
            click.echo(f"  {len(warnings)} warning(s):")
            for w in warnings:
                click.echo(f"    ! {w}")


# ---------------------------------------------------------------------------
# mdf info
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
def info(input_file: str) -> None:
    """Print document metadata and structure."""
    # ---- Parse ----
    try:
        doc = parse_file(input_file)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except MDFParseError as exc:
        click.echo(f"Parse error: {exc}", err=True)
        sys.exit(1)

    manifest = doc.manifest
    level_names = {1: "Basic", 2: "Print", 3: "Full"}

    click.echo(f"MDF Document: {input_file}")
    click.echo(f"  MDF version:       {doc.version}")
    click.echo(f"  Title:             {manifest.title or '(none)'}")
    click.echo(f"  Author:            {manifest.author or '(none)'}")
    click.echo(f"  Created:           {manifest.created or '(none)'}")
    click.echo(f"  Language:          {manifest.language}")
    lvl = manifest.conformance_level
    click.echo(f"  Conformance level: {lvl} ({level_names.get(lvl, 'Unknown')})")

    # Print intent
    if manifest.print_intent:
        pi = manifest.print_intent
        click.echo(f"  Print intent:      {pi.color_mode.upper()} / {pi.substrate} / {pi.resolution_target}")

    # Fonts
    if manifest.fonts:
        click.echo(f"  Fonts ({len(manifest.fonts)}):")
        for fid, font in manifest.fonts.items():
            embed_flag = " [embedded]" if font.embed else ""
            click.echo(f"    {fid}: {font.family} {font.weight} {font.style}{embed_flag}")
    else:
        click.echo("  Fonts:             (none)")

    # ICC profiles
    if manifest.icc_profiles:
        click.echo(f"  ICC profiles ({len(manifest.icc_profiles)}):")
        for pid in manifest.icc_profiles:
            click.echo(f"    {pid}")

    # Spot colors
    if manifest.spot_colors:
        click.echo(f"  Spot colors ({len(manifest.spot_colors)}):")
        for sc in manifest.spot_colors.values():
            c, m, y, k = sc.cmyk_approximation
            click.echo(f"    {sc.id}: {sc.name}  cmyk({c:.2f} {m:.2f} {y:.2f} {k:.2f})")

    # Canvases
    click.echo(f"  Canvases ({len(doc.canvases)}):")
    for idx, canvas in enumerate(doc.canvases):
        cid = canvas.id or f"(canvas {idx})"
        click.echo(f"    [{idx}] id={cid}  {canvas.width:g}×{canvas.height:g} {canvas.units}")

        if canvas.shape_type:
            meaning = canvas.shape_meaning or ""
            click.echo(f"         shape: {canvas.shape_type}" + (f"  ({meaning})" if meaning else ""))

        if canvas.die_cut:
            click.echo(f"         die-cut: {canvas.die_cut_type}  bleed={canvas.bleed:g}{canvas.units}")

        # Boundary path (truncated)
        bp = canvas.boundary_path
        bp_display = bp if len(bp) <= 80 else bp[:77] + "..."
        click.echo(f"         boundary: {bp_display}")

        # Layers
        click.echo(f"         layers ({len(canvas.layers)}):")
        for layer in canvas.layers:
            lid = layer.id or "(unnamed)"
            visible_flag = "" if layer.visible else " [hidden]"
            blend_flag = f" blend={layer.blend_mode}" if layer.blend_mode != "normal" else ""
            opacity_flag = f" opacity={layer.opacity:g}" if layer.opacity < 1.0 else ""
            n_els = len(layer.elements)
            click.echo(
                f"           {lid}{visible_flag}{blend_flag}{opacity_flag}"
                f"  ({n_els} element{'s' if n_els != 1 else ''})"
            )

        if canvas.cut_lines:
            click.echo(f"         cut-lines ({len(canvas.cut_lines)}):")
            for cl in canvas.cut_lines:
                click.echo(f"           {cl.id}: {cl.cut_type}")

        if canvas.folds:
            click.echo(f"         folds ({len(canvas.folds)}):")
            for fl in canvas.folds:
                click.echo(f"           {fl.id}: {fl.fold_type} {fl.angle}°")


# ---------------------------------------------------------------------------
# mdf pack / unpack (stub — future work)
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--output", default=None, help="Output .mdfx file path")
def pack(input_dir: str, output: Optional[str]) -> None:
    """Pack a directory into an .mdfx bundle."""
    click.echo(f"Packing {input_dir}...")
    click.echo("Pack not yet implemented. Coming in v0.2.")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", default=None, help="Output directory path")
def unpack(input_file: str, output: Optional[str]) -> None:
    """Unpack an .mdfx bundle to a directory."""
    click.echo(f"Unpacking {input_file}...")
    click.echo("Unpack not yet implemented. Coming in v0.2.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
