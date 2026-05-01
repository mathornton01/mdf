# MDF Specification v0.1 — Chapter 8: Conformance

## 8.1 Overview

The MDF specification defines three conformance levels for documents and five
conformance classes for processors. These are designed to allow incremental
adoption: a browser-based viewer need only implement Level 1, while a commercial
print workflow system implements all three levels. Higher levels are strict
supersets of lower levels — a Level 2 document is also a valid Level 1 document, and
a Level 3 processor correctly processes Level 1 and Level 2 documents.

The conformance level of a document is declared in its manifest:

```xml
<manifest>
  <meta:conformance level="1"/>
</manifest>
```

A document that does not declare a conformance level MUST be treated as Level 1 by
conformant processors.

This chapter uses the terms MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY as defined
in RFC 2119.

## 8.2 Level 1 — Basic Conformance

Level 1 is the minimum conformance level for all MDF documents. It covers
screen-renderable documents with arbitrary shape boundaries, shape-aware typography,
and semantic annotations. Level 1 does not require print-specific features.

### 8.2.1 Level 1 Document Requirements

A Level 1 conformant document MUST satisfy all of the following:

**Structure**

1. Parse as well-formed XML 1.0 encoded in UTF-8.
2. Have a root element `<mdf>` in the namespace `https://morphousdoc.org/ns/0.1`.
3. The `<mdf>` root element MUST have a `version` attribute containing a valid MDF
   version string of the form `MAJOR.MINOR` (e.g. `"0.1"`).
4. Contain exactly one `<manifest>` element as the first child of `<mdf>`.
5. Contain either exactly one `<canvas>` element as a direct child of `<mdf>`, or
   exactly one `<document>` element containing one or more `<canvas>` elements.
6. `<meta:conformance level="1"/>` MUST be present in `<manifest>` (or the
   conformance attribute may be absent, in which case Level 1 is assumed).

**Canvas**

7. Each `<canvas>` element MUST have `width`, `height`, and `units` attributes.
8. Each `<canvas>` element MUST have a `boundary` attribute containing a valid SVG
   path data string.
9. The boundary path MUST be closed (end with `Z` or `z`).
10. The boundary path MUST be simply connected (no holes, no multiple sub-paths).
11. The boundary path MUST be non-self-intersecting.
12. The boundary path MUST fit within the bounding box defined by `width` and
    `height`.

**Layers**

13. All `<layer>` `blend-mode` attribute values MUST be from the vocabulary defined
    in §6.2.2, or absent (defaulting to `normal`).
14. All `<layer>` `opacity` values MUST be in the range `[0.0, 1.0]`.

**Typography**

15. All `<text-block>` elements MUST have a `font-ref` attribute whose value
    references a `<font>` declared in the manifest.
16. All `<text-block>` elements MUST contain a `<reflow-region>` child element.
17. Each `<reflow-region>` MUST have either a `shape` or a `shape-ref` attribute,
    but not both.
18. All font assets referenced in the manifest MUST be resolvable from the document
    (embedded, local, or fetchable URL) at render time.

**Colors**

19. All color values MUST use valid MDF color syntax (Chapter 4).
20. Undefined color function names MUST cause a validation error.

**Namespace**

21. A conformant Level 1 document MUST NOT use the `print:` namespace
    (`https://morphousdoc.org/ns/print/0.1`) for any element or attribute that is
    defined by this specification as Level 2 or Level 3 only. Extension attributes
    in the `print:` namespace that are not defined in this specification MAY be
    present.

### 8.2.2 Level 1 Processor Requirements

A Level 1 conformant processor MUST:

1. Accept both `.mdf` (plain XML) and `.mdfx` (ZIP bundle) formats.
2. Parse all Level 1 XML elements and attributes defined in this specification.
3. Render all `<canvas>`, `<layer>`, `<shape>`, `<image>`, `<text-block>`, and
   `<group>` elements as defined in Chapters 3, 5, and 6.
4. Implement the shape reflow algorithm as specified in §5.4, including:
   a. Scanline tessellation (§5.4.2)
   b. HarfBuzz-compatible glyph packing (§5.4.3)
   c. Overflow clipping and linked overflow (§5.4.4)
5. Apply boundary clipping to rendered output: content outside the canvas boundary
   path MUST NOT appear in output (§3.5).
