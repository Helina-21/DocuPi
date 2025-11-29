# Human-in-the-loop Review

Launch the review UI for a run:
```
docetl review --run runs/<run_id> --port 8787
```

The FastAPI app serves a simple HTML page backed by `/records` and `/submit` endpoints. Records listed in `runs/<run_id>/needs_review.jsonl` are displayed for certification. Approved entries are appended to `runs/<run_id>/certified.jsonl` with reviewer and timestamp metadata.
