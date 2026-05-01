# MDF Project Charter

## Purpose

The MDF (Morphous Document Format) Project exists to develop, publish, and maintain an open, community-governed document format specification as a replacement for PDF in digital and print production workflows.

## Governance

### Steering Committee

The MDF Project is governed by a Steering Committee of 3–7 members. The Steering Committee:

- Approves changes to the spec that affect compatibility
- Manages the versioning and release process
- Resolves disputes between contributors
- Appoints and removes Working Group leads

Initial Steering Committee members are the founding contributors. New members are added by a simple majority vote of the existing committee. Members serve until they resign or are removed by a two-thirds supermajority vote.

### Working Groups

Technical work is organized into Working Groups:

| Working Group | Scope |
|---------------|-------|
| Core Spec | Canvas, layers, color, the core XML schema |
| Typography | Text reflow algorithm, font handling |
| Print Production | Die-cut, color management, print marks |
| Semantics | Shape vocabulary, accessibility |
| Reference Implementation | Python and Rust implementations |
| Conformance | Test suite, conformance levels |
| Ecosystem | Viewer, tools, integration libraries |

### Decision Making

- **Minor changes** (editorial, non-normative, examples): Working Group lead approval
- **Normative spec changes**: 2-week comment period, then Working Group lead + 1 Steering Committee member approval
- **Breaking/major changes**: Steering Committee vote (simple majority), 4-week comment period

All decisions are made in public in GitHub issues and pull requests.

## Versioning Policy

- Patch versions (0.1.1): editorial changes, spec clarifications, no normative changes
- Minor versions (0.2): new features, backward-compatible
- Major versions (1.0, 2.0): breaking changes allowed; migration guides required

The spec does not move to v1.0 until:
1. At least two independent implementations pass the full conformance suite
2. The Steering Committee votes to declare it stable

## Contributions

All contributions to the spec and reference implementations require:
1. Signing the Contributor License Agreement (CLA.md)
2. Adherence to the Code of Conduct
3. A pull request with review from at least one Working Group member

## Patent Policy

See PATENTS.md. All Steering Committee members and contributors must agree not to assert patents against conformant implementations of MDF.

## Trademark

"MDF" and "Morphous Document Format" are trademarks of the MDF Project. Use of these marks is permitted for:
- Implementations that pass the conformance suite
- Documentation, articles, and educational materials

Use of these marks for non-conformant implementations requires prior written approval from the Steering Committee.

## Amendments

This charter may be amended by a two-thirds supermajority vote of the Steering Committee, with a 4-week public comment period.
