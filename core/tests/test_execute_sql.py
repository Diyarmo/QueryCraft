from unittest.mock import patch

from django.test import SimpleTestCase

from core.agent.workflow import execute_sql


class ExecuteSQLNodeTests(SimpleTestCase):
    @patch("core.agent.workflow.execute_safe_sql")
    def test_execute_sql_populates_rows_and_metadata(self, mock_execute_safe_sql):
        mock_execute_safe_sql.return_value = {
            "sql": "SELECT id FROM customers LIMIT 5",
            "columns": ["id"],
            "rows": [{"id": 1}, {"id": 2}],
        }
        state = {
            "sql": "SELECT id FROM customers",
            "max_rows": 5,
            "metadata": {},
        }

        result = execute_sql(state)

        self.assertEqual(result["sql"], "SELECT id FROM customers LIMIT 5")
        self.assertEqual(result["columns"], ["id"])
        self.assertEqual(result["rows"], [{"id": 1}, {"id": 2}])
        self.assertEqual(result["metadata"]["row_count"], 2)
        self.assertEqual(result["metadata"]["max_rows"], 5)
        self.assertEqual(result["stage"], "execute_sql")
        self.assertIn("execution_ms", result)

    def test_execute_sql_requires_sql(self) -> None:
        with self.assertRaises(ValueError):
            execute_sql({})

    @patch("core.agent.workflow.execute_safe_sql", side_effect=RuntimeError("db down"))
    def test_execute_sql_captures_errors(self, mock_execute_safe_sql) -> None:
        state = {"sql": "SELECT 1"}

        result = execute_sql(state)

        self.assertEqual(result["error_message"], "db down")
        self.assertEqual(result["error_stage"], "execute_sql")
        self.assertEqual(result["stage"], "execute_sql")
