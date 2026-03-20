# Contributing to Lunaris

## Code style

All Rust code is formatted with `rustfmt` using the `.rustfmt.toml` in the `distro` repository.
Run `cargo fmt --all` before committing. CI will reject unformatted code.

Lints are enforced with `clippy::pedantic`. Add the following to every crate root:

```rust
#![warn(clippy::pedantic)]
#![allow(clippy::module_name_repetitions)]
#![allow(clippy::must_use_candidate)]
```

Code comments and all identifiers are in English.

## Documentation

Every public item must have a `///` doc comment. This is a CI requirement, not a suggestion.
Panics must be documented with a `# Panics` section. Errors must be documented with a
`# Errors` section once the API is stable.

## Commits

Format: `<scope>: <what changed>`

The scope is the repo or module being changed. Examples:

```
event-bus: add unix socket transport
sdk: implement EventEmitter mock
knowledge: fix promotion pipeline backpressure
distro: add just vm-debug recipe
```

One logical change per commit. No "fix stuff" or "WIP" commits on main.

## Branches

- `feat/<description>` for new features
- `fix/<description>` for bug fixes
- `chore/<description>` for tooling, CI, or dependency updates

## Pull requests

Every PR must reference an issue: `Closes #<number>` or `Part of #<number>` in the PR description.
PRs that change a public interface must update the corresponding mock in the same PR.
PRs that add a public item must include a doc comment for that item.

No PR merges without green CI.
