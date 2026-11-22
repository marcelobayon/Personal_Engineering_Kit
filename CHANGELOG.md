# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

## [0.2.0] - 2026-11-22

First working release. The repository previously contained only a philosophy
README; this release turns it into an installable, tested package.

### Added
- `mbkit.log` — idempotent, configurable logger factory with optional JSON
  output and `bind()` for request-scoped context.
- `mbkit.config` — layered configuration (`defaults < file < environment`) with
  typed getters and `.json` / `.toml` / `.env` support.
- `mbkit.resilience` — `retry` (bounded backoff + jitter), `CircuitBreaker`
  (closed/open/half-open, thread-safe), and `FallbackChain` / `fallback`.
- `mbkit.result` — `Result[T, E]` with `Ok` / `Err` for railway-oriented error
  handling.
- `mbkit.timing` — `Timer` context manager and `@timed` decorator.
- `src/` layout, `pyproject.toml`, test suite, MIT license, and
  `docs/biology-to-software.md` connecting the resilience patterns to the
  biology-computing theory.

[0.2.0]: https://github.com/marcelobayon/personal_engineering_kit/releases/tag/v0.2.0
