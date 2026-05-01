# MDF — Morphous Document Format

MDF is an open, next-generation document format designed to replace PDF for digital and print production workflows. Its defining feature: **the shape of a document is a first-class semantic element**, not just a visual decoration.

## Why MDF?

PDF was designed in 1993. Its page is always a rectangle. Its print production model is an afterthought bolted onto PostScript. Its spec is complex, patent-entangled, and difficult to implement from scratch.

MDF starts from different axioms:

1. **Shape is semantics.** A circular resume, a key-shaped brochure, a star-shaped badge — the form communicates meaning before you read a word. MDF encodes this.
2. **Print-first, screen-friendly.** Die-cut specs, bleed zones, registration marks, ink limits, spot colors — all first-class elements in the spec, not PostScript hacks.
3. **Composition over inheritance.** Layers, textures, color spaces, and reflow regions compose cleanly. No Z-order surprises.
4. **Completely open.** Apache 2.0 license. Explicit patent non-assertion pledge. Governed by a community steering committee.

## Format at a Glance

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mdf version="0.1" xmlns="https://morphousdoc.org/ns/0.1">
  <manifest>
    <meta:title>My Circular Resume</meta:title>
    <conformance level="print"/>
  </manifest>

  <!-- The document boundary is an SVG path — any shape is valid -->
  <canvas width="200mm" height="200mm" units="mm"
          boundary="M 100,0 A 100,100 0 1,1 100,0.001 Z"
          print:die-cut="true"
          print:bleed="3mm"
          sem:shape-meaning="badge">

    <layers>
      <layer id="background">
        <rect fill="color(cmyk 0 0 0 0.05)" shape="inherit"/>
      </layer>
      <layer id="content">
        <!-- Text reflows inside the circular boundary automatically -->
        <text-block font="body" size="10pt">
          <reflow-region shape="inherit" padding="10mm"/>
          <p>Jane Smith — Software Engineer</p>
        </text-block>
      </layer>
    </layers>

  </canvas>
</mdf>
```

## File Formats

| Extension | Description |
|-----------|-------------|
| `.mdf`    | Plain UTF-8 XML — human-readable, versionable |
| `.mdfx`   | Binary bundle (ZIP64) — XML + fonts + ICC profiles + assets |

## Conformance Levels

| Level | Name    | Description |
|-------|---------|-------------|
| 1     | Basic   | Rectangular canvas, RGB color, screen rendering |
| 2     | Print   | Arbitrary canvas shape, CMYK, die-cut, bleed, marks |
| 3     | Full    | Gradient mesh, compound reflow regions, surface textures, interactivity |

## Project Layout

```
spec/           Versioned specification documents
schema/         XML Schema + JSON Schema definitions
reference-impl/ Reference implementations (Python primary, Rust performance)
viewer/         Browser-based viewer (TypeScript + WebGL)
examples/       Annotated example .mdf documents
conformance/    Conformance test suite
tools/          CLI tools (mdf-lint, mdf-pack)
docs/           Documentation site source
```

## Status

This project is in **pre-alpha (v0.1 draft)** status. The spec is being written. No stable API or format compatibility is guaranteed until v1.0.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions require agreeing to the [Contributor License Agreement](CLA.md) and adherence to the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

Apache 2.0. See [LICENSE](LICENSE) and [PATENTS.md](PATENTS.md) for the patent non-assertion pledge.

## Governance

MDF is governed by a steering committee. See [CHARTER.md](CHARTER.md).
