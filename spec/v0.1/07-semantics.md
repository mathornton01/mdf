# MDF Specification v0.1 — Chapter 7: Semantics and Accessibility

## 7.1 Overview

MDF carries semantic meaning at multiple levels: the shape of the document itself,
the structure of its content, the reading order for assistive technology, and
machine-readable metadata for search engines and linked data consumers. Semantic
markup in MDF is a first-class feature, not an afterthought.

Semantic markup lives primarily in the `sem:` namespace:

```
https://morphousdoc.org/ns/semantics/0.1
```

This namespace MUST be declared in the root `<mdf>` element before any `sem:`
attributes or elements are used:

```xml
<mdf version="0.1"
     xmlns="https://morphousdoc.org/ns/0.1"
     xmlns:sem="https://morphousdoc.org/ns/semantics/0.1"
     ...>
```

A conformant processor encountering `sem:` attributes it does not recognize MUST
ignore them and MUST NOT raise an error (unknown namespace passthrough, §1.2.1).
Semantic attributes are advisory; they do not alter rendering behavior unless this
specification explicitly states otherwise.

The semantic system addresses three distinct consumer audiences:

1. **Accessibility tools** — screen readers, reflow engines, Braille displays — that
   need a logical content structure independent of visual layout.
2. **Search and indexing systems** — document management platforms, search engines —
   that need structured metadata and content classification.
3. **Linked data consumers** — RDF processors, knowledge graphs, AI systems — that
   need formal semantic annotations mapped to standard vocabularies.

## 7.2 Shape Semantics

The most distinctive semantic feature of MDF is that the document's shape is
meaningful data, not merely geometry. A circular business card communicates
something different from a rectangular one before a single word is read. MDF
encodes this intent in machine-readable form on the `<canvas>` element.

### 7.2.1 Shape Type

The `sem:shape-type` attribute on `<canvas>` declares the geometric classification
of the document's boundary path. This is computed from the path geometry and MUST
accurately reflect the actual boundary shape. An editor or authoring tool MUST NOT
set `sem:shape-type` to a value that does not correspond to the actual boundary path.

| Value | Geometric Definition |
|-------|---------------------|
| `rectangle` | Four straight edges, all interior angles 90° |
| `rounded-rectangle` | Rectangle with circular or elliptical corner arcs |
| `circle` | Boundary path approximates a circle within 1% of radius variance |
| `ellipse` | Boundary path approximates an ellipse within 1% of axis variance |
| `polygon` | Closed path with only straight line segments; more than four sides |
| `star` | Convex polygon with alternating long and short radii |
| `arrow` | Polygon with one or two directional pointer shapes |
| `organic` | Freeform Bézier curve path with no repeating geometric regularity |
| `compound` | Multiple sub-paths (Level 3 documents only; see §3.4.1) |
| `custom` | Shape does not fit any predefined classification |

A processor SHOULD compute `sem:shape-type` automatically from the boundary path
when authoring a new document. When reading a document, a processor SHOULD validate
that the declared `sem:shape-type` is consistent with the boundary geometry.
Inconsistencies SHOULD be reported as warnings, not errors.

### 7.2.2 Shape Meaning

The `sem:shape-meaning` attribute on `<canvas>` declares the semantic role of the
document — what the document *is*, not merely what it contains. This is the
central semantic innovation of the MDF format.

The full `sem:shape-meaning` vocabulary is defined in Chapter 3 (§3.6.2). A summary
of representative values:

| Value | Description |
|-------|-------------|
| `business-card` | Personal or professional business card |
| `sticker` | Adhesive sticker, any shape |
| `badge` | Wearable badge or name tag |
| `label` | Product or shipping label |
| `brochure` | Folded promotional brochure |
| `certificate` | Certificate, diploma, or award |
| `envelope` | Mailing envelope |
| `packaging` | Product packaging or box blank |
| `custom` | User-defined (MUST be accompanied by `sem:shape-meaning-iri`) |

When `sem:shape-meaning="custom"`, the `sem:shape-meaning-iri` attribute MUST also
be present to provide a dereferenceable IRI pointing to a controlled vocabulary
term that defines the custom meaning.

