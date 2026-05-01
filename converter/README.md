# pdf2mdf — PDF to MDF Converter

Converts PDF files to **MDF (Morphous Document Format)** — a structured XML format at `https://morphousdoc.org/ns/0.1`. Works entirely offline with no external API calls.

---

## Requirements

- Python 3.10 or later
- [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`) — free and open-source

---

## Installation

```bash
pip install pymupdf
```

Or from the requirements file:

```bash
pip install -r requirements.txt
```

---

## Usage

```
python pdf2mdf.py INPUT.pdf [OUTPUT] [options]
```

### Arguments

| Argument | Description |
|---|---|
| `INPUT.pdf` | Path to the input PDF file |
| `OUTPUT` | Output path: a `.mdf` file (single page) or a directory (multi-page). Defaults to `<stem>_mdf/` |

### Options

| Option | Description |
|---|---|
| `--page N` | Convert only page N (1-based). Default: all pages |
| `--single` | (Future) All pages in one .mdf file; currently outputs a folder |
| `--quality HIGH\|MEDIUM\|LOW` | Image DPI: HIGH=150 (default), MEDIUM=96, LOW=72 |
| `--no-images` | Skip image extraction |
| `--verbose` | Print conversion progress to stdout |

---

## Examples

**Convert an entire PDF to a folder of per-page .mdf files:**
```bash
python pdf2mdf.py document.pdf
# Output: document_mdf/page-1.mdf, page-2.mdf, ..., manifest.json
```

**Convert to a named output directory:**
```bash
python pdf2mdf.py document.pdf output_dir/
```

**Convert a single page to one .mdf file:**
```bash
python pdf2mdf.py document.pdf page1.mdf
# Converts page 1 only (warns if multi-page)
```

**Convert only page 3:**
```bash
python pdf2mdf.py document.pdf --page 3
# Output: document_mdf/page-3.mdf
```

**Convert without images:**
```bash
python pdf2mdf.py document.pdf --no-images --verbose
```

**Lower-quality images (faster):**
```bash
python pdf2mdf.py document.pdf --quality LOW
```

---

## Output Structure

### Single page (`.mdf` output)
```
output.mdf
images/
  page-1-img-0.jpg
  page-1-img-1.jpg
```

### Multi-page (directory output)
```
output_dir/
  manifest.json
  page-1.mdf
  page-2.mdf
  ...
  images/
    page-1-img-0.jpg
    page-2-img-0.jpg
```

### manifest.json
```json
{
  "source": "document.pdf",
  "total_pages": 3,
  "converted": "2026-05-01T00:00:00Z",
  "pages": [
    { "page": 1, "file": "page-1.mdf" },
    { "page": 2, "file": "page-2.mdf" },
    { "page": 3, "file": "page-3.mdf" }
  ]
}
```

---

## MDF Format Overview

Each converted PDF page becomes a `<canvas>` element:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mdf version="0.1"
     xmlns="https://morphousdoc.org/ns/0.1"
     xmlns:print="https://morphousdoc.org/ns/print/0.1"
     xmlns:sem="https://morphousdoc.org/ns/semantics/0.1"
     xmlns:meta="https://morphousdoc.org/ns/meta/0.1">
  <manifest>
    <meta:title>My Document</meta:title>
    <meta:author>Author Name</meta:author>
    <meta:created>2026-05-01T00:00:00Z</meta:created>
    <meta:language>en-US</meta:language>
    <conformance level="screen"/>
    <assets>
      <font id="font-0" family="Helvetica" weight="400" src="" embed="false"/>
    </assets>
  </manifest>

  <canvas width="210.0" height="297.0" units="mm"
          boundary="M 0,0 L 210.0,0 L 210.0,297.0 L 0,297.0 Z"
          sem:shape-type="polygon"
          sem:shape-meaning="standard-a4">
    <layers>
      <layer id="content" blend-mode="normal">
        <text-block id="block-0" font-ref="font-0" size="12pt" leading="14.4pt"
                    text-align="left" color="color(cmyk 0 0 0 1)">
          <reflow-region shape="M 20,20 L 190,20 L 190,50 L 20,50 Z" padding="0"/>
          <p><span id="span-0-0" font-ref="font-0" size="12pt" color="color(cmyk 0.000 0.000 0.000 1.000)">Hello, world</span></p>
        </text-block>
        <image src="images/page-1-img-0.jpg" x="50" y="100" width="110" height="80"/>
      </layer>
    </layers>
  </canvas>
</mdf>
```

### Page shape detection

| Shape | Width (mm) | Height (mm) |
|---|---|---|
| `standard-a4` | 210 | 297 |
| `standard-a4-landscape` | 297 | 210 |
| `standard-a3` | 297 | 420 |
| `standard-letter` | 215.9 | 279.4 |
| `standard-legal` | 215.9 | 355.6 |
| `custom` | any other | |

---

## Running Tests

Tests work without any PDF files (the fitz module is stubbed if not installed):

```bash
python test_converter.py
# or
python -m pytest test_converter.py -v
```

---

## Notes

- Runs fully offline — no internet connection required after installation
- PyMuPDF is free software (AGPL-3.0); see [pymupdf.readthedocs.io](https://pymupdf.readthedocs.io/)
- PDF text colors are converted from RGB to CMYK automatically
- Font subset prefixes (e.g. `ABCDEF+`) are stripped from family names
- Visually adjacent text blocks (within 2pt vertical gap, overlapping horizontally) are merged into a single `<text-block>` for cleaner output
- Reading order is preserved (PyMuPDF returns blocks top-to-bottom, left-to-right)
