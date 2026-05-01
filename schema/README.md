# MDF Schema Files

XSD schemas for validating MDF (Morphous Document Format) v0.1 documents.

## Files

| File | Namespace | Description |
|------|-----------|-------------|
| `mdf-0.1.xsd` | `https://morphousdoc.org/ns/0.1` | Main schema — root element, manifest, canvas, layers, shapes, text |
| `mdf-meta-0.1.xsd` | `https://morphousdoc.org/ns/meta/0.1` | Metadata elements (title, author, created, conformance, …) |
| `mdf-print-0.1.xsd` | `https://morphousdoc.org/ns/print/0.1` | Print production elements and attributes (die-cut, bleed, marks, …) |
| `mdf-semantics-0.1.xsd` | `https://morphousdoc.org/ns/semantics/0.1` | Shape and content semantic attributes (shape-type, shape-meaning, role, …) |

The companion schema files must all be in the same directory as `mdf-0.1.xsd`
for `xs:import` resolution to work with the relative `schemaLocation` paths.

## Validating with xmllint

`xmllint` (part of libxml2) can validate against XSD schemas. Install it via
your OS package manager (`libxml2-utils` on Debian/Ubuntu, `libxml2` on macOS
via Homebrew).

### Validate a single .mdf file

```sh
xmllint --noout \
        --schema /path/to/schema/mdf-0.1.xsd \
        /path/to/document.mdf
```

A clean document prints nothing (with `--noout`) and exits 0.
Validation errors are printed to stderr.

### Validate the circle-resume example

From the repository root:

```sh
xmllint --noout \
        --schema schema/mdf-0.1.xsd \
        examples/shapes/circle-resume.mdf
```

### Validate all .mdf files in the examples tree

```sh
find examples -name "*.mdf" -print0 \
  | xargs -0 xmllint --noout --schema schema/mdf-0.1.xsd
```

### Show validation errors in context

Drop `--noout` to also print the XML on stdout, or add `--debug` for verbose
libxml2 internal information.

```sh
xmllint --schema schema/mdf-0.1.xsd examples/shapes/circle-resume.mdf
```

## Notes on cross-namespace attributes

MDF uses attributes from the `print:` and `sem:` namespaces on elements in the
default MDF namespace (for example `print:die-cut` on `<canvas>`,
`sem:shape-type` on `<canvas>`, and `print:role` on `<layer>`).

XSD 1.0 does not allow `<xs:attribute ref="print:die-cut"/>` inside a
`complexType` defined in a different target namespace without importing and
referencing the attribute declaration from the foreign namespace schema, which
requires those schemas to declare global attributes — a design that would force
every `print:` and `sem:` attribute to be declared globally rather than inside
attribute groups.

To avoid this complexity while keeping schemas readable, all three schemas
declare `xs:anyAttribute namespace="##other" processContents="lax"` on their
element types. This means:

- The main validator accepts any attribute from any namespace.
- Attribute-level validation of `print:` and `sem:` attributes is performed
  laxly: if the validator can resolve the attribute declaration in the imported
  schema it validates the value; if not it passes without error.

In practice, `xmllint` with libxml2 validates foreign-namespace attributes
only when it can locate the schema for that namespace. Since the schemas are
imported with explicit `schemaLocation`, attribute values such as the
`sem:shape-type` enum and `print:die-cut` boolean will be validated.

To enable strict foreign-attribute validation in tools that support XSD 1.1
(such as Saxon-EE), change `processContents="lax"` to `processContents="strict"`
in all four schema files.

## XSD 1.0 vs 1.1

These schemas target XSD 1.0, which is what `xmllint` (libxml2) implements.
They do not use assertions (`xs:assert`) or conditional type assignment
(`xs:alternative`). Constraints such as "reflow-region must have exactly one of
shape or shape-ref" are expressed in the specification prose and enforced by
conformant processors at runtime rather than by the XSD.
