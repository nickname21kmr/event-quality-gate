# Event Quality Gate

[![CI](https://github.com/nickname21kmr/event-quality-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/nickname21kmr/event-quality-gate/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Event Quality Gate is a local-first command-line tool for enforcing data contracts on JSONL event streams. It validates records line by line, catches schema and business-rule violations, and emits deterministic JSON, Markdown, text, or JUnit XML reports suitable for CI annotations, artifacts, and audit trails.

The first example models synthetic LiveOps telemetry, but the validator is domain-neutral: the same contract format can protect product analytics, experimentation, operations, or public-data pipelines.

## Why this exists

Event pipelines often fail quietly. A renamed field, duplicated identifier, malformed timestamp, or negative purchase amount can reach a dashboard before anyone notices. Event Quality Gate makes those assumptions executable and fails with a non-zero exit code when a contract is violated.

Current checks include:

- required and optional field types;
- nested fields through dot paths;
- ISO 8601 timestamps;
- allowed values;
- uniqueness constraints;
- conditional required fields and numeric bounds;
- malformed JSON and non-object records.

Runtime dependencies: **none**. The implementation uses only the Python standard library.

## Quick start

```bash
python -m pip install -e .

event-quality-gate validate \
  --contract examples/contracts/liveops-event-v1.json \
  --input examples/events/valid.jsonl \
  --format markdown
```

Validate the deliberately broken fixture:

```bash
event-quality-gate validate \
  --contract examples/contracts/liveops-event-v1.json \
  --input examples/events/invalid.jsonl \
  --format json
```

The second command exits with status `1`, making it usable as a CI quality gate. Configuration or file errors exit with status `2`.

## Contract format

```json
{
  "contract_version": 1,
  "name": "liveops-event-v1",
  "required": {
    "event_id": "string",
    "event_type": "string",
    "user_id": "string",
    "occurred_at": "datetime"
  },
  "optional": {
    "session_id": "string",
    "properties": "object"
  },
  "unique": ["event_id"],
  "allowed_values": {
    "event_type": ["login", "session_start", "purchase", "level_complete"]
  },
  "constraints": [
    {
      "when": {"field": "event_type", "equals": "purchase"},
      "require": ["properties.amount", "properties.currency"],
      "types": {
        "properties.amount": "number",
        "properties.currency": "string"
      },
      "minimum": {"properties.amount": 0}
    }
  ]
}
```

Supported types are `string`, `integer`, `number`, `boolean`, `object`, `array`, and `datetime`.

## Reports

Write a report to disk with `--output`:

```bash
event-quality-gate validate \
  --contract examples/contracts/liveops-event-v1.json \
  --input examples/events/invalid.jsonl \
  --format markdown \
  --output reports/invalid-events.md
```

Every report contains the contract name, source path, pass/fail status, record counts, issue codes, line numbers, field paths, and messages. `--max-issues` limits displayed details without changing the aggregate counts.

CI systems can ingest one failed test case per invalid record with `--format junit`:

```bash
event-quality-gate validate \
  --contract examples/contracts/liveops-event-v1.json \
  --input examples/events/invalid.jsonl \
  --format junit \
  --output reports/event-quality.xml
```

Valid records are summarized in one passing test case so large valid streams do not create unnecessarily large XML files. Failure counts remain exact when `--max-issues` truncates the displayed details.

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall -q src
```

The repository deliberately keeps the first release small and inspectable. See [ROADMAP.md](ROADMAP.md) for the next independent work packages and [CONTRIBUTING.md](CONTRIBUTING.md) for the issue-to-merge workflow.

## Data and evidence boundaries

All example events are synthetic and contain no production identifiers, customer data, or proprietary schemas. This repository demonstrates validation design and reproducible engineering controls; it does not claim deployment in a commercial telemetry pipeline.

## License

Code is available under the [MIT License](LICENSE). Synthetic example data may be reused under the same terms.
