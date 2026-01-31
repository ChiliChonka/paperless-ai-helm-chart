# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- JSON Schema (`values.schema.json`) for IDE autocompletion and validation
- Security contexts with sensible defaults (pod and container level)
- Default resource requests and limits
- Startup probe for slow-starting containers
- NetworkPolicy template (disabled by default)
- ServiceMonitor template for Prometheus monitoring (disabled by default)
- Example values files:
  - `examples/values-minimal.yaml` - Quick start configuration
  - `examples/values-production.yaml` - Production-ready with security hardening
  - `examples/values-with-ollama.yaml` - Configuration for Ollama integration
- Helm unit tests using helm-unittest
- Pre-commit hooks configuration for local validation
- CI/CD improvements:
  - Helm linting on PRs and before release
  - Template validation (dry-run)
  - Runs lint/validate on pull requests affecting chart files

### Changed
- Improved `values.yaml` with inline documentation comments
- Changed default ingress pathType from `ImplementationSpecific` to `Prefix`
- Enhanced probe configuration with tunable parameters (initialDelaySeconds, timeoutSeconds, etc.)

### Fixed
- N/A

## [0.1.1] - 2025-01-XX

### Added
- Initial Helm chart release
- StatefulSet deployment (single replica)
- Persistent volume claim for `/app/data`
- Service and Ingress configuration
- `enableServiceLinks: false` to prevent Kubernetes env injection issues

### Notes
- paperless-ai v3.0.9 support
- First-start web wizard required for initial configuration