6. Implement all Required blend modes defined in §6.2.2.
7. Implement the alpha compositing formula in §6.7.4 using linear light color space
   (§6.7.5).
8. Resolve font assets from all three source types: embedded data URIs, relative
   paths (for `.mdf`), and `mdfx:` IDs (for `.mdfx` bundles).
9. Ignore elements and attributes in unknown XML namespaces without raising an
   error (unknown namespace passthrough, §1.2.1).
10. Report validation errors for any Level 1 document requirement (§8.2.1) that is
    violated.
11. Verify SHA-256 hashes for assets in `.mdfx` bundles (§1.3.1) and MUST either
    reject or warn on mismatch.

A Level 1 conformant processor MUST NOT:

- Render content outside the canvas boundary path.
- Fail to parse a document solely because it contains unknown elements or attributes
  in unknown namespaces.
- Silently corrupt text content during round-trip parse-and-serialize.

A Level 1 conformant processor SHOULD:

- Produce an accessibility tree from `sem:` annotations (§7.4.5).
- Expose `sem:alt-text` values to platform accessibility APIs.
- Preserve all XML content (including unknown elements) on round-trip serialization.

## 8.3 Level 2 — Print Conformance

Level 2 adds print-production capabilities to Level 1. A Level 2 conformant
document is suitable for submission to a professional print workflow.

### 8.3.1 Level 2 Document Requirements

A Level 2 conformant document MUST satisfy all Level 1 requirements (§8.2.1), plus:

**Manifest**

1. `<meta:conformance level="2"/>` MUST be present in `<manifest>`.
2. A `<print-intent>` element MUST be present in `<manifest>` with valid
   `substrate`, `color-mode`, and `icc-profile-ref` attributes.
3. The ICC profile referenced by `icc-profile-ref` MUST be declared in the manifest
   and MUST be resolvable.
4. All fonts MUST be embedded (`embed="true"` on each `<font>` declaration). External
   font URLs are not permitted in Level 2 documents.

**Color**

5. All design content colors (body layer elements) MUST be in a print-appropriate
   color space: CMYK (`color(cmyk ...)`) or a declared spot color (`spot(...)`).
6. RGB and HSL color values MUST NOT appear on any element in a layer with
   `print:role="body"`. They MAY appear on layers with
   `print:visible-in-render="false"` that are for screen-preview purposes only.
7. All `color(cmyk ...)` values MUST satisfy the ink limit declared in the ICC
   profile. A Level 2 validator MUST check ink limit compliance.

**Geometry**

8. If `print:die-cut="true"` on the canvas, a bleed region MUST be declared via
   `print:bleed` with a value of at least `2mm` (or equivalent in other units).
9. If `print:die-cut="true"`, the document SHOULD contain a layer with
   `print:role="die-cut-overlay"` whose geometry defines the die-cut path.
10. If registration marks are enabled (`print:registration-marks` in the manifest's
    `<print-intent>`), the document MUST contain a layer with
    `print:role="registration-marks"`.

**Spot Colors**

11. All spot colors used in the document MUST be declared in the manifest as
    `<spot-color>` elements with valid `name`, `cmyk-approximation`, and optionally
    `lab` values.
12. Each spot color plate layer (`print:role="spot-color-plate"`) MUST use exactly
    one spot color. Mixed-ink spot-color layers are not permitted at Level 2.

### 8.3.2 Level 2 Processor Requirements

A Level 2 conformant processor MUST satisfy all Level 1 processor requirements
(§8.2.2), plus:

1. Parse and render all Level 2 print-namespace elements and attributes.
2. Separate spot color plates: produce one additional output channel per
   `print:role="spot-color-plate"` layer, named by the spot color.
3. Generate bleed regions by extending the canvas content to the bleed boundary
   defined by `print:bleed` on the canvas.
4. Generate crop marks and registration crosshairs from the
   `print:role="registration-marks"` layer, or auto-generate them if the layer is
   empty and registration marks are declared in `<print-intent>`.
5. Export to PDF/X-4 on request (via `--export-pdfx` flag or equivalent API). The
   exported PDF/X-4 MUST:
   a. Embed all fonts as subsets.
   b. Embed the declared ICC profile as the output intent.
   c. Include all spot color channels as DeviceN colorants.
   d. Comply with PDF/X-4 output intent and transparency requirements.
