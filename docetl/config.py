import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

try:  # pragma: no cover
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def _extract_steps(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "pipeline" in data and isinstance(data["pipeline"], list):
        return data["pipeline"]
    if "steps" in data and isinstance(data["steps"], list):
        return data["steps"]
    if "operations" in data and "pipeline" in data and isinstance(data.get("pipeline"), list):
        ops = data.get("operations", {})
        steps = []
        for name in data.get("pipeline", []):
            op_cfg = ops.get(name)
            if not op_cfg:
                continue
            steps.append({"name": name, **op_cfg})
        return steps
    raise ValueError("Pipeline YAML must include 'steps' or 'pipeline'")


@dataclass
class OperatorConfig:
    name: str
    type: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    name: str
    steps: List[OperatorConfig]
    raw: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.steps:
            raise ValueError("Pipeline requires at least one step")


def load_pipeline(path: Path) -> PipelineConfig:
    content = path.read_text()
    if yaml:
        data = yaml.safe_load(content) or {}
    else:
        data = json.loads(content)
    steps = [OperatorConfig(**s) for s in _extract_steps(data)]
    return PipelineConfig(name=data.get("name", "pipeline"), steps=steps, raw=data)
