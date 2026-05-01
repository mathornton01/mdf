# MDF Specification v0.1 — Chapter 4: Color System and Texture

## 4.1 Overview

MDF's color system is designed from the ground up for professional print production. It is richer than PDF's color model in three important ways:

1. **Multi-notation color values** — A single color attribute can be expressed in any of six notations (hex, RGB, CMYK, CIE L*a*b*, spot, or N-channel device), chosen to match the production context. There is no dominant "native" colorspace — all notations are first-class.
2. **Gradient and pattern paint servers** — Gradients and patterns are declared as named resources and referenced via paint functions, not inlined on elements. This keeps geometry and paint decoupled.
3. **Surface treatments as first-class print objects** — Spot UV, foil, emboss, and other finishing operations are declared in the manifest and assigned to elements as print attributes, producing separate output plates automatically.

This chapter defines the full color, gradient, pattern, and surface treatment system.

---

## 4.2 Color Syntax

Color values appear as attribute values on `fill`, `stroke`, `color` (on text elements), and other properties. MDF supports six color notations. A conformant processor MUST support all notations that are applicable to its conformance level.

### 4.2.1 Hex Notation

```
#rrggbb
#rrggbbaa
```

Six-digit or eight-digit hex. Channel values are in `[00, FF]`. The alpha channel `aa` is optional; if omitted, the color is fully opaque (`ff`).

```xml
fill="#e63946"
fill="#e6394680"     <!-- 50% opacity red -->
fill="#ffffff"
fill="#000000ff"
```

Hex notation addresses the sRGB colorspace. A Level 2 processor rendering to a CMYK output intent MUST convert hex colors through the document's declared ICC profile chain.

### 4.2.2 RGB Notation

```
rgb(r, g, b)
rgba(r, g, b, a)
```

Channels `r`, `g`, `b` are either:
- **Integer** in `[0, 255]`, or
- **Float** in `[0.0, 1.0]`

The two forms MUST NOT be mixed within a single value. A value is interpreted as integer if any of `r`, `g`, or `b` is greater than `1.0`. If all three are in `[0.0, 1.0]` and at least one is not an integer, they are interpreted as floats.

The `a` channel (alpha) is a float in `[0.0, 1.0]`. Default is `1.0` (fully opaque).

```xml
fill="rgb(230, 57, 70)"
fill="rgba(230, 57, 70, 0.5)"
fill="rgb(0.902, 0.224, 0.275)"
```

RGB notation addresses the sRGB colorspace.

### 4.2.3 CMYK Notation

```
cmyk(c, m, y, k)
```

Channels `c`, `m`, `y`, `k` are floats in `[0.0, 1.0]`, representing Cyan, Magenta, Yellow, and Black ink percentages.

```xml
fill="cmyk(0, 0.95, 0.95, 0.05)"     <!-- Pantone 485 C approximation -->
fill="cmyk(0, 0, 0, 1.0)"            <!-- Registration black -->
fill="cmyk(0.6, 0.3, 0, 0.1)"        <!-- Process blue -->
stroke="cmyk(0, 0, 0, 0.5)"          <!-- 50% black keyline -->
```

CMYK notation is valid at all conformance levels. At Level 1 (screen), a processor MUST convert CMYK values to RGB for display, using the document's declared ICC output intent if available, or the default FOGRA39→sRGB transform if no output intent is declared. A Level 1 processor MUST NOT emit CMYK values directly to screen rendering without conversion.

At Level 2 (print), CMYK values are passed through to the output without conversion, subject to the output intent ICC profile transform.

### 4.2.4 CIE L\*a\*b\* Notation

```
lab(L, a, b)
```

`L` is a float in `[0.0, 100.0]` (lightness). `a` and `b` are floats in `[-128.0, 127.0]` (chromaticity axes). This notation specifies a device-independent color in the CIE L*a*b* colorspace (D50 illuminant, as per ICC specification).

```xml
fill="lab(53.2, 71.4, 49.6)"          <!-- Pantone 485 C colorimetric target -->
fill="lab(0, 0, 0)"                   <!-- Perceptual black -->
fill="lab(100, 0, 0)"                 <!-- Perceptual white -->
```

A processor MUST convert `lab()` values to the output colorspace using a color-managed transform. At Level 1 the target colorspace is sRGB. At Level 2 the target colorspace is defined by the `<print-intent>` output ICC profile.

### 4.2.5 Spot Color Notation

```
spot(id, tint)
```

`id` is the `id` of a `<spot-color>` declared in the manifest (§2.7). `tint` is a float in `[0.0, 1.0]` representing the ink density: `1.0` is full ink, `0.0` is no ink (substrate).

