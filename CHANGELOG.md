# Changelog

One section per chart version, newest first. The section of a version becomes the "Changes" part of its
GitHub release (`scripts/release-notes.sh`). `scripts/check.sh` fails when the version in
`paperless-ai/Chart.yaml` has no section here – write it in the same PR that bumps the version.

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
