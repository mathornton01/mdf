# MDF Spec Changelog

## v0.1.0 — 2026-05-01 (initial draft)

First public draft of the MDF specification.

Chapters published:
- 00: Overview (goals, non-goals, design philosophy)
- 01: File structure (.mdf XML, .mdfx bundle)
- 03: Canvas and shape boundary (the core innovation)
- 05: Typography and shape reflow algorithm
- 09: Print production (die-cut, bleed, marks, spot colors)

Chapters in progress:
- 02: Manifest
- 04: Layer model
- 06: Color system
- 07: Texture and pattern system
- 08: Semantic layer
- 10: Interactivity
- 11: Binary pack format
- 12: Accessibility
- 13: Conformance

Reference implementation:
- Python: document model, reflow tessellator stub, CLI skeleton
- Rust: not yet started
- Web viewer: not yet started
