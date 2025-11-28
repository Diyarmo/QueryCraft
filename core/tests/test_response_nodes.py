from django.test import SimpleTestCase

from core.agent.workflow import format_response, handle_error


class ResponseNodeTests(SimpleTestCase):
    def test_handle_error_preserves_failure_stage_and_message(self) -> None:
        state = {
            "stage": "validate_sql",
            "validation_error": "Only SELECT statements are permitted.",
        }

        result = handle_error(state)

        self.assertEqual(result["error_stage"], "validate_sql")
        self.assertEqual(result["error_message"], "Only SELECT statements are permitted.")
        self.assertEqual(result["stage"], "error")

    def test_format_response_success_payload(self) -> None:
        state = {
            "sql": "SELECT id FROM customers LIMIT 5",
            "columns": ["id"],
            "rows": [{"id": 1}],
            "execution_ms": 12.5,
            "metadata": {"max_rows": 5},
            "stage": "execute_sql",
        }

        result = format_response(state)
        payload = result["response"]

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["sql"], "SELECT id FROM customers LIMIT 5")
        self.assertEqual(payload["columns"], ["id"])
        self.assertEqual(payload["rows"], [{"id": 1}])
        self.assertEqual(payload["execution_ms"], 12.5)
        self.assertEqual(payload["metadata"], {"max_rows": 5})
        self.assertEqual(result["stage"], "format_response")

    def test_format_response_error_payload(self) -> None:
        state = {
            "error_message": "Database timeout",
            "error_stage": "execute_sql",
            "metadata": {"max_rows": 5},
            "stage": "error",
        }

        result = format_response(state)
        payload = result["response"]

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["message"], "Database timeout")
        self.assertEqual(payload["stage"], "execute_sql")
        self.assertEqual(payload["metadata"], {"max_rows": 5})