```xml
fill="spot(acme-red, 1.0)"            <!-- Full-density Pantone 485 C -->
fill="spot(acme-red, 0.5)"            <!-- 50% tint of Pantone 485 C -->
fill="spot(acme-silver, 0.8)"         <!-- 80% tint of metallic silver -->
stroke="spot(pantone-877c, 1.0)"
```

Spot notation is valid at all conformance levels. At Level 1, a processor MUST substitute the `cmyk` approximation from the spot color declaration and apply the given tint. It MUST NOT attempt to render spot inks as screen primaries without approximation. A Level 2 processor MUST preserve spot colors as separate ink channels in the output. Spot colors MUST appear on their own separation plate in production output.

If the referenced `id` does not match any declared `<spot-color>`, the processor MUST substitute a warning color (RECOMMENDED: process magenta, `cmyk(0, 1, 0, 0)`) and MUST emit a validation error.

### 4.2.6 Device Color Notation

```
device(c1, c2, ..., cN)
```

Device notation specifies an N-channel color in an arbitrary device colorspace. It requires a `<print-intent>` with a declared `icc-profile-ref` that defines an N-channel output profile. Channel values are floats in `[0.0, 1.0]`.

```xml
fill="device(0.0, 0.5, 0.8, 0.0, 0.1)"   <!-- 5-channel Pantone hexachrome or similar -->
```

Device notation is a Level 2 feature. A Level 1 processor that encounters `device()` MUST attempt a conversion to sRGB using the document's ICC profile. If no ICC profile is declared that defines the channel count, the processor MUST substitute a warning color and emit a validation error.

The number of channels in a `device()` value MUST match the channel count of the output intent ICC profile declared in `<print-intent>`. A mismatch is a hard error.

### 4.2.7 Special Color Values

| Value | Description |
|-------|-------------|
| `none` | Transparent (no paint). Valid for `fill` and `stroke`. |
| `inherit` | Inherits the computed value from the enclosing `<layer>`. (See §4.7.1.) |
| `currentColor` | Uses the text `color` value of the current element. Valid on `stroke` only. |

### 4.2.8 Color Value Summary

| Notation | Level | Colorspace | Alpha |
|----------|-------|------------|-------|
| `#rrggbb` / `#rrggbbaa` | 1+ | sRGB | Optional (aa channel) |
| `rgb()` / `rgba()` | 1+ | sRGB | Optional (rgba form) |
| `cmyk()` | 1+ | Device CMYK | No |
| `lab()` | 1+ | CIE L*a*b* D50 | No |
| `spot()` | 1+ | Named ink channel | Via tint |
| `device()` | 2+ | N-channel device | No |

---

## 4.3 Color Management

### 4.3.1 Default Colorspaces

When no explicit ICC profile is declared, the following defaults apply:

| Context | Default Colorspace |
|---------|--------------------|
| Screen / Level 1 rendering | sRGB (IEC 61966-2-1) |
| Print / Level 2 rendering, coated substrate | ISO Coated v2 (FOGRA39) |
| Print / Level 2 rendering, uncoated substrate | ISO Uncoated (FOGRA29) |

A conformant Level 2 processor MUST NOT use screen colorspace defaults when producing print-ready output. The output intent profile from `<print-intent>` takes precedence over all defaults.

### 4.3.2 ICC Transform Chain

When rendering a document, the processor MUST apply ICC color transforms in the following order:

1. **Source colorspace**: determined by the color notation.
   - `#hex`, `rgb()`: sRGB
   - `cmyk()`: document output intent CMYK profile
   - `lab()`: CIE L*a*b* D50 (ICC PCS)
   - `spot()`: colorimetric target from spot color `lab` attribute, or CMYK approximation
   - `device()`: N-channel ICC profile declared in `print-intent`

2. **Profile connection space (PCS)**: CIE L*a*b* D50 (as defined by the ICC specification)

3. **Destination colorspace**: the output device profile.

A processor MUST use the relative colorimetric rendering intent as the default for production color conversions. A processor MAY allow the user to select perceptual, saturation, or absolute colorimetric intents as overrides.

### 4.3.3 Overprint Behavior

At Level 2, the `print:overprint` attribute on paint-carrying elements controls ink overprint:

```xml
<shape fill="cmyk(0,0.95,0.95,0.05)" print:overprint="true"/>
```

When `print:overprint="true"`, the element's ink is laid down on top of underlying inks without knocking out the underlying color. This is standard behavior for spot colors on a printing press. A Level 2 processor MUST respect `print:overprint` in production output. A Level 1 processor MUST ignore `print:overprint`.

The default is `print:overprint="false"` (knockout).

---

## 4.4 Gradients

