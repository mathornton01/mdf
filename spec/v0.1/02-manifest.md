# MDF Specification v0.1 — Chapter 2: Manifest and Metadata

## 2.1 Overview

The `<manifest>` element is a required direct child of the root `<mdf>` element. It MUST appear before any `<canvas>` or `<document>` element. The manifest serves two distinct purposes:

1. **Metadata** — document title, authorship, creation date, language, and descriptive fields. These correspond to the `meta:` namespace elements defined in this chapter.
2. **Asset declarations** — fonts, ICC color profiles, and spot colors that are referenced by content elements throughout the document. Assets MUST be declared in the manifest before any element references them.

A conformant processor MUST parse the manifest before rendering any canvas content. If the manifest declares assets that cannot be resolved (missing files, failed integrity checks), the processor MUST NOT silently substitute alternative assets without warning the user.

A conformant processor MUST ignore elements in unknown namespaces within `<manifest>`. Extension elements MUST NOT be required for rendering conformance.

## 2.2 Manifest Element

```xml
<manifest
  xmlns:meta="https://morphousdoc.org/ns/meta/0.1">
```

The `<manifest>` element takes no attributes of its own. All configuration is expressed through child elements. The `meta:` namespace prefix MUST be declared on either the root `<mdf>` element or the `<manifest>` element before any `<meta:*>` child is used.

The manifest contains the following child sections, in the order specified:

1. Metadata elements (`<meta:title>`, `<meta:author>`, etc.)
2. `<meta:conformance>`
3. `<fonts>`
4. `<icc-profiles>`
5. `<spot-colors>`
6. `<print-intent>`

All sections are optional unless stated otherwise. A minimal conformant manifest MAY be empty.

## 2.3 Metadata Elements

Metadata elements use the `meta:` namespace (`https://morphousdoc.org/ns/meta/0.1`). All metadata elements are optional. Their values are plain text unless otherwise noted.

### 2.3.1 Element Reference

| Element | Required | Content Type | Description |
|---------|----------|--------------|-------------|
| `<meta:title>` | No | Plain text | Human-readable document title |
| `<meta:author>` | No | Plain text | Primary author name or organization |
| `<meta:created>` | No | ISO 8601 datetime | Document creation timestamp |
| `<meta:language>` | No | BCP 47 tag | Primary language of the document content |
| `<meta:description>` | No | Plain text | Short description or abstract |
| `<meta:keywords>` | No | Plain text | Comma-separated keywords |
| `<meta:subject>` | No | Plain text | Subject category or classification |

### 2.3.2 `<meta:created>`

The value of `<meta:created>` MUST be a valid ISO 8601 datetime string. It SHOULD include a timezone offset or `Z` for UTC. If the timezone is omitted, the value is interpreted as local time at the point of creation, and this ambiguity SHOULD be avoided.

```xml
<meta:created>2024-11-15T09:30:00Z</meta:created>
```

### 2.3.3 `<meta:language>`

