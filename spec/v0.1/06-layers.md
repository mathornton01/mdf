# MDF Specification v0.1 — Chapter 6: Layer Model

## 6.1 Overview

The MDF layer model provides compositing control, organizes document content into
named stacking contexts, and separates print production plates from design content.
Layers are structurally similar to layers in raster editing applications (Photoshop,
Illustrator) but are fully and precisely specified here so that independent renderer
implementations produce identical compositing results.

Layers serve three distinct functions in MDF:

1. **Compositing control** — each layer has a blend mode and opacity that govern how
   its contents interact with the layers beneath it. Isolation groups (§6.7.3) allow
   complex multi-layer effects without unexpected bleed-through.

2. **Content organization** — layers provide a named, ordered structure for document
   elements, enabling editors to present a meaningful layer panel to users and to
   implement selective visibility, locking, and export.

3. **Print plate separation** — the `print:role` attribute assigns semantic production
   roles to layers (spot-color plate, foil plate, die-cut overlay, registration marks).
   A print processor uses these roles to generate the correct separations and overlays
   for press output (see §6.8 and Chapter 9).

All layers are children of a `<canvas>` element. Layers are composited in document
order: the first `<layer>` element in document order is the bottommost layer; the
last is the topmost. Within a layer, elements composite in document order (first
element = bottom).

## 6.2 Layer Element

```xml
<layer
  id="design-content"
  blend-mode="normal"
  opacity="1.0"
  visible="true"
  lock="false"
  print:role="body"
  print:visible-in-render="true"
  print:overprint="false">

  <!-- child elements: text-block, image, shape, group, layer -->

</layer>
```

### 6.2.1 Layer Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `id` | Recommended | — | Unique identifier for this layer within the document |
| `blend-mode` | No | `normal` | Compositing blend mode (see §6.2.2) |
| `opacity` | No | `1.0` | Layer opacity, range `[0.0, 1.0]` |
| `visible` | No | `true` | If `false`, the layer is not rendered |
| `lock` | No | `false` | Editorial hint; if `true`, editors SHOULD prevent modification |
| `print:role` | No | `body` | Semantic print production role (see §6.2.3) |
| `print:visible-in-render` | No | `true` | If `false`, layer is excluded from screen renders and exported proofs (see §6.2.4) |
| `print:overprint` | No | `false` | If `true`, layer contents overprint rather than knock out (see §6.2.5) |

The `lock` attribute is an editorial metadata hint only. A conformant renderer MUST
render locked layers identically to unlocked layers.

### 6.2.2 Blend Modes

The `blend-mode` attribute accepts the following values, which correspond directly to
the CSS Compositing and Blending Level 1 specification (W3C CR 2015). Renderers MUST
implement all modes listed as Required; MAY implement modes listed as Optional.

| Value | Required | Description |
|-------|----------|-------------|
| `normal` | Yes | Standard alpha compositing (Porter-Duff source-over) |
| `multiply` | Yes | Multiplies color channels; darkens |
| `screen` | Yes | Inverse of multiply; lightens |
| `overlay` | Yes | Multiply or screen depending on base |
| `darken` | Yes | Selects darker of base and blend |
| `lighten` | Yes | Selects lighter of base and blend |
| `color-dodge` | Yes | Brightens base to reflect blend |
| `color-burn` | Yes | Darkens base to reflect blend |
| `hard-light` | Yes | Overlay with source and destination swapped |
| `soft-light` | Yes | Softer version of hard-light |
| `difference` | Yes | Absolute difference of channels |
| `exclusion` | Yes | Lower-contrast version of difference |
| `hue` | Yes | Hue of blend, luminance+chroma of base |
| `saturation` | Yes | Saturation of blend, hue+luminance of base |
| `color` | Yes | Hue+saturation of blend, luminance of base |
| `luminosity` | Yes | Luminance of blend, hue+saturation of base |
| `dissolve` | Optional | Probabilistic pixel selection by opacity |
| `pass-through` | Yes | Nested layer composites into parent context, not isolated group |

The `pass-through` mode is valid only on nested `<layer>` elements (layers that are
children of another layer). A `pass-through` nested layer does not create an
isolation group; its elements composite directly into the parent layer's compositing
stack. A top-level layer MUST NOT have `blend-mode="pass-through"`; if a conformant
parser encounters this, it MUST treat the value as `normal`.