Gradients are declared as named elements in the `<canvas>` element's `<defs>` section and referenced via the `gradient()` paint function. A `<defs>` element MAY appear as the first child of any `<canvas>`.

```xml
<canvas ...>
  <defs>
    <gradient id="brand-gradient">
      <linear-gradient x1="0" y1="0" x2="1" y2="0"
                       gradientUnits="boundingBox">
        <stop offset="0.0" color="#e63946"/>
        <stop offset="1.0" color="#457b9d"/>
      </linear-gradient>
    </gradient>
  </defs>
</canvas>
```

A `<gradient>` element MUST have an `id` attribute. The `id` MUST be unique within the document.

### 4.4.1 Linear Gradients

```xml
<gradient id="sunset">
  <linear-gradient x1="0" y1="0" x2="0" y2="1"
                   gradientUnits="boundingBox">
    <stop offset="0.0"  color="#ff6b6b"/>
    <stop offset="0.45" color="#ffd93d"/>
    <stop offset="1.0"  color="#6c63ff"/>
  </linear-gradient>
</gradient>
```

#### `<linear-gradient>` Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `x1` | No | `0` | X coordinate of gradient start point |
| `y1` | No | `0` | Y coordinate of gradient start point |
| `x2` | No | `1` | X coordinate of gradient end point |
| `y2` | No | `0` | Y coordinate of gradient end point |
| `angle` | No | — | Shorthand angle in degrees; if present, overrides `x1/y1/x2/y2` |
| `gradientUnits` | No | `boundingBox` | Coordinate system for gradient geometry (see §4.4.4) |
| `spreadMethod` | No | `pad` | `pad`, `reflect`, or `repeat` |

The `angle` shorthand specifies the direction of the gradient vector in degrees (0° = left-to-right, 90° = top-to-bottom, following CSS convention). When `angle` is present, the processor MUST compute `x1/y1/x2/y2` from the angle and the bounding box of the filled element, and MUST ignore any explicit `x1/y1/x2/y2` values.

#### `<stop>` Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `offset` | Yes | — | Stop position as a float in `[0.0, 1.0]` |
| `color` | Yes | — | Color at this stop; any MDF color notation |
| `opacity` | No | `1.0` | Stop opacity, float in `[0.0, 1.0]` |

A gradient MUST have at least two `<stop>` elements. Stops MUST be ordered by ascending `offset`. If two stops have the same `offset`, the second defines a hard color break.

All MDF color notations are valid for stop colors. A gradient MAY mix color notations across stops; a processor MUST perform color space conversion between stops when interpolating (interpolation is performed in CIE L*a*b* by default; a processor MAY use sRGB interpolation if the gradient contains no CMYK, lab, or spot stops).

### 4.4.2 Radial Gradients

```xml
<gradient id="spotlight">
  <radial-gradient cx="0.5" cy="0.5" r="0.5"
                   fx="0.4" fy="0.4"
                   gradientUnits="boundingBox">
    <stop offset="0.0" color="#ffffff"/>
    <stop offset="1.0" color="#000000"/>
  </radial-gradient>
</gradient>
```

#### `<radial-gradient>` Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `cx` | No | `0.5` | X coordinate of the gradient circle center |
| `cy` | No | `0.5` | Y coordinate of the gradient circle center |
| `r` | No | `0.5` | Radius of the gradient circle |
| `fx` | No | `cx` | X coordinate of the focal point |
| `fy` | No | `cy` | Y coordinate of the focal point |
| `gradientUnits` | No | `boundingBox` | Coordinate system (see §4.4.4) |
| `spreadMethod` | No | `pad` | `pad`, `reflect`, or `repeat` |

The focal point (`fx`, `fy`) MUST be inside or on the gradient circle. If the focal point falls outside the circle, the processor MUST clamp it to the nearest point on the circle boundary.

Gradient interpolation: color values are interpolated between stops as a function of the distance from the focal point, normalized to the circle radius.

### 4.4.3 Mesh Gradients (Level 3)

Mesh gradients implement a Coons patch mesh, providing smooth multi-directional color transitions. This feature is Level 3 only; a Level 1 or Level 2 processor MUST fall back to the nearest equivalent radial gradient approximation if it encounters a `<mesh-gradient>` element.

