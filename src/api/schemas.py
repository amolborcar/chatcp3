"""Pydantic request and response schemas for API routes."""

from pydantic import BaseModel, Field

from src.domain.query_plan import QueryPlan


class HealthResponse(BaseModel):
    status: str
    service: str


class SearchResult(BaseModel):
    id: int
    name: str
    meta: dict[str, str] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: list[SearchResult]


class QueryResponse(BaseModel):
    applied_filters: dict
    rows: list[dict]
    summary: str
    meta: dict


class ChatQueryRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    ui_filter_context: dict | None = None


class ChatQueryResponse(BaseModel):
    mode: str
    query_plan: QueryPlan | None = None
    clarifications: list[str] = Field(default_factory=list)
    result: QueryResponse | None = None