### 7.2.3 Shape Meaning IRI

```xml
<canvas ...
        sem:shape-meaning="custom"
        sem:shape-meaning-iri="https://example.com/vocab/shapes/guitar-pick"/>
```

The `sem:shape-meaning-iri` attribute MUST be a valid IRI (RFC 3987). The IRI
SHOULD dereference to an RDF resource or JSON-LD document describing the shape
meaning. When `sem:shape-meaning` is any value other than `custom`, a
`sem:shape-meaning-iri` attribute MAY be present to provide a reference to the
authoritative vocabulary term; the MDF specification's canonical IRIs for built-in
shape meanings are of the form:

```
https://morphousdoc.org/vocab/shape-meaning/business-card
https://morphousdoc.org/vocab/shape-meaning/sticker
```

### 7.2.4 Shape Context

The `sem:shape-context` attribute is a free-text field for the author to explain why
a particular shape was chosen for this document. It is intended for preservation of
design intent.

```xml
<canvas ...
        sem:shape-context="Circular shape chosen to convey inclusivity and
          approachability for this community event badge; deliberately non-corporate."/>
```

`sem:shape-context` has no effect on rendering. A document archival system or AI
assistant SHOULD store and surface this value when analyzing design decisions. The
value is a plain Unicode string; no markup is permitted within it.

### 7.2.5 Rationale

Shape communicates meaning in human visual culture before any text is read. A
circular business card signals creativity and individuality. A star-shaped sticker
signals achievement. An envelope shape signals correspondence. By encoding this
intent in a machine-readable attribute on the canvas element, MDF enables:

- Screen readers to announce the document type to blind users
- Search engines to index documents by their shape role
- Document management systems to sort by document type without parsing content
- AI assistants to understand what a document is and how it should be presented

This is not achievable in PDF, where shape is purely decorative geometry.

## 7.3 Content Semantics

Semantic role attributes may be applied to any content element (`<text-block>`,
`<shape>`, `<image>`, `<group>`, `<layer>`) to declare the element's role in the
document's logical structure.

### 7.3.1 Semantic Role

The `sem:role` attribute declares the logical content role of an element:

| Value | Description |
|-------|-------------|
| `heading` | Section or document heading (use with `sem:heading-level`) |
| `body` | Main body text |
| `caption` | Caption for an image, figure, or table |
| `byline` | Author attribution line |
| `dateline` | Date or date-range line |
| `pullquote` | Excerpt highlighted outside the main text flow |
| `sidebar` | Secondary content adjacent to main flow |
| `footnote` | Reference footnote |
| `endnote` | Reference endnote |
| `label` | Short identifying label (not a product label — see `sem:shape-meaning`) |
| `decoration` | Purely decorative element; should be skipped by assistive technology (equivalent to `sem:decorative="true"`) |
| `background` | Background visual element with no semantic content |
| `figure` | An image or diagram that is a meaningful part of the content |
| `logo` | Organization or brand logo |
| `signature` | Signature field or signature image |
| `stamp` | Official stamp or seal |

A processor MUST NOT change rendering based on `sem:role`; the attribute is advisory
for accessibility and indexing consumers only.

```xml
<text-block id="doc-title" font-ref="heading-font" size="24pt" sem:role="heading" sem:heading-level="1">
  <reflow-region shape-ref="canvas-boundary" padding="10mm"/>
  <p>Annual Report 2025</p>
</text-block>

<text-block id="author-name" font-ref="body-font" size="9pt" sem:role="byline">
  <reflow-region shape-ref="canvas-boundary" padding="10mm"/>
  <p>Prepared by the Finance Department</p>
</text-block>
```

### 7.3.2 Heading Level

The `sem:heading-level` attribute is valid on elements with `sem:role="heading"`. It
declares the hierarchical depth of the heading, analogous to HTML `<h1>` through
`<h6>`.

| Value | Description |
|-------|-------------|
| `1` | Top-level document heading |
| `2` | Section heading |
| `3` | Sub-section heading |
| `4` | Sub-sub-section heading |
| `5` | Level 5 (rarely used) |
| `6` | Level 6 (rarely used) |