```xml
<!-- Level 3 only -->
<gradient id="sunset-mesh">
  <mesh-gradient rows="2" cols="2">
    <mesh-row>
      <mesh-patch>
        <patch-color position="top-left"     color="#e63946"/>
        <patch-color position="top-right"    color="#457b9d"/>
        <patch-color position="bottom-left"  color="#2a9d8f"/>
        <patch-color position="bottom-right" color="#e9c46a"/>
      </mesh-patch>
      <mesh-patch>
        <patch-color position="top-left"     color="#457b9d"/>
        <patch-color position="top-right"    color="#264653"/>
        <patch-color position="bottom-left"  color="#e9c46a"/>
        <patch-color position="bottom-right" color="#f4a261"/>
      </mesh-patch>
    </mesh-row>
  </mesh-gradient>
</gradient>
```

The mesh gradient uses a bicubic Coons patch formulation: each patch is defined by its four corner colors. The boundary curves between patches share control points to ensure C0 continuity. The renderer MUST sample the patch at sufficient resolution to produce a smooth result at the output resolution.

### 4.4.4 Gradient Units

The `gradientUnits` attribute defines the coordinate system in which gradient geometry is expressed:

| Value | Description |
|-------|-------------|
| `boundingBox` | Coordinates are fractions of the bounding box of the filled element. `(0,0)` = top-left corner, `(1,1)` = bottom-right corner. |
| `userSpaceOnUse` | Coordinates are in the canvas coordinate space, in the same units as the canvas `units` attribute. |

The default is `boundingBox`. `userSpaceOnUse` is useful for gradients that must align across multiple elements (e.g. a gradient that spans the full canvas width).

### 4.4.5 Spread Methods

| Value | Description |
|-------|-------------|
| `pad` | Colors outside the gradient range use the terminal stop color. |
| `reflect` | The gradient reflects (reverses) at each boundary, alternating direction. |
| `repeat` | The gradient repeats from start after reaching the end. |

### 4.4.6 Referencing Gradients

Gradients are referenced using the `gradient()` paint function:

```xml
<shape fill="gradient(brand-gradient)" .../>
<text-block color="gradient(sunset)" .../>
```

A gradient reference MUST resolve to a `<gradient>` element with a matching `id`. If the referenced gradient does not exist, the processor MUST substitute `fill="none"` and emit a validation error.

---

## 4.5 Patterns

Patterns define a tiling paint server: a rectangular tile of MDF content that is repeated to fill an element.

### 4.5.1 Pattern Declaration

Patterns are declared in the `<defs>` section of a `<canvas>`:

```xml
<defs>
  <pattern id="hatch"
           width="4"
           height="4"
           units="userSpaceOnUse"
           patternContentUnits="userSpaceOnUse">
    <shape boundary="M 0,0 L 4,4"
           stroke="cmyk(0,0,0,0.3)"
           stroke-width="0.5"
           fill="none"/>
    <shape boundary="M -1,3 L 1,5"
           stroke="cmyk(0,0,0,0.3)"
           stroke-width="0.5"
           fill="none"/>
    <shape boundary="M 3,-1 L 5,1"
           stroke="cmyk(0,0,0,0.3)"
           stroke-width="0.5"
           fill="none"/>
  </pattern>
</defs>
```

### 4.5.2 Pattern Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `id` | Yes | — | Unique identifier |
| `width` | Yes | — | Width of the tile |
| `height` | Yes | — | Height of the tile |
| `units` | No | `userSpaceOnUse` | Coordinate system for `width`/`height` (see §4.5.3) |
| `patternContentUnits` | No | `userSpaceOnUse` | Coordinate system for the tile content |
| `patternTransform` | No | identity | SVG transform applied to the entire pattern before tiling |

### 4.5.3 Pattern Units

| Value | Description |
|-------|-------------|
| `userSpaceOnUse` | `width` and `height` are in the canvas coordinate space. |
| `boundingBox` | `width` and `height` are fractions of the filled element's bounding box. `(0,0)` = top-left, `(1,1)` = bottom-right. |

### 4.5.4 Pattern Content

The content of a `<pattern>` element is a sequence of MDF shape, image, and text elements rendered into the tile. These elements MUST use the same element types as defined for canvas layers (Chapter 6). The tile content is clipped to the `[0, 0, width, height]` rectangle.

Pattern content elements MUST NOT reference other patterns (circular references are not permitted). A processor that detects a circular pattern reference MUST reject the document.

### 4.5.5 Referencing Patterns

```xml
<shape fill="pattern(hatch)" .../>
<shape fill="pattern(polka-dots)" stroke="cmyk(0,0,0,1)" stroke-width="0.25"/>
```

---

## 4.6 Fill and Stroke

Every shape and text element in MDF carries fill and stroke paint properties. This section defines those properties normatively.

### 4.6.1 Fill

The `fill` attribute specifies the paint applied to the interior of a shape, or the text glyphs of a text element.