A processor that encounters an unknown `blend-mode` value MUST treat it as `normal`
and SHOULD emit a warning.

### 6.2.3 Print Role Values

The `print:role` attribute assigns a semantic production role to a layer. These roles
are used by print processors (§8.5) to generate correct press output.

| Value | Description |
|-------|-------------|
| `body` | Standard design content (default) |
| `die-cut-overlay` | Die-cut shape overlay; defines the cut path for production |
| `bleed-content` | Content that extends into the bleed zone |
| `registration-marks` | Registration and crop marks (see §6.8.2) |
| `spot-color-plate` | Spot color separation plate (see §6.8.3) |
| `foil-plate` | Foil coverage map (see §6.8.4) |
| `emboss-plate` | Emboss/deboss coverage and depth map (see §6.8.5) |
| `overprint-preview` | Simulated overprint preview composite; not output to press |

A document MAY contain multiple layers with the same `print:role`. For example, a
document with two spot colors will have two layers each with `print:role="spot-color-plate"`.

### 6.2.4 Visibility in Render

The `print:visible-in-render` attribute controls whether the layer participates in
screen rendering and raster export. When `false`, the layer is output only in
print-specific contexts (plate separation, press PDF generation).

| `visible` | `print:visible-in-render` | Screen render | Print output |
|-----------|--------------------------|---------------|--------------|
| `true` | `true` | Yes | Yes |
| `true` | `false` | No | Yes |
| `false` | `true` | No | No |
| `false` | `false` | No | No |

Layers with `print:role="registration-marks"` SHOULD default to
`print:visible-in-render="false"` unless a proof render has been explicitly requested
(see §6.8.2).

### 6.2.5 Overprint

When `print:overprint="true"`, the layer's elements are rendered using overprint
compositing rather than knockout. In overprint mode, the layer's ink values are added
to the ink values already present on the substrate rather than replacing them. This
is a print-production concept; in screen rendering, overprint is simulated by
compositing the layer contents using the `multiply` blend mode.

A renderer MUST NOT interpret `print:overprint` on a layer with `print:role` values
other than `body`, `spot-color-plate`, or `foil-plate`.

## 6.3 Layer Contents

A `<layer>` element MAY contain any combination of the following child elements, in
any order:

| Element | Description |
|---------|-------------|
| `<text-block>` | A block of text that reflows within a shape (Chapter 5) |
| `<image>` | A raster or vector image asset (§6.5) |
| `<shape>` | A vector shape element (§6.4) |
| `<group>` | A transform/compositing group (§6.6) |
| `<layer>` | A nested layer (see §6.7.3 for isolation behavior) |

Child elements composite in document order within the layer: the first child is
rendered first (bottommost); the last child is rendered last (topmost). An empty
`<layer>` is valid and MUST be rendered as fully transparent.

## 6.4 Shape Element

The `<shape>` element is the fundamental vector graphics primitive in MDF. It
represents a single filled and/or stroked path.

```xml
<shape
  id="background-blob"
  path="M 20,20 C 60,0 140,0 180,20 C 200,60 200,140 180,180 C 140,200 60,200 20,180 C 0,140 0,60 20,20 Z"
  fill="color(cmyk 0.05 0.12 0.30 0.00)"
  stroke="color(cmyk 0 0 0 1)"
  stroke-width="0.5pt"
  stroke-linecap="round"
  stroke-linejoin="round"
  opacity="1.0"
  blend-mode="normal"
  print:surface-treatment="none"/>
```