A document SHOULD have exactly one element with `sem:heading-level="1"`. A
processor encountering multiple level-1 headings SHOULD NOT raise an error; the
semantic structure is advisory.

### 7.3.3 Reading Order

The `sem:reading-order` attribute is an unsigned integer that defines the element's
position in the logical reading sequence. Elements are read in ascending order of
`sem:reading-order` value by assistive technology and reflow engines.

```xml
<text-block id="headline" sem:reading-order="1" .../>
<text-block id="subhead"  sem:reading-order="2" .../>
<image       id="photo"    sem:reading-order="3" sem:role="figure" sem:alt-text="..."/>
<text-block id="body"     sem:reading-order="4" .../>
```

Values MUST be positive integers. Values need not be consecutive; gaps are
permitted to allow for later insertions. When two elements share the same
`sem:reading-order` value, a processor SHOULD read them in document order.

Elements that lack `sem:reading-order` are appended to the reading sequence after
all elements that have the attribute, in document order.

Elements with `sem:decorative="true"` or `sem:role="background"` or
`sem:role="decoration"` are excluded from the reading sequence entirely.

### 7.3.4 Document-Level Reading Order Declaration

For documents that require an explicit, authoritative reading order independent of
`sem:reading-order` attributes, a `<sem:reading-order>` child element MAY be
included in the `<manifest>`. This takes precedence over all per-element
`sem:reading-order` attributes.

```xml
<manifest>
  ...
  <sem:reading-order>
    <sem:item ref="headline"/>
    <sem:item ref="subhead"/>
    <sem:item ref="photo"/>
    <sem:item ref="body-col-1"/>
    <sem:item ref="body-col-2"/>
    <sem:item ref="footer"/>
  </sem:reading-order>
</manifest>
```

Each `<sem:item>` MUST have a `ref` attribute whose value is the `id` of a content
element in the document. A `<sem:item>` referencing a non-existent `id` MUST be
ignored. Elements not listed in the `<sem:reading-order>` list are appended after
the listed items, in document order.

## 7.4 Document Accessibility

### 7.4.1 Alternative Text

The `sem:alt-text` attribute provides a text alternative for non-text content. It
MUST be present on all `<image>` elements that carry semantic content. It SHOULD be
present on `<shape>` elements whose shape conveys meaning not expressed by adjacent
text.

```xml
<image id="company-logo"
       src="mdfx:logo"
       x="5mm" y="5mm" width="40mm" height="15mm"
       sem:alt-text="Acme Corporation logo: stylized gear with company name"/>

<shape id="approval-stamp"
       path="M 50,50 A 20,20 0 1,1 50,50.001 Z"
       fill="color(cmyk 0 0.6 0.8 0)"
       sem:role="stamp"
       sem:alt-text="APPROVED stamp"/>
```

`sem:alt-text` MUST be plain Unicode text. Markup MUST NOT be included. The value
SHOULD be concise (under 150 characters) and MUST convey the meaning of the visual
content, not merely describe its appearance.

An image with `sem:decorative="true"` MUST NOT carry `sem:alt-text`; the attributes
are mutually exclusive. A validator MUST report an error if both are present.

### 7.4.2 Extended Description

The `sem:description` attribute provides a longer prose description of an element's
content for screen reader users. Unlike `sem:alt-text`, it is intended for complex
images, charts, or diagrams that require more than a brief label.

```xml
<image id="sales-chart"
       src="mdfx:chart"
       x="10mm" y="30mm" width="80mm" height="50mm"
       sem:role="figure"
       sem:alt-text="Q3 sales by region bar chart"
       sem:description="Bar chart showing sales for four regions in Q3 2025.
         North: 1.2M. South: 0.9M. East: 1.5M. West: 0.7M. East leads
         with 35% of total revenue."/>
```

`sem:description` MUST be plain text. The value MAY be multi-sentence. There is no
length limit, though descriptions exceeding 1000 characters SHOULD be stored as a
separate `<sem:long-description>` child element of the content element.

### 7.4.3 Language Override

The `sem:lang` attribute overrides the document language (declared in the manifest)
for an element and all its descendants. The value MUST be a valid BCP 47 language
tag.

