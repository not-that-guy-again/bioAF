from typing import Literal

from pydantic import BaseModel


class ProvenanceNode(BaseModel):
    id: str
    type: Literal["experiment", "sample", "pipeline_run", "snapshot", "reference", "file", "project"]
    label: str
    metadata: dict = {}


class ProvenanceEdge(BaseModel):
    source: str
    target: str
    relationship: str


class ProvenanceDAG(BaseModel):
    nodes: list[ProvenanceNode]
    edges: list[ProvenanceEdge]