The value of `<meta:language>` MUST be a valid BCP 47 language tag (as defined in [RFC 5646](https://www.rfc-editor.org/rfc/rfc5646)). The default, if absent, is `und` (undetermined). The language declared here is the document-level default; individual `<text-block>` elements MAY override it with a `language` attribute.

```xml
<meta:language>en-US</meta:language>
```

## 2.4 Conformance Declaration

```xml
<meta:conformance level="2"/>
```

The `<meta:conformance>` element declares the conformance level that the document author intends the document to satisfy. This is a declaration of intent, not a computed property — a processor MUST NOT refuse to parse a document solely because it claims a conformance level the processor does not support.

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `level` | Yes | — | Integer: `1`, `2`, or `3` |

Conformance level meanings:

| Level | Name | Description |
|-------|------|-------------|
| `1` | Basic | Screen rendering, core shapes, typography, RGB/sRGB color, raster images. No print-specific features. |
| `2` | Print | Extends Level 1 with CMYK, spot colors, ICC profiles, bleed, die-cut, print marks, surface treatments, and embedded fonts. |
| `3` | Full | Extends Level 2 with mesh gradients, compound canvas paths, linked text overflow chains, interactivity, and accessibility annotations. |

A Level 2 document MUST satisfy all Level 1 requirements. A Level 3 document MUST satisfy all Level 2 requirements. A processor that claims to support Level N MUST support all levels 1 through N.

If `<meta:conformance>` is absent, the processor MUST assume Level 1.

## 2.5 Font Declarations

The `<fonts>` section declares all font assets used in the document. Each font face is declared as a `<font>` element.

```xml
<fonts>
  <font id="body-font"
        family="Inter"
        weight="400"
        style="normal"
        src="fonts/Inter-Regular.woff2"
        format="woff2"
        embed="true"/>
  <font id="body-font-bold"
        family="Inter"
        weight="700"
        style="normal"
        src="fonts/Inter-Bold.woff2"
        format="woff2"
        embed="true"/>
  <font id="body-font-italic"
        family="Inter"
        weight="400"
        style="italic"
        src="fonts/Inter-Italic.woff2"
        format="woff2"
        embed="true"/>
</fonts>
```

### 2.5.1 Font Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `id` | Yes | — | Unique identifier; referenced by `font-ref` on text elements |
| `family` | Yes | — | Font family name as it appears in the font's name table |
| `weight` | No | `400` | Numeric weight: `100`, `200`, `300`, `400`, `500`, `600`, `700`, `800`, `900` |
| `style` | No | `normal` | `normal` or `italic` or `oblique` |
| `src` | Yes | — | Path, URL, data URI, or `mdfx:` asset reference |
| `format` | No | `woff2` | `woff2`, `woff`, `otf`, `ttf` |
| `embed` | No | `false` | Whether the font binary is embedded (see §2.5.2) |

The `id` attribute MUST be unique within the document. A processor that encounters duplicate `id` values MUST treat the first declaration as canonical and SHOULD emit a warning for subsequent duplicates.

### 2.5.2 Font Embedding

The `embed` attribute controls whether the font binary is embedded in the document:

- `embed="true"` — the font binary is expected to be present in the document bundle. In an `.mdfx` file, this means the font file is in the `fonts/` directory of the ZIP archive. In a plain `.mdf` file, this means the `src` is either a relative file path (resolved relative to the `.mdf` file) or a data URI.
- `embed="false"` — the font is a reference only. The processor MUST attempt to resolve `src`. If the font cannot be resolved, the processor SHOULD fall back to a generic font in the same metric class and MUST warn the user.

A Level 2 (print) conformant document MUST set `embed="true"` for all fonts used in print content. A Level 2 processor MUST reject a document for print production output if any print-content font has `embed="false"` and cannot be resolved.

### 2.5.3 Font References in `.mdfx` Bundles

In an `.mdfx` bundle, embedded fonts are stored in the `fonts/` directory and referenced by their bundle asset ID using the `mdfx:` scheme:

```xml
<font id="body-font"
      family="Inter"
      weight="400"
      style="normal"
      src="mdfx:body-font"
      format="woff2"
      embed="true"/>
```

The asset ID (`body-font`) MUST match the `id` field in the `META-INF/manifest.json` bundle manifest. See Chapter 1 §1.3.2 for the full asset reference scheme.

### 2.5.4 Font Subsetting

When a Level 2 or Level 3 document is exported for distribution, a conformant producer SHOULD subset embedded fonts to include only the Unicode codepoints used in the document. A processor MUST NOT assume that an embedded font file is complete; it MUST only use glyphs that are present in the font file.

## 2.6 ICC Profile Declarations

The `<icc-profiles>` section declares ICC color profile assets. Profiles declared here are referenced by `<print-intent>` and by individual color values using the `device()` color notation.

```xml
<icc-profiles>
  <icc-profile id="fogra39"
               src="icc/ISOcoated_v2_eci.icc"
               description="ISO Coated v2 (FOGRA39)"/>
  <icc-profile id="srgb"
               src="icc/sRGB_IEC61966-2-1.icc"
               description="sRGB IEC61966-2-1"/>
</icc-profiles>
```

### 2.6.1 ICC Profile Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `id` | Yes | — | Unique identifier within the document |
| `src` | Yes | — | Path, URL, or `mdfx:` reference to the ICC profile file |
| `description` | No | — | Human-readable name of the profile |

The `id` attribute MUST be unique across all ICC profiles in the document. A processor MUST verify that the referenced file is a valid ICC profile (magic number `acsp` at byte offset 36 in the profile header) before applying it to color transforms.

In an `.mdfx` bundle, ICC profiles are stored in the `icc/` directory:

```xml
<icc-profile id="fogra39"
             src="mdfx:fogra39"
             description="ISO Coated v2 (FOGRA39)"/>
```

## 2.7 Spot Color Declarations

The `<spot-colors>` section declares named spot colors. These are referenced in color values using the `spot()` notation defined in Chapter 4.

```xml
<spot-colors>
  <spot-color id="pantone-485c"
              name="Pantone 485 C"
              cmyk="0,0.95,0.95,0.05"
              lab="53.2,71.4,49.6"
              plate-name="Pantone 485 C"/>
  <spot-color id="pantone-877c"
              name="Pantone 877 C"
              cmyk="0,0,0,0.45"
              lab="60.0,0.0,0.0"
              plate-name="Pantone 877 C (Silver)"/>
</spot-colors>
```

### 2.7.1 Spot Color Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `id` | Yes | — | Unique identifier; used in `spot(id, tint)` color references |
| `name` | Yes | — | Human-readable color name (e.g. `Pantone 485 C`) |
| `cmyk` | Yes | — | CMYK approximation as four comma-separated floats in `[0.0, 1.0]` |
| `lab` | No | — | CIE L*a*b* values as three comma-separated floats; provides a device-independent color target |
| `plate-name` | No | — | Ink plate identifier used in press-ready output; if absent, defaults to `name` |

The `cmyk` attribute provides a fallback approximation for rendering contexts that cannot use the spot ink directly (Level 1 renderers, screen preview). A Level 2 processor MUST preserve spot colors as separate ink channels in print production output; it MUST NOT silently flatten spot colors to CMYK without a user-visible warning.

The `lab` attribute, when present, MUST be used by color-managed workflows as the colorimetric target for spot color simulation. When `lab` is absent, the `cmyk` approximation is used for colorimetric intent.

## 2.8 Print Intent

The `<print-intent>` element declares the intended print production context for the document. It is required for Level 2 conformance.

```xml
<print-intent
  substrate="coated"
  color-mode="cmyk"
  icc-profile-ref="fogra39"
  resolution-target="300dpi"
  press-type="offset-litho"/>
```

### 2.8.1 Print Intent Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `substrate` | Level 2 | `coated` | Print substrate type |
| `color-mode` | Level 2 | `cmyk` | Primary color mode for production output |
| `icc-profile-ref` | Level 2 | — | `id` of the ICC profile to use as the output intent |
| `resolution-target` | Level 2 | `300dpi` | Target rasterization resolution |
| `press-type` | No | — | Press technology identifier |

#### `substrate` values

| Value | Description |
|-------|-------------|
| `coated` | Coated paper (gloss or silk). Default for offset litho. |
| `uncoated` | Uncoated paper. Typically requires higher ink density for equivalent density. |
| `specialty` | Specialty substrate: foil, synthetic, board, textile, etc. The press operator is responsible for color profiling. |

#### `color-mode` values

| Value | Description |
|-------|-------------|
| `cmyk` | Four-color process printing. Default for most offset and digital press production. |
| `rgb` | RGB output (digital wide-format, inkjet, screen). |
| `grayscale` | Single-channel grayscale output. |
| `spot` | Spot-color-only output (e.g. two-color Pantone jobs). |

A document with `color-mode="cmyk"` SHOULD specify `icc-profile-ref` pointing to a declared ICC profile. If no ICC profile is declared and `color-mode="cmyk"`, a Level 2 processor MUST assume ISO Coated v2 (FOGRA39) as the default output intent.

#### `resolution-target` values

| Value | Description |
|-------|-------------|
| `300dpi` | Standard offset press. Default. |
| `600dpi` | High-resolution digital press or fine-art print. |
| `1200dpi` | High-fidelity inkjet or flexo preparation. |

The `resolution-target` applies to rasterization of vector elements for production output; it does not constrain the resolution of raster image assets within the document.

#### `press-type` values

This attribute is informational and does not affect rendering behavior. Suggested values:

`offset-litho`, `digital-hp-indigo`, `digital-xerox-iridesse`, `flexo`, `gravure`, `screen-print`, `inkjet-wide-format`, `laser`

A processor MUST NOT reject a document with an unrecognized `press-type` value.

### 2.8.2 Relationship to ICC Profiles

The `icc-profile-ref` attribute MUST reference the `id` of an `<icc-profile>` element declared in the `<icc-profiles>` section of the same manifest. A processor that encounters an `icc-profile-ref` that does not match any declared profile MUST treat this as an error condition and MUST NOT proceed to production output without user intervention.

## 2.9 Validation Rules

### 2.9.1 ID Uniqueness

All `id` attributes within `<fonts>`, `<icc-profiles>`, and `<spot-colors>` MUST be unique across the entire manifest. A `<font>` and an `<icc-profile>` MUST NOT share the same `id`. The uniqueness domain is the manifest element.

### 2.9.2 Reference Integrity

Every reference in the document MUST resolve to a declaration in the manifest:

- `font-ref="X"` on a `<text-block>` or inline element MUST match the `id` of a declared `<font>`.
- `icc-profile-ref="X"` on `<print-intent>` MUST match the `id` of a declared `<icc-profile>`.
- `spot(X, ...)` in a color value MUST match the `id` of a declared `<spot-color>`.

A conformant processor MUST report a validation error for any unresolved reference. It MAY attempt to render the document in a degraded mode, substituting a placeholder color (such as magenta) for unresolved spot colors.

### 2.9.3 Unknown Elements

A conformant processor MUST ignore elements in unknown namespaces within `<manifest>`. It MUST NOT treat unknown elements as errors. This rule enables forward compatibility and private extensions. Unknown elements MUST be preserved in round-trip serialization (a processor that reads and re-serializes an MDF document MUST preserve unknown manifest elements).

### 2.9.4 Level Consistency

If `<meta:conformance level="2"/>` is declared, the processor SHOULD warn if no `<print-intent>` element is present. If `<meta:conformance level="2"/>` is declared and text content uses fonts with `embed="false"`, the processor MUST warn.

## 2.10 Complete Manifest Example

The following is a complete manifest for a coated-stock CMYK brochure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mdf version="0.1"
     xmlns="https://morphousdoc.org/ns/0.1"
     xmlns:print="https://morphousdoc.org/ns/print/0.1"
     xmlns:sem="https://morphousdoc.org/ns/semantics/0.1"
     xmlns:meta="https://morphousdoc.org/ns/meta/0.1">

  <manifest>

    <!-- === Metadata === -->
    <meta:title>Acme Widget Co. — Product Brochure 2024</meta:title>
    <meta:author>Acme Design Team</meta:author>
    <meta:created>2024-11-15T09:30:00Z</meta:created>
    <meta:language>en-US</meta:language>
    <meta:description>
      Four-color coated brochure for the Acme Widget product line,
      Q4 2024 release. Die-cut circular format.
    </meta:description>
    <meta:keywords>widget, acme, product, brochure, 2024</meta:keywords>
    <meta:subject>Product Marketing</meta:subject>

    <!-- === Conformance === -->
    <meta:conformance level="2"/>

    <!-- === Fonts === -->
    <fonts>
      <font id="heading-font"
            family="Playfair Display"
            weight="700"
            style="normal"
            src="mdfx:heading-font"
            format="woff2"
            embed="true"/>
      <font id="body-font"
            family="Inter"
            weight="400"
            style="normal"
            src="mdfx:body-font"
            format="woff2"
            embed="true"/>
      <font id="body-font-bold"
            family="Inter"
            weight="700"
            style="normal"
            src="mdfx:body-font-bold"
            format="woff2"
            embed="true"/>
      <font id="caption-font"
            family="Inter"
            weight="400"
            style="italic"
            src="mdfx:caption-font"
            format="woff2"
            embed="true"/>
    </fonts>

    <!-- === ICC Profiles === -->
    <icc-profiles>
      <icc-profile id="fogra39"
                   src="mdfx:fogra39"
                   description="ISO Coated v2 (FOGRA39)"/>
    </icc-profiles>

    <!-- === Spot Colors === -->
    <spot-colors>
      <spot-color id="acme-red"
                  name="Pantone 485 C"
                  cmyk="0,0.95,0.95,0.05"
                  lab="53.2,71.4,49.6"
                  plate-name="Pantone 485 C"/>
      <spot-color id="acme-silver"
                  name="Pantone 877 C"
                  cmyk="0,0,0,0.45"
                  lab="60.0,0.0,0.0"
                  plate-name="Pantone 877 C (Silver)"/>
    </spot-colors>

    <!-- === Print Intent === -->
    <print-intent
      substrate="coated"
      color-mode="cmyk"
      icc-profile-ref="fogra39"
      resolution-target="300dpi"
      press-type="offset-litho"/>

  </manifest>

  <canvas width="200" height="200" units="mm"
          boundary="M 100,0 A 100,100 0 1,1 100,0.001 Z"
          print:die-cut="true"
          print:bleed="3mm"
          sem:shape-type="circle"
          sem:shape-meaning="card">
    <!-- canvas content -->
  </canvas>

</mdf>
```

## 2.11 Minimal Manifest Example

The following is a minimal conformant manifest for a Level 1 (screen) document:

```xml
<manifest>
  <meta:title>Hello World</meta:title>
  <meta:conformance level="1"/>
  <fonts>
    <font id="body-font"
          family="Inter"
          weight="400"
          style="normal"
          src="fonts/Inter-Regular.woff2"
          format="woff2"/>
  </fonts>
</manifest>
```

Note that `embed="false"` is the default; this is acceptable for Level 1 documents. The font will be resolved from the path relative to the `.mdf` file.
