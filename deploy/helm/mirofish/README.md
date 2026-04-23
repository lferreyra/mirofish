# MiroFish Helm chart

Minimal chart that provisions:

- `backend` Deployment + Service (Flask app, horizontally scalable)
- `redis` Deployment + Service (run-state cache; disable with `--set redis.enabled=false`)
- optional `vllm` Deployment + Service (GPU required; `--set vllm.enabled=true`)
- optional `ingress` for public access
- placeholder `Secret` (populate externally via sealed-secrets / external-secrets)

## Install

```bash
helm install mirofish ./deploy/helm/mirofish \
  --set backend.image.repository=ghcr.io/your-org/mirofish-backend \
  --set backend.image.tag=0.6.0 \
  --set memory.neo4j.uri=neo4j+s://xxx.databases.neo4j.io \
  --set llm.backendMode=cloud
```

Populate the `mirofish-secrets` Secret out-of-band before the backend can
make cloud LLM calls — the chart intentionally ships it empty so `helm
install` against a dry-run cluster succeeds.

## Lint

```bash
helm lint ./deploy/helm/mirofish
helm template ./deploy/helm/mirofish | kubectl apply --dry-run=client -f -
```

## Values overview

See `values.yaml` — every key is documented inline. The groups:

- `backend.*` — image, replicas, resources, probes
- `frontend.*` — disabled by default (upstream frontend not yet containerized)
- `redis.*` — inline Redis for run-state cache
- `vllm.*` — optional GPU-backed inference server
- `memory.*` — Neo4j / Zep backend selection
- `llm.*` — per-role provider / model overrides; defaults to the legacy
  `LLM_*` env keys if left empty
- `auth.*` — API-key auth controls
- `observability.*` — OTel endpoint, Prometheus scrape annotations
- `ingress.*` — external routing