```xml
<manifest>
  <meta:language>en-US</meta:language>
</manifest>

<canvas ...>
  <layer id="main">
    <text-block id="body-en" sem:lang="en-US" ...>
      <p>English text.</p>
    </text-block>
    <text-block id="body-fr" sem:lang="fr-FR" ...>
      <p>Texte en français.</p>
    </text-block>
  </layer>
</canvas>
```

A renderer MUST use the `sem:lang` value (or the nearest ancestor's `sem:lang`
value) to select hyphenation dictionaries and text shaping rules for the element.
This attribute thus has normative rendering implications in addition to its
accessibility role.

### 7.4.4 Decorative Elements

The `sem:decorative="true"` attribute marks an element as purely decorative — it
carries no information that would be lost if it were invisible to assistive
technology.

```xml
<shape id="bg-swirl"
       path="M 0,0 C 30,10 70,10 100,0 ..."
       fill="color(cmyk 0 0 0 0.03)"
       sem:decorative="true"/>
```

An element with `sem:decorative="true"` MUST be excluded from:

- The accessibility reading order (§7.3.3)
- The accessibility tree exported by the processor
- Screen reader announcement

A conformant processor MUST NOT require `sem:decorative="true"` to be set on every
background element; it is an advisory annotation. Elements without any `sem:role`
or `sem:alt-text` MAY be treated as decorative by assistive technology
implementations.

### 7.4.5 Accessibility Tree

A conformant Level 1 processor that implements accessibility export MUST be capable
of producing an accessibility tree from the document's semantic annotations. The
accessibility tree is a logical, ordered representation of the document's content
elements with their roles, labels, and reading order, suitable for passing to
platform accessibility APIs (ARIA, ATK, UIA).

The accessibility tree construction algorithm is:

1. Begin with an empty ordered list.
2. If the manifest contains a `<sem:reading-order>` declaration, use it as the
   primary ordering (§7.3.4); otherwise order by `sem:reading-order` attribute
   values, then document order.
3. For each element in the ordered list:
   a. Exclude elements with `sem:decorative="true"`.
   b. Exclude elements with `sem:role="background"` or `sem:role="decoration"`.
   c. Exclude elements on layers where `visible="false"`.
   d. Include the element with its `sem:role`, `sem:alt-text` or text content, and
      `sem:heading-level` if applicable.
4. Return the ordered list as the accessibility tree.

## 7.5 Metadata Vocabulary

Document metadata is declared in the `<manifest>` using the `meta:` namespace
(`https://morphousdoc.org/ns/meta/0.1`). The `meta:` vocabulary maps directly to
established metadata standards for interoperability.

### 7.5.1 Core Metadata Elements

```xml
<manifest>
  <meta:title>Annual Report 2025</meta:title>
  <meta:author>Finance Department, Acme Corp</meta:author>
  <meta:creator-tool>Morphous Designer 1.0</meta:creator-tool>
  <meta:created>2025-10-01T09:00:00Z</meta:created>
  <meta:modified>2025-10-15T14:32:11Z</meta:modified>
  <meta:language>en-US</meta:language>
  <meta:description>
    Acme Corporation Annual Report for fiscal year 2025, covering financial
    performance, strategic initiatives, and corporate governance.
  </meta:description>
  <meta:keywords>annual report, finance, 2025, acme</meta:keywords>
  <meta:subject>Corporate finance</meta:subject>
  <meta:conformance level="2"/>
</manifest>
```

### 7.5.2 Metadata Mapping Table

| MDF Element | Dublin Core | Schema.org | XMP |
|-------------|-------------|------------|-----|
| `meta:title` | `dc:title` | `schema:name` | `xmp:Title` |
| `meta:author` | `dc:creator` | `schema:author` | `xmp:Author` |
| `meta:created` | `dc:date` | `schema:dateCreated` | `xmp:CreateDate` |
| `meta:modified` | `dc:modified` | `schema:dateModified` | `xmp:ModifyDate` |
| `meta:description` | `dc:description` | `schema:description` | `xmp:Description` |
| `meta:subject` | `dc:subject` | `schema:about` | `xmp:Subject` |
| `meta:keywords` | `dc:subject` | `schema:keywords` | `pdf:Keywords` |
| `meta:language` | `dc:language` | `schema:inLanguage` | `xmp:Language` |
| `meta:creator-tool` | — | — | `xmp:CreatorTool` |

