import json
from typing import Any, Dict

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_POST

from core.agent import run_query_agent


def _json_error(message: str, *, status: int = 400, stage: str = "request") -> JsonResponse:
    payload: Dict[str, Any] = {"status": "error", "message": message, "stage": stage}
    return JsonResponse(payload, status=status)


def _parse_request_body(request: HttpRequest) -> Dict[str, Any]:
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON payload.") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON payload must be an object.")
    return data


@require_POST
def query_api(request: HttpRequest) -> JsonResponse:
    """
    Minimal REST endpoint bridging HTTP clients with the LangGraph workflow.
    """

    try:
        payload = _parse_request_body(request)
    except ValueError as exc:
        return _json_error(str(exc))

    question_raw = payload.get("question")
    if question_raw is None:
        return _json_error("`question` is required.")
    if not isinstance(question_raw, str):
        return _json_error("`question` must be a string.")
    question = question_raw.strip()
    if not question:
        return _json_error("`question` is required.")

    language_raw = payload.get("language", "en")
    if not isinstance(language_raw, str):
        return _json_error("`language` must be a string.")
    language = (language_raw or "en").strip() or "en"
    if len(language) > 10:  # guard against unreasonable values passed downstream
        return _json_error("`language` value is too long.")
    max_rows_value = payload.get("max_rows")

    max_rows: int | None = None
    if max_rows_value is not None:
        try:
            max_rows_int = int(max_rows_value)
        except (TypeError, ValueError) as exc:
            return _json_error("`max_rows` must be an integer.")  # pragma: no cover - paranoia
        if max_rows_int <= 0:
            return _json_error("`max_rows` must be greater than zero.")
        max_rows = max_rows_int

    try:
        response = run_query_agent(
            question,
            language=language,
            max_rows=max_rows,
        )
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:  # pragma: no cover - defensive against unexpected errors.
        return _json_error("Internal server error.", status=500, stage="server")

    status_code = 200 if response.get("status") == "ok" else 400
    return JsonResponse(response, status=status_code)
