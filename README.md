# DocETL

A lightweight document ETL toolkit with streaming execution, checkpointing, vector indexing, lineage emission, and a minimal review loop.

## Quickstart
```
pip install -r requirements.txt
pip install -e .

# Run a sample pipeline
DOCETL_DEBUG=1 docetl run examples/contracts_risk.yaml

# Stream from a folder with checkpointing
docetl run examples/contracts_risk.yaml --stream --watch eval/datasets/sample_contracts/docs --checkpoint state.json

# Launch human review for a run
docetl review --run runs/<run_id>

# Evaluate against sample dataset
docetl eval --pipeline examples/contracts_risk.yaml --dataset eval/datasets/sample_contracts
```

See `docs/` for architecture, lineage, streaming, vector indexing, and review details.
