import json
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


def load_queue(run_dir: Path) -> List[dict]:
    queue_path = run_dir / "needs_review.jsonl"
    if not queue_path.exists():
        return []
    return [json.loads(line) for line in queue_path.read_text().splitlines() if line.strip()]


def append_certified(run_dir: Path, record: dict, reviewer: str):
    target = run_dir / "certified.jsonl"
    record["reviewer"] = reviewer
    record["reviewed_at"] = datetime.utcnow().isoformat() + "Z"
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


class ReviewRequest(BaseModel):
    record: dict
    reviewer: str


def create_app(run_dir: Path) -> FastAPI:
    app = FastAPI(title="DocETL Review")

    @app.get("/")
    def index():
        html = (run_dir / "artifacts" / "review.html").read_text()
        return HTMLResponse(html)

    @app.get("/records")
    def records():
        return {"items": load_queue(run_dir)}

    @app.post("/submit")
    def submit(payload: ReviewRequest):
        if not payload.record:
            raise HTTPException(status_code=400, detail="record required")
        append_certified(run_dir, payload.record, payload.reviewer)
        return {"status": "ok"}

    return app


def build_static_page(run_dir: Path):
    html = """
    <!doctype html>
    <html><head><title>DocETL Review</title></head>
    <body>
    <h2>Review Queue</h2>
    <div id="records"></div>
    <script>
    async function loadRecords(){
      const res = await fetch('/records');
      const data = await res.json();
      const container = document.getElementById('records');
      container.innerHTML = '';
      data.items.forEach((item, idx)=>{
        const div = document.createElement('div');
        div.innerHTML = `<pre>${JSON.stringify(item, null, 2)}</pre>`;
        const reviewer = document.createElement('input');
        reviewer.placeholder = 'Reviewer name';
        const btn = document.createElement('button');
        btn.innerText = 'Certify';
        btn.onclick = async ()=>{
            await fetch('/submit', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({record:item, reviewer: reviewer.value || 'anon'})});
            alert('Saved');
        }
        div.appendChild(reviewer);
        div.appendChild(btn);
        container.appendChild(div);
      });
    }
    loadRecords();
    </script>
    </body></html>
    """
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "review.html").write_text(html)


def launch_review(run_dir: Path, port: int = 8787):
    build_static_page(run_dir)
    app = create_app(run_dir)
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)
