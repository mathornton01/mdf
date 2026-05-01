# MDF Specification v0.1 — Chapter 1: File Structure

## 1.1 Overview

An MDF document exists in one of two representations:

- **Plain `.mdf`** — a single UTF-8 XML file. Human-readable, diff-friendly, suitable for version control.
- **Binary bundle `.mdfx`** — a ZIP64 archive containing the XML document plus embedded assets (fonts, ICC profiles, raster images). Suitable for distribution and production workflows.

Both representations encode the same document. A conformant processor MUST accept both.

## 1.2 The Plain `.mdf` Format

A plain `.mdf` file is a well-formed XML 1.0 document encoded in UTF-8. The document MUST begin with an XML declaration:

```xml
<?xml version="1.0" encoding="UTF-8"?>
```

The root element MUST be `<mdf>` in the namespace `https://morphousdoc.org/ns/0.1`. The `version` attribute MUST be present and MUST contain a valid MDF version string.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mdf version="0.1"
     xmlns="https://morphousdoc.org/ns/0.1"
     xmlns:print="https://morphousdoc.org/ns/print/0.1"
     xmlns:sem="https://morphousdoc.org/ns/semantics/0.1"
     xmlns:meta="https://morphousdoc.org/ns/meta/0.1">

  <manifest>
    <!-- document metadata and asset declarations -->
  </manifest>

  <canvas ...>
    <!-- document content -->
  </canvas>

</mdf>
```

### 1.2.1 Namespace Declarations

The following namespaces are defined by this specification:

| Prefix  | Namespace URI | Required |
|---------|---------------|----------|
| (default) | `https://morphousdoc.org/ns/0.1` | Yes |
| `print` | `https://morphousdoc.org/ns/print/0.1` | Level 2+ |
| `sem`   | `https://morphousdoc.org/ns/semantics/0.1` | Recommended |
| `meta`  | `https://morphousdoc.org/ns/meta/0.1` | Yes (in manifest) |

Additional namespaces MAY be declared for extension elements. A conformant processor MUST ignore elements and attributes in unknown namespaces (unknown namespace passthrough).

### 1.2.2 Asset References in Plain Files

When assets (fonts, images, ICC profiles) are referenced in a plain `.mdf` file, the `src` attribute MUST be either:

- A relative file path (relative to the `.mdf` file's directory)
- An absolute `https://` URL
- A data URI (`data:...`)

A processor MAY refuse to load external URLs for security reasons.

## 1.3 The Binary Bundle `.mdfx` Format

An `.mdfx` file is a ZIP64 archive (as specified by PKWARE's Application Note 6.3.10). The archive MUST contain:

| Path | Required | Description |
|------|----------|-------------|
| `META-INF/manifest.json` | Yes | Bundle manifest (JSON) |
| `document.mdf` | Yes | The MDF XML document |
| `fonts/` | Optional | Embedded font files (.woff2, .otf, .ttf) |
| `icc/` | Optional | ICC color profiles (.icc, .icm) |
| `assets/` | Optional | Raster images, patterns, other assets |

### 1.3.1 Bundle Manifest

`META-INF/manifest.json` describes the bundle contents:

```json
{
  "mdfx-version": "0.1",
  "document": "document.mdf",
  "assets": [
    {
      "id": "body-font",
      "path": "fonts/Inter-Regular.woff2",
      "mime-type": "font/woff2",
      "sha256": "a3f9..."
    },
    {
      "id": "fogra39",
      "path": "icc/ISOcoated_v2.icc",
      "mime-type": "application/vnd.iccprofile",
      "sha256": "b7e2..."
    }
  ]
}
```

The `sha256` field is the hex-encoded SHA-256 hash of the asset file. A processor SHOULD verify hashes before using assets. If a hash does not match, the processor MUST either reject the document or present a warning to the user.

### 1.3.2 Asset ID References

In the XML document, assets are referenced by their `id` as declared in the bundle manifest using the `mdfx:src` scheme:

```xml
<font id="body-font" src="mdfx:body-font"/>
<icc-profile id="fogra39" src="mdfx:fogra39"/>
```

## 1.4 MIME Types

| Format | MIME Type |
|--------|-----------|
| `.mdf` | `application/vnd.mdf+xml` |
| `.mdfx` | `application/vnd.mdfx` |

## 1.5 File Size Limits

This specification does not impose file size limits. Individual implementations MAY impose limits appropriate to their context.

## 1.6 Encoding

The XML document MUST be encoded in UTF-8. A processor MUST NOT accept `.mdf` files in other encodings. (The XML declaration's `encoding` attribute, if present, MUST be `UTF-8`.)

Asset files within an `.mdfx` bundle are stored as binary and are not subject to encoding constraints.
