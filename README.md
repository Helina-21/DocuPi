# DocETL

A lightweight, local-first document ETL toolkit for running YAML-defined pipelines with:

- **Streaming execution** (watch a folder and process incrementally)
- **Checkpointing** (skip documents already processed)
- **Vector indexing + retrieval** (FAISS when available, deterministic fallback in dry-run/offline mode)
- **Lineage/provenance** (record-level `lineage.jsonl`)
- **Human review loop** (flag records into a review queue + simple FastAPI review UI)
- **PII-safe logs by default** (redaction unless you explicitly enable debug content)

---

## Why DocETL

DocETL is designed for “document → chunks → embeddings → retrieval → outputs” workflows where you care about:
- reproducibility (content fingerprints + deterministic IDs),
- traceability (lineage per operator),
- operational hygiene (run directories, metrics, dead-letter errors),
- and a minimal human-in-the-loop review path.

---

## Install

```bash
git clone <your-repo-url>
cd <repo>

python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

pip install -r requirements.txt
pip install -e .