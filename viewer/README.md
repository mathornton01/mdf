# MDF Viewer

A free, client-side web viewer for **Morphous Document Format** (`.mdf`) files.

## Usage

### Opening the viewer

Open `index.html` directly in any modern browser — no server, no install, no build step required. Works from `file://` URLs.

### Loading a document

- **Drag and drop** an `.mdf` file onto the viewer window, or
- Click **Open .mdf File** in the header, or
- Press `Ctrl+O` / `Cmd+O`

### Navigation

| Action | Controls |
|--------|----------|
| Zoom in | `+` key or scroll wheel up |
| Zoom out | `−` key or scroll wheel down |
| Fit to window | `0` key or ⊡ button |
| Fine zoom | Zoom buttons in the toolbar |

### Demo mode

Add `?demo` to the URL to load a built-in circular badge document without needing an `.mdf` file:

```
file:///path/to/viewer/index.html?demo
```

## What the viewer renders

| MDF element | SVG output |
|-------------|------------|
| `<circle>`  | `<circle>` |
| `<rect>`    | `<rect>` |
| `<line>`    | `<line>` |
| `<path>` / `<shape>` | `<path>` |
| `<text-block>` + `<p>` | `<text>` / `<tspan>` |
| `<image>` (URL/data URI) | `<image>` |
| `<group>` | `<g>` with transform |
| `canvas boundary` | SVG `<clipPath>` |

### Color support

- `color(cmyk C M Y K)` — converted to RGB using the standard formula
- `color(gray V)` — converted to RGB
- `cmyk(C M Y K)` — same conversion
- `#rrggbb` / `#rrggbbaa` — passed through
- `rgb()` / `rgba()` — passed through
- `lab(L a b)` — approximate sRGB via CIE XYZ transform

### What is skipped

- Print-only layers: `registration-marks`, `foil-plate`, `emboss-plate`, layers with `print:visible-in-render="false"`
- Layers with `visible="false"`
- Font assets at `fonts/` paths or `mdfx:` URIs (falls back to `serif`/`sans-serif`)
- `spot()` color notation (rendered as a semi-transparent blue placeholder)

## Browser support

Any browser with SVG and ES2017 support: Chrome 60+, Firefox 60+, Safari 12+, Edge 18+.

## Implementation notes

- Pure vanilla HTML/CSS/JS — zero dependencies, zero build tooling
- Namespace-aware XML parsing via `DOMParser` with `application/xml`
- Attributes are resolved using `localName` matching and `getAttributeNS` for robustness across namespace implementations
- Text blocks are positioned using the `<reflow-region>` bounding box; full scanline reflow is not performed (browser text layout is used instead)
- Zoom is implemented via CSS `width`/`height` on the SVG element, preserving the `viewBox` coordinate space
