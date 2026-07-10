# launch-engagement scripts

Canonical skill tree: `.claude/skills/launch-engagement/`. The `.agents/skills/launch-engagement/` copy must stay in sync.

## Intake validator

Validates and normalizes intake JSON before Phase 0. Writes normalized state to `.cache/launch-engagement/state.json` (gitignored).

```bash
# From vault root — file input
python3 .claude/skills/launch-engagement/scripts/validate_intake.py \
  --file .claude/skills/launch-engagement/examples/portfolio_tool_bi.json

# Inline JSON
python3 .claude/skills/launch-engagement/scripts/validate_intake.py \
  --json '{"kind":"portfolio","name":"Demo","delivery_lane":"advisory-only"}'

# Stdin
cat examples/portfolio_tool_bi.json | python3 scripts/validate_intake.py --root ../..
```

Schema: `intake.schema.json`. Examples: `examples/`.

## Module layout

| Module | Role |
|---|---|
| `validate_intake.py` | CLI entrypoint |
| `intake_normalize.py` | Field validation, defaults, path rules |
| `intake_readiness.py` | Resume artifact checks (kit-aware via manifest `deploy_root`) |
| `intake_commands.py` | Emits `start-project` / `project-kit` command arrays |
| `intake_schema.py` | `Intake` + `IntakeResult` dataclasses |
| `kit_registry.py` | Loads `06_Templates/Kits/*/manifest.json` |
| `_paths.py` | Vault-root import bootstrap |

Shared enums: `scripts/engagement_constants.py` (also used by `start-project`).

## Resume artifact matrix

| `starting_phase` | Required artifacts |
|---|---|
| 0 | None |
| 1 | Dossier (`.md`), project folder, `SOP Runbook.md` |
| 2 | + `Deliverables/01_Situation_Assessment.md` |
| 3 | + `Deliverables/02_KPI_Design.md` |
| 4 (tool-built-bi) | + `<kit deploy_root>/AI Build Runbook.md` |
| 5 (tool-built-bi) | + `<kit deploy_root>/Build Recipe (TEMPLATE).md` |

## Tests

```bash
python3 .claude/skills/launch-engagement/tests/test_validate_intake.py -v
```

Coverage includes a **downstream-command contract test** (parses the emitted `start-project` command
through the real `build_project.build_parser()` so a renamed flag fails in tests, not production) and a
**schema-drift guard** (asserts `intake.schema.json` enums match `engagement_constants`, since the schema
is reference-only and not loaded at runtime). Lane skip-phase sets live in `engagement_constants`
(`SOFTWARE_CODE_SKIP_PHASES`, `ADVISORY_ONLY_SKIP_PHASES`) — the resume guard and phase plan share them.
