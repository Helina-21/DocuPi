# Vector Indexing

DocETL provides FAISS-backed vector storage via the `embed` and `retrieve` operators.
- `embed` generates embeddings using OpenAI if configured or deterministic local vectors when offline.
- Metadata for each chunk is stored alongside vector positions for auditable retrieval.
- Index files and metadata are persisted under `runs/<run_id>/artifacts/index.faiss` and `.meta.json`.

Example operator configuration:
```
- name: chunk
  type: chunk
  config:
    size: 800
    overlap: 120
- name: embed
  type: embed
  config:
```
