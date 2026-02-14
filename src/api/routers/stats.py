"""Deterministic stats query endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.orm import Session

from src.api.schemas import QueryResponse
from src.core.config import get_settings
from src.db.models import PlayerGameStats
from src.db.session import get_db
from src.domain.query_plan import AggregationSpec, QueryPlan

router = APIRouter(prefix="/stats", tags=["stats"])
ALLOWED_METRICS = {
    "points": PlayerGameStats.points,
    "assists": PlayerGameStats.assists,
    "rebounds": PlayerGameStats.rebounds,
    "steals": PlayerGameStats.steals,
    "blocks": PlayerGameStats.blocks,
    "turnovers": PlayerGameStats.turnovers,
    "minutes": PlayerGameStats.minutes,
    "fg_pct": PlayerGameStats.fg_pct,
    "fg3_pct": PlayerGameStats.fg3_pct,
    "ft_pct": PlayerGameStats.ft_pct,
    "plus_minus": PlayerGameStats.plus_minus,
}
ALLOWED_OPS = {"avg", "sum", "max", "min"}
GROUPABLE_DIMENSIONS = {
    "player_id": PlayerGameStats.player_id,
    "team_id": PlayerGameStats.team_id,
    "opponent_team_id": PlayerGameStats.opponent_team_id,
    "season": PlayerGameStats.season,
}
PLAYER_GAME_SORTABLE_FIELDS = {**ALLOWED_METRICS, **GROUPABLE_DIMENSIONS, "game_date": PlayerGameStats.game_date}
AGGREGATE_SORTABLE_FIELDS = {**GROUPABLE_DIMENSIONS, "value": None}


def _validate_metrics(metrics: list[str]) -> None:
    invalid_metrics = [metric for metric in metrics if metric not in ALLOWED_METRICS]
    if invalid_metrics:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported metrics: {', '.join(sorted(set(invalid_metrics)))}",
        )


def _validate_aggregations(aggregations: list[AggregationSpec]) -> None:
    for aggregation in aggregations:
        if aggregation.metric not in ALLOWED_METRICS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported aggregation metric: {aggregation.metric}",
            )
        if aggregation.op not in ALLOWED_OPS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported aggregation op: {aggregation.op}",
            )


def _validate_dimensions(dimensions: list[str]) -> None:
    invalid_dimensions = [dimension for dimension in dimensions if dimension not in GROUPABLE_DIMENSIONS]
    if invalid_dimensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported dimensions: {', '.join(sorted(set(invalid_dimensions)))}",
        )


def _validate_sort_fields(sort_specs, allowed_fields: set[str]) -> None:
    invalid_sort_fields = [sort_spec.field for sort_spec in sort_specs if sort_spec.field not in allowed_fields]
    if invalid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported sort fields: {', '.join(sorted(set(invalid_sort_fields)))}",
        )


def _build_filter_conditions(plan: QueryPlan) -> list:
    filters = plan.filters
    conditions = []
    if filters.player_ids:
        conditions.append(PlayerGameStats.player_id.in_(filters.player_ids))
    if filters.team_ids:
        conditions.append(PlayerGameStats.team_id.in_(filters.team_ids))
    if filters.opponent_team_ids:
        conditions.append(PlayerGameStats.opponent_team_id.in_(filters.opponent_team_ids))
    if filters.seasons:
        conditions.append(PlayerGameStats.season.in_(filters.seasons))
    if filters.season_type != "any":
        conditions.append(PlayerGameStats.season_type == filters.season_type.value)
    if filters.date_from:
        conditions.append(PlayerGameStats.game_date >= filters.date_from)
    if filters.date_to:
        conditions.append(PlayerGameStats.game_date <= filters.date_to)
    if filters.home_away == "home":
        conditions.append(PlayerGameStats.is_home.is_(True))
    if filters.home_away == "away":
        conditions.append(PlayerGameStats.is_home.is_(False))
    if filters.started_only:
        conditions.append(PlayerGameStats.started.is_(True))
    if filters.min_minutes > 0:
        conditions.append(PlayerGameStats.minutes >= filters.min_minutes)
    if filters.game_result == "win":
        conditions.append(PlayerGameStats.win.is_(True))
    if filters.game_result == "loss":
        conditions.append(PlayerGameStats.win.is_(False))
    return conditions


def _apply_sorting(base_query, sort_specs, field_mapping: dict[str, object], default_sort):
    order_clauses = []
    for sort_spec in sort_specs:
        col = field_mapping.get(sort_spec.field)
        if col is None:
            continue
        order_clauses.append(asc(col) if sort_spec.direction == "asc" else desc(col))
    if not order_clauses:
        order_clauses = [default_sort]
    return base_query.order_by(*order_clauses)


@router.post("/player-games/query", response_model=QueryResponse)
def query_player_games(plan: QueryPlan, db: Session = Depends(get_db)) -> QueryResponse:
    settings = get_settings()
    _validate_metrics(plan.metrics)
    _validate_aggregations(plan.aggregations)
    _validate_dimensions(plan.dimensions)
    _validate_sort_fields(plan.sort, set(PLAYER_GAME_SORTABLE_FIELDS))
    conditions = _build_filter_conditions(plan)
    capped_limit = min(plan.limit, settings.max_limit)

    query = select(PlayerGameStats)
    if conditions:
        query = query.where(and_(*conditions))
    query = _apply_sorting(
        base_query=query,
        sort_specs=plan.sort,
        field_mapping=PLAYER_GAME_SORTABLE_FIELDS,
        default_sort=desc(PlayerGameStats.game_date),
    )
    query = query.limit(capped_limit).offset(plan.offset)
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
    settings = get_settings()
    _validate_metrics(plan.metrics)
    _validate_aggregations(plan.aggregations)
    _validate_dimensions(plan.dimensions)
    _validate_sort_fields(plan.sort, set(AGGREGATE_SORTABLE_FIELDS))
    metric = plan.aggregations[0].metric if plan.aggregations else "points"
    op = plan.aggregations[0].op if plan.aggregations else "avg"
    metric_column = ALLOWED_METRICS[metric]

    if op == "sum":
        agg_expr = func.sum(metric_column)
    elif op == "max":
        agg_expr = func.max(metric_column)
    elif op == "min":
        agg_expr = func.min(metric_column)
    else:
        agg_expr = func.avg(metric_column)

    group_columns = []
    for dim in plan.dimensions:
        col = GROUPABLE_DIMENSIONS.get(dim)
        if col is not None:
            group_columns.append(col)
    if not group_columns:
        group_columns = [PlayerGameStats.player_id]

    query = select(*group_columns, agg_expr.label("value"))
    conditions = _build_filter_conditions(plan)
    if conditions:
        query = query.where(and_(*conditions))
    query = query.group_by(*group_columns)
    query = _apply_sorting(
        base_query=query,
        sort_specs=plan.sort,
        field_mapping={**GROUPABLE_DIMENSIONS, "value": agg_expr},
        default_sort=desc(agg_expr),
    )
    query = query.limit(min(plan.limit, settings.max_limit)).offset(plan.offset)
    rows = db.execute(query).all()
    payload = []
    for row in rows:
        mapping = row._mapping
        value = mapping.get("value")
        row_payload = {"value": float(value) if value is not None else None}
        for dim in GROUPABLE_DIMENSIONS:
            if dim in mapping:
                row_payload[dim] = mapping.get(dim)
        payload.append(row_payload)
    return QueryResponse(
        applied_filters=plan.filters.model_dump(mode="json"),
        rows=payload,
        summary=f"Computed {op} {metric} for {len(payload)} players.",
        meta={"entity": plan.entity, "source": "deterministic_sql"},
    )


@router.post("/team-aggregate/query", response_model=QueryResponse)
def query_team_aggregate(plan: QueryPlan, db: Session = Depends(get_db)) -> QueryResponse:
    settings = get_settings()
    _validate_metrics(plan.metrics)
    _validate_aggregations(plan.aggregations)
    _validate_dimensions(plan.dimensions)
    _validate_sort_fields(plan.sort, set(AGGREGATE_SORTABLE_FIELDS))
    metric = plan.aggregations[0].metric if plan.aggregations else "points"
    op = plan.aggregations[0].op if plan.aggregations else "avg"
    metric_column = ALLOWED_METRICS[metric]

    if op == "sum":
        agg_expr = func.sum(metric_column)
    elif op == "max":
        agg_expr = func.max(metric_column)
    elif op == "min":
        agg_expr = func.min(metric_column)
    else:
        agg_expr = func.avg(metric_column)

    query = select(PlayerGameStats.team_id, agg_expr.label("value"))
    conditions = _build_filter_conditions(plan)
    if conditions:
        query = query.where(and_(*conditions))
    query = query.group_by(PlayerGameStats.team_id)
    query = _apply_sorting(
        base_query=query,
        sort_specs=plan.sort,
        field_mapping={"team_id": PlayerGameStats.team_id, "value": agg_expr},
        default_sort=desc(agg_expr),
    )
    query = query.limit(min(plan.limit, settings.max_limit)).offset(plan.offset)
    rows = db.execute(query).all()
    payload = [{"team_id": row.team_id, "value": float(row.value) if row.value is not None else None} for row in rows]
    return QueryResponse(
        applied_filters=plan.filters.model_dump(mode="json"),
        rows=payload,
        summary=f"Computed {op} {metric} for {len(payload)} teams.",
        meta={"entity": plan.entity, "source": "deterministic_sql"},
    )


@router.post("/leaderboard/query", response_model=QueryResponse)
def query_leaderboard(plan: QueryPlan, db: Session = Depends(get_db)) -> QueryResponse:
    """
    Leaderboard is a constrained aggregate grouped by player_id.
    """
    leaderboard_plan = plan.model_copy(deep=True)
    if not leaderboard_plan.dimensions:
        leaderboard_plan.dimensions = ["player_id"]
    if not leaderboard_plan.aggregations:
        leaderboard_plan.aggregations = [AggregationSpec(metric="points", op="avg", alias="avg_points")]
    return query_player_aggregate(leaderboard_plan, db)
