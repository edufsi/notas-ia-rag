from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SearchStrategy = Literal["auto", "bm25", "dense", "hybrid"]


class LegalSource(BaseModel):
    chunk_id: str
    document: str
    section: str
    context: str
    text: str
    organization: str
    source_type: str
    jurisdiction: str
    locality: str | None = None
    url: str
    published_at: str
    verified_at: str
    score: float


class LegalSearchResponse(BaseModel):
    query: str
    requested_strategy: SearchStrategy
    effective_strategy: Literal["bm25", "dense", "hybrid"]
    fallback_reason: str | None = None
    corpus_version: str
    results: list[LegalSource] = Field(default_factory=list)

