# Changelog

One section per chart version, newest first. The section of a version becomes the "Changes" part of its
GitHub release (`scripts/release-notes.sh`). `scripts/check.sh` fails when the version in
`paperless-ai/Chart.yaml` has no section here – write it in the same PR that bumps the version.

## 1.1.0

paperless-ai **4.5.1** (from 4.3.1). `helm upgrade` is enough; migrations run on the first start. Back up the
volume first and read README → *Upgrade* → *To chart 1.1.0*.

- 4.4: prompt rules – different prompts and settings per kind of document (`PROMPT_RULES` via `envs`)
- 4.5: optional built-in archive without Paperless-ngx (files in `data/library`), workflows, search syntax,
  API for the Paperless-ngx mobile apps (`/ngx`), MCP server (`/mcp`), API keys with fine-grained permissions
- 4.5: existing accounts become administrators; API keys need the new permissions to delete documents or
  manage labels
- 4.5.1: OCR with PP-OCRv6, model size selectable
- Verified with the chart's security context (uid 1000, read-only root filesystem, `/tmp` as emptyDir):
  4.3.1 started on an empty volume, then 4.5.1 on the same volume – migrations 10–18 applied, `/health` 200
- Not yet: extra volumes for watch folders (`/scans`, `/consume`)

## 1.0.0

paperless-ai **4.3.1**. paperless-ai 4.0 is a rewrite: one Node.js process, settings in
`data/config.json` + SQLite, environment variables override **and lock** settings in the web interface.

**Breaking – upgrade from 0.1.x needs manual steps** (README → *Upgrade*): chart 0.1.x put version labels
into the StatefulSet's volume claim template, which Kubernetes does not allow to change, so a plain
`helm upgrade` fails. Delete the StatefulSet once with `--cascade=orphan`, upgrade, delete the pod.
The PVC `data-<release>-0` is kept; paperless-ai migrates the 3.x `data/.env` and `documents.db` on the
first start.

- Paperless-ngx at any address (in-cluster Service or external URL): `paperless.url`, `paperless.publicUrl`,
  API token from an existing Secret (`paperless.existingSecret`), `hostAliases`, own CA bundle
  (`extraCaCerts`)
- Single sign-on with OpenID Connect (`oidc.*`), `publicUrl`; `TRUST_PROXY=1` with the ingress
- Probes on `/health` with a startup probe; container port fixed at 3000
- Runs as uid 1000 with a read-only root filesystem (`/tmp` as emptyDir), `fsGroup` 1000
- `image.variant: cuda` for OCR on NVIDIA GPUs
- Render-time validation: variables ending in `_KEY`, `_SECRET`, `_TOKEN`, `_PASSWORD` in `envs` need
  `valueFrom`; OIDC needs issuer, client secret and `publicUrl`
- Volume claim template only carries stable labels – later upgrades need no manual steps
- Paperless-ngx 3.5+: add the host paperless-ai uses to `PAPERLESS_ALLOWED_HOSTS` (README)

## 0.1.2

paperless-ai 3.0.9.

- Defaults: `ingress.enabled: false`, `persistence.data.size: 5Gi`
- README updated

## 0.1.1

paperless-ai 3.0.9. Initial version of the chart.
