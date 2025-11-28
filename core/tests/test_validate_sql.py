from django.test import SimpleTestCase

from core.agent.workflow import validate_sql
from core.services.sql_executor import DEFAULT_MAX_ROWS


class ValidateSQLNodeTests(SimpleTestCase):
    def test_valid_sql_gets_sanitized_and_metadata(self) -> None:
        state = {
            "sql": "SELECT id, name FROM customers",
            "max_rows": 5,
            "metadata": {},
        }

        result = validate_sql(state)

        self.assertEqual(
            result["sql"],
            "SELECT id, name FROM customers LIMIT 5",
        )
        self.assertNotIn("validation_error", result)
        self.assertEqual(result["stage"], "validate_sql")
        self.assertEqual(result["metadata"]["max_rows"], 5)

    def test_existing_limit_is_respected_when_under_cap(self) -> None:
        state = {
            "sql": "SELECT id FROM customers LIMIT 10",
            "max_rows": 50,
        }

        result = validate_sql(state)

        self.assertEqual(result["sql"], "SELECT id FROM customers LIMIT 10")
        self.assertNotIn("validation_error", result)

    def test_invalid_sql_sets_validation_error(self) -> None:
        state = {"sql": "DELETE FROM customers"}

        result = validate_sql(state)

        self.assertIn("validation_error", result)
        self.assertEqual(result["stage"], "validate_sql")

    def test_limit_exceeding_max_sets_validation_error(self) -> None:
        state = {
            "sql": "SELECT id FROM customers LIMIT 9999",
            "max_rows": 100,
        }

        result = validate_sql(state)

        self.assertIn("validation_error", result)
        self.assertEqual(result["stage"], "validate_sql")

    def test_default_max_rows_is_used_when_missing(self) -> None:
        state = {
            "sql": "SELECT id FROM customers",
        }

        result = validate_sql(state)

        self.assertEqual(
            result["sql"],
            f"SELECT id FROM customers LIMIT {DEFAULT_MAX_ROWS}",
        )
        self.assertEqual(result["metadata"]["max_rows"], DEFAULT_MAX_ROWS)
