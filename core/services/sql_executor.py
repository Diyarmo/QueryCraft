import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Sequence, Tuple

from django.db import connection, transaction


class SQLValidationError(ValueError):
    """Raised when a raw SQL statement fails safety checks."""
LIMIT_REGEX = re.compile(r"\blimit\s+(\d+)\b", re.IGNORECASE)
DEFAULT_MAX_ROWS = 200


def _ensure_select_statement(sql: str) -> str:
    if not sql or not sql.strip():
        raise SQLValidationError("SQL text cannot be empty.")

    cleaned = sql.strip().rstrip(";")
    lowered = cleaned.lower()

    if not lowered.startswith("select"):
        raise SQLValidationError("Only SELECT statements are permitted.")

    if ";" in cleaned:
        raise SQLValidationError("Multiple SQL statements are not allowed.")

    return cleaned


def _enforce_limit(sql: str, max_rows: int) -> str:
    match = LIMIT_REGEX.search(sql)
    if match:
        limit_value = int(match.group(1))
        if limit_value > max_rows:
            raise SQLValidationError(
                f"Queries are limited to {max_rows} rows; requested {limit_value}."
            )
        return sql

    return f"{sql} LIMIT {max_rows}"


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def execute_safe_sql(
    sql: str, params: Sequence[Any] | None = None, max_rows: int = DEFAULT_MAX_ROWS
) -> Dict[str, Any]:
    """
    Validate and execute a read-only SQL query, returning rows plus metadata.
    """
    if max_rows <= 0:
        raise ValueError("max_rows must be a positive integer.")

    sanitized = _enforce_limit(_ensure_select_statement(sql), max_rows)
    params = params or None

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY;")
            cursor.execute(sanitized, params)
            columns = [col[0] for col in cursor.description or []]
            rows = [
                {col: _serialize_value(val) for col, val in zip(columns, row)}
                for row in cursor.fetchall()
            ]

    return {"columns": columns, "rows": rows, "sql": sanitized}
