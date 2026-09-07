# Roadmap

The roadmap is intentionally split into independently testable work packages.

## 0.2 — Pipeline integration

- Directory and glob input support with per-file summaries.
- Machine-readable contract validation errors.

## 0.3 — Contract evolution

- Backward-compatibility checks between contract versions.
- Deprecation metadata and migration hints.
- Contract diff output in Markdown and JSON.

## 0.4 — Scale and observability

- Reproducible one-million-record benchmark.
- Bounded issue sampling for high-volume invalid streams.
- Rule-level timing and failure distributions.

## Later exploration

- SQL DDL and dbt test generation from contracts.
- SARIF output for code-scanning interfaces.
- Optional plugin interface for domain-specific rules.

Items remain proposals until implemented and verified. The current README documents only released behavior.
