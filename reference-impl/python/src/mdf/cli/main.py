"""
MDF CLI — mdf command-line tool

Commands:
  mdf render <file.mdf>   — render to PNG/SVG/PDF
  mdf validate <file.mdf> — validate against schema
  mdf pack <dir/>         — pack a directory into .mdfx bundle
  mdf unpack <file.mdfx>  — unpack .mdfx bundle to directory
  mdf info <file.mdf>     — print document metadata
"""

import click


@click.group()
@click.version_option(version="0.1.0", prog_name="mdf")
def cli():
    """MDF — Morphous Document Format tools."""
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", default=None, help="Output file path")
@click.option("-f", "--format", "output_format",
              type=click.Choice(["png", "svg", "pdf"]), default="png",
              help="Output format (default: png)")
@click.option("--dpi", default=150, help="Resolution for raster output (default: 150)")
@click.option("--proof", is_flag=True, help="Show bleed and marks in output")
def render(input_file, output, output_format, dpi, proof):
    """Render an MDF document to an image or PDF."""
    click.echo(f"Rendering {input_file} to {output_format}...")
    # TODO: implement
    click.echo("Renderer not yet implemented. Coming in v0.2.")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--level", type=click.Choice(["1", "2", "3"]), default="1",
              help="Conformance level to validate against (default: 1)")
def validate(input_file, level):
    """Validate an MDF document against the spec schema."""
    click.echo(f"Validating {input_file} (Level {level})...")
    # TODO: implement
    click.echo("Validator not yet implemented. Coming in v0.1.")


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--output", default=None, help="Output .mdfx file path")
def pack(input_dir, output):
    """Pack a directory into an .mdfx bundle."""
    click.echo(f"Packing {input_dir}...")
    # TODO: implement
    click.echo("Pack not yet implemented. Coming in v0.1.")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", default=None, help="Output directory path")
def unpack(input_file, output):
    """Unpack an .mdfx bundle to a directory."""
    click.echo(f"Unpacking {input_file}...")
    # TODO: implement
    click.echo("Unpack not yet implemented. Coming in v0.1.")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
def info(input_file):
    """Print document metadata and structure."""
    click.echo(f"MDF Document: {input_file}")
    # TODO: implement parser and print manifest info
    click.echo("Info not yet implemented. Coming in v0.1.")


if __name__ == "__main__":
    cli()
