# Lineage and Provenance

Each run emits `runs/<run_id>/lineage.jsonl` capturing record-level provenance:
- run_id, pipeline_hash, git_sha
- operator name and hashed config
- input doc fingerprint and source URI
- chunk IDs
- timing metadata

Lineage records enable auditing and replay. Extend operator implementations to attach model/provider and validation output when applicable.
