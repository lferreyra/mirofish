# Research Project Data Model V1

Date: March 15, 2026

## Purpose

This document defines the first backend data model and API surface for MiroFish research mode.

It sits on top of the finalized bottleneck ontology and gives the backend a stable persistence contract for:

- thesis intake
- claims audit
- scorecards
- summary/report metadata

This is intentionally separate from the original simulation project flow.

## Persistence Model

Research projects are file-backed, mirroring the existing `ProjectManager` pattern.

Root folder:

- `backend/uploads/research_projects/<research_project_id>/`

Within each project:

- `research_project.json`
- `artifacts/thesis_intake.json`
- `artifacts/claims_audit.json`
- `artifacts/claims_audit.csv`
- `artifacts/scorecards.json`
- `artifacts/summary.json`
- `files/`

## Canonical Model

The canonical backend model lives in:

- [research_project.py](/home/d/codex/MiroFish/backend/app/models/research_project.py)

Core fields:

- `research_project_id`
- `name`
- `status`
- `created_at`
- `updated_at`
- `ontology_name`
- `ontology_version`
- `thesis_intake`
- `claims_audit_count`
- `scorecard_count`
- `tags`
- `focus_areas`
- `source_files`
- `notes`
- `summary`
- `error`

## Status Model

Current status progression:

- `created`
- `intake_defined`
- `claims_audited`
- `scored`
- `reported`
- `failed`

This is intentionally simple. It tracks research workflow progression, not background job orchestration.

## API Surface

The first stable API routes live in:

- [research.py](/home/d/codex/MiroFish/backend/app/api/research.py)

Endpoints:

- `GET /api/research/ontology`
- `POST /api/research/project`
- `GET /api/research/project/list`
- `GET /api/research/project/<research_project_id>`
- `DELETE /api/research/project/<research_project_id>`
- `GET /api/research/project/<research_project_id>/artifacts`
- `POST /api/research/project/<research_project_id>/thesis-intake`
- `POST /api/research/project/<research_project_id>/claims-audit`
- `POST /api/research/project/<research_project_id>/scorecards`
- `POST /api/research/project/<research_project_id>/summary`

## Why This Is Enough

This is enough to unblock the next layer of work:

- backend persistence
- frontend research-mode flows
- import/export of case-study artifacts
- future scoring/report-generation endpoints

It is not yet:

- a full automation pipeline
- a full document-ingestion workflow for research mode
- a frontend-integrated product surface

## Next Step

The next correct step is frontend and workflow integration:

1. decide the research-mode entry flow
2. add frontend API wrappers
3. build a thesis-intake and artifact view
4. decide whether source upload belongs in research mode directly or stays separate
