"""Deterministic stats query endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.api.schemas import QueryResponse
from src.db.models import PlayerGameStats
from src.db.session import get_db
from src.domain.query_plan import QueryPlan

router = APIRouter(prefix="/stats", tags=["stats"])


@router.post("/player-games/query", response_model=QueryResponse)
def query_player_games(plan: QueryPlan, db: Session = Depends(get_db)) -> QueryResponse:
    conditions = []
    if plan.filters.player_ids:
        conditions.append(PlayerGameStats.player_id.in_(plan.filters.player_ids))
    if plan.filters.seasons:
        conditions.append(PlayerGameStats.season.in_(plan.filters.seasons))

    query = select(PlayerGameStats).order_by(PlayerGameStats.game_date.desc()).limit(plan.limit).offset(plan.offset)
    if conditions:
        query = query.where(and_(*conditions))
    rows = db.execute(query).scalars().all()
    payload = [
        {
            "game_id": row.game_id,
            "player_id": row.player_id,
            "game_date": row.game_date.isoformat(),
            "season": row.season,
            "points": float(row.points) if row.points is not None else None,
            "rebounds": float(row.rebounds) if row.rebounds is not None else None,
            "assists": float(row.assists) if row.assists is not None else None,
        }
        for row in rows
    ]
    return QueryResponse(
        applied_filters=plan.filters.model_dump(mode="json"),
        rows=payload,
        summary=f"Returned {len(payload)} player game records.",
        meta={"entity": plan.entity, "source": "deterministic_sql"},
    )


@router.post("/player-aggregate/query", response_model=QueryResponse)
def query_player_aggregate(plan: QueryPlan, db: Session = Depends(get_db)) -> QueryResponse:
    metric = plan.aggregations[0].metric if plan.aggregations else "points"
    op = plan.aggregations[0].op if plan.aggregations else "avg"
    metric_column = getattr(PlayerGameStats, metric, PlayerGameStats.points)

    if op == "sum":
        agg_expr = func.sum(metric_column)
    elif op == "max":
        agg_expr = func.max(metric_column)
    elif op == "min":
        agg_expr = func.min(metric_column)
    else:
        agg_expr = func.avg(metric_column)

    query = select(PlayerGameStats.player_id, agg_expr.label("value")).group_by(PlayerGameStats.player_id)
    if plan.filters.player_ids:
        query = query.where(PlayerGameStats.player_id.in_(plan.filters.player_ids))
    if plan.filters.seasons:
        query = query.where(PlayerGameStats.season.in_(plan.filters.seasons))

    query = query.limit(plan.limit).offset(plan.offset)
    rows = db.execute(query).all()
    payload = [{"player_id": row.player_id, "value": float(row.value) if row.value is not None else None} for row in rows]
    return QueryResponse(
        applied_filters=plan.filters.model_dump(mode="json"),
        rows=payload,
        summary=f"Computed {op} {metric} for {len(payload)} players.",
        meta={"entity": plan.entity, "source": "deterministic_sql"},
    )