| Value | Description |
|-------|-------------|
| *color value* | Any MDF color notation (§4.2) |
| `gradient(id)` | Reference to a declared `<gradient>` |
| `pattern(id)` | Reference to a declared `<pattern>` |
| `none` | No fill (transparent interior) |
| `inherit` | Inherit from enclosing element |

Default: `none` for shapes; implementation-defined for text (RECOMMENDED: `#000000`).

### 4.6.2 Stroke

The `stroke` attribute specifies the paint applied to the outline of a shape.

| Value | Description |
|-------|-------------|
| *color value* | Any MDF color notation (§4.2) |
| `gradient(id)` | Reference to a declared `<gradient>` |
| `currentColor` | Use the element's `fill` color for the stroke |
| `none` | No stroke |
| `inherit` | Inherit from enclosing element |

Default: `none`.

### 4.6.3 Stroke Properties

These attributes modify stroke rendering:

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `stroke-width` | No | `1pt` | Width of the stroke, in canvas units or with a unit suffix |
| `stroke-linecap` | No | `butt` | `butt`, `round`, or `square` |
| `stroke-linejoin` | No | `miter` | `miter`, `round`, or `bevel` |
| `stroke-miterlimit` | No | `4` | Miter length limit (ratio); when exceeded, falls back to bevel |
| `stroke-dasharray` | No | — | Dash pattern as space-separated lengths; e.g. `"4 2"` |
| `stroke-dashoffset` | No | `0` | Phase offset into the dash pattern |

#### `stroke-linecap` values

| Value | Description |
|-------|-------------|
| `butt` | The stroke ends exactly at the path endpoint. |
| `round` | A semicircle is drawn at each endpoint, with diameter equal to `stroke-width`. |
| `square` | A rectangle is drawn at each endpoint, extending `stroke-width / 2` beyond the path. |

#### `stroke-linejoin` values

| Value | Description |
|-------|-------------|
| `miter` | Outer edges of the stroke at a corner are extended to a point. Subject to `stroke-miterlimit`. |
| `round` | A circular arc is drawn at corners. |
| `bevel` | The outer edge of the corner is filled with a triangle. |

### 4.6.4 Opacity

The `opacity` attribute applies a uniform opacity to the entire element (both fill and stroke):

```xml
<shape fill="#e63946" stroke="none" opacity="0.5"/>
```

`opacity` is a float in `[0.0, 1.0]`. Default is `1.0`. The opacity is composited after all element paint (fill, stroke) is resolved. Fill and stroke may also carry per-channel alpha (via `rgba()` or `#rrggbbaa`); these are applied before `opacity`.

### 4.6.5 Blend Mode

The `blend-mode` attribute specifies how the element composites with the content beneath it:

```xml
<shape fill="#e63946" blend-mode="multiply"/>
```

Supported blend modes:

| Value | Description |
|-------|-------------|
| `normal` | Standard alpha compositing (Porter-Duff source-over). Default. |
| `multiply` | Multiplies source and destination colors. Darkens. |
| `screen` | Complement of multiply of complements. Lightens. |
| `overlay` | Multiply for darks, screen for lights. Increases contrast. |
| `darken` | Selects the darker of source and destination per channel. |
| `lighten` | Selects the lighter of source and destination per channel. |
| `color-dodge` | Brightens destination to reflect source. |
| `color-burn` | Darkens destination to reflect source. |
| `hard-light` | Overlay with source and destination swapped. |
| `soft-light` | Softer version of hard-light. |
| `difference` | Absolute value of source minus destination. |
| `exclusion` | Lower-contrast version of difference. |
| `hue` | Hue of source, saturation and luminosity of destination. |
| `saturation` | Saturation of source, hue and luminosity of destination. |
| `color` | Hue and saturation of source, luminosity of destination. |
| `luminosity` | Luminosity of source, hue and saturation of destination. |

Blend modes are computed in the sRGB colorspace. A Level 2 processor rendering to CMYK MUST convert colors to sRGB, apply the blend, then convert the result back to the output colorspace using the declared ICC transform chain.

A Level 1 processor MUST support all blend modes listed above. Unknown `blend-mode` values MUST be treated as `normal`.

### 4.6.6 Fill Rule

For closed paths with self-intersections or sub-paths, the `fill-rule` attribute determines which regions are considered "inside":

| Value | Description |
|-------|-------------|
| `nonzero` | The nonzero winding number rule. Default. |
| `evenodd` | The even-odd rule. |

```xml
<shape fill="#457b9d" fill-rule="evenodd" boundary="..."/>
```

---

## 4.7 Surface Treatments (Level 2+)

Surface treatments model print finishing operations that apply physical effects to specific regions of the printed piece: UV coating, foil stamping, embossing, and lamination. These operations are handled as separate output plates in prepress workflow.

