# MDF Patent Non-Assertion Pledge

## Statement

The MDF Project and its contributors make the following pledge with respect to patents:

Any patent claims that the MDF Project or its contributors own, control, or have the right to sublicense, and that are necessarily infringed by implementing the MDF specification as published at `https://morphousdoc.org/spec/`, are hereby licensed to any person or entity, free of charge, for the purpose of implementing, using, and distributing compliant implementations of the MDF format.

This pledge is irrevocable and applies to all versions of the MDF specification published by the MDF Project.

## Scope

This pledge covers:

- Implementing an MDF parser or renderer
- Creating tools that read, write, or process `.mdf` or `.mdfx` files
- Distributing software that implements MDF
- Creating documents in the MDF format

This pledge does NOT cover:

- Patents unrelated to the MDF specification
- Third-party patents not owned or controlled by the MDF Project
- Uses of MDF implementations for purposes other than document creation and rendering

## Rationale

The PDF format's history is encumbered by patents and corporate control. MDF is designed from the start to be fully open. This patent pledge, combined with the Apache 2.0 license, ensures that no entity can use patents to restrict implementation or adoption of the MDF format.

## Third-Party Components

MDF implementations may incorporate third-party components (fonts, ICC profiles, compression algorithms, etc.) that are subject to their own licenses and potentially patent obligations. This pledge does not cover such components.

In particular:
- Font file formats (WOFF2, OTF, TTF) are subject to their own specifications
- ICC profiles are subject to the ICC specification
- The ZIP64 file format used by `.mdfx` is a PKWARE specification

Implementers should verify the licensing status of any third-party components they incorporate.

---

Effective: 2026-05-01
MDF Project — https://morphousdoc.org
