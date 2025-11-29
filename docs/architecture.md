# DocETL Architecture

DocETL executes YAML pipelines composed of operators. Each run creates an isolated run directory under `./runs` with snapshots and metrics. Operators are deterministic and receive structured records.

Pipeline lifecycle:
1. Load pipeline YAML and validate schema.
2. Initialize run directory with hashes and git metadata.
3. Execute operators in order, emitting lineage records per record per operator.
4. Persist outputs, metrics, lineage, and configuration snapshots.

Core components:
- **Runner**: orchestrates pipeline execution, streaming loops, checkpoints, retries, and artifact emission.
- **Operators**: modular steps (ingest, chunk, embed, retrieve, sinks) that operate on iterable records.
- **Providers**: wrappers for external services (embeddings), with deterministic local fallbacks for offline mode.
- **Artifacts**: run.json, lineage.jsonl, metrics.json, output files, and errors captured per run.

Reliability features:
- Deterministic doc fingerprints used for checkpointed resume.
- JSON structured logging with PII redaction by default.
- Dead-letter storage under `runs/<run_id>/errors/`.