6. Apply the ink limit from the ICC profile. Elements that exceed the ink limit MUST
   be flagged in validation output; renderers SHOULD clamp to the ink limit.
7. Handle overprint correctly: elements on layers with `print:overprint="true"` MUST
   be composited without knocking out underlying ink. Screen renderers SHOULD
   simulate overprint using the `multiply` blend mode (§6.2.5).
8. Verify that all ICC profiles are valid ICC v2 or v4 profiles and MUST report
   errors for corrupt or missing profiles.

A Level 2 conformant processor SHOULD:

- Provide a soft-proofing preview mode that simulates press output using the
  declared ICC profile.
- Warn when an image's effective resolution (given its placed size) is below the
  `print:resolution-check` value declared on the `<image>` element.
- Implement GCR (grey component replacement) and UCR (undercolour removal) as
  defined by the output ICC profile.

## 8.4 Level 3 — Full Conformance

Level 3 is the complete MDF feature set. It adds advanced vector features, extended
color science, 3D structural simulation, and full linked data capabilities.

### 8.4.1 Level 3 Document Requirements

A Level 3 conformant document MUST satisfy all Level 2 requirements (§8.3.1), plus:

**Manifest**

1. `<meta:conformance level="3"/>` MUST be present in `<manifest>`.

**Paths and Geometry**

2. Compound paths (boundary paths with holes or multiple sub-paths) are permitted on
   the canvas element at Level 3 (§3.4.1). The sub-path winding rule MUST be
   declared via `fill-rule="evenodd"` or `fill-rule="nonzero"` on the canvas.
3. Mesh gradient fills on `<shape>` elements are permitted. A mesh gradient MUST be
   declared as a `<mesh-gradient>` child of the `<shape>`, with a grid of patch
   mesh nodes conforming to the Coons patch mesh format (as in PDF Type 7 shading).

**Color**

4. Spectral color values using the `color(spectral ...)` function MAY be used at
   Level 3. The spectral data MUST include reflectance values at standard 10nm
   intervals from 380nm to 730nm (36 values).
5. Multi-channel DeviceN colors (more than four channels) are permitted.

**3D Structure**

6. Fold simulation using `<fold-line>` elements is a Level 3 feature. Each
   `<fold-line>` MUST have a `path`, `fold-type`, and `angle` attribute.
7. A Level 3 document MAY include a `<sem:3d-structure>` element in the manifest
   describing the 3D folded form of the document (for packaging dielines).

**Accessibility**

8. A Level 3 document MUST include complete `sem:reading-order` attributes on all
   non-decorative content elements, OR a `<sem:reading-order>` declaration in the
   manifest.
9. All `<image>` elements carrying semantic content MUST have `sem:alt-text`.
10. All heading elements MUST have correct `sem:heading-level` values in a valid
    hierarchy (no skipped heading levels without explicit `sem:heading-skip`).

**Linked Data**

11. A Level 3 document MUST be capable of producing a valid JSON-LD export as
    defined in §7.6 when processed by a Level 3 conformant processor.
12. A `<meta:identifier>` element SHOULD be present in the manifest with a stable
    IRI identifying this document instance.

### 8.4.2 Level 3 Processor Requirements

A Level 3 conformant processor MUST satisfy all Level 2 processor requirements
(§8.3.2), plus:

1. Parse and render compound paths (holes and multi-sub-path boundaries).
2. Render mesh gradients using Coons patch interpolation.
3. Implement spectral color rendering: convert spectral data to tristimulus values
   using the CIE 1931 2° observer color-matching functions.
4. Render fold simulations: apply the geometric fold transform to `<fold-line>`
   geometry and composite folded panels with correct occlusion.
5. Produce JSON-LD linked data export as specified in §7.6.
6. Produce a complete and correct accessibility tree (§7.4.5) for all documents.
7. Verify the completeness of `sem:` annotations and report missing `sem:alt-text`
   on non-decorative images as Level 3 validation errors.

## 8.5 Processor Conformance Classes

In addition to conformance levels (which concern document features), this
specification defines five processor conformance classes that describe what a
processor does with MDF documents.