A Level 1 processor MUST ignore all `print:surface-treatment` attributes and `<surface-treatment>` declarations. A Level 2 processor MUST preserve surface treatment information in production output.

### 4.7.1 Surface Treatment Declarations

Surface treatments are declared in the manifest:

```xml
<manifest>
  ...
  <surface-treatments>
    <surface-treatment id="gloss-uv"   type="spot-uv"/>
    <surface-treatment id="gold-foil"  type="foil"      foil-type="gold"/>
    <surface-treatment id="holo-foil"  type="foil"      foil-type="holographic"/>
    <surface-treatment id="title-emboss" type="emboss"  depth="0.5mm"/>
    <surface-treatment id="soft-touch"   type="soft-touch-laminate"/>
  </surface-treatments>
</manifest>
```

The `<surface-treatments>` section is a child of `<manifest>` (alongside `<fonts>`, `<icc-profiles>`, etc.).

### 4.7.2 Surface Treatment Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `id` | Yes | — | Unique identifier; referenced via `print:surface-treatment` |
| `type` | Yes | — | Treatment type (see §4.7.3) |
| `foil-type` | Foil only | — | Foil variant (see §4.7.4) |
| `depth` | Emboss/deboss | `0.3mm` | Emboss/deboss depth |

### 4.7.3 Treatment Types

| Type | Level | Description |
|------|-------|-------------|
| `spot-uv` | 2 | Gloss UV varnish applied to specific areas only. Creates a contrast between coated and uncoated surfaces. |
| `foil` | 2 | Metallic or holographic foil stamping. Requires `foil-type`. |
| `emboss` | 2 | Raised relief of the element shape into the substrate. |
| `deboss` | 2 | Recessed relief (inverse of emboss). |
| `thermography` | 2 | Heat-raised powder coating for a tactile raised effect. |
| `soft-touch-laminate` | 2 | Full-surface soft-touch lamination (declared on a layer, not an element). |
| `gloss-laminate` | 2 | Full-surface gloss lamination. |
| `matte-laminate` | 2 | Full-surface matte lamination. |

Lamination types (`soft-touch-laminate`, `gloss-laminate`, `matte-laminate`) apply to the full print surface and SHOULD be declared on a layer element via `print:surface-treatment` rather than on individual shapes. A processor MUST treat lamination treatments as full-surface operators.

### 4.7.4 Foil Types

| Value | Description |
|-------|-------------|
| `gold` | Standard metallic gold foil |
| `silver` | Standard metallic silver foil |
| `rose-gold` | Rose gold metallic foil |
| `holographic` | Rainbow holographic foil |
| `custom` | Custom foil; a `foil-name` attribute SHOULD be present with the supplier's foil name |

```xml
<surface-treatment id="custom-foil"
                   type="foil"
                   foil-type="custom"
                   foil-name="API Foils HX999 Prismatic Blue"/>
```

### 4.7.5 Applying Surface Treatments to Elements

Surface treatments are applied to shape and image elements using the `print:surface-treatment` attribute:

```xml
<!-- Shape with gold foil applied -->
<shape boundary="M 10,10 L 80,10 L 80,40 L 10,40 Z"
       fill="cmyk(0,0,0,0)"
       print:surface-treatment="gold-foil"/>

<!-- Text with spot UV applied -->
<text-block font-ref="heading-font"
            size="36pt"
            print:surface-treatment="gloss-uv">
  <reflow-region shape-ref="canvas-boundary" padding="10mm"/>
  <p>Premium Quality</p>
</text-block>

<!-- Shape with emboss -->
<shape boundary="M 50,50 A 30,30 0 1,1 50,50.001 Z"
       fill="none"
       print:surface-treatment="title-emboss"/>
```

A processor MUST extract elements bearing `print:surface-treatment` into separate output plates named after the treatment `id`. In a production PDF/X-4 or press-ready output, each surface treatment MUST appear on a named spot color separation with the treatment `id` as the separation name.

Multiple surface treatments on the same element are not supported. If multiple treatments are needed on the same geometric area, the designer MUST create separate shape elements for each treatment.

### 4.7.6 Surface Treatment Output Plate Naming

When exporting to a press-ready format, surface treatment plates are named as follows:

| Treatment Type | Plate Name Convention |
|----------------|----------------------|
| `spot-uv` | `[id]` (e.g. `gloss-uv`) |
| `foil` | `[id]` (e.g. `gold-foil`) |
| `emboss` | `[id]` (e.g. `title-emboss`) |
| `deboss` | `[id]` |
| `thermography` | `[id]` |
| Lamination | Full-surface; no separate plate |

