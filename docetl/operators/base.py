from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List


class Operator(ABC):
    name: str

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config

    @abstractmethod
    def process(self, records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        ...


class PassthroughOperator(Operator):
    def process(self, records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        for record in records:
            yield record