A single software product MAY conform to multiple classes simultaneously (for
example, an editor that also renders to screen satisfies both the Editor and
Viewer classes).

### 8.5.1 Viewer

A **Viewer** renders MDF documents to a screen display surface (monitor, display,
browser canvas).

| Requirement | Level |
|-------------|-------|
| Level 1 processor requirements (§8.2.2) | Required |
| Level 2 processor requirements (§8.3.2) | Optional |
| Level 3 processor requirements (§8.4.2) | Optional |
| Screen rendering with boundary clipping | Required |
| Accessibility tree export | Required |
| PDF/X-4 export | Not applicable |

A Viewer MUST implement pixel-accurate boundary clipping. A Viewer MUST NOT render
content outside the canvas boundary path.

A Viewer SHOULD implement print layer filtering: layers with
`print:visible-in-render="false"` MUST NOT be visible in standard screen rendering.
A Viewer MAY provide a proof mode that makes such layers visible.

### 8.5.2 Renderer

A **Renderer** rasterizes MDF documents to pixel arrays or raster image files
(PNG, TIFF, JPEG).

| Requirement | Level |
|-------------|-------|
| Level 1 processor requirements (§8.2.2) | Required |
| Level 2 processor requirements (§8.3.2) | Required |
| Level 3 processor requirements (§8.4.2) | Optional |
| Anti-aliased boundary clipping | Required |
| Minimum output resolution | 72 PPI (screen), 300 PPI (print) |

A Renderer MUST support an output resolution parameter. A Renderer intended for
print output MUST support at least 300 PPI output resolution. A Renderer MUST
apply anti-aliasing at the boundary path edge.

When rasterizing a document with `print:bleed` declared, a Renderer MUST provide
a mode to include or exclude the bleed region in output.

### 8.5.3 Print Processor

A **Print Processor** generates press-ready output files from MDF documents for
submission to a print production workflow.

| Requirement | Level |
|-------------|-------|
| Level 1 processor requirements (§8.2.2) | Required |
| Level 2 processor requirements (§8.3.2) | Required |
| Level 3 processor requirements (§8.4.2) | Recommended |
| PDF/X-4 export | Required |
| Spot color plate separation | Required |
| Ink limit enforcement | Required |
| Overprint compositing | Required |
| Registration mark generation | Required |
| Bleed region generation | Required |

A Print Processor MUST produce PDF/X-4 output that passes the Ghent PDF Workgroup
(GWG) PDF/X-4 preflight profile without errors when given a Level 2 conformant
input document.

A Print Processor SHOULD support the following additional output formats:

- PDF/X-3 (for legacy press workflows)
- TIFF/IT (for legacy prepress workflows)

### 8.5.4 Validator

A **Validator** checks an MDF document against the requirements of one or more
conformance levels and reports violations.

| Requirement | Level |
|-------------|-------|
| Level 1 document validation | Required |
| Level 2 document validation | Required if declaring Level 2 support |
| Level 3 document validation | Required if declaring Level 3 support |
| Machine-readable output | Required |
| Human-readable error messages | Required |

A Validator MUST produce a structured validation report. The report MUST include,
for each violation:

- The conformance level of the violated requirement
- The section of this specification that defines the requirement
- The XPath expression identifying the violating element or attribute in the document
- A human-readable description of the violation
- A severity classification: `error` (document fails the declared conformance level)
  or `warning` (document is valid but suboptimal)

The machine-readable output format for validation reports is JSON:

```json
{
  "mdf-version": "0.1",
  "document": "my-document.mdf",
  "conformance-level-declared": 2,
  "result": "fail",
  "violations": [
    {
      "severity": "error",
      "level": 2,
      "spec-section": "8.3.1.6",
      "xpath": "/mdf/canvas/layer[@id='body']/shape[@id='header-bg']/@fill",
      "message": "Color 'color(rgb 255 0 0)' uses RGB color space; Level 2 body layer elements must use CMYK or spot color."
    },
    {
      "severity": "warning",
      "level": 1,
      "spec-section": "7.4.1",
      "xpath": "/mdf/canvas/layer/image[@id='logo']",
      "message": "Image element is missing sem:alt-text attribute."
    }
  ]
}
```

A Validator MUST NOT modify the document it is validating.