The treatment `id` is used verbatim as the plate name. Producers SHOULD use descriptive IDs (e.g. `spot-uv-highlights`, `gold-foil-logo`) so that plate names are meaningful to the prepress operator.

---

## 4.8 Layer Inheritance

Color-related attributes are not globally inherited across the element tree; however, elements within a `<layer>` may declare layer-level defaults using the `inherit` special value.

A `<layer>` element MAY carry the following paint attributes as defaults for child elements:

```xml
<layer id="brand-elements"
       opacity="0.9"
       blend-mode="multiply">
  <!-- All children composite with multiply at 90% opacity -->
  <shape fill="inherit" .../>
</layer>
```

When a child element uses `fill="inherit"` or `stroke="inherit"`, the processor MUST use the nearest ancestor `<layer>` element's corresponding fill or stroke value. If no ancestor layer declares the attribute, the initial value (`none` for fill/stroke) is used.

The `opacity` and `blend-mode` attributes on `<layer>` define the layer's compositing group properties. All children are composited into the layer's isolated compositing group before the layer itself is composited with the layers beneath it using the layer's `opacity` and `blend-mode`.

---

## 4.9 Examples

### 4.9.1 CMYK Business Card with Spot Color

```xml
<canvas width="90" height="50" units="mm"
        boundary="M 0,0 L 90,0 L 90,50 L 0,50 Z"
        sem:shape-meaning="business-card">
  <defs>
    <gradient id="card-bg">
      <linear-gradient angle="135"
                       gradientUnits="boundingBox">
        <stop offset="0.0" color="cmyk(0.8,0.4,0,0.2)"/>
        <stop offset="1.0" color="cmyk(1.0,0.6,0,0.4)"/>
      </linear-gradient>
    </gradient>
  </defs>

  <layer id="background">
    <!-- Background gradient fill -->
    <shape boundary="M 0,0 L 90,0 L 90,50 L 0,50 Z"
           fill="gradient(card-bg)"/>
  </layer>

  <layer id="logo">
    <!-- Logo shape with gold foil -->
    <shape boundary="M 10,10 L 30,10 L 30,25 L 10,25 Z"
           fill="cmyk(0,0,0,0)"
           print:surface-treatment="gold-foil"/>
  </layer>

  <layer id="text-content">
    <text-block id="name"
                font-ref="heading-font"
                size="11pt"
                leading="14pt">
      <reflow-region shape="M 35,8 L 82,8 L 82,28 L 35,28 Z"/>
      <p color="cmyk(0,0,0,0)">Jane Smith</p>
    </text-block>
    <text-block id="title"
                font-ref="body-font"
                size="8pt"
                leading="11pt">
      <reflow-region shape="M 35,22 L 82,22 L 82,42 L 35,42 Z"/>
      <p color="spot(acme-silver, 0.8)">Creative Director</p>
    </text-block>
  </layer>
</canvas>
```

### 4.9.2 Gradient with Mixed Color Notations

```xml
<defs>
  <!-- Gradient from CMYK black to a Lab-specified warm tone -->
  <gradient id="ink-to-warm">
    <linear-gradient x1="0" y1="0" x2="1" y2="0"
                     gradientUnits="boundingBox">
      <stop offset="0.0" color="cmyk(0,0,0,1.0)"/>
      <stop offset="0.5" color="lab(45, 10, 15)"/>
      <stop offset="1.0" color="cmyk(0,0.3,0.8,0)"/>
    </linear-gradient>
  </gradient>
</defs>
```

### 4.9.3 Surface Treatment Usage — Spot UV over Matte Laminate

```xml
<!-- In manifest -->
<surface-treatments>
  <surface-treatment id="overall-matte" type="matte-laminate"/>
  <surface-treatment id="title-uv"      type="spot-uv"/>
</surface-treatments>

<!-- In canvas — laminate layer covers everything -->
<layer id="laminate-layer" print:surface-treatment="overall-matte">
  <!-- All content here is under matte laminate -->
  <shape boundary="M 0,0 L 210,0 L 210,297 L 0,297 Z"
         fill="cmyk(0.5,0.2,0,0.1)"/>
</layer>

<!-- Spot UV on top -->
<layer id="finishing-layer">
  <text-block id="main-title"
              font-ref="heading-font"
              size="48pt"
              print:surface-treatment="title-uv">
    <reflow-region shape-ref="canvas-boundary" padding="20mm"/>
    <p fill="none">Luxury Brand Name</p>
  </text-block>
</layer>
```

### 4.9.4 Pattern Fill

