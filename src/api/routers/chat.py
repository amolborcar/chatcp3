"""Chat endpoint with rule-based parsing and deterministic execution path."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.schemas import ChatQueryRequest, ChatQueryResponse
from src.api.routers.stats import query_player_aggregate
from src.db.session import get_db
from src.domain.chat_parser import parse_text_to_query_plan

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/query", response_model=ChatQueryResponse)
def query_chat(request: ChatQueryRequest, db: Session = Depends(get_db)) -> ChatQueryResponse:
    plan, clarifications = parse_text_to_query_plan(request.message)
    if clarifications:
        return ChatQueryResponse(mode="clarification_required", clarifications=clarifications)

    result = query_player_aggregate(plan=plan, db=db)
    return ChatQueryResponse(mode="result", query_plan=plan, result=result)