`meta:created` and `meta:modified` values MUST be ISO 8601 datetime strings in UTC,
with timezone designator `Z` or explicit offset.

### 7.5.3 Rights and Licensing

```xml
<manifest>
  ...
  <meta:rights>Copyright 2025 Acme Corporation. All rights reserved.</meta:rights>
  <meta:license-iri>https://creativecommons.org/licenses/by/4.0/</meta:license-iri>
</manifest>
```

| Element | Dublin Core | Schema.org |
|---------|-------------|------------|
| `meta:rights` | `dc:rights` | `schema:copyrightNotice` |
| `meta:license-iri` | `dc:license` | `schema:license` |

### 7.5.4 Custom Metadata

Custom metadata MAY be included in the manifest using any namespace. A conformant
processor MUST preserve custom metadata on round-trip (read then write) and MUST
NOT modify it. Custom metadata elements that share the `meta:` namespace MUST be
prefixed with `meta:x-` to avoid conflict with future specification additions:

```xml
<meta:x-project-id>PRJ-2025-0047</meta:x-project-id>
<meta:x-print-run>10000</meta:x-print-run>
```

## 7.6 Linked Data Export

A conformant processor MAY export the document's semantic metadata as JSON-LD.
This enables MDF documents to participate in the semantic web as Schema.org
`CreativeWork` resources.

### 7.6.1 Base JSON-LD Graph

The canonical JSON-LD export of an MDF document's semantic metadata is structured
as a `schema:CreativeWork` with MDF-specific extensions:

```json
{
  "@context": {
    "schema": "https://schema.org/",
    "mdf": "https://morphousdoc.org/vocab/",
    "dc": "http://purl.org/dc/elements/1.1/"
  },
  "@type": "schema:CreativeWork",
  "schema:name": "Annual Report 2025",
  "schema:author": {
    "@type": "schema:Organization",
    "schema:name": "Finance Department, Acme Corp"
  },
  "schema:dateCreated": "2025-10-01T09:00:00Z",
  "schema:dateModified": "2025-10-15T14:32:11Z",
  "schema:inLanguage": "en-US",
  "schema:description": "Acme Corporation Annual Report...",
  "schema:encodingFormat": "application/vnd.mdf+xml",
  "mdf:shapeType": "rectangle",
  "mdf:shapeMeaning": "page-a4",
  "mdf:shapeMeaningIRI": "https://morphousdoc.org/vocab/shape-meaning/page-a4",
  "mdf:shapeContext": null,
  "mdf:conformanceLevel": 2
}
```

### 7.6.2 Shape Semantics in JSON-LD

Shape semantics are represented as top-level properties under the `mdf:` prefix:

| MDF attribute | JSON-LD property |
|---------------|-----------------|
| `sem:shape-type` | `mdf:shapeType` |
| `sem:shape-meaning` | `mdf:shapeMeaning` |
| `sem:shape-meaning-iri` | `mdf:shapeMeaningIRI` |
| `sem:shape-context` | `mdf:shapeContext` |

When `sem:shape-meaning-iri` is present, it SHOULD be included in the JSON-LD
export as both a plain string and a linked `@id`:

```json
"mdf:shapeMeaning": {
  "@id": "https://morphousdoc.org/vocab/shape-meaning/business-card",
  "@value": "business-card"
}
```

### 7.6.3 Processor Requirements for Linked Data Export

A processor that implements linked data export:

- MUST produce valid JSON-LD 1.1 (W3C Recommendation, 2020)
- MUST include all `meta:` namespace elements from the manifest that have
  Schema.org or Dublin Core equivalents (per the mapping table in §7.5.2)
- MUST include all `sem:` canvas attributes that have `mdf:` vocabulary terms
- SHOULD include a `schema:identifier` property with a stable document IRI if
  available (from `meta:identifier` in the manifest)
