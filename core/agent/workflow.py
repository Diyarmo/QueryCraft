"""
LangGraph workflow scaffolding for translating natural-language questions into SQL.

The actual node implementations will be filled in subsequent tasks; this module
only wires up the graph structure so downstream work can focus on each node's
logic independently.
"""

from __future__ import annotations

import os
from functools import lru_cache
from time import perf_counter
from typing import Any, Dict, Literal, TypedDict

from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from core.services.sql_executor import (
    DEFAULT_MAX_ROWS,
    SQLValidationError,
    execute_safe_sql,
    sanitize_sql,
)

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
    max_rows: int
    error_message: str
    error_stage: str
    response: Dict[str, Any]


# Preferred ordering for the schema summary so the prompt remains predictable.
SCHEMA_REFERENCE = """
customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    registration_date TIMESTAMPTZ NOT NULL
)

products (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    price BIGINT NOT NULL -- stored in IRR
)

orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    order_date TIMESTAMPTZ NOT NULL,
    quantity INTEGER NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('pending','completed','cancelled','refunded'))
)

"""

SYSTEM_PROMPT = f"""
### Instructions:
Your task is to convert a natural-language analytics question into a SQL query, given a Postgres database schema for an e-commerce system.

Adhere to these rules:
- Only generate a single valid SQL SELECT statement and nothing else.
- **Deliberately go through the question and database schema word by word** to appropriately answer the question
- `order_id`, `product_id` and `customer_id` are not valid. simply use `id`.

### Database Schema:
The query will run on a database whose schema is represented by the following tables:

{SCHEMA_REFERENCE}
"""

USER_PROMPT_TEMPLATE = """### Question
Here is the question: `{question}`.

### Answer
Strictly following the given the database schema and instructions,
here is the SQL query without anyother extra words that answers the question and NO OTHER TEXT AFTER THAT.

```sql
"""



def _get_ollama_base_url() -> str:
    return os.environ.get("OLLAMA_HOST") or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"


def _get_ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "sqlcoder:7b-q4_K_M")


def _get_sqlcoder_client() -> ChatOllama:
    """
    Create a cached ChatOllama instance for calling the sqlcoder model.

    LangGraph nodes are synchronous, so sharing a single client avoids repeated
    handshakes with the Ollama HTTP API while keeping configuration centralized.
    """

    return ChatOllama(
        model=_get_ollama_model(),
        base_url=_get_ollama_base_url(),
        temperature=0,
    )


def _message_to_text(response: Any) -> str:
    # LangChain responses vary (plain string, object with content, or chunk lists),
    # so normalize everything into a single text blob for downstream parsing.
    if response is None:
        return ""

    if hasattr(response, "content"):
        content = response.content
    else:
        content = response

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for chunk in content:
            if isinstance(chunk, dict) and "text" in chunk:
                text_parts.append(chunk["text"])
            else:
                text_parts.append(str(chunk))
        return "".join(text_parts)

    return str(content)


def _strip_sql_code_fences(value: str) -> str:
    # Models often wrap SQL in ``` (sometimes ```sql), so peel those wrappers off.
    cleaned = value.strip()

    if not cleaned.startswith("```"):
        return cleaned

    cleaned = cleaned.lstrip("`")
    if cleaned.lower().startswith("sql"):
        cleaned = cleaned[3:]
    cleaned = cleaned.lstrip("\n")
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def question_to_sql(state: QueryState) -> QueryState:
    """
    Convert the incoming natural-language question into SQL using the sqlcoder model.
    """

    question = (state.get("question") or "").strip()
    if not question:
        raise ValueError("Question text is required for QuestionToSQL node.")

    language = (state.get("language") or "en").strip() or "en"

    llm = _get_sqlcoder_client()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=USER_PROMPT_TEMPLATE.format(
                question=question,
                language=language,
            )
        ),
    ]
    # response = llm.invoke("hi")
    response = llm.invoke(messages)
    sql = _strip_sql_code_fences(_message_to_text(response))
    if not sql:
        raise RuntimeError("The SQL model returned an empty response.")

    updated_state = dict(state)
    updated_state["sql"] = sql
    updated_state["stage"] = "question_to_sql"
    metadata = dict(updated_state.get("metadata") or {})
    metadata["llm_model"] = _get_ollama_model()
    metadata["ollama_base_url"] = _get_ollama_base_url()
    updated_state["metadata"] = metadata

    return updated_state


