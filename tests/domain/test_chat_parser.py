from src.domain.chat_parser import parse_text_to_query_plan


def test_parse_text_to_query_plan_success():
    plan, clarifications = parse_text_to_query_plan("average points for 2024-25")
    assert clarifications == []
    assert plan is not None
    assert plan.aggregations[0].op == "avg"
    assert plan.aggregations[0].metric == "points"
    assert plan.filters.seasons == ["2024-25"]


def test_parse_text_to_query_plan_clarification():
    plan, clarifications = parse_text_to_query_plan("show me stuff")
    assert plan is None
    assert len(clarifications) > 0

