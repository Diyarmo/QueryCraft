"""
LangGraph workflow scaffolding for translating natural-language questions into SQL.

The actual node implementations will be filled in subsequent tasks; this module
only wires up the graph structure so downstream work can focus on each node's
logic independently.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

try:  # pragma: no cover - purely for typing compatibility across LangGraph versions.
    from langgraph.graph.graph import CompiledGraph
except Exception:  # noqa: BLE001 - fallback to a generic type when not available.
    CompiledGraph = Any  # type: ignore[assignment]


class QueryState(TypedDict, total=False):
    """
    Shared state that flows through the LangGraph workflow.

    Fields will be populated incrementally by different nodes. Optional typing
    keeps the scaffolding flexible until the concrete implementation lands.
    """

    question: str
    language: str
    sql: str
    validation_error: str
    columns: list[str]
    rows: list[Dict[str, Any]]
    execution_ms: float
    metadata: Dict[str, Any]
    stage: str


def question_to_sql(state: QueryState) -> QueryState:
    """LLM call placeholder that should convert the question into an SQL string."""
    raise NotImplementedError("QuestionToSQL node has not been implemented yet.")


def validate_sql(state: QueryState) -> QueryState:
    """Placeholder for running read-only and safety checks on the SQL text."""
    raise NotImplementedError("ValidateSQL node has not been implemented yet.")


def execute_sql(state: QueryState) -> QueryState:
    """Placeholder for executing validated SQL against Postgres."""
    raise NotImplementedError("ExecuteSQL node has not been implemented yet.")


def format_response(state: QueryState) -> QueryState:
    """Placeholder node that should normalize success/error payloads."""
    raise NotImplementedError("FormatResponse node has not been implemented yet.")


def handle_error(state: QueryState) -> QueryState:
    """
    Placeholder error handler that will format validation issues in later steps.
    """
    raise NotImplementedError("Error handler node has not been implemented yet.")


def _route_validation(state: QueryState) -> Literal["valid", "invalid"]:
    """Conditional edge helper that routes based on validation results."""
    return "invalid" if state.get("validation_error") else "valid"


def _build_graph() -> CompiledGraph:
    graph = StateGraph(QueryState)

    graph.add_node("question_to_sql", question_to_sql)
    graph.add_node("validate_sql", validate_sql)
    graph.add_node("execute_sql", execute_sql)
    graph.add_node("format_response", format_response)
    graph.add_node("error", handle_error)

    graph.set_entry_point("question_to_sql")

    graph.add_edge("question_to_sql", "validate_sql")
    graph.add_conditional_edges(
        "validate_sql",
        _route_validation,
        {
            "valid": "execute_sql",
            "invalid": "error",
        },
    )
    graph.add_edge("execute_sql", "format_response")
    graph.add_edge("error", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()


@lru_cache(maxsize=1)
def get_query_agent() -> CompiledGraph:
    """
    Return a lazily-instantiated compiled LangGraph workflow.

    Using an lru_cache avoids reconstructing the workflow on every request while
    still letting tests reset the state by clearing the cache if needed.
    """

    return _build_graph()