def validate_sql(state: QueryState) -> QueryState:
    """
    Ensure the generated SQL is a single safe SELECT statement with a reasonable LIMIT.
    """

    sql = (state.get("sql") or "").strip()
    if not sql:
        raise ValueError("SQL text is required for validation.")

    max_rows = state.get("max_rows") or DEFAULT_MAX_ROWS
    try:
        max_rows_int = int(max_rows)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive path
        raise ValueError("max_rows must be an integer.") from exc

    updated_state = dict(state)
    try:
        sanitized = sanitize_sql(sql, max_rows_int)
    except SQLValidationError as exc:
        updated_state["validation_error"] = str(exc)
        updated_state["stage"] = "validate_sql"
        return updated_state

    updated_state["sql"] = sanitized
    updated_state.pop("validation_error", None)
    updated_state["stage"] = "validate_sql"

    metadata = dict(updated_state.get("metadata") or {})
    metadata["max_rows"] = max_rows_int
    updated_state["metadata"] = metadata

    return updated_state


def execute_sql(state: QueryState) -> QueryState:
    """
    Execute the sanitized SQL against Postgres and capture result metadata.
    """

    sql = (state.get("sql") or "").strip()
    if not sql:
        raise ValueError("SQL text is required for execution.")

    max_rows = state.get("max_rows") or DEFAULT_MAX_ROWS
    start = perf_counter()
    result = execute_safe_sql(sql, max_rows=max_rows)
    elapsed_ms = (perf_counter() - start) * 1000

    updated_state = dict(state)
    updated_state["sql"] = result.get("sql", sql)
    updated_state["columns"] = result.get("columns", [])
    updated_state["rows"] = result.get("rows", [])
    updated_state["execution_ms"] = elapsed_ms
    updated_state["stage"] = "execute_sql"

    metadata = dict(updated_state.get("metadata") or {})
    metadata.setdefault("max_rows", max_rows)
    metadata["row_count"] = len(updated_state["rows"])
    metadata["execution_ms"] = elapsed_ms
    updated_state["metadata"] = metadata

    return updated_state


def format_response(state: QueryState) -> QueryState:
    """
    Normalize the workflow output into a consistent payload for downstream consumers.
    """

    updated_state = dict(state)
    metadata = dict(updated_state.get("metadata") or {})
    error_message = updated_state.get("error_message") or updated_state.get("validation_error")
    is_error = bool(error_message) or updated_state.get("stage") == "error"

    if is_error:
        response = {
            "status": "error",
            "message": error_message or "An unknown error occurred.",
            "stage": updated_state.get("error_stage") or updated_state.get("stage") or "unknown",
        }
        if metadata:
            response["metadata"] = metadata
    else:
        response = {
            "status": "ok",
            "sql": updated_state.get("sql"),
            "columns": updated_state.get("columns") or [],
            "rows": updated_state.get("rows") or [],
            "execution_ms": updated_state.get("execution_ms"),
        }
        if metadata:
            response["metadata"] = metadata

    updated_state["response"] = response
    updated_state["stage"] = "format_response"
    return updated_state


def handle_error(state: QueryState) -> QueryState:
    """
    Capture validation/execution issues and prepare the state for the format node.
    """

    failure_stage = state.get("stage") or "unknown"
    message = state.get("validation_error") or state.get("error_message") or "An unknown error occurred."
    updated_state = dict(state)
    updated_state["error_message"] = message
    updated_state["error_stage"] = failure_stage
    updated_state["stage"] = "error"
    return updated_state


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
