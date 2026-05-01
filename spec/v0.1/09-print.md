# MDF Specification v0.1 — Chapter 9: Print Production

## 9.1 Overview

Print production features are Level 2 elements in MDF. They are defined in the `print:` namespace (`https://morphousdoc.org/ns/print/0.1`).

A Level 1 (screen) renderer MUST ignore all `print:` elements and attributes. A Level 2 (print) renderer MUST process them correctly.

The philosophy: print production metadata is inseparable from the document itself. A die-cut sticker knows it is a die-cut sticker. Its shape, its bleed, its spot UV coating — these are document facts, not external instructions to a print operator.

## 9.2 Die-Cut

The die-cut specification tells a print shop the exact cut line for the finished piece. In MDF, the die-cut line is the canvas boundary path.

```xml
<canvas width="100" height="100" units="mm"
        boundary="M 50,0 A 50,50 0 1,1 50,0.001 Z"
        print:die-cut="true"
        print:die-cut-type="cut"
        print:bleed="3mm"
        sem:shape-meaning="sticker">
```

### 9.2.1 Die-Cut Types

The `print:die-cut-type` attribute specifies the type of die operation:

| Value | Description |
|-------|-------------|
| `cut` | Full cut through the substrate (default) |
| `score` | Partial cut / score line for folding |
| `perforate` | Series of small cuts for tear-off lines |
| `kiss-cut` | Cuts through face stock only, not liner (stickers on backing) |
| `crease` | Crease without cutting (for fold lines) |

A single canvas can have only one primary die-cut type. For multiple cut types on one piece (e.g., a sticker sheet with kiss-cuts and a full-cut border), use multiple `<print:cut-line>` elements within the canvas:

```xml
<canvas ...>
  <print:cut-lines>
    <print:cut-line id="outer-cut" path="M 0,0 L 100,0 L 100,100 L 0,100 Z" type="cut"/>
    <print:cut-line id="sticker-cut" path="M 50,10 A 40,40 0 1,1 50,10.001 Z" type="kiss-cut"/>
  </print:cut-lines>
  <layers>...</layers>
</canvas>
```

## 9.3 Bleed

The bleed zone extends artwork beyond the trim/die-cut line to ensure no white edges appear after cutting.

```xml
<canvas ... print:bleed="3mm">
```

The `print:bleed` attribute specifies the bleed extension as a length. The canvas boundary path is extended outward by this amount to define the bleed boundary. Artwork in the `background` layer SHOULD extend to the bleed boundary.

Renderers MUST provide a way to:
- Render the document at trim size (no bleed visible) — for final output
- Render with bleed visible — for press checking

### 9.3.1 Safe Zone

The safe zone is an inset from the trim line within which all critical content (text, logos) should be placed. It protects against cutting variation.

```xml
<canvas ... print:bleed="3mm">
  <print:safe-zone margin="5mm" display="advisory"/>
```

The `display="advisory"` attribute means the safe zone boundary is shown in design tools but not rendered in final output.

## 9.4 Color Bars and Registration Marks

Registration marks and color bars are placed outside the trim boundary, in the bleed/slug area.

```xml
<canvas ...>
  <print:marks>
    <print:registration-marks style="crosshair" offset="8mm"/>
    <print:color-bar position="bottom" offset="10mm" width="6mm"
                     colors="cmyk spot:pantone-877c"/>
    <print:crop-marks length="5mm" weight="0.25pt" offset="3mm"/>
    <print:info-block position="top-left" offset="8mm">
      <print:info-field name="file-name" value="circular-resume-v3.mdfx"/>
      <print:info-field name="date" value="auto"/>
      <print:info-field name="color-mode" value="auto"/>
    </print:info-block>
  </print:marks>
</canvas>
```

These elements are rendered on a separate, non-clipped layer above the document content. They are visible only in print output (a screen renderer MAY omit them or show them as an overlay in proof mode).

## 9.5 Color Management for Print

### 9.5.1 Ink Limits

```xml
<print:ink-limits total-area-coverage="320%" black-generation="auto"/>
```

`total-area-coverage` (TAC) specifies the maximum total ink coverage as a percentage. Industry standards:
- Coated paper: 320–350%
- Uncoated paper: 260–280%
- Newsprint: 220–240%

A Level 2 renderer MUST enforce TAC limits when converting RGB colors to CMYK.

### 9.5.2 Overprint

```xml
<layer id="black-text" print:overprint="true">
  <text-block .../>
</layer>
```

When `print:overprint="true"`, the layer's ink plates are printed on top of underlying inks without knocking out. This is the standard treatment for black text in CMYK printing.

### 9.5.3 Spot Colors

Spot colors (Pantone, HKS, etc.) are declared in the manifest:

```xml
<manifest>
  <assets>
    <spot-color id="pantone-877c"
                name="Pantone 877 C"
                cmyk-approximation="0 0 0 0.2"
                lab="78 0 3"
                plate-name="PANTONE 877 C"/>
  </assets>
</manifest>
```

And referenced in content:

```xml
<rect fill="color(spot pantone-877c 1.0)"/>
```

A spot color generates its own ink plate in the print output. A screen renderer MUST use the `cmyk-approximation` or `lab` value for screen display.

## 9.6 Fold Lines

For multi-panel documents (brochures, cards):

```xml
<canvas width="630" height="297" units="mm" ...>
  <print:folds>
    <print:fold id="fold-1" path="M 210,0 L 210,297" type="valley" angle="180deg"/>
    <print:fold id="fold-2" path="M 420,0 L 420,297" type="valley" angle="180deg"/>
  </print:folds>
  <layers>...</layers>
</canvas>
```

Fold types: `valley` (fold toward viewer), `mountain` (fold away from viewer), `score-only`.

## 9.7 Surface Treatments

Special printing effects are declared as `<print:surface-treatment>` elements within a layer:

```xml
<layer id="foil-layer">
  <print:surface-treatment type="hot-foil" color="gold"
                            mask="assets/foil-mask.png"
                            plate-name="FOIL-GOLD"/>
  <rect x="40" y="40" width="120" height="30" fill="color(spot pantone-877c 1.0)"/>
</layer>

<layer id="spot-uv-layer">
  <print:surface-treatment type="spot-uv"
                            mask="assets/uv-pattern.png"
                            plate-name="SPOT-UV"/>
</layer>
```

Supported surface treatment types:
- `spot-uv` — UV spot varnish
- `hot-foil` — metallic foil stamping
- `emboss` — blind emboss or deboss
- `deboss` — deboss (pressed in)
- `soft-touch` — soft-touch laminate coverage area
- `gloss-laminate` — gloss laminate coverage area
- `matte-laminate` — matte laminate coverage area

## 9.8 Print Intent Declaration

The manifest SHOULD declare the print intent to help processors and RIPs configure correctly:

```xml
<manifest>
  <print:intent>
    <print:substrate>coated</print:substrate>
    <print:color-mode>cmyk</print:color-mode>
    <print:icc-profile ref="fogra39"/>
    <print:resolution target="300dpi" minimum="150dpi"/>
    <print:press-type>offset-lithography</print:press-type>
  </print:intent>
</manifest>
```
