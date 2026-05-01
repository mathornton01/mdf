# MDF Specification v0.1 — Overview

## Goals

MDF (Morphous Document Format) is designed to be:

- **Shape-native**: document boundaries are arbitrary SVG paths, not rectangles. The shape is part of the document's meaning.
- **Print-production-ready**: die-cut specs, bleed, registration marks, spot colors, ink limits, and fold lines are first-class spec elements.
- **Completely open**: Apache 2.0 license, explicit patent non-assertion pledge, community governance.
- **Readable and implementable**: the primary serialization is UTF-8 XML. Any developer with an XML parser and basic graphics knowledge should be able to write a conformant renderer.
- **A true PDF replacement**: not a subset. MDF aims to cover everything PDF does for digital and print documents, plus the shape-native and production features PDF lacks.

## Non-Goals

- MDF is **not** a spreadsheet or presentation format. For those, use ODS/OOXML.
- MDF is **not** a scripting platform. Interactivity (Level 3) is limited to links and annotations — no embedded JavaScript.
- MDF is **not** backward-compatible with PDF. Import/export converters exist as tools, but MDF makes no attempt to replicate PDF's PostScript heritage.
- MDF is **not** an image format. For raster-only content, use PNG/TIFF.

## Design Philosophy

### Shape is Semantics

In every existing document format, shape is decorative. A circle drawn on a PDF page is just a path element — it carries no meaning about the document itself. MDF changes this. The canvas boundary path, and the shapes of reflow regions, carry semantic annotations (`sem:` namespace) that describe what the shape *means*:

- `sem:shape-meaning="badge"` — this circular document is a badge
- `sem:shape-meaning="business-card"` — this rectangular document follows business card conventions
- `sem:shape-meaning="label-bottle"` — this is a wraparound bottle label

This semantic layer enables screen readers, search engines, document management systems, and AI assistants to understand what a document *is* from its shape alone.

### Composition Over Inheritance

Layers, blend modes, color spaces, and typography styles compose rather than cascade. There is no "document default" that elements silently inherit and then contradict. Every element that depends on a context (color space, font, reflow region) must either declare it explicitly or reference a named declaration. This makes MDF documents easier to reason about and easier to implement consistently across renderers.

### Print-First, Screen-Friendly

Most document formats start with screen rendering and bolt on print support. MDF reverses this: print production features are in the core spec (Level 2), and screen rendering is a subset. A Level 2 conformant renderer handles die-cut shapes, spot colors, and registration marks. A Level 1 renderer handles only a subset — this is the screen/browser use case.

## Specification Structure

The spec is organized into numbered chapters:

| Chapter | Title |
|---------|-------|
| 01 | File Structure |
| 02 | Manifest |
| 03 | Canvas and Shape Boundary |
| 04 | Layer Model |
| 05 | Typography and Shape Reflow |
| 06 | Color System |
| 07 | Texture and Pattern System |
| 08 | Semantic Layer |
| 09 | Print Production |
| 10 | Interactivity (Level 3) |
| 11 | Binary Pack Format (.mdfx) |
| 12 | Accessibility |
| 13 | Conformance |

## Normative Language

This specification uses the key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY as defined in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## Versioning

The spec version is declared in the root `<mdf version="...">` attribute. The version string is `MAJOR.MINOR`. Minor versions are backward compatible — a renderer for v0.3 MUST render v0.1 documents correctly. Major versions MAY break compatibility; the transition will be documented in a migration guide.

Current version: **0.1** (pre-alpha draft)
