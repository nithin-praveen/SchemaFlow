"""Unit tests for the SQL Query Pipeline execution simulator."""

import pytest
from core.query_pipeline import simulate_query_pipeline, PRESET_QUERIES, CANONICAL_EMP_DATASET


def test_preset_queries_simulate_successfully():
    """All preset queries should execute without error and return expected steps."""
    for p in PRESET_QUERIES:
        res = simulate_query_pipeline(p["sql"])
        assert res["total_steps"] >= 3
        assert len(res["steps"]) == res["total_steps"]
        assert res["steps"][0]["clause"] == "FROM"
        assert res["final_row_count"] > 0
        assert "┌" in res["final_ascii_table"]


def test_where_clause_filters_tuples():
    """WHERE clause must accurately filter rows and populate status."""
    sql = "SELECT emp_name, salary FROM emp WHERE salary >= 70000;"
    res = simulate_query_pipeline(sql)
    # Expected salaries >= 70000: Aditi Rao (75000), Priya Nair (95000), Sneha Roy (72000) -> 3 rows
    assert res["final_row_count"] == 3
    where_step = next(s for s in res["steps"] if s["clause"] == "WHERE")
    assert where_step["output_count"] == 3
    assert where_step["input_count"] == 8


def test_group_by_having_pipeline():
    """GROUP BY and HAVING steps must correctly partition and filter groups."""
    sql = "SELECT dept, COUNT(*) AS cnt FROM emp GROUP BY dept HAVING COUNT(*) >= 2;"
    res = simulate_query_pipeline(sql)
    clauses = [s["clause"] for s in res["steps"]]
    assert clauses == ["FROM", "GROUP BY", "HAVING", "SELECT"]
    # Depts with >= 2 emps: Engineering (3), Marketing (2), Sales (2) -> 3 groups
    assert res["final_row_count"] == 3


def test_order_by_and_limit():
    """ORDER BY and LIMIT must sort and slice output cardinality."""
    sql = "SELECT emp_name, salary FROM emp ORDER BY salary DESC LIMIT 2;"
    res = simulate_query_pipeline(sql)
    assert res["final_row_count"] == 2
    # Top 2 salaries should be 95000 and 75000
    top_salaries = [r["salary"] for r in res["steps"][-1]["rows"]]
    assert top_salaries == [95000, 75000]


def test_invalid_query_raises_syntax_error():
    """Non-SELECT or malformed queries should raise ValueError."""
    with pytest.raises(ValueError) as exc:
        simulate_query_pipeline("INSERT INTO emp VALUES (1, 'Test');")
    assert "SELECT" in str(exc.value)

    with pytest.raises(ValueError):
        simulate_query_pipeline("SELECT FROM broken WHERE;")