### 6.4.1 Shape Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `id` | Recommended | — | Unique identifier |
| `path` | Yes | — | SVG path data string (same command subset as canvas boundary, §3.4) |
| `fill` | No | `none` | Fill color using MDF color syntax (Chapter 4), or `none` |
| `fill-rule` | No | `nonzero` | Fill rule for self-intersecting paths: `nonzero` or `evenodd` |
| `stroke` | No | `none` | Stroke color using MDF color syntax, or `none` |
| `stroke-width` | No | `1pt` | Stroke width with unit suffix |
| `stroke-linecap` | No | `butt` | End cap style: `butt`, `round`, `square` |
| `stroke-linejoin` | No | `miter` | Join style: `miter`, `round`, `bevel` |
| `stroke-miterlimit` | No | `4` | Miter limit (dimensionless ratio) |
| `stroke-dasharray` | No | `none` | Dash pattern: space-separated lengths with unit suffixes, or `none` |
| `stroke-dashoffset` | No | `0` | Dash offset with unit suffix |
| `opacity` | No | `1.0` | Element opacity `[0.0, 1.0]`, applied before compositing into layer |
| `blend-mode` | No | `normal` | Element blend mode (same vocabulary as §6.2.2, except `pass-through` is invalid on elements) |
| `print:surface-treatment` | No | `none` | Surface treatment specification (see §6.4.2) |

If both `fill` and `stroke` are `none`, the shape MUST still be included in the
accessibility tree (it MAY carry `sem:` attributes) but MUST NOT contribute pixels
to the render output.

### 6.4.2 Surface Treatment

The `print:surface-treatment` attribute specifies a finishing treatment applied to
the shape's region in press output. This is distinct from foil and emboss plates
(which use dedicated layer roles); `print:surface-treatment` is an inline hint for
treatments applied uniformly over a shape.

| Value | Description |
|-------|-------------|
| `none` | No special treatment (default) |
| `varnish-gloss` | Gloss spot varnish over the shape region |
| `varnish-matte` | Matte spot varnish over the shape region |
| `varnish-soft-touch` | Soft-touch varnish over the shape region |
| `uv-raised` | Raised UV coating over the shape region |

A print processor MUST output the shape's path as a separate varnish mask layer in
the press PDF when `print:surface-treatment` is any value other than `none`.
A screen renderer SHOULD ignore `print:surface-treatment`.

## 6.5 Image Element

The `<image>` element places a raster or vector image asset within the layer.

```xml
<image
  id="product-photo"
  src="assets/product.png"
  x="10mm"
  y="10mm"
  width="80mm"
  height="60mm"
  object-fit="cover"
  object-position="center center"
  opacity="1.0"
  blend-mode="normal"
  clip-to-boundary="true"
  print:resolution-check="300dpi"/>
```

### 6.5.1 Image Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `id` | Recommended | — | Unique identifier |
| `src` | Yes | — | Asset reference: relative path, absolute URL, data URI, or `mdfx:` ID |
| `x` | Yes | — | X position of image origin (top-left), in canvas units |
| `y` | Yes | — | Y position of image origin (top-left), in canvas units |
| `width` | Yes | — | Rendered width in canvas units |
| `height` | Yes | — | Rendered height in canvas units |
| `object-fit` | No | `fill` | Scaling behavior (see §6.5.2) |
| `object-position` | No | `center center` | Position of image within its box when `object-fit` is `contain` or `cover` |
| `opacity` | No | `1.0` | Element opacity `[0.0, 1.0]` |
| `blend-mode` | No | `normal` | Element blend mode (§6.2.2 vocabulary, `pass-through` invalid) |
| `clip-to-boundary` | No | `true` | If `true`, image is clipped to the canvas boundary path |
| `clip-path` | No | — | SVG path data string; clips image to this shape in addition to canvas boundary |
| `print:resolution-check` | No | — | Minimum resolution hint for validators (e.g. `300dpi`). Not a rendering instruction. |

### 6.5.2 Object Fit Values

| Value | Description |
|-------|-------------|
| `fill` | Image is stretched to exactly fill the declared `width` × `height` box |
| `contain` | Image is scaled uniformly to fit within the box; letterboxing may result |
| `cover` | Image is scaled uniformly to cover the entire box; cropping may result |
| `none` | Image is rendered at its intrinsic size, positioned by `object-position` |
| `scale-down` | Equivalent to the smaller of `none` and `contain` |

### 6.5.3 Supported Image Formats

A conformant Level 1 processor MUST support the following raster image formats as
`<image>` sources:

| Format | MIME Type | Notes |
|--------|-----------|-------|
| PNG | `image/png` | All bit depths; transparency supported |
| JPEG | `image/jpeg` | All standard JPEG variants |
| WebP | `image/webp` | Lossy and lossless |
| SVG | `image/svg+xml` | Vector; rendered at target resolution |

