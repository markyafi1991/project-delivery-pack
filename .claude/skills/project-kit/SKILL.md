---
name: project-kit
description: Deploy a reusable Project Kit — a packaged, tool-specific bundle of build accelerators (templates, assets, checklists, runbook) — into an existing client or portfolio project to speed delivery. Kits live in 06_Templates/Kits/; the first is the Power BI Project Kit (branded theme, TMDL model starter, DAX library, model tests, synthetic-data generator, layout mockup, Deneb custom visual, and an AI Build Runbook for authoring a PBIP as code). Use when the user says "/project-kit", "deploy the power bi kit", "drop the kit into this project", "set up a power bi project", "use the project kit", "list the kits", or scaffolds a build that a kit covers. Business-scoped software/delivery lane — never reads 09_Job_Search or 10_Personal.
---

## Before proceeding

Read `01_Operations/Skill Notes/project-kit - Owner Notes.md` if it exists, and the target kit's
`… — Kit Guide.md`. Treat owner highlights and `[!owner-*]` callouts as required context.

# Project Kit

Deploy a **Project Kit** into a project folder. A kit is the *technical build payload* that fills
the design→build→QA→handoff phases of an engagement — distinct from the [[AI-BI Consulting
Engagement — Template Guide|engagement lifecycle template]] (the PM spine) and the [[SOPs Hub|SOPs]]
(the procedure). Pattern + anatomy: [[Kits Hub]]. Decision: [[2026-07-03 Project Kit pattern and Power BI kit]].

## Orchestration Flow

When invoked, the agent MUST act as a step-by-step orchestrator, operating in three distinct phases. 

### Phase 1: Project Inheritance & Discovery
1. **List Kits:** Run `python3 .agents/skills/project-kit/scripts/deploy_kit.py list` to see available kits in `06_Templates/Kits/`.
2. **Ask the User:** Ask the user which kit they want to deploy, the target project directory, and the specific goal/type of the project (e.g., Financial Dashboard vs Operational Tracker).

### Phase 2: Up-Front Outlining & Automation
Before any development begins, the agent MUST fully outline and automate the project scaffold:
1. **Draft Requirements:** Based on the user's answers, autonomously fill out the `Dashboard_Requirements (TEMPLATE).md` (Audience, KPIs, Grain).
2. **Draft Recipe:** Scaffold the `Build Recipe (TEMPLATE).md` with the overarching step-by-step plan.
3. **Deploy Kit:** Run `python3 .agents/skills/project-kit/scripts/deploy_kit.py deploy --kit "<Kit>" --project "<Project>"` (use `--dry-run` first, confirm, then run live). The deploy script rejects projects outside `02_Clients/` or `04_Portfolio/` and exits nonzero if any manifest file is missing.
4. **ClickUp Automation:** Use the `clickup` MCP server tools to autonomously create a list inside the matching type folder of the Portfolio Projects space. Build the *entire* milestone-driven tree per [[SOP - Milestone-Driven ClickUp Project Setup]] based on the runbook, and stamp the list + milestone IDs back into the project dossier.

### Phase 3: Runbook Orchestration (Step-by-Step Execution)
Once the up-front outlining is complete, the agent MUST open the deployed runbook (e.g., `<project>/Power BI Kit/AI Build Runbook.md`) and guide the user through it sequentially:
- **Agent Tasks:** Autonomously execute Python scripts for synthetic data, scaffold the PBIP tree, author TMDL models, and write DAX/tests.
- **Human Tasks:** Pause execution and clearly instruct the human on exactly what buttons to click in Power BI Desktop (e.g., enable preview features, apply refresh, QA the visuals). The agent MUST wait for the user's explicit confirmation before moving to the next phase.

Software/code builds are **not** tracked in ClickUp — they go to Linear (discriminator: code-vs-tool, not topic).

## Kit diagram (Lucidchart)

Every kit ships a `Diagram.mmd` (Mermaid source of truth) whose published copy lives in **Lucidchart**. No Lucid connector is wired into the vault, so publishing is a manual one-paste step — **Lucidchart → New → Import → Mermaid**, paste `Diagram.mmd`, Import — then stamp the URL into `manifest.json` (`diagram.lucidchart_url`). When **authoring a new kit**, produce its `Diagram.mmd` (validate with the Mermaid renderer) and import it; when a kit changes, update the diagram and re-import. Pattern: [[Kits Hub]].

## Close-out

Report the kit + version deployed, the destination path, files copied vs. skipped, the post-deploy notes, and the next runbook phase. Do not report "done" on the script's say-so — confirm the files landed and the runbook is in place ([[verify-build]]).
