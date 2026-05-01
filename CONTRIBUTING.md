# Contributing to MDF

Thanks for your interest in the Morphous Document Format project.

## Ways to Contribute

- **Spec feedback**: open an issue with the `spec` label to propose changes, ask for clarification, or report ambiguity
- **Implementation**: contribute to the Python or Rust reference implementations
- **Examples**: add `.mdf` example documents to `examples/`
- **Conformance tests**: add test cases to `conformance/suite/`
- **Documentation**: improve docs in `docs/` or inline spec chapters
- **Tooling**: contribute to `tools/mdf-lint` or `tools/mdf-pack`

## Getting Started

1. Fork the repo and clone locally
2. Read `spec/v0.1/00-overview.md` to understand the design philosophy
3. Check the [open issues](https://github.com/mathornton03/mdf/issues) for good first contributions

## Pull Request Process

1. Open an issue first for significant changes (spec changes, new features)
2. Fork and create a branch from `main`
3. Make your changes
4. For spec changes: update or add examples in `examples/`
5. For implementation changes: add tests in the relevant `tests/` directory
6. Submit a PR with a clear description of what changed and why

## Spec Change Guidelines

When proposing spec changes:

- Reference the relevant spec chapter(s) in your PR
- Consider all three conformance levels
- Provide at least one example `.mdf` document that exercises the new feature
- If the change affects rendering, describe the expected renderer behavior precisely

## Code Style

Python code should follow PEP 8. Use `ruff` for linting.

Rust code should pass `cargo clippy` without warnings.

TypeScript code should pass `tsc --noEmit`.

## Contributor License Agreement

By submitting a contribution, you agree that:

1. Your contribution is your original work or you have the right to submit it
2. You grant the MDF Project a perpetual, irrevocable, royalty-free license to use your contribution
3. You agree to the patent pledge in PATENTS.md
4. You will not assert any patent claims against conformant MDF implementations

## Code of Conduct

This project follows the Contributor Covenant Code of Conduct. See CODE_OF_CONDUCT.md. Be excellent to each other.