A Level 2 processor MUST additionally support:

| Format | MIME Type | Notes |
|--------|-----------|-------|
| TIFF | `image/tiff` | Including CMYK TIFF with ICC profile |
| EPS | `application/postscript` | Encapsulated PostScript (rasterized at target resolution) |

## 6.6 Group Element

The `<group>` element aggregates child elements into a single compositing unit and
applies a shared geometric transform, opacity, and blend mode to all children.

```xml
<group
  id="logo-lockup"
  opacity="1.0"
  blend-mode="normal"
  transform="translate(20, 15) rotate(45, 50, 50) scale(1.5)">

  <shape id="logo-bg" path="..." fill="color(cmyk 1 0.8 0 0.2)"/>
  <text-block id="logo-text" .../>

</group>
```

### 6.6.1 Group Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `id` | Recommended | — | Unique identifier |
| `opacity` | No | `1.0` | Group opacity `[0.0, 1.0]`, applied after compositing children |
| `blend-mode` | No | `normal` | Blend mode for the group composite against parent (§6.2.2 vocabulary) |
| `transform` | No | identity | SVG transform string (see §6.6.2) |
| `clip-path` | No | — | SVG path data string; all children are clipped to this shape |
| `isolation` | No | `auto` | Isolation behavior: `auto` or `isolate` (see §6.7.3) |

A `<group>` MUST form an isolation group when its `opacity` is less than `1.0`, when
its `blend-mode` is not `normal`, or when `isolation="isolate"` is explicitly set.
When `isolation="auto"` and neither condition applies, the group MAY or MAY NOT
create an isolation group — the compositing result is identical either way.

### 6.6.2 Transform Attribute

The `transform` attribute is a string containing one or more SVG transform functions,
applied right-to-left (as in SVG 2 §10.2). The following functions are supported:

| Function | Description |
|----------|-------------|
| `translate(tx[, ty])` | Translate by `tx`, `ty` (in canvas units). If `ty` is omitted, defaults to `0`. |
| `scale(sx[, sy])` | Scale by `sx`, `sy`. If `sy` is omitted, uniform scale. |
| `rotate(angle[, cx, cy])` | Rotate by `angle` degrees. If `cx, cy` provided, rotate about that point. |
| `skewX(angle)` | Skew along X axis by `angle` degrees |
| `skewY(angle)` | Skew along Y axis by `angle` degrees |
| `matrix(a, b, c, d, e, f)` | Arbitrary 2D affine transform matrix |

Transform values are in canvas coordinate units (as declared by `<canvas units="...">`).
Angles are in degrees. A processor MUST apply transforms in the order they appear,
right-to-left (i.e. the rightmost transform is applied first to input coordinates).

### 6.6.3 Group Contents

A `<group>` MAY contain any combination of `<text-block>`, `<image>`, `<shape>`,
`<group>` (nested), and `<layer>` elements. Nesting depth is not specified as a
limit by this specification; implementations MAY impose reasonable depth limits
and MUST document any such limits.

## 6.7 Z-Order and Compositing

### 6.7.1 Layer Stacking Order

Layers within a `<canvas>` composite in document order. The first `<layer>` element
in document order is rendered first and forms the base of the compositing stack. Each
subsequent layer is composited on top using its declared `blend-mode` and `opacity`.

```xml
<canvas ...>
  <layer id="background"/>   <!-- rendered first, bottommost -->
  <layer id="midground"/>    <!-- composited on top of background -->
  <layer id="foreground"/>   <!-- composited on top, topmost -->
</canvas>
```

The composited result of all visible layers is then clipped to the canvas boundary
path (§3.5) before final output.

### 6.7.2 Element Stacking Order Within a Layer

Within a `<layer>` or `<group>`, child elements composite in document order: the
first child element is bottommost; the last is topmost. This is the same ordering
rule as SVG.

There is no `z-index` attribute in MDF. Stacking order is entirely determined by
document order. Editors that wish to reorder elements MUST reorder the XML elements.

### 6.7.3 Isolation Groups

