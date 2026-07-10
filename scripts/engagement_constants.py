"""Shared engagement metadata enums for start-project and launch-engagement."""

from __future__ import annotations

DATA_CLASSIFICATIONS = (
    "synthetic",
    "public",
    "internal",
    "confidential",
    "financial",
    "phi",
)
ENGAGEMENT_TYPES = ("analytics", "automation", "advisory")
PROJECT_KINDS = ("client", "portfolio")
DELIVERY_LANES = ("tool-built-bi", "software-code", "advisory-only")
CLIENT_STATUSES = ("prospect", "proposal-sent", "active", "delivered", "dormant")
SENSITIVE_PROJECT_PARTS = {"client-comms", "contracts", "intake"}

WORK_SURFACES = {
    "tool-built-bi": "ClickUp Portfolio Projects",
    "software-code": "Linear",
    "advisory-only": "ClickUp business execution",
}

# Orchestration phases a lane does not run. Single source of truth shared by the
# resume guard (intake_normalize) and the phase plan (intake_commands) so the two
# can never disagree about which phases a lane skips. Kit phases (3=kit deploy,
# 4=build, 5=QA, 6=handoff) do not apply to code builds tracked in Linear; phases
# 7-9 (readout/value/close) remain valid resume points for every lane.
SOFTWARE_CODE_SKIP_PHASES = frozenset({3, 4, 5, 6})
ADVISORY_ONLY_SKIP_PHASES = frozenset({3, 4, 5})

STATE_DIR = ".cache/launch-engagement"
STATE_FILENAME = "state.json"
