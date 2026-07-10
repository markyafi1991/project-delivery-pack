---
name: start-project
description: Create a new Algonquin client engagement or portfolio project, scaffold its dossier and working folders, and generate or refresh a project-specific SOP runbook from the canonical vault procedures. Use when the user says "/start-project", "create a client engagement", "onboard a new client", "create a portfolio project", "start a project", or asks which SOPs apply to a project.
---
## Before proceeding

Read `01_Operations/Skill Notes/start-project - Owner Notes.md` if it exists. Treat owner highlights and `[!owner-*]` callouts as required context.


# Start Project

Create project structure and an applicable SOP runbook without modifying canonical SOPs.

For an **AI/BI client or portfolio engagement**, scaffold from the reusable template **[[AI-BI Consulting Engagement — Template Guide]]** (`06_Templates/Projects/AI-BI Consulting Engagement/`) — it carries the full-lifecycle runbook, the deliverable templates (SOW, brand/design system, situation assessment), and the SOP/skills/ClickUp blueprint. Worked example: the Variance Pack (`04_Portfolio/PowerBI_Variance_Pack/`).

## Guardrails

- Treat markdown in the vault as the source of truth.
- Never put real client data into `04_Portfolio/`.
- Require portfolio data classification to be `synthetic` or `public`.
- Never overwrite an existing dossier with `create`.
- Never edit canonical files in `01_Operations/SOPs/` automatically.
- Capture lessons and proposed canonical changes in the generated runbook for owner approval.

## Inputs

Collect:

- Kind: `client` or `portfolio`
- Name
- Industry
- Engagement type: `analytics`, `automation`, or `advisory`
- Data classification: `synthetic`, `public`, `internal`, `confidential`, `financial`, or `phi`
- Deliverables: one or more short descriptions
- Source and status when relevant

For a real client engagement, default status to `prospect` unless the contract is active. For a portfolio project, default status to `active` and data classification to `synthetic`.

## Create

Preview first:

```bash
python3 .claude/skills/start-project/scripts/build_project.py create \
  --kind client \
  --name "Client Name" \
  --industry "Fund administration" \
  --engagement-type analytics \
  --data-classification financial \
  --deliverable "Power BI dashboard" \
  --source "Upwork" \
  --dry-run
```

Review the printed paths and applicability decisions, then rerun without `--dry-run`.

The script creates:

- A dossier beside the project folder
- Standard working folders
- Client onboarding/offboarding checklists for client engagements
- `SOP Runbook.md`, containing the applicable canonical SOP links, gaps, and improvement-capture checklist

After creation, inspect the dossier and runbook. Add judgment-driven business context only after the deterministic scaffold is correct.

## Register

The script scaffolds files but does not register the project anywhere. After creation, wire it into the vault by hand:

- **Client:** the dossier auto-surfaces in [[Clients Hub]] via Dataview (`type: client`) — no action needed there. Add a pipeline row to `02_Clients/CRM_Pipeline_Tracker.md` for the new prospect (Client Name / Source / Status / Next Step / Last Contacted / Deal Value).
- **Portfolio:** [[Portfolio Hub]] is manually curated and has no Dataview auto-list — link the new build into it explicitly, or it stays orphaned.
- **Both:** append a line to today's note in `01_Operations/Logs/Daily/` per the [[CLAUDE]] write protocol (create from template if missing).

## Refresh

Regenerate the SOP runbook after project metadata changes:

```bash
python3 .claude/skills/start-project/scripts/build_project.py sync \
  --dossier "02_Clients/Client Name.md"
```

Use optional metadata flags to override missing legacy metadata. `sync` only replaces the generated runbook; it does not change the dossier or canonical SOPs.

## Close-Out

Report:

- Dossier and project-folder paths
- Applicable SOPs and missing-procedure gaps
- Any metadata assumptions
- The runbook's proposed SOP improvements requiring owner review

Do not register an unattended trigger in `01_Operations/Cadence.md` until the owner has battle-tested this manual workflow.