- MUST NOT include font binary data or ICC profile binary data in the export
- MAY include a `schema:accessibilityFeature` array reflecting the document's
  semantic annotations:
  - `"alternativeText"` if any `<image>` has `sem:alt-text`
  - `"readingOrder"` if `<sem:reading-order>` or per-element `sem:reading-order`
    attributes are present
  - `"structuredNavigation"` if heading hierarchy is present

### 7.6.4 Invoking Linked Data Export

Linked data export is triggered by the `--export-jsonld` flag in conformant
command-line processors, or by the equivalent API call. The output is a UTF-8
JSON file. The MIME type of the output MUST be `application/ld+json`.

## 7.7 Extended Example

The following illustrates a fully annotated business card document:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mdf version="0.1"
     xmlns="https://morphousdoc.org/ns/0.1"
     xmlns:print="https://morphousdoc.org/ns/print/0.1"
     xmlns:sem="https://morphousdoc.org/ns/semantics/0.1"
     xmlns:meta="https://morphousdoc.org/ns/meta/0.1">

  <manifest>
    <meta:title>Priya Sharma — Business Card</meta:title>
    <meta:author>Priya Sharma</meta:author>
    <meta:created>2025-04-01T10:00:00Z</meta:created>
    <meta:language>en-US</meta:language>
    <meta:conformance level="2"/>

    <sem:reading-order>
      <sem:item ref="name-block"/>
      <sem:item ref="title-block"/>
      <sem:item ref="email-block"/>
      <sem:item ref="phone-block"/>
    </sem:reading-order>

    <assets>
      <font id="body-font" family="Inter" weight="400" src="fonts/Inter-Regular.woff2" embed="true"/>
      <font id="name-font" family="Inter" weight="700" src="fonts/Inter-Bold.woff2" embed="true"/>
    </assets>
  </manifest>

  <canvas width="85" height="55" units="mm"
          boundary="M 3,0 L 82,0 A 3,3 0 0,1 85,3 L 85,52 A 3,3 0 0,1 82,55 L 3,55 A 3,3 0 0,1 0,52 L 0,3 A 3,3 0 0,1 3,0 Z"
          print:die-cut="false"
          print:bleed="3mm"
          sem:shape-type="rounded-rectangle"
          sem:shape-meaning="business-card"
          sem:shape-context="Standard CR80 rounded-corner format for professional contact cards">

    <layer id="background" print:role="body">
      <shape id="bg" path="M 0,0 L 85,0 L 85,55 L 0,55 Z"
             fill="color(cmyk 0 0 0 0)"
             sem:decorative="true"/>
    </layer>

    <layer id="content" print:role="body">
      <image id="logo"
             src="mdfx:company-logo"
             x="5mm" y="5mm" width="25mm" height="10mm"
             sem:role="logo"
             sem:alt-text="Acme Corporation logo"/>

      <text-block id="name-block"
                  font-ref="name-font"
                  size="11pt"
                  sem:role="heading"
                  sem:heading-level="1"
                  sem:reading-order="1">
        <reflow-region shape="M 5,20 L 60,20 L 60,30 L 5,30 Z"/>
        <p>Priya Sharma</p>
      </text-block>

      <text-block id="title-block"
                  font-ref="body-font"
                  size="8pt"
                  sem:role="label"
                  sem:reading-order="2">
        <reflow-region shape="M 5,31 L 60,31 L 60,37 L 5,37 Z"/>
        <p>Senior Product Designer</p>
      </text-block>

      <text-block id="email-block"
                  font-ref="body-font"
                  size="7.5pt"
                  sem:role="body"
                  sem:reading-order="3"
                  sem:lang="en-US">
        <reflow-region shape="M 5,40 L 80,40 L 80,46 L 5,46 Z"/>
        <p>priya@acme.com</p>
      </text-block>

      <text-block id="phone-block"
                  font-ref="body-font"
                  size="7.5pt"
                  sem:role="body"
                  sem:reading-order="4">
        <reflow-region shape="M 5,47 L 80,47 L 80,53 L 5,53 Z"/>
        <p>+1 (555) 234-5678</p>
      </text-block>
    </layer>

  </canvas>
</mdf>
```
