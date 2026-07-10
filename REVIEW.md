# Production-Readiness Review — Intake Phase

*Principal-engineer ship review of the `launch-engagement` intake phase (`validate_intake.py` and its modules). Conducted before promoting the phase to production. The defects below were found during review; the [Resolution](#resolution) section records what shipped in response.*

---

## Executive summary

The intake phase does one job: take a loose intake payload, validate and normalize it against the engagement's guardrails, and emit the exact downstream commands plus a lane-filtered phase plan that the rest of the orchestration consumes. It is small (~600 LOC across focused modules), well-factored, tested, and — verified during review — the command contract it produces actually holds end-to-end (the emitted `start-project` command runs clean in dry-run). Close to ship-ready, held back by one real correctness bug on a resume path and a set of single-source-of-truth hygiene issues.

## Verdict

**Ship with minor revisions.** Quality score **7.5 / 10**. The happy paths are correct and verified; failure modes are gated defensively; nothing risks data loss. Two items block an unqualified "ready": one resume-path bug, and the fact that the phase's core value proposition — command compatibility with downstream skills — had **zero automated coverage**.

## Major strengths

- **The integration contract works.** Every flag the validator emits is accepted by the downstream `build_project.py` parser, verified by running the emitted command end-to-end in dry-run.
- **Clean modular decomposition** — normalization, resume-readiness, command emission, kit registry, and dataclasses are each single-responsibility and independently testable.
- **Guardrails enforced in code, not just documented** — portfolio-only-synthetic/public, software-code-carries-no-kit, path confinement to the vault root, sensitive-subfolder rejection, null-byte and separator rejection in names.
- **Kit-awareness via manifest `deploy_root`** rather than hardcoded paths, so new kits drop in without touching the validator.

## Critical concerns (as found)

1. **Correctness bug — software-code engagements could not resume past Phase 2.** The guard rejected `starting_phase >= 3`, but the kit phases are only 3–6; phases 7–9 (readout, value, close) are legitimate, non-kit resume points that the phase plan explicitly keeps for this lane. The guard conflated "no kit phases" with "no phase ≥ 3."
2. **The JSON schema was decorative.** `intake.schema.json` was never loaded — validation was hand-rolled — so the schema was a third, unenforced copy of rules that would silently drift.
3. **No test covered the phase's actual purpose.** All tests exercised normalization in isolation; nothing asserted that the emitted command is accepted by the downstream CLI. A renamed flag downstream would break production with every test still green.

## Design trade-offs noted

- Field contract documented in three places (skill doc, JSON schema, Python) — readable, but drift-prone without a guard.
- Kit-name validation silently no-ops when the kit registry is empty — portable, but lets a typo pass until deploy.
- Resume readiness gates only through Phase 5 artifacts; phases 6–9 resume without artifact checks.

## Resolution

All blocking items were fixed and merged before promotion:

- **Resume-guard bug fixed.** The guard now rejects only the kit phases `{3,4,5,6}`, sourced from a shared `SOFTWARE_CODE_SKIP_PHASES` constant that both the guard and the phase plan derive from — so they can no longer disagree. Phases 7–9 resume correctly for code builds.
- **Downstream-command contract test added.** The emitted `start-project` command is now parsed through the real `build_project.build_parser()`; a renamed or removed flag now fails in the test suite rather than at runtime. A structural check covers the kit-deploy command.
- **Schema-drift guard added.** A test asserts `intake.schema.json`'s enums match `engagement_constants`, closing the silent-divergence gap.
- **Empty kit-registry** now emits a warning instead of silently accepting an unverifiable kit name.
- **Docs** updated to record the software-code resume boundary and the Phase 6–9 readiness gap.

**Verification:** the intake suite expanded from 9 to 14 tests, all passing; the other pack consumers were confirmed unaffected.

### Deferred (non-blocking, fast-follow)

- Consolidate the field contract to a single generative source.
- Refactor `deploy_kit.py` to expose a reusable parser so its emitted command can get a real (not structural) contract test.
