"""SchemaFlow Stage A Live Demonstration CLI.

Run this script to demonstrate the deterministic parsing and relationship
classification engine to teachers, evaluators, or peers.

Usage:
    python demo.py
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from core.parser import parse_sql, SchemaParseError
from core.classifier import get_direct_relationships, get_many_to_many_relationships


def run_demo():
    print("=" * 70)
    print("       SCHEMAFLOW - STAGE A DEMO: DETERMINISTIC SQL ANALYZER")
    print("=" * 70)
    print("Societal Goal: 100% offline, zero-AI, accessible visual SQL parser.\n")

    samples_dir = Path("samples")
    sample_files = list(samples_dir.glob("*.sql"))

    if not sample_files:
        print("No sample files found in samples/ directory.")
        return

    print("Available Sample Schemas:")
    for idx, f in enumerate(sample_files, start=1):
        print(f"  [{idx}] {f.name}")
    print("  [5] Test Syntax Error Handling")

    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()
    else:
        try:
            choice = input("\nSelect a sample to inspect (1-5, default=4 school.sql): ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "4"
            print("4 (defaulted)")
    if choice == "5":
        test_error_handling()
        return

    chosen_file = sample_files[3] if len(sample_files) >= 4 else sample_files[0]
    if choice in ("1", "2", "3", "4"):
        chosen_file = sample_files[int(choice) - 1]

    print(f"\n---> Loading and parsing '{chosen_file.name}'...\n")
    sql_text = chosen_file.read_text(encoding="utf-8")

    try:
        schema = parse_sql(sql_text)
    except SchemaParseError as err:
        print(f"Error parsing schema: {err}")
        return

    print(f"Successfully parsed {len(schema.tables)} tables deterministically:\n")

    for tbl_name, table in schema.tables.items():
        junction_badge = " [JUNCTION TABLE (M:N)]" if table.is_junction else ""
        print(f"┌── TABLE: {tbl_name}{junction_badge}")
        print(f"│   Primary Key: {', '.join(table.primary_key) if table.primary_key else 'None'}")
        print(f"│   Columns ({len(table.columns)}):")
        for col in table.columns:
            tags = []
            if col.is_pk:
                tags.append("PK")
            if col.is_unique and not col.is_pk:
                tags.append("UNIQUE")
            if not col.is_nullable:
                tags.append("NOT NULL")
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            print(f"│     • {col.name:<18} {col.data_type:<15}{tag_str}")
        if table.foreign_keys:
            print("│   Foreign Keys:")
            for fk in table.foreign_keys:
                print(f"│     -> {fk.column_name} REFERENCES {fk.target_table}({fk.target_column})")
        print("└──" + "─" * 40)

    print("\nCLASSIFIED RELATIONSHIPS:")
    direct = get_direct_relationships(schema)
    for r in direct:
        print(f"  • {r.source_table}.{r.source_column} ──({r.cardinality})──> {r.target_table}.{r.target_column}")

    m2m = get_many_to_many_relationships(schema)
    if m2m:
        print("\nIDENTIFIED MANY-TO-MANY (M:N) CONNECTIONS:")
        for r in m2m:
            print(f"  ★ {r.source_table} <──(M:N via {r.junction_table})──> {r.target_table}")

    print("\n" + "=" * 70)
    print("Demo completed successfully. Zero AI/ML used: 100% deterministic parsing.")
    print("=" * 70)


def test_error_handling():
    print("\n--- Demonstrating Syntax Error Handling (No Stack Traces) ---")
    broken_sql = "CREATE TABLE broken_table (id INT PRIMARY KEY, name VARCHAR(50"
    print(f"Input broken SQL:\n  {broken_sql}\n")
    try:
        parse_sql(broken_sql)
    except SchemaParseError as err:
        print(f"SchemaFlow Output: {err}")
        print("\nNote: The user receives a clean, accessible message with line and column info.")


if __name__ == "__main__":
    run_demo()
