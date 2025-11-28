import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse


class QueryApiTests(TestCase):
    def _post(self, payload: dict | str):
        data = payload if isinstance(payload, str) else json.dumps(payload)
        return self.client.post(
            reverse("query-api"),
            data=data,
            content_type="application/json",
        )

    @patch("core.views.run_query_agent")
    def test_success_response(self, mock_run_query_agent):
        mock_run_query_agent.return_value = {
            "status": "ok",
            "sql": "SELECT 1",
            "rows": [],
            "columns": [],
        }
        response = self._post({"question": "List customers"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        mock_run_query_agent.assert_called_once()

    @patch("core.views.run_query_agent")
    def test_agent_error_returns_400(self, mock_run_query_agent):
        mock_run_query_agent.return_value = {
            "status": "error",
            "message": "Invalid column",
            "stage": "execute_sql",
        }
        response = self._post({"question": "List customers"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["stage"], "execute_sql")

    def test_missing_question_returns_400(self):
        response = self._post({})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "`question` is required.")

    def test_blank_question_returns_400(self):
        response = self._post({"question": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "`question` is required.")

    def test_non_string_question_returns_400(self):
        response = self._post({"question": 123})

        self.assertEqual(response.status_code, 400)
        self.assertIn("must be a string", response.json()["message"])

    def test_non_string_language_returns_400(self):
        response = self._post({"question": "hi", "language": 42})

        self.assertEqual(response.status_code, 400)
        self.assertIn("`language` must be a string", response.json()["message"])

    def test_language_too_long(self):
        response = self._post({"question": "hi", "language": "x" * 20})

        self.assertEqual(response.status_code, 400)
        self.assertIn("language", response.json()["message"])

    def test_invalid_json_returns_400(self):
        response = self._post("{invalid json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid JSON", response.json()["message"])

    def test_json_must_be_object(self):
        response = self._post("[]")

        self.assertEqual(response.status_code, 400)
        self.assertIn("must be an object", response.json()["message"])

    @patch("core.views.run_query_agent", side_effect=Exception("boom"))
    def test_unexpected_server_error_returns_500(self, mock_run_query_agent):
        response = self._post({"question": "boom"})

        self.assertEqual(response.status_code, 500)
        body = response.json()
        self.assertEqual(body["stage"], "server")
        self.assertEqual(body["status"], "error")