```xml
<defs>
  <pattern id="diagonal-lines"
           width="6" height="6"
           units="userSpaceOnUse">
    <shape boundary="M 0,0 L 6,6"
           stroke="cmyk(0,0,0,0.15)"
           stroke-width="1"
           fill="none"/>
    <shape boundary="M -1,5 L 1,7"
           stroke="cmyk(0,0,0,0.15)"
           stroke-width="1"
           fill="none"/>
    <shape boundary="M 5,-1 L 7,1"
           stroke="cmyk(0,0,0,0.15)"
           stroke-width="1"
           fill="none"/>
  </pattern>
</defs>

<shape boundary="M 20,20 A 60,60 0 1,1 20,20.001 Z"
       fill="pattern(diagonal-lines)"
       stroke="cmyk(0.6,0.3,0,0.2)"
       stroke-width="1"/>
```

### 4.9.5 Complete Color-Rich Document Fragment

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mdf version="0.1"
     xmlns="https://morphousdoc.org/ns/0.1"
     xmlns:print="https://morphousdoc.org/ns/print/0.1"
     xmlns:meta="https://morphousdoc.org/ns/meta/0.1"
     xmlns:sem="https://morphousdoc.org/ns/semantics/0.1">

  <manifest>
    <meta:conformance level="2"/>
    <fonts>
      <font id="display" family="Playfair Display" weight="700"
            src="mdfx:display-font" format="woff2" embed="true"/>
    </fonts>
    <icc-profiles>
      <icc-profile id="fogra39" src="mdfx:fogra39"
                   description="ISO Coated v2"/>
    </icc-profiles>
    <spot-colors>
      <spot-color id="gold"
                  name="Pantone 872 C"
                  cmyk="0,0.12,0.55,0.30"
                  lab="61.3,3.2,27.8"
                  plate-name="Pantone 872 C (Gold)"/>
    </spot-colors>
    <surface-treatments>
      <surface-treatment id="foil-gold" type="foil" foil-type="gold"/>
      <surface-treatment id="title-emboss" type="emboss" depth="0.4mm"/>
    </surface-treatments>
    <print-intent substrate="coated" color-mode="cmyk"
                  icc-profile-ref="fogra39" resolution-target="300dpi"/>
  </manifest>

  <canvas width="148" height="210" units="mm"
          boundary="M 0,0 L 148,0 L 148,210 L 0,210 Z"
          print:die-cut="false"
          print:bleed="3mm"
          sem:shape-meaning="card">

    <defs>
      <gradient id="bg-gradient">
        <radial-gradient cx="0.5" cy="0.3" r="0.7"
                         gradientUnits="boundingBox">
          <stop offset="0.0" color="cmyk(0.05,0.1,0.15,0.0)"/>
          <stop offset="1.0" color="cmyk(0.1,0.15,0.25,0.5)"/>
        </radial-gradient>
      </gradient>
    </defs>

    <layer id="bg">
      <shape boundary="M 0,0 L 148,0 L 148,210 L 0,210 Z"
             fill="gradient(bg-gradient)"/>
    </layer>

    <layer id="foil-elements">
      <!-- Gold foil border rule -->
      <shape boundary="M 8,8 L 140,8 L 140,202 L 8,202 Z"
             fill="none"
             stroke="cmyk(0,0,0,0)"
             stroke-width="0.75"
             print:surface-treatment="foil-gold"
             print:overprint="false"/>
    </layer>

    <layer id="content">
      <text-block id="headline" font-ref="display" size="32pt" leading="38pt">
        <reflow-region shape="M 16,40 L 132,40 L 132,120 L 16,120 Z"/>
        <p color="spot(gold, 1.0)"
           print:surface-treatment="title-emboss">The Art of
          <span color="lab(95, 2, 8)">Excellence</span>
        </p>
      </text-block>
    </layer>

  </canvas>

</mdf>
```

---

## 4.10 Conformance Summary

| Feature | Level 1 | Level 2 | Level 3 |
|---------|---------|---------|---------|
| Hex color | Required | Required | Required |
| `rgb()` / `rgba()` | Required | Required | Required |
| `cmyk()` (converted to RGB for display) | Required | Required | Required |
| `cmyk()` (native CMYK output) | — | Required | Required |
| `lab()` | Required | Required | Required |
| `spot()` (CMYK fallback) | Required | Required | Required |
| `spot()` (native separation) | — | Required | Required |
| `device()` | Fallback only | Required | Required |
| Linear gradient | Required | Required | Required |
| Radial gradient | Required | Required | Required |
| Mesh gradient | — | — | Required |
| Pattern fill | Required | Required | Required |
| ICC color management | Recommended | Required | Required |
| Overprint | Ignored | Required | Required |
| Surface treatments | Ignored | Required | Required |
| All blend modes | Required | Required | Required |
