# MDF Specification v0.1 — Chapter 5: Typography and Shape Reflow

## 5.1 Overview

MDF's typography system is built around **shape-aware text reflow**: text flows inside an arbitrary shape boundary, not just a rectangle. This is the core typographic innovation that enables the format's shape-native design goals.

A `<text-block>` element contains text content and declares a `<reflow-region>` that defines the shape the text flows within. The renderer is responsible for calculating line widths at each vertical position and packing glyphs accordingly.

## 5.2 Text Block

```xml
<text-block id="body-copy"
            font-ref="body-font"
            size="10pt"
            leading="14pt"
            language="en-US"
            text-align="justify"
            direction="ltr">

  <reflow-region shape="M 20,20 A 80,80 0 1,1 20,20.001 Z"
                 padding="8pt"
                 padding-top="12pt"/>

  <p>The quick brown fox jumps over the lazy dog.</p>
  <p>Lorem ipsum dolor sit amet...</p>

</text-block>
```

### 5.2.1 Text Block Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `id` | Recommended | — | Unique identifier |
| `font-ref` | Yes | — | Reference to a declared font |
| `size` | Yes | — | Font size (pt, px, mm) |
| `leading` | No | 120% of size | Line height |
| `language` | Recommended | `und` | BCP 47 language tag, for hyphenation |
| `text-align` | No | `start` | `start`, `end`, `center`, `justify` |
| `direction` | No | `ltr` | `ltr`, `rtl`, `ttb` (top-to-bottom) |
| `column-count` | No | `1` | Number of text columns within the reflow region |
| `column-gap` | No | `1em` | Gap between columns |
| `orphans` | No | `2` | Minimum lines at bottom of region |
| `widows` | No | `2` | Minimum lines at top of continuation |

## 5.3 Reflow Region

The `<reflow-region>` element defines the shape that text flows within.

```xml
<reflow-region
  shape="M 20,20 A 80,80 0 1,1 20,20.001 Z"
  shape-ref="canvas-boundary"
  padding="8pt"
  padding-top="16pt"
  padding-right="8pt"
  padding-bottom="8pt"
  padding-left="8pt"/>
```

| Attribute | Description |
|-----------|-------------|
| `shape` | Inline SVG path data for the reflow region |
| `shape-ref` | ID reference to a shape defined elsewhere; `canvas-boundary` is a reserved ID for the canvas boundary path |
| `padding` | Uniform inset from the shape boundary |
| `padding-top/right/bottom/left` | Per-side padding (override `padding`) |

A `<reflow-region>` MUST have either `shape` or `shape-ref`, but not both.

### 5.3.1 Canvas Boundary Reference

The reserved value `shape-ref="canvas-boundary"` instructs the renderer to use the canvas boundary path as the reflow region (minus padding). This is the most common case: text fills the document shape.

```xml
<reflow-region shape-ref="canvas-boundary" padding="10mm"/>
```

## 5.4 The Shape Reflow Algorithm

This section is normative. All Level 1+ conformant renderers MUST implement this algorithm.

### 5.4.1 Inputs

- `P`: the reflow region path (after applying padding inset)
- `font`: the font face and size
- `leading`: the line height
- `text`: the sequence of Unicode codepoints to lay out
- `language`: BCP 47 language tag for hyphenation

### 5.4.2 Scanline Tessellation

1. Compute the bounding box `[x0, y0, x1, y1]` of path `P`.
2. Starting at `y = y0 + baseline_offset`, stepping by `leading`, compute scanlines.
3. For each scanline at height `y`:
   a. Cast a horizontal ray across the bounding box at height `y`.
   b. Compute all intersection points of the ray with path `P`.
   c. Sort intersections by x-coordinate.
   d. Apply the even-odd fill rule to determine which intervals are inside `P`.
   e. The union of inside intervals is the **available line slot** for this scanline.
4. Discard scanlines with total available width less than `min-line-width` (default: 2× em-size).

### 5.4.3 Glyph Packing

For each scanline slot (from §5.4.2):

1. Determine the available width `W` for this slot.
2. Using the HarfBuzz-compatible text shaping pipeline:
   a. Apply Unicode bidirectional algorithm (UBA, Unicode TR#9) to the text run.
   b. Apply font-specific GSUB/GPOS substitutions and positioning.
3. Greedily pack glyphs into the slot width `W`:
   a. Add glyphs until the next glyph would exceed `W`.
   b. If `text-align` is `justify` and this is not the last line, distribute remaining space among word spaces.
   c. If `text-align` is not `justify`, position according to `start`/`end`/`center`.
4. If a word does not fit and `language` hyphenation is available:
   a. Find the hyphenation point closest to the break that allows the word to fit.
   b. Insert a soft hyphen glyph at that point.

### 5.4.4 Overflow

If text content exceeds the reflow region, the overflow text is:
- Discarded (default, `overflow="clip"`)
- Flowed into a linked text block (`overflow="link" overflow-ref="next-block-id"`)

Linked text flow allows multi-column layouts and multi-region document designs.

```xml
<text-block id="col1" ...>
  <reflow-region .../>
  <overflow mode="link" target="col2"/>
  <p>Long article text...</p>
</text-block>

<text-block id="col2" ...>
  <reflow-region shape="..." />
  <!-- content flows in from col1 -->
</text-block>
```

## 5.5 Font Declarations

Fonts MUST be declared in the manifest before use:

```xml
<manifest>
  <assets>
    <font id="body-font"
          family="Inter"
          weight="400"
          style="normal"
          src="fonts/Inter-Regular.woff2"
          format="woff2"
          embed="true"/>
    <font id="heading-font"
          family="Inter"
          weight="700"
          style="normal"
          src="fonts/Inter-Bold.woff2"
          format="woff2"
          embed="true"/>
  </assets>
</manifest>
```

Font formats supported: `woff2` (preferred), `woff`, `otf`, `ttf`.

The `embed="true"` attribute indicates the font binary is embedded in the document (in the `.mdfx` bundle or as a data URI in a plain `.mdf`). A Level 2 (print) conformant document MUST embed all fonts.

## 5.6 Text Styles

Text style properties can be applied inline on paragraph and span elements:

```xml
<p font-ref="heading-font" size="18pt" leading="22pt" color="color(cmyk 0 0 0 1)">
  Section Heading
</p>
<p>
  Normal text with <span font-ref="body-font" style="italic" color="color(cmyk 0 0 0 0.6)">
  emphasized text</span> inline.
</p>
```

## 5.7 Vertical Text

For top-to-bottom text (CJK vertical writing modes), set `direction="ttb"`. The scanline algorithm runs in the X direction instead of Y:

- Scanlines are vertical (constant X, varying Y)
- Available column slot heights replace available line widths
- The leading is applied horizontally

RTL text (`direction="rtl"`) uses the standard scanline algorithm but applies the Unicode Bidirectional Algorithm to reverse glyph order within each line slot.
