# MDF Project Roadmap

## v0.1 — Foundation (current)

Goal: establish the core spec architecture and a working proof-of-concept renderer.

- [x] Project structure and governance documents
- [x] Spec chapters: overview, file structure, canvas/shape boundary, typography, print production
- [x] Spec chapters: manifest, layer model, color system, semantics, conformance
- [ ] Spec chapters: texture system, accessibility (standalone chapter), binary pack
- [x] XML Schema definitions for core elements (XSD for all four namespaces)
- [x] Python reference implementation: parser + SVG renderer
- [x] Python SVG renderer: full color notation support (cmyk, gray, lab, spot, rgba)
- [x] Example documents: shapes (circle, star, heart, hexagon, shield), basic, color, semantics, typography, print-production
- [ ] Conformance suite Level 1 (basic)

## v0.2 — Shape Reflow

Goal: working shape-aware text reflow in the reference implementation.

- [ ] Finalize typography spec including reflow algorithm
- [ ] Python: scanline tessellator implementation
- [ ] Python: HarfBuzz integration for text shaping
- [ ] Python: hyphenation support
- [ ] Reflow examples: text in circle, text in polygon, multi-column in hexagon
- [ ] Conformance suite Level 1 (complete)

## v0.3 — Print Production

Goal: full Level 2 (print) conformance in the reference implementation.

- [ ] Print spec finalization: die-cut, bleed, marks, ink limits, overprint
- [ ] Spot color support
- [ ] ICC profile integration
- [ ] Python: PDF export for print pipeline
- [ ] Print production examples: sticker sheet, business card, brochure
- [ ] Conformance suite Level 2

## v0.4 — Viewer and Ecosystem

Goal: browser-based viewer and ecosystem tooling.

- [ ] TypeScript web viewer (Canvas2D)
- [ ] mdf-lint CLI tool
- [ ] mdf-pack CLI tool
- [ ] VSCode extension for syntax highlighting
- [ ] Basic documentation site

## v0.5 — Rust Engine

Goal: production-grade renderer for WASM and server-side use.

- [ ] Rust parser (roxmltree)
- [ ] Rust reflow engine
- [ ] tiny-skia based renderer
- [ ] WASM compilation target
- [ ] Web viewer upgraded to WASM engine

## v0.6 — Textures and Color

Goal: full color system and texture/pattern support.

- [ ] Gradient mesh (Coons patch)
- [ ] Pattern fill system
- [ ] Surface texture declarations (spot UV, foil, emboss)
- [ ] Color management pipeline (LAB, spectral)
- [ ] Conformance suite: color and texture

## v1.0 — Stable

Goal: stable spec, two independent conformant implementations.

- [ ] All spec chapters complete and reviewed
- [ ] Python reference implementation passes Level 1 and 2 conformance
- [ ] Rust implementation passes Level 1 and 2 conformance
- [ ] Web viewer functional
- [ ] Documentation site live at morphousdoc.org
- [ ] Steering Committee votes to declare stable

## Future (post 1.0)

- Interactivity layer (links, annotations, form fields)
- Compound reflow regions (holes, multi-path)
- 3D document geometry (fold/unfold simulation)
- Animation layer
- Digital signature and DRM (optional, not in core spec)
- PDF import/export fidelity improvements
