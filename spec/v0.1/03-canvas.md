# MDF Specification v0.1 — Chapter 3: Canvas and Shape Boundary

## 3.1 The Canvas Element

The `<canvas>` element is the root geometric container of an MDF document. It defines:

- The physical dimensions of the document
- The boundary path — the shape of the document
- The coordinate space for all child content
- Print production geometry (bleed, die-cut)
- Semantic meaning of the shape

There MUST be exactly one `<canvas>` element in an MDF document, as a direct child of the root `<mdf>` element, following the `<manifest>`.

## 3.2 Canvas Attributes

```xml
<canvas
  width="210mm"
  height="297mm"
  units="mm"
  boundary="M 0,0 L 210,0 L 210,297 L 0,297 Z"
  print:die-cut="false"
  print:bleed="3mm"
  sem:shape-type="polygon"
  sem:shape-meaning="standard-a4">
```

| Attribute | Required | Description |
|-----------|----------|-------------|
| `width`   | Yes | Width of the bounding box, in `units` |
| `height`  | Yes | Height of the bounding box, in `units` |
| `units`   | Yes | `mm`, `cm`, `in`, `pt`, `px` |
| `boundary` | Yes | SVG path data string defining the document shape |
| `print:die-cut` | Level 2 | If `true`, the boundary path is also the die-cut line |
| `print:bleed`   | Level 2 | Bleed extension distance (e.g. `3mm`) |
| `sem:shape-type` | Recommended | Geometric class of the shape (see §3.6) |
| `sem:shape-meaning` | Recommended | Semantic meaning of the shape (see §3.6) |

## 3.3 Coordinate Space

The canvas coordinate space has its origin at the top-left corner of the bounding box. The positive X axis points right; the positive Y axis points down. Units are as declared in the `units` attribute.

The `width` and `height` attributes define the bounding box of the boundary path. The boundary path MUST fit within this bounding box.

All child element coordinates are in this same space.

## 3.4 The Boundary Path

The `boundary` attribute contains SVG path data (as defined in the SVG 2 specification, section 9.3). MDF supports a subset of SVG path commands:

| Command | Name | Support |
|---------|------|---------|
| `M`/`m` | moveto | Required |
| `L`/`l` | lineto | Required |
| `H`/`h` | horizontal lineto | Required |
| `V`/`v` | vertical lineto | Required |
| `C`/`c` | cubic Bézier | Required |
| `S`/`s` | smooth cubic Bézier | Required |
| `Q`/`q` | quadratic Bézier | Required |
| `T`/`t` | smooth quadratic Bézier | Required |
| `A`/`a` | elliptical arc | Required |
| `Z`/`z` | closepath | Required |

### 3.4.1 Path Constraints

For Level 1 and Level 2 conformance, the boundary path MUST be:

- **Closed**: the path MUST end with a `Z`/`z` command.
- **Simply connected**: the path MUST form a single region with no holes.
- **Non-self-intersecting**: the path MUST NOT cross itself.

Level 3 conformance allows compound paths (holes and multiple sub-paths).

### 3.4.2 Path Normalization

A processor SHOULD normalize the boundary path before rendering:

1. Convert all relative commands to absolute
2. Decompose `S`, `T` shorthand commands
3. Convert arcs to cubic Bézier approximations (for internal use)

The normalized form is for internal use only; the original path data MUST be preserved in serialization.

## 3.5 Boundary and Clipping

All content layers are clipped to the boundary path. A renderer MUST NOT render content outside the boundary path. This clipping is applied after all layer compositing.

When `print:die-cut="true"`, the boundary path is also interpreted as the die-cut line for print production. See Chapter 9 (Print Production) for details.

## 3.6 Semantic Shape Attributes

The `sem:shape-type` and `sem:shape-meaning` attributes provide machine-readable semantics for the document shape.

### 3.6.1 Shape Type Vocabulary

`sem:shape-type` describes the geometric class:

| Value | Description |
|-------|-------------|
| `rectangle` | Four-sided polygon with right angles |
| `polygon` | Closed polygon with straight edges |
| `circle` | Perfect circle |
| `ellipse` | Ellipse |
| `rounded-rectangle` | Rectangle with rounded corners |
| `organic` | Freeform Bézier shape with no geometric regularity |
| `compound` | Multiple sub-paths (Level 3 only) |

### 3.6.2 Shape Meaning Vocabulary

`sem:shape-meaning` describes the document's role or identity. This is the semantic innovation of MDF — the shape communicates meaning.

Built-in vocabulary:

| Value | Description |
|-------|-------------|
| `page-a4` | Standard ISO A4 page |
| `page-letter` | US Letter page |
| `business-card` | Standard business card |
| `badge` | Wearable badge or name tag |
| `sticker` | Adhesive sticker |
| `label` | Product or shipping label |
| `label-bottle` | Wraparound bottle label |
| `label-can` | Wraparound can label |
| `tag` | Hang tag or price tag |
| `envelope` | Mailing envelope |
| `poster` | Large-format poster |
| `banner` | Wide-format banner |
| `card` | Generic greeting/info card |
| `certificate` | Certificate or diploma |
| `voucher` | Coupon or voucher |
| `ticket` | Event ticket |
| `bookmark` | Bookmark |
| `coaster` | Drink coaster |
| `custom` | User-defined (use `sem:shape-meaning-iri` for custom vocabulary) |

For custom meanings, use `sem:shape-meaning="custom"` and provide an IRI:

```xml
<canvas ... sem:shape-meaning="custom"
            sem:shape-meaning-iri="https://example.com/shapes/guitar-pick"/>
```

## 3.7 Multiple Canvases (Multi-Page Documents)

A multi-page MDF document uses a `<document>` wrapper containing multiple `<canvas>` elements:

```xml
<mdf version="0.1" ...>
  <manifest>...</manifest>
  <document>
    <canvas id="front" width="90mm" height="50mm" ...>
      <!-- front of business card -->
    </canvas>
    <canvas id="back" width="90mm" height="50mm" ...>
      <!-- back of business card -->
    </canvas>
  </document>
</mdf>
```

Each canvas is independent — it can have a different shape, size, and semantic meaning.

## 3.8 Examples

### Rectangular A4 Page

```xml
<canvas width="210" height="297" units="mm"
        boundary="M 0,0 L 210,0 L 210,297 L 0,297 Z"
        sem:shape-meaning="page-a4"/>
```

### Circular Badge

```xml
<canvas width="100" height="100" units="mm"
        boundary="M 50,0 A 50,50 0 1,1 50,0.001 Z"
        print:die-cut="true"
        print:bleed="3mm"
        sem:shape-type="circle"
        sem:shape-meaning="badge"/>
```

### Die-Cut Star Sticker

```xml
<canvas width="80" height="80" units="mm"
        boundary="M 40,0 L 49,27 L 77,27 L 55,43 L 63,70 L 40,54 L 17,70 L 25,43 L 3,27 L 31,27 Z"
        print:die-cut="true"
        print:bleed="3mm"
        sem:shape-type="polygon"
        sem:shape-meaning="sticker"/>
```