### 8.5.5 Editor

An **Editor** creates and/or modifies MDF documents. Editors are authoring tools
(desktop applications, web applications, command-line generators).

| Requirement | Level |
|-------------|-------|
| Level 1 documents: produce valid output | Required |
| Level 2 documents: produce valid output | Required if claiming Level 2 editing support |
| Unknown namespace preservation | Required |
| Semantic annotation UI | Recommended |

An Editor MUST produce well-formed, valid MDF documents for the conformance level it
claims to support. An Editor MUST preserve all XML content in unknown namespaces when
round-tripping (reading then saving) a document.

An Editor MUST NOT remove `sem:`, `meta:`, or `print:` attributes that it does not
understand from a document it is editing, unless the user explicitly requests their
removal.

An Editor SHOULD provide a UI for declaring `sem:` semantic annotations (shape
meaning, alt text, reading order) and SHOULD validate documents against the
conformance level they declare before saving.

## 8.6 Conformance Test Suite

The MDF conformance test suite provides a normative set of test inputs and expected
outputs for validating processor implementations.

### 8.6.1 Test Suite Location

The test suite is maintained at:

```
/conformance/
```

within the MDF specification repository. The directory structure is:

```
/conformance/
  README.md
  level-1/
    valid/        — well-formed Level 1 documents that MUST parse and render without error
    invalid/      — malformed documents with declared violations; validators MUST report errors
    render/       — documents with known pixel-accurate expected outputs
  level-2/
    valid/
    invalid/
    render/
    separation/   — documents with expected plate separation outputs
  level-3/
    valid/
    invalid/
    render/
  expected/
    render/       — PNG expected-output images at 96 PPI
    separation/   — expected plate files (TIFF, grayscale)
    jsonld/       — expected JSON-LD export outputs
    validation/   — expected validation report JSON files
```

### 8.6.2 Test File Format

Each test case consists of:

- A `.mdf` or `.mdfx` input file
- A `<test-id>.json` metadata file describing the test and expected outcomes
- For render tests: a `<test-id>.png` expected output file at 96 PPI

The metadata file format:

```json
{
  "id": "level1-boundary-circle-001",
  "description": "Circular canvas boundary with centered text block",
  "conformance-level": 1,
  "type": "render",
  "input": "level1-boundary-circle-001.mdf",
  "expected-render": "expected/render/level1-boundary-circle-001.png",
  "render-resolution": 96,
  "tolerance-pixels": 2,
  "notes": "Anti-aliasing tolerance of 2 pixels at boundary edge is acceptable."
}
```

### 8.6.3 Expected Output Matching

For render tests, a conformant processor's output MUST match the expected PNG within
the declared pixel tolerance. Matching is performed as follows:

1. Render the test document at the declared resolution.
2. Compare each pixel with the expected output.
3. A pixel difference of more than the declared `tolerance-pixels` in any channel is
   a test failure.
4. The pass threshold is: fewer than 0.1% of total pixels may exceed the tolerance.

Sub-pixel anti-aliasing differences at shape boundaries are expected and are
accommodated by the pixel tolerance.

### 8.6.4 Running the Test Suite

The reference test runner is a Python script at `/conformance/run_tests.py`. It
accepts a processor command via the `--processor` flag and invokes it for each test
case:

```bash
python /conformance/run_tests.py \
  --processor "mdf-render --output {output}" \
  --level 1 \
  --type render
```

The test runner produces a JSON report of pass/fail results and a human-readable
summary. A processor claiming conformance to a given level MUST pass 100% of `valid/`
tests and 100% of `invalid/` tests (correct error reporting) for that level.

### 8.6.5 Submitting Conformance Claims

Implementors wishing to claim MDF conformance MUST:

1. Run the full conformance test suite against their processor.
2. Publish the test runner output report at a stable URL.
3. Open a pull request against the specification repository at
   `https://github.com/morphousdoc/mdf-spec` adding their implementation to
   `/conformance/implementations.md`.

The MDF specification editors review submitted claims and MAY audit the
implementation before listing it as conformant.

## 8.7 Versioning

### 8.7.1 Specification Version

The MDF specification uses semantic versioning: `MAJOR.MINOR`.

