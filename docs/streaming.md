# Streaming and Incremental Processing

Use `docetl run pipeline.yaml --stream --watch ./inbox --checkpoint ./state.json` to continuously process new documents. The runner:
- fingerprints each document based on content and skips already processed fingerprints found in the checkpoint file.
- writes checkpoint files after each iteration to allow deterministic resume.
- stores dead-letter errors in `runs/<run_id>/errors/` with context.

Configuration tips:
- Set the ingest operator `path` to the `--watch` folder.
- Use `jsonl_sink` with `path: runs/<run_id>/output.jsonl` to collect results per run.
