# Project Delivery Pack

A set of composable [Claude Code](https://docs.claude.com/en/docs/claude-code) skills that specify an AI/BI consulting engagement end-to-end — from intake to closeout — and run its front end as a **step-by-step orchestrator over deterministic Python tooling**.

The design principle throughout: an LLM decides *what* to do at each seam, but the *validation, path safety, command construction, and state* are handled by plain, tested Python — not left to prompt judgment. In this repository that principle is implemented in code for **the intake pipeline and Phase 0**: those gates are enforced in Python and covered by tests. The later phases are specified in the skill documents and executed by an agent against those specifications; they do not ship here as runnable gate machinery. See [Scope of this extract](#scope-of-this-extract) for the exact line between the two.

> This is a self-contained slice extracted from a larger private "AI Operating System" vault. Some `[[wikilinks]]` and `NN_Area/` paths in the skill docs point to notes that live in that vault, not in this repo — that's expected. The **code and tests that are here are fully standalone and pass on their own.**

---

## Status — Beta

The Project Delivery Pack is **one versioned product**. The automation, its published documentation, and its audit boards all carry the same number; they never advertise different versions. It is currently at **Beta**.

**Beta means: built, reviewed across six independent AI reviewer seats, and not yet run end to end on a live engagement.** That is the entire claim. All eleven pipeline stages — intake plus Phases 0–9 — have been through all six seats; owner acceptance — the final sign-off, which is not delegated — is outstanding on every one, so no phase is marked verified yet. [REVIEW.md](REVIEW.md) is the principal-engineering seat applied to the intake phase.

| Milestone | Meaning |
|---|---|
| **Beta** | Pre-battle-test. Built and audited, not yet run on a live engagement. **Current state.** |
| **v1** | The first engagement run end to end. |
| **v1.x** | Each audit round that lands changes. |
| **v2** | A structural change to the phase chain or gate model — by definition, regardless of diff size. |
| **v2.x** | The v1.x rule on the v2 line. The pattern is `<major>.<audit-round>`. |

## Scope of this extract

This repository is a sanitized extract, not the whole system. Being exact about that line is part of the point:

- **Runnable coverage is the intake pipeline and Phase 0.** Intake validation, normalization, path safety, resume gating, downstream-command emission, the Phase 0 scaffold, and kit deploy are here as working, tested Python.
- **Phases 1–9 are documented, not shipped.** This repo's copy of the `launch-engagement` skill carries **215 lines of specification against 667 in the private tree**; it *summarises* Phases 3–9 rather than shipping their gate machinery. The private tree carries **41 script modules and 14 test files**; the `launch-engagement` skill as published here carries **7 modules and 1 test file**.
- **This is the more stale of the two public copies.** The same skill is also published in the companion `launch-engagement-automation` repository. Where the two disagree, that one is closer to current.
- **Known limitation — a single shared state file.** `scripts/engagement_constants.py` here writes engagement state to one shared path (`.cache/launch-engagement/state.json`), so two engagements run against the same checkout would overwrite each other. The private tree replaced this with per-engagement state — one file per engagement, keyed by a 16-hex digest of the engagement identity, plus an index, at schema version 2. The shared singleton is a property of the extract, not of the current design.
- **No real client data.** Every worked example is synthetic. "Variance Pack" is a synthetic portfolio project, not a client engagement.

---

## The three skills

| Skill | Role | Core artifact |
|---|---|---|
| **`launch-engagement`** | Orchestrator. Validates intake and computes a lane-filtered phase plan (0–9) in code; the per-phase drive is specified in its `SKILL.md` and executed by the agent against the child skills. | `validate_intake.py` |
| **`start-project`** | Scaffolds a project folder + dossier and generates an SOP runbook from a procedure map. | `build_project.py` |
| **`project-kit`** | Deploys a reusable, tool-specific **kit** (e.g. a Power BI accelerator bundle) into an existing project. | `deploy_kit.py` |

They share one module, `scripts/engagement_constants.py`, so the enums and phase-skip sets have a single source of truth.

## How intake works (the reviewed centerpiece)

`launch-engagement` never proceeds on prompt judgment. It requires a small JSON intake payload, then **validates and normalizes it** before any work begins:

```bash
python3 .claude/skills/launch-engagement/scripts/validate_intake.py \
  --json '{"kind":"portfolio","name":"Variance Pack","delivery_lane":"tool-built-bi","kit":"Power BI Project Kit"}'
```

The validator:

- **Enforces guardrails in code** — portfolio projects may only carry `synthetic`/`public` data; software/code builds route to Linear and cannot carry a kit; project paths are confined to the vault root and blocked from confidential subfolders (path-traversal and null-byte safe).
- **Applies sensible defaults** and fills a normalized `Intake` record.
- **Computes a lane-filtered phase plan** — e.g. `advisory-only` skips the kit-build phases; portfolio builds skip the client readout unless asked.
- **Gates resumes** — starting at a later phase requires the prior-phase artifacts to exist on disk.
- **Emits the exact downstream commands** (`start-project`, `project-kit --dry-run`) that the orchestrator then runs — a contract test parses those commands through the *real* downstream argument parsers, so a renamed flag fails in the test suite rather than at runtime. (There is no CI configured in this repo; the suites are run by hand — see [Running the tests](#running-the-tests).)
- **Persists state** to `.cache/launch-engagement/state.json` — a single shared file in this extract, superseded by per-engagement state in the private tree. See [Scope of this extract](#scope-of-this-extract).

## Delivery lanes

| Lane | Executes on | Phases run |
|---|---|---|
| `tool-built-bi` | ClickUp Portfolio Projects + kit deploy | 0–9 (portfolio skips 7 by default) |
| `software-code` | Linear (kit phases 3–6 don't apply) | 0–2, 7–9 |
| `advisory-only` | ClickUp business execution | 0–2, 6, 8–9 |

## Running the tests

Every skill ships a unit suite; the pack is green standalone:

```bash
python3 .claude/skills/launch-engagement/tests/test_validate_intake.py -v   # intake validation + downstream contract
python3 .claude/skills/start-project/tests/test_build_project.py -v         # scaffold + runbook generation
python3 .claude/skills/project-kit/tests/test_deploy_kit.py -v              # kit deploy + path safety
```

No third-party dependencies — standard-library Python 3 only.

## Repository layout

```
.claude/skills/
  launch-engagement/   orchestrator + intake validator (7 modules, 14 tests)
  start-project/       project scaffolder + SOP runbook generator
  project-kit/         reusable kit deployer
scripts/
  engagement_constants.py   shared enums + phase-skip sets (single source of truth)
REVIEW.md              principal-engineer production-readiness audit of the intake phase
```

## Engineering notes

The intake phase went through a formal production-readiness review — see **[REVIEW.md](REVIEW.md)** for the full audit, the defects it surfaced (including a resume-guard correctness bug), and the fixes that shipped in response.

## License

MIT — see [LICENSE](LICENSE).