An isolation group is a compositing context that composites its children against a
fully transparent background before the result is composited against the parent
context. This prevents blend modes on child elements from interacting with elements
below the group.

A `<layer>` MUST be treated as an isolation group when any of the following are true:

- Its `opacity` is less than `1.0`
- Its `blend-mode` is not `normal` and not `pass-through`
- It contains a nested `<layer>` or `<group>` with non-normal compositing

A `<layer>` with `blend-mode="pass-through"` MUST NOT form an isolation group; its
children composite directly into the parent canvas compositing stack.

A `<group>` MUST be treated as an isolation group when:

- Its `opacity` is less than `1.0`
- Its `blend-mode` is not `normal`
- `isolation="isolate"` is explicitly declared

### 6.7.4 Alpha Compositing Formula

For standard (non-blended) compositing, MDF uses the Porter-Duff "source over"
operator. Given a source color `Cs` with alpha `αs`, compositing over a destination
color `Cd` with alpha `αd`:

```
αr = αs + αd × (1 - αs)
Cr = (αs × Cs + αd × Cd × (1 - αs)) / αr     (if αr > 0)
Cr = 0                                          (if αr = 0)
```

Where `Cr` and `αr` are the resulting color and alpha.

For blend modes other than `normal`, the blended color `B(Cs, Cd)` replaces `Cs` in
the formula above:

```
αr = αs + αd × (1 - αs)
Cr = ((1 - αd) × αs × Cs + (1 - αs) × αd × Cd + αs × αd × B(Cs, Cd)) / αr
```

Blend function definitions for each mode are as specified in W3C CSS Compositing and
Blending Level 1, §8.

Layer opacity is applied by multiplying the layer's alpha channel by the opacity
value before the layer is composited into the canvas stack:

```
αs_effective = αs_layer × layer.opacity
```

### 6.7.5 Compositing Color Space

All compositing operations MUST be performed in a linear light color space. When
source images or colors are in a gamma-encoded space (sRGB, display-P3), a
conformant renderer MUST linearize the values before compositing and re-apply gamma
encoding to the output.

For CMYK content (Level 2+), compositing is performed in the ICC profile's
connection space (CIEXYZ or CIELAB). The print processor MUST convert to the target
color space after compositing.

## 6.8 Print Layer Roles

This section specifies how layers with specific `print:role` values are handled
during print production output. Screen renderers SHOULD ignore print-specific
behavior and render only layers where `visible="true"` and
`print:visible-in-render="true"`.

### 6.8.1 Body Layer

Layers with `print:role="body"` (the default) are standard design content. A print
processor MUST include body layers in all color separation outputs.

### 6.8.2 Registration Marks Layer

A layer with `print:role="registration-marks"` contains registration crosshairs,
crop marks, and color bars for press alignment.

- A conformant print processor MUST include this layer in press-ready PDF/X output.
- A screen renderer MUST NOT render this layer in standard screen output.
- When a `--proof` flag or equivalent proof-render request is active, a renderer
  MAY render this layer to show the marks.
- The elements within a registration marks layer SHOULD use 100% black
  (`color(cmyk 0 0 0 1)`) or registration color (all channels at 100%).
- A Level 2 document that declares `print:die-cut="true"` on its canvas SHOULD
  include a registration marks layer.

### 6.8.3 Spot Color Plate Layers

A layer with `print:role="spot-color-plate"` defines the coverage area for a single
spot color ink. The following rules apply:

- A spot color plate layer MUST contain only `<shape>` or `<image>` elements that
  use a declared spot color (see Manifest `<spot-color>` declarations, Chapter 2).
- The spot color used within the plate layer identifies the ink for that plate. All
  elements within a single spot-color-plate layer MUST use the same spot color ink.
- If a document uses multiple spot colors, each spot color MUST have its own
  dedicated `print:role="spot-color-plate"` layer.
- During plate separation, a print processor MUST output one additional press plate
  per spot-color-plate layer, using the declared spot color's ink name.
- Spot color plate layers MUST have `print:overprint="true"` unless the designer
  explicitly specifies knockout behavior.
- A screen renderer SHOULD approximate spot color appearance using the spot color's
  `cmyk-approximation` value (see §2.x, Chapter 2).