- **Minor versions** (e.g. 0.1 → 0.2) are backwards-compatible additions or
  clarifications. A processor conformant to v0.2 MUST correctly process v0.1
  documents. New elements or attributes added in a minor version MUST be optional
  or have defined defaults so that v0.1 documents remain valid.

- **Major versions** (e.g. 0.x → 1.0, or 1.x → 2.0) MAY introduce breaking changes.
  The namespace URIs MUST change when a major version is released:
  - v1.0 core namespace: `https://morphousdoc.org/ns/1.0`
  - v1.0 print namespace: `https://morphousdoc.org/ns/print/1.0`
  - v1.0 semantics namespace: `https://morphousdoc.org/ns/semantics/1.0`

- **Pre-release versions** (e.g. 0.x) are unstable drafts. Documents using
  pre-release spec versions MUST declare `version="0.x"` in the root element.
  Processors MUST warn when processing pre-release documents.

### 8.7.2 Document Version Declaration

The `version` attribute on the root `<mdf>` element declares the minimum spec version
required to process the document:

```xml
<mdf version="0.1" ...>
```

A processor with support for spec version `X.Y` MUST correctly process any document
declaring version `X.Z` where `Z ≤ Y`. A processor MUST NOT silently produce
incorrect output for documents declaring a version it does not support; it MUST
report an error or warning indicating the version mismatch.

### 8.7.3 Feature Flags

Future minor versions MAY introduce optional features that can be declared in the
manifest as feature flags:

```xml
<meta:requires-feature name="mesh-gradients"/>
<meta:requires-feature name="spectral-color"/>
```

A processor that encounters a `<meta:requires-feature>` element for a feature it
does not support MUST either:

- Report an error if the feature is required for correct rendering, or
- Emit a warning and render a best-effort approximation if a graceful degradation
  is defined for the feature.

Feature flags that are defined at Level 3 are listed in §8.4. Feature flags for
future minor versions will be defined in the changelog.

### 8.7.4 Deprecation Policy

Features deprecated in a minor version will be:

1. Annotated as deprecated in the specification text
2. Listed in the changelog
3. Retained in the specification for at least two subsequent minor versions
4. Removed only in a major version

Processors SHOULD warn when processing deprecated features and SHOULD provide
migration guidance.

## 8.8 Interoperability Notes

### 8.8.1 PDF Import and Export

MDF does not define a normative PDF import or export format beyond the PDF/X-4
export requirement for Level 2 Print Processors (§8.5.3). The following guidance
is non-normative:

- When importing from PDF, processors SHOULD attempt to reconstruct semantic
  annotations (`sem:role`, `sem:alt-text`) from the PDF's structure tree if present.
- When exporting to PDF/X-4, the MDF boundary path SHOULD be represented as a PDF
  die-cut trim box when `print:die-cut="true"`.
- Shape reflow text exported to PDF MUST be converted to positioned glyph runs; PDF
  does not support shape-reflow text natively.

### 8.8.2 SVG Interoperability

The MDF path syntax for `boundary`, `shape`, and `reflow-region` is a subset of SVG
2 path data. MDF documents MAY be partially round-tripped through SVG authoring
tools with the following caveats:

- SVG does not have a canvas boundary concept; the boundary path would need to be
  represented as a `<clipPath>` in SVG.
- MDF print namespaces have no SVG equivalent and will be lost in SVG export.
- `sem:` attributes have no SVG equivalent; they SHOULD be preserved as custom
  `data-` attributes in SVG export if round-trip preservation is required.

### 8.8.3 Accessibility Standards Alignment

MDF semantic annotations are designed to align with:

- **WCAG 2.2** (Web Content Accessibility Guidelines) — `sem:alt-text` satisfies
  Success Criterion 1.1.1 (Non-text Content) for MDF documents rendered as web
  content.
- **PDF/UA-1** (ISO 14289-1) — MDF Level 3 accessibility requirements (§8.4.1)
  align with PDF/UA structure requirements. A PDF/X-4 export from a Level 3 MDF
  document SHOULD be capable of passing PDF/UA-1 validation when the exporter
  maps the MDF accessibility tree to PDF structure tags.
- **EPUB Accessibility 1.1** — MDF linked data export (§7.6) produces metadata
  compatible with EPUB Accessibility `schema:accessibilityFeature` vocabulary.
