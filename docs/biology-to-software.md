# Biology → software: the thinking behind `mbkit.resilience`

This kit's resilience module is a small, *bounded* translation of a longer
research note (`BIOLOGICAL_COMPUTING_THEORY.md`, kept with the project / the
BioHeal charter). The idea is not that software is alive, but that biology is a
useful source of **design hypotheses** for systems that must survive changing
conditions and partial failure.

The discipline that matters: a biological analogy generates a hypothesis; it
does not prove the mechanism works. Keep a pattern only when it earns its
complexity. And **self-healing means *verified* recovery — not changing code
until the error disappears.**

## What maps to what

| Biological concept | Engineering interpretation | Where it lives in `mbkit` |
|---|---|---|
| Homeostasis | Keep operating within safe limits; stop when a dependency is unhealthy | `resilience.CircuitBreaker` |
| Redundancy | Preserve a function through reviewed alternatives | `resilience.FallbackChain` / `fallback` |
| Opportunistic behaviour | Use an *approved* alternative when the preferred one is down — never an arbitrary substitute | `FallbackChain` (named, ordered options) |
| Adaptation under transient stress | Give a transient failure a bounded second chance | `resilience.retry` (backoff + jitter) |
| Repair / reversibility | An outcome is explicit and carries a reason; failures don't masquerade as success | `result.Result` (`Ok` / `Err`) |
| Resource efficiency | Measure before you throttle | `timing.Timer`, `timing.timed` |

## The guardrails (carried over from the theory note)

These are the lines the resilience code is written to respect:

- **Bounded, not infinite.** Retries have a ceiling; breakers have a cooling-off
  window; fallbacks are a finite, named list.
- **Allowlist, not arbitrary.** `FallbackChain` tries *reviewed* options in
  order. Nothing installs packages or trusts an unverified substitute.
- **Classify failures.** `retry` and `CircuitBreaker` only react to the
  exception types you name — a validation error is not an outage and must not
  trip a breaker or burn a retry.
- **Verify, don't assume.** `fallback(..., validate=...)` rejects a result that
  returned without error but is empty/stale/wrong. "It didn't throw" is not
  success.

## Not in scope here

The theory note and the BioHeal charter describe larger machinery — candidate
generation, sandboxed repair, policy engines, hosted orchestration. That is a
**separate project** (BioHeal), deliberately not bolted onto this personal kit.
`mbkit` stays a dependency-free library of patterns you import; BioHeal is the
product that would build on ideas like these.
