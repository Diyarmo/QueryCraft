from unittest.mock import patch

from django.test import SimpleTestCase

from core.agent.workflow import run_query_agent


class RunQueryAgentTests(SimpleTestCase):
    @patch("core.agent.workflow.get_query_agent")
    def test_invokes_graph_with_expected_state(self, mock_get_agent) -> None:
        class DummyGraph:
            def __init__(self) -> None:
                self.state = None
                self.config = None

            def invoke(self, state):
                self.state = state
                return {
                    "response": {
                        "status": "ok",
                        "sql": "SELECT 1",
                        "rows": [],
                        "columns": [],
                        "execution_ms": 1.0,
                    }
                }

        dummy = DummyGraph()
        mock_get_agent.return_value = dummy

        response = run_query_agent(
            "List customers",
            language="fa",
            max_rows=25,
            metadata={"foo": "bar"},
        )

        self.assertEqual(response["status"], "ok")
        self.assertEqual(dummy.state["question"], "List customers")
        self.assertEqual(dummy.state["language"], "fa")
        self.assertEqual(dummy.state["max_rows"], 25)
        self.assertEqual(dummy.state["metadata"], {"foo": "bar"})

    @patch("core.agent.workflow.get_query_agent")
    def test_missing_response_falls_back_to_simple_payload(self, mock_get_agent) -> None:
        class DummyGraph:
            def invoke(self, state):
                return {
                    "sql": "SELECT 1",
                    "rows": [],
                    "columns": [],
                    "metadata": {"foo": "bar"},
                }

        mock_get_agent.return_value = DummyGraph()

        response = run_query_agent("ping")

        self.assertEqual(response["sql"], "SELECT 1")
        self.assertEqual(response["metadata"], {"foo": "bar"})

    def test_blank_question_raises(self) -> None:
        with self.assertRaises(ValueError):
            run_query_agent("   ")