### 6.8.4 Foil Plate Layers

A layer with `print:role="foil-plate"` defines the coverage map for metallic foil
or holographic stamping.

- A foil plate layer MUST be output as a single-channel grayscale coverage map by
  a print processor. Black (100% K) represents full foil coverage; white (0% K)
  represents no foil.
- Multi-color foils (e.g. color-shifting holographic) are represented by multiple
  foil-plate layers, one per foil type. Each such layer SHOULD carry a
  `print:foil-type` attribute (e.g. `print:foil-type="gold"`,
  `print:foil-type="holographic"`) to identify the stamping die.
- A screen renderer SHOULD render foil plate layers with a metallic sheen
  simulation or, if unavailable, with a gold-tinted semi-transparent overlay.
- Foil plate layers MUST have `print:visible-in-render="false"` in standard
  output; they are only visible in proof renders.

### 6.8.5 Emboss Plate Layers

A layer with `print:role="emboss-plate"` defines the coverage and depth map for
embossing or debossing.

- An emboss plate layer MUST be output as a grayscale depth map: black (100% K)
  indicates maximum relief depth; white (0% K) indicates no relief.
- The `print:emboss-depth` attribute on the layer MAY specify the maximum physical
  depth (e.g. `print:emboss-depth="0.5mm"`).
- A screen renderer SHOULD render emboss plate layers with a subtle highlight/shadow
  simulation or ignore them entirely.
- Whether to emboss or deboss is specified by `print:emboss-direction`:
  `up` (emboss, default) or `down` (deboss).

### 6.8.6 Overprint Preview Layer

A layer with `print:role="overprint-preview"` is a pre-composited simulation of
overprint effects for design review purposes. It is informational only and MUST NOT
be output to press. A print processor MUST exclude overprint-preview layers from all
plate outputs.

## 6.9 Example: Complete Layer Stack

The following example illustrates a typical two-sided sticker document with full
print layer stack:

```xml
<canvas width="80" height="80" units="mm"
        boundary="M 40,0 A 40,40 0 1,1 40,0.001 Z"
        print:die-cut="true"
        print:bleed="3mm"
        sem:shape-type="circle"
        sem:shape-meaning="sticker"
        xmlns="https://morphousdoc.org/ns/0.1"
        xmlns:print="https://morphousdoc.org/ns/print/0.1"
        xmlns:sem="https://morphousdoc.org/ns/semantics/0.1">

  <!-- Bottommost: bleed artwork that extends to edge -->
  <layer id="bleed"
         print:role="bleed-content"
         print:visible-in-render="true">
    <shape id="bleed-bg"
           path="M -3,-3 L 83,-3 L 83,83 L -3,83 Z"
           fill="color(cmyk 0 0.72 0.95 0)"/>
  </layer>

  <!-- Main design content -->
  <layer id="artwork" blend-mode="normal" opacity="1.0" print:role="body">
    <image id="logo" src="mdfx:logo-png" x="10" y="10" width="60" height="60"/>
    <text-block id="tagline" font-ref="body-font" size="8pt">
      <reflow-region shape-ref="canvas-boundary" padding="12mm"/>
      <p>Fresh &amp; Local</p>
    </text-block>
  </layer>

  <!-- Pantone 485 spot color overlay for brand red -->
  <layer id="brand-red-plate"
         print:role="spot-color-plate"
         print:overprint="true"
         print:visible-in-render="false">
    <shape id="brand-ring"
           path="M 40,5 A 35,35 0 1,1 40,5.001 Z"
           stroke="spot(pantone-485)"
           stroke-width="2pt"
           fill="none"/>
  </layer>

  <!-- Gold foil plate for logo highlight -->
  <layer id="foil-plate"
         print:role="foil-plate"
         print:foil-type="gold"
         print:visible-in-render="false">
    <shape id="foil-area"
           path="M 25,25 A 15,15 0 1,1 25,25.001 Z"
           fill="color(gray 1.0)"/>
  </layer>

  <!-- Registration marks, proof-only -->
  <layer id="marks"
         print:role="registration-marks"
         print:visible-in-render="false">
    <!-- registration crosshairs generated by print processor -->
  </layer>

</canvas>
```
