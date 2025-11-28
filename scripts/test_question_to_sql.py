"""
Quick manual test for the QuestionToSQL LangGraph node.

Usage:
    python scripts/test_question_to_sql.py
"""

from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "querycraft.settings")

import django  # noqa: E402

django.setup()

from core.services.sql_executor import execute_safe_sql  # noqa: E402
from core.agent.workflow import question_to_sql  # noqa: E402

def test_question_to_sql_simple_select() -> None:
    state = {
        "question": "List the latest 4 customers and their registration dates.",
        "language": "en",
    }
    result = question_to_sql(state)
    print("Generated SQL:\n", result["sql"])


def test_question_to_sql_simple_join() -> None:
    state = {
        "question": "Name of customer with the most orders.",
        "language": "en",
    }
    result = question_to_sql(state)
    print("Generated SQL:\n", result["sql"])


def test_execute_sql_query():
    print(execute_safe_sql("""select * from core_product"""))


if __name__ == "__main__":
    # test_question_to_sql_simple_select()
    # test_question_to_sql_simple_join()
    test_execute_sql_query()