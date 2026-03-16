# Source Monitor Plan v1

## Purpose

Translate the acquisition plan into an execution queue.

This layer does not fetch sources yet. It decides:

- what can already be automated locally
- what should be tracked as a public-web watch
- what is blocked by login or subscription
- what cadence each source should follow

## Implementation

Primary logic:

- [source_registry.py](/home/d/codex/MiroFish/backend/app/services/source_registry.py)

CLI entry point:

- [build_source_monitor_plan.py](/home/d/codex/MiroFish/scripts/build_source_monitor_plan.py)

Generated example:

- [robotics actuation monitor plan](/home/d/codex/MiroFish/research/analysis/2026-03-16-robotics-actuation-source-monitor-plan-v1.json)

## Why This Phase Matters

Phase 4 is intentionally small.

The goal is not to fake full ingestion automation without connectors. The goal is to make the next automation work legible by separating:

- `automatable_now`
- `web_monitor_ready`
- `blocked_login`
- `blocked_subscription`
- `manual_only`

That gives MiroFish a clean operational handoff from:

`what sources matter`

to:

`how should we actually track them`

## Current Read

For the robotics actuation plan:

- the two local market-data workflows are already `automatable_now`
- most external sources are `web_monitor_ready`
- this is enough to begin building targeted connectors later without redesigning the registry or planning layers
