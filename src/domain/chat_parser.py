"""Very small rule-based parser for budget-mode chat queries."""

import re

from src.domain.query_plan import AggregationSpec, EntityType, FilterSpec, QueryPlan

_METRIC_TOKENS = {
    "points": "points",
    "assists": "assists",
    "rebounds": "rebounds",
    "steals": "steals",
    "blocks": "blocks",
}

_AGG_TOKENS = {
    "average": "avg",
    "avg": "avg",
    "sum": "sum",
    "total": "sum",
    "max": "max",
    "min": "min",
}


def parse_text_to_query_plan(message: str) -> tuple[QueryPlan | None, list[str]]:
    """
    Parse free text into a constrained query plan.

    Returns `(query_plan, clarifications)` where only one is populated.
    """

    lowered = message.lower().strip()
    if not lowered:
        return None, ["What player or team do you want stats for?"]

    metrics = [metric for token, metric in _METRIC_TOKENS.items() if token in lowered]
    if not metrics:
        return None, ["Which metric do you want (points, assists, rebounds, steals, or blocks)?"]

    agg = "avg"
    for token, op in _AGG_TOKENS.items():
        if re.search(rf"\b{re.escape(token)}\b", lowered):
            agg = op
            break

    seasons = re.findall(r"\b20\d{2}-\d{2}\b", lowered)
    filters = FilterSpec(seasons=seasons)
    plan = QueryPlan(
        entity=EntityType.PLAYER_AGGREGATE,
        metrics=metrics,
        aggregations=[AggregationSpec(metric=metrics[0], op=agg, alias=f"{agg}_{metrics[0]}")],
        dimensions=["player_id"],
        filters=filters,
        limit=50,
    )
    return plan, []

