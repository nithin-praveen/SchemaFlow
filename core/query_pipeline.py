"""Deterministic SQL Query Pipeline Execution Simulator for SchemaFlow.

Simulates the physical order of execution of SQL SELECT queries:
1. FROM (Read canonical dataset tuples into working memory)
2. WHERE (Evaluate tuple-level boolean filter predicates)
3. GROUP BY (Bucket tuples into groups by grouping keys)
4. HAVING (Evaluate group-level aggregate predicates)
5. SELECT (Project expressions, calculate aggregates, apply aliases)
6. ORDER BY (Sort result rows by specified columns/expressions)
7. LIMIT / OFFSET (Slice final result set cardinality)

Operates 100% deterministically on the canonical 8-row benchmark dataset.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import sqlglot
from sqlglot import exp


# Canonical benchmark dataset (emp table)
CANONICAL_EMP_DATASET: List[Dict[str, Any]] = [
    {"emp_id": 101, "emp_name": "Aditi Rao", "dept": "ENGINEERING", "job": "DEV", "salary": 75000, "hire_date": "2021-03-15"},
    {"emp_id": 102, "emp_name": "Rohan Sharma", "dept": "MARKETING", "job": "ANALYST", "salary": 45000, "hire_date": "2022-06-10"},
    {"emp_id": 103, "emp_name": "Priya Nair", "dept": "ENGINEERING", "job": "LEAD", "salary": 95000, "hire_date": "2020-01-20"},
    {"emp_id": 104, "emp_name": "Vikram Das", "dept": "SALES", "job": "EXECUTIVE", "salary": 42000, "hire_date": "2023-02-01"},
    {"emp_id": 105, "emp_name": "Ananya Patel", "dept": "MARKETING", "job": "MANAGER", "salary": 68000, "hire_date": "2019-11-12"},
    {"emp_id": 106, "emp_name": "Karan Verma", "dept": "ENGINEERING", "job": "DEV", "salary": 60000, "hire_date": "2022-09-05"},
    {"emp_id": 107, "emp_name": "Sneha Roy", "dept": "SALES", "job": "MANAGER", "salary": 72000, "hire_date": "2021-07-18"},
    {"emp_id": 108, "emp_name": "Devendra Jha", "dept": "HR", "job": "RECRUITER", "salary": 38000, "hire_date": "2023-08-25"},
]

PRESET_QUERIES = [
    {
        "id": "preset_full",
        "title": "Full Pipeline (WHERE + GROUP BY + HAVING + ORDER BY)",
        "description": "Standard university DBMS exam query filtering high-earners, grouping by department, filtering groups with HAVING, and sorting.",
        "sql": "SELECT dept, COUNT(*) AS total_emps, MAX(salary) AS top_sal FROM emp WHERE salary >= 45000 GROUP BY dept HAVING COUNT(*) >= 2 ORDER BY top_sal DESC;"
    },
    {
        "id": "preset_filter_sort",
        "title": "Filter & Sort (WHERE + ORDER BY)",
        "description": "Demonstrates tuple filtering row-by-row and deterministic descending sort.",
        "sql": "SELECT emp_name, dept, salary FROM emp WHERE salary >= 60000 ORDER BY salary DESC;"
    },
    {
        "id": "preset_group_agg",
        "title": "Department Statistics (GROUP BY + Aggregates)",
        "description": "Demonstrates row bucketing and multi-aggregate calculation (COUNT, AVG, MAX).",
        "sql": "SELECT dept, COUNT(*) AS emp_count, AVG(salary) AS avg_sal, MAX(salary) AS max_sal FROM emp GROUP BY dept;"
    },
    {
        "id": "preset_limit_slice",
        "title": "Top-Earners Slice (ORDER BY + LIMIT)",
        "description": "Demonstrates sorting and cardinality slicing with LIMIT clause.",
        "sql": "SELECT emp_name, dept, salary FROM emp ORDER BY salary DESC LIMIT 3;"
    }
]


def render_ascii_table(rows: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> str:
    """Renders a list of row dictionaries as a monospace Unicode box table."""
    if not rows:
        return "(0 rows returned)"

    if columns is None:
        columns = list(rows[0].keys())

    str_rows: List[Dict[str, str]] = []
    for r in rows:
        str_rows.append({col: str(r.get(col, "")) for col in columns})

    col_widths = {col: max(len(col), max(len(r[col]) for r in str_rows)) for col in columns}
    for col in col_widths:
        col_widths[col] += 2

    top_line = "┌" + "┬".join("─" * col_widths[c] for c in columns) + "┐"
    header_line = "│" + "│".join(f" {c} ".ljust(col_widths[c]) for c in columns) + "│"
    sep_line = "├" + "┼".join("─" * col_widths[c] for c in columns) + "┤"
    bottom_line = "└" + "┴".join("─" * col_widths[c] for c in columns) + "┘"

    data_lines = []
    for r in str_rows:
        line = "│" + "│".join(f" {r[c]} ".ljust(col_widths[c]) for c in columns) + "│"
        data_lines.append(line)

    return "\n".join([top_line, header_line, sep_line] + data_lines + [bottom_line])


def eval_expr_on_row(node: exp.Expression, row: Dict[str, Any]) -> Any:
    """Evaluates an AST expression against a row dictionary."""
    if isinstance(node, exp.Column):
        col_name = node.name.lower()
        for k, v in row.items():
            if k.lower() == col_name:
                return v
        return None
    elif isinstance(node, exp.Literal):
        if node.is_int:
            return int(node.this)
        if node.is_number:
            return float(node.this)
        return node.this
    elif isinstance(node, exp.GTE):
        l_val = eval_expr_on_row(node.left, row)
        r_val = eval_expr_on_row(node.right, row)
        return l_val is not None and r_val is not None and l_val >= r_val
    elif isinstance(node, exp.LTE):
        l_val = eval_expr_on_row(node.left, row)
        r_val = eval_expr_on_row(node.right, row)
        return l_val is not None and r_val is not None and l_val <= r_val
    elif isinstance(node, exp.GT):
        l_val = eval_expr_on_row(node.left, row)
        r_val = eval_expr_on_row(node.right, row)
        return l_val is not None and r_val is not None and l_val > r_val
    elif isinstance(node, exp.LT):
        l_val = eval_expr_on_row(node.left, row)
        r_val = eval_expr_on_row(node.right, row)
        return l_val is not None and r_val is not None and l_val < r_val
    elif isinstance(node, exp.EQ):
        l_val = eval_expr_on_row(node.left, row)
        r_val = eval_expr_on_row(node.right, row)
        if l_val is None or r_val is None:
            return l_val == r_val
        if isinstance(l_val, (int, float)) and isinstance(r_val, (int, float)):
            return l_val == r_val
        return str(l_val).lower() == str(r_val).lower()
    elif isinstance(node, exp.NEQ):
        l_val = eval_expr_on_row(node.left, row)
        r_val = eval_expr_on_row(node.right, row)
        if isinstance(l_val, (int, float)) and isinstance(r_val, (int, float)):
            return l_val != r_val
        return str(l_val).lower() != str(r_val).lower()
    elif isinstance(node, exp.And):
        return eval_expr_on_row(node.left, row) and eval_expr_on_row(node.right, row)
    elif isinstance(node, exp.Or):
        return eval_expr_on_row(node.left, row) or eval_expr_on_row(node.right, row)
    elif isinstance(node, exp.Not):
        return not eval_expr_on_row(node.this, row)
    elif isinstance(node, exp.Paren):
        return eval_expr_on_row(node.this, row)
    return True


def simulate_query_pipeline(sql_text: str) -> Dict[str, Any]:
    """Simulates physical SQL execution pipeline step-by-step with rich visual flow metadata."""
    try:
        parsed = sqlglot.parse_one(sql_text, read="mysql")
    except Exception as exc:
        raise ValueError(f"Query Syntax Error: {str(exc)}")

    if not isinstance(parsed, exp.Select):
        raise ValueError("Simulator requires a valid SQL SELECT statement.")

    # Target table resolution
    from_clause = parsed.find(exp.From)
    table_name = "emp"
    if from_clause:
        t_node = from_clause.find(exp.Table)
        if t_node:
            table_name = t_node.name

    steps: List[Dict[str, Any]] = []

    # =========================================================================
    # STEP 1: FROM Clause
    # =========================================================================
    current_rows = [dict(r) for r in CANONICAL_EMP_DATASET]
    steps.append({
        "step_number": 1,
        "clause": "FROM",
        "title": f"FROM {table_name.upper()}",
        "visual_type": "stream",
        "what_is_happening": f"The database locates the table '{table_name}' on disk and pulls all {len(current_rows)} employees into memory buffer.",
        "under_the_hood": "Even though you write 'SELECT' first in SQL syntax, the database engine MUST start with 'FROM' to know where the data comes from.",
        "written_vs_physical": "Written in SQL query at position #2 ──► Executes FIRST under the hood",
        "explanation": f"The query processor identifies the data source '{table_name}'. It scans all {len(current_rows)} tuples from storage into the working execution memory buffer.",
        "rule": "DBMS Physical Execution Rule: FROM executes first to allocate relation buffers and resolve attribute schemas.",
        "input_count": len(current_rows),
        "output_count": len(current_rows),
        "columns": list(current_rows[0].keys()),
        "rows": [dict(r) for r in current_rows],
        "ascii_table": render_ascii_table(current_rows),
    })

    # =========================================================================
    # STEP 2: WHERE Clause
    # =========================================================================
    where_node = parsed.find(exp.Where)
    if where_node:
        condition_sql = where_node.this.sql()
        evaluated_rows = []
        kept_rows = []

        for r in current_rows:
            passes = bool(eval_expr_on_row(where_node.this, r))
            eval_record = dict(r)
            eval_record["_eval_status"] = "KEEP [✔]" if passes else "DROP [✖]"
            eval_record["_passed"] = passes
            sal = r.get("salary", 0)
            eval_record["_calc_str"] = f"salary (${sal:,}) vs condition"
            evaluated_rows.append(eval_record)
            if passes:
                kept_rows.append(r)

        current_rows = kept_rows
        discarded_count = len(evaluated_rows) - len(kept_rows)
        display_cols = ["emp_id", "emp_name", "dept", "salary", "_eval_status"]

        steps.append({
            "step_number": len(steps) + 1,
            "clause": "WHERE",
            "title": f"WHERE ({condition_sql})",
            "visual_type": "filter",
            "what_is_happening": f"The engine scans every employee one-by-one. {len(kept_rows)} employees passed the test ({condition_sql}); {discarded_count} failed and are thrown out right now.",
            "under_the_hood": "Why filter now? It saves huge CPU & memory! If you're going to group or calculate averages, don't waste time grouping employees you're going to discard anyway.",
            "written_vs_physical": "Written in SQL query at position #3 ──► Executes SECOND under the hood",
            "explanation": f"Evaluated predicate ({condition_sql}) tuple-by-tuple. {len(kept_rows)} tuples evaluated to TRUE and proceed; {discarded_count} tuples evaluated to FALSE and are permanently discarded.",
            "rule": "DBMS Physical Execution Rule: WHERE acts as a pre-aggregation tuple filter. It executes BEFORE GROUP BY, pruning unneeded rows before expensive group partitioning.",
            "input_count": len(evaluated_rows),
            "output_count": len(kept_rows),
            "columns": display_cols,
            "rows": evaluated_rows,
            "ascii_table": render_ascii_table(evaluated_rows, display_cols),
        })

    # =========================================================================
    # STEP 3: GROUP BY Clause
    # =========================================================================
    group_node = parsed.find(exp.Group)
    groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
    group_col_names: List[str] = []

    if group_node:
        for col_expr in group_node.expressions:
            if isinstance(col_expr, exp.Column):
                group_col_names.append(col_expr.name.lower())
            else:
                group_col_names.append(col_expr.sql().lower())

        for r in current_rows:
            key = tuple(r.get(c, "") for c in group_col_names)
            groups.setdefault(key, []).append(r)

        # Build structured visual buckets for rendering
        visual_buckets = []
        group_display_rows = []
        for g_key, g_members in groups.items():
            key_str = ", ".join(f"{c}={v}" for c, v in zip(group_col_names, g_key))
            emp_names = ", ".join(m["emp_name"] for m in g_members)
            visual_buckets.append({
                "group_name": key_str,
                "count": len(g_members),
                "members": [
                    {
                        "emp_id": m.get("emp_id"),
                        "emp_name": m.get("emp_name"),
                        "salary": m.get("salary"),
                        "job": m.get("job"),
                    }
                    for m in g_members
                ]
            })
            group_display_rows.append({
                "group_partition": key_str,
                "tuple_count": len(g_members),
                "member_tuples": emp_names,
            })

        steps.append({
            "step_number": len(steps) + 1,
            "clause": "GROUP BY",
            "title": f"GROUP BY {', '.join(group_col_names).upper()}",
            "visual_type": "buckets",
            "what_is_happening": f"The engine takes the surviving employees and separates them into {len(groups)} distinct buckets based on their {', '.join(group_col_names)}.",
            "under_the_hood": "Notice how the schema changed: individual employees disappear here! From this point forward, the engine only works with whole buckets, not individual people.",
            "written_vs_physical": "Written in SQL query at position #4 ──► Executes THIRD under the hood",
            "explanation": f"Partitioned {len(current_rows)} tuples into {len(groups)} distinct group buckets sharing identical values for {', '.join(group_col_names)}.",
            "rule": "DBMS Physical Execution Rule: GROUP BY transforms a flat set of tuples into partitioned aggregate buckets. Scalar columns not part of the GROUP BY key or aggregate functions become inaccessible.",
            "input_count": len(current_rows),
            "output_count": len(groups),
            "columns": ["group_partition", "tuple_count", "member_tuples"],
            "rows": group_display_rows,
            "buckets": visual_buckets,
            "ascii_table": render_ascii_table(group_display_rows),
        })

    # =========================================================================
    # STEP 4: HAVING Clause
    # =========================================================================
    having_node = parsed.find(exp.Having)
    if having_node and groups:
        having_sql = having_node.this.sql()
        retained_groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
        having_display_rows = []
        having_buckets = []

        for g_key, g_members in groups.items():
            key_str = ", ".join(f"{c}={v}" for c, v in zip(group_col_names, g_key))
            count_val = len(g_members)
            salaries = [m["salary"] for m in g_members if "salary" in m]
            avg_val = sum(salaries) / len(salaries) if salaries else 0
            max_val = max(salaries) if salaries else 0
            min_val = min(salaries) if salaries else 0

            agg_row = {
                "count(*)": count_val,
                "count": count_val,
                "avg(salary)": avg_val,
                "max(salary)": max_val,
                "min(salary)": min_val,
            }
            for c, v in zip(group_col_names, g_key):
                agg_row[c] = v

            passes = True
            cond_node = having_node.this
            if isinstance(cond_node, (exp.GTE, exp.LTE, exp.GT, exp.LT, exp.EQ, exp.NEQ)):
                left_val = None
                if isinstance(cond_node.left, exp.Count):
                    left_val = count_val
                elif isinstance(cond_node.left, exp.Avg):
                    left_val = avg_val
                elif isinstance(cond_node.left, exp.Max):
                    left_val = max_val
                elif isinstance(cond_node.left, exp.Min):
                    left_val = min_val
                elif isinstance(cond_node.left, exp.Column):
                    left_val = agg_row.get(cond_node.left.name.lower())

                right_val = None
                if isinstance(cond_node.right, exp.Literal):
                    right_val = int(cond_node.right.this) if cond_node.right.is_int else float(cond_node.right.this)

                if left_val is not None and right_val is not None:
                    if isinstance(cond_node, exp.GTE):
                        passes = left_val >= right_val
                    elif isinstance(cond_node, exp.LTE):
                        passes = left_val <= right_val
                    elif isinstance(cond_node, exp.GT):
                        passes = left_val > right_val
                    elif isinstance(cond_node, exp.LT):
                        passes = left_val < right_val
                    elif isinstance(cond_node, exp.EQ):
                        passes = left_val == right_val
                    elif isinstance(cond_node, exp.NEQ):
                        passes = left_val != right_val

            status_str = "KEEP [✔]" if passes else "DROP [✖]"
            having_buckets.append({
                "group_name": key_str,
                "count": count_val,
                "passed": passes,
                "condition_check": f"Calculated: COUNT={count_val} vs condition ({having_sql})",
                "members": [
                    {
                        "emp_id": m.get("emp_id"),
                        "emp_name": m.get("emp_name"),
                        "salary": m.get("salary"),
                        "job": m.get("job"),
                    }
                    for m in g_members
                ]
            })
            having_display_rows.append({
                "group_partition": key_str,
                "aggregate_metric": f"COUNT={count_val}, AVG={int(avg_val)}",
                "predicate_eval": f"{having_sql} -> {passes}",
                "_status": status_str,
            })
            if passes:
                retained_groups[g_key] = g_members

        groups = retained_groups
        dropped_buckets_cnt = len(having_display_rows) - len(retained_groups)

        steps.append({
            "step_number": len(steps) + 1,
            "clause": "HAVING",
            "title": f"HAVING ({having_sql})",
            "visual_type": "filter_buckets",
            "what_is_happening": f"The engine now filters the BUCKETS themselves! Buckets matching ({having_sql}) survive ({len(retained_groups)} kept). Buckets failing are discarded ({dropped_buckets_cnt} dropped).",
            "under_the_hood": "CRITICAL DIFFERENCE: 'WHERE' filters individual rows before grouping. 'HAVING' filters whole groups after grouping. You can never use HAVING without or before groups!",
            "written_vs_physical": "Written in SQL query at position #5 ──► Executes FOURTH under the hood",
            "explanation": f"Evaluated group-level predicate ({having_sql}). {len(retained_groups)} group buckets satisfied the threshold; {dropped_buckets_cnt} groups discarded.",
            "rule": "DBMS Physical Execution Rule: HAVING acts as a post-aggregation group filter. Unlike WHERE (which acts on individual rows), HAVING tests properties of entire aggregated groups.",
            "input_count": len(having_display_rows),
            "output_count": len(retained_groups),
            "columns": ["group_partition", "aggregate_metric", "predicate_eval", "_status"],
            "rows": having_display_rows,
            "buckets": having_buckets,
            "ascii_table": render_ascii_table(having_display_rows),
        })

    # =========================================================================
    # STEP 5: SELECT Clause (Projection & Aggregation)
    # =========================================================================
    projected_rows: List[Dict[str, Any]] = []
    expr_targets: List[Tuple[str, exp.Expression]] = []

    for e in parsed.expressions:
        if isinstance(e, exp.Star):
            col_names = list(current_rows[0].keys()) if current_rows else ["emp_id", "emp_name", "dept", "job", "salary", "hire_date"]
            for cn in col_names:
                expr_targets.append((cn, exp.column(cn)))
        elif isinstance(e, exp.Alias):
            expr_targets.append((e.alias, e.this))
        else:
            expr_targets.append((e.sql(), e))

    if groups:
        for g_key, g_members in groups.items():
            out_row = {}
            for col_alias, col_expr in expr_targets:
                if isinstance(col_expr, exp.Count):
                    out_row[col_alias] = len(g_members)
                elif isinstance(col_expr, exp.Avg):
                    sals = [m["salary"] for m in g_members if "salary" in m]
                    out_row[col_alias] = round(sum(sals) / len(sals), 2) if sals else 0
                elif isinstance(col_expr, exp.Sum):
                    sals = [m["salary"] for m in g_members if "salary" in m]
                    out_row[col_alias] = sum(sals)
                elif isinstance(col_expr, exp.Max):
                    sals = [m["salary"] for m in g_members if "salary" in m]
                    out_row[col_alias] = max(sals) if sals else 0
                elif isinstance(col_expr, exp.Min):
                    sals = [m["salary"] for m in g_members if "salary" in m]
                    out_row[col_alias] = min(sals) if sals else 0
                elif isinstance(col_expr, exp.Column):
                    c_name = col_expr.name.lower()
                    out_row[col_alias] = g_members[0].get(c_name, "")
                else:
                    out_row[col_alias] = g_members[0].get(col_alias, "")
            projected_rows.append(out_row)
    else:
        for r in current_rows:
            out_row = {}
            for col_alias, col_expr in expr_targets:
                val = eval_expr_on_row(col_expr, r)
                out_row[col_alias] = val if val is not None else ""
            projected_rows.append(out_row)

    current_rows = projected_rows
    proj_cols = [t[0] for t in expr_targets]
    steps.append({
        "step_number": len(steps) + 1,
        "clause": "SELECT",
        "title": f"SELECT ({', '.join(proj_cols)})",
        "visual_type": "materialized",
        "what_is_happening": f"The engine finally does the math for each group, projects the requested columns ({', '.join(proj_cols)}), and throws away everything else.",
        "under_the_hood": "SURPRISE! Although SELECT is the very first word in your SQL query, it executes near the very END! This is why column aliases defined in SELECT cannot be used inside the WHERE clause.",
        "written_vs_physical": "Written in SQL query at position #1 ──► Executes FIFTH under the hood",
        "explanation": f"Materialized the projection list. Calculated requested expressions and aggregates ({', '.join(proj_cols)}). Discarded unreferenced attributes.",
        "rule": "DBMS Physical Execution Rule: Despite appearing first in SQL syntax, SELECT evaluates after FROM, WHERE, GROUP BY, and HAVING.",
        "input_count": len(current_rows),
        "output_count": len(current_rows),
        "columns": proj_cols,
        "rows": current_rows,
        "ascii_table": render_ascii_table(current_rows, proj_cols),
    })

    # =========================================================================
    # STEP 6: ORDER BY Clause
    # =========================================================================
    order_node = parsed.find(exp.Order)
    if order_node and current_rows:
        order_desc_list = []
        for ordered in order_node.expressions:
            col_target = ordered.this.sql().lower()
            desc = ordered.args.get("desc", False)
            order_desc_list.append((col_target, desc))

        def sort_key(row_dict):
            keys = []
            for col_target, desc in order_desc_list:
                val = None
                for k, v in row_dict.items():
                    if k.lower() == col_target or k.lower() == col_target.replace(" ", ""):
                        val = v
                        break
                if val is None:
                    first_val = list(row_dict.values())[0] if row_dict else 0
                    val = 0 if isinstance(first_val, (int, float)) else ""
                keys.append(val)
            return tuple(keys)

        reverse_order = order_desc_list[0][1] if order_desc_list else False
        current_rows = sorted(current_rows, key=sort_key, reverse=reverse_order)

        order_str = ", ".join(f"{c} {'DESC' if d else 'ASC'}" for c, d in order_desc_list)
        steps.append({
            "step_number": len(steps) + 1,
            "clause": "ORDER BY",
            "title": f"ORDER BY {order_str.upper()}",
            "visual_type": "sort",
            "what_is_happening": f"The engine sorts the final rows into the desired order ({order_str}).",
            "under_the_hood": "ORDER BY runs on the final rows. Sorting a tiny list of 2 or 3 rows at the end is practically instantaneous compared to sorting millions of raw rows at the start.",
            "written_vs_physical": "Written in SQL query at position #6 ──► Executes SIXTH under the hood",
            "explanation": f"Sorted the materialized result set deterministically by ({order_str}).",
            "rule": "DBMS Physical Execution Rule: ORDER BY operates on the post-SELECT materialized tuples. It is one of the final physical execution steps.",
            "input_count": len(current_rows),
            "output_count": len(current_rows),
            "columns": proj_cols,
            "rows": current_rows,
            "ascii_table": render_ascii_table(current_rows, proj_cols),
        })

    # =========================================================================
    # STEP 7: LIMIT Clause
    # =========================================================================
    limit_node = parsed.find(exp.Limit)
    if limit_node and current_rows:
        limit_val = int(limit_node.expression.this)
        sliced_rows = current_rows[:limit_val]
        steps.append({
            "step_number": len(steps) + 1,
            "clause": "LIMIT",
            "title": f"LIMIT {limit_val}",
            "visual_type": "slice",
            "what_is_happening": f"The engine slices off rows past row #{limit_val} to deliver only the requested slice to the user.",
            "under_the_hood": "LIMIT stops cursor transmission once the count is reached, conserving network bandwidth.",
            "written_vs_physical": "Written at end of query ──► Executes LAST under the hood",
            "explanation": f"Constrained output cardinality to {limit_val} tuples. Discarded remaining {max(0, len(current_rows) - limit_val)} tuples.",
            "rule": "DBMS Physical Execution Rule: LIMIT executes last, truncating output buffer delivery to the client application.",
            "input_count": len(current_rows),
            "output_count": len(sliced_rows),
            "columns": proj_cols,
            "rows": sliced_rows,
            "ascii_table": render_ascii_table(sliced_rows, proj_cols),
        })
        current_rows = sliced_rows

    return {
        "query": sql_text.strip(),
        "total_steps": len(steps),
        "steps": steps,
        "final_row_count": len(current_rows),
        "final_ascii_table": render_ascii_table(current_rows, proj_cols) if current_rows else "(0 rows returned)",
    }
