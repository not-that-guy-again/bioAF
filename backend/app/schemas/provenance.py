from datetime import datetime

from pydantic import BaseModel


class ProvenanceNode(BaseModel):
    entity_type: str
    entity_id: int
    label: str
    timestamp: datetime | None = None
    children: list[int] = []
    metadata: dict = {}


class ProvenanceChain(BaseModel):
    experiment: ProvenanceNode
    samples: list[ProvenanceNode] = []
    fastq_uploads: list[ProvenanceNode] = []
    pipeline_runs: list[ProvenanceNode] = []
    outputs: list[ProvenanceNode] = []
    cellxgene_publications: list[ProvenanceNode] = []
    qc_dashboards: list[ProvenanceNode] = []
