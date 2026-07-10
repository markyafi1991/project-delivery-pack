# Project Delivery Pack

A set of composable [Claude Code](https://docs.claude.com/en/docs/claude-code) skills that automate an AI/BI consulting engagement end-to-end — from intake to closeout — as a **step-by-step orchestrator over deterministic Python tooling**.

The design principle throughout: an LLM decides *what* to do at each seam, but the *validation, path safety, command construction, and state* are handled by plain, tested Python — not left to prompt judgment. Every gate that matters is enforced in code and covered by a test.

> This is a self-contained slice extracted from a larger private "AI Operating System" vault. Some `[[wikilinks]]` and `NN_Area/` paths in the skill docs point to notes that live in that vault, not in this repo — that's expected. The **code and tests are fully standalone and pass on their own.**

---

## The three skills

| Skill | Role | Core artifact |
|---|---|---|
| **`launch-engagement`** | Orchestrator. Validates intake, computes a lane-filtered phase plan (0–9), and drives each phase by delegating to the child skills. | `validate_intake.py` |
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
- **Emits the exact downstream commands** (`start-project`, `project-kit --dry-run`) that the orchestrator then runs — a contract test parses those commands through the *real* downstream argument parsers so a renamed flag fails in CI, not in production.
- **Persists state** to `.cache/launch-engagement/state.json`.

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
