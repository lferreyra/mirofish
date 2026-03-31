from pydantic import BaseModel
from src.models.source_data import CollectedSources


class Entity(BaseModel):
    name: str
    type: str  # "person" | "organization" | "location"
    mention_count: int = 0
    sources: list[str] = []


class TimelineEvent(BaseModel):
    date: str
    event: str
    source: str
    confidence: str = "medium"  # "high" | "medium" | "low"


class ResearchResult(BaseModel):
    topic: str
    topic_classification: list[str]
    collected_at: str
    sources: CollectedSources
    entities: list[Entity] = []
    timeline: list[TimelineEvent] = []
