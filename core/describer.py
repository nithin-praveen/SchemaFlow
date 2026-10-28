"""Screen-reader plain English describer for SchemaFlow.

Converts relational database schemas into accessible natural language:
- Explains tables, columns, data types, and primary key constraints.
- Details foreign key linkages with explicit semantic cardinality.
- Explains associative junction tables as many-to-many bridges.
"""

from core.classifier import get_direct_relationships, get_many_to_many_relationships
from core.model import Schema, Table


def describe_table(table: Table) -> str:
    """Produces accessible natural language describing a single table."""
    col_count = len(table.columns)
    col_noun = "column" if col_count == 1 else "columns"
    lines = [f"Table '{table.name}' has {col_count} {col_noun}."]

    # Primary key description
    if len(table.primary_key) == 1:
        lines.append(f"Its primary key is '{table.primary_key[0]}'.")
    elif len(table.primary_key) > 1:
        pk_list = ", ".join(f"'{k}'" for k in table.primary_key)
        lines.append(f"Its primary key is composite, consisting of ({pk_list}).")
    else:
        lines.append("It does not have an explicit primary key defined.")

    # Unique constraints
    unique_cols = [c.name for c in table.columns if c.is_unique and not c.is_pk]
    if unique_cols:
        uq_list = ", ".join(f"'{u}'" for u in unique_cols)
        lines.append(f"Unique constraints are enforced on: {uq_list}.")

    # Columns overview
    col_details = [f"{c.name} ({c.data_type})" for c in table.columns]
    lines.append(f"Columns: {', '.join(col_details)}.")

    # Junction table explanation
    if table.is_junction and len(table.foreign_keys) >= 2:
        linked_tables = sorted(list({fk.target_table for fk in table.foreign_keys}))
        lines.append(
            f"This table functions as a junction (associative) table bridging a many-to-many relationship "
            f"between {', '.join(linked_tables)}."
        )
    elif table.foreign_keys:
        for fk in table.foreign_keys:
            col = table.get_column(fk.column_name)
            is_1_to_1 = (col and col.is_unique) or (table.primary_key == [fk.column_name])
            if is_1_to_1:
                rel_desc = (
                    f"This is a one-to-one relationship: one '{fk.target_table}' corresponds "
                    f"to exactly one '{table.name}'."
                )
            else:
                rel_desc = (
                    f"This is a one-to-many relationship: one '{fk.target_table}' can associate "
                    f"with many '{table.name}' records."
                )
            lines.append(
                f"It has a foreign key '{fk.column_name}' that references '{fk.target_table}.{fk.target_column}'. "
                f"{rel_desc}"
            )

    return " ".join(lines)


def describe_schema(schema: Schema) -> str:
    """Produces a complete, screen-reader friendly narrative for an entire database schema."""
    if not schema.tables:
        return "The database schema is currently empty. No tables to describe."

    table_count = len(schema.tables)
    table_noun = "table" if table_count == 1 else "tables"
    direct_rels = get_direct_relationships(schema)
    m2m_rels = get_many_to_many_relationships(schema)

    sections = [
        f"Database Schema Overview: This schema contains {table_count} {table_noun} and "
        f"{len(direct_rels)} foreign key relationships.\n"
    ]

    for table in schema.tables.values():
        sections.append(describe_table(table) + "\n")

    if m2m_rels:
        sections.append("Many-to-Many Summary:")
        for rel in m2m_rels:
            sections.append(
                f"- Many-to-many relationship between '{rel.source_table}' and '{rel.target_table}', "
                f"implemented via junction table '{rel.junction_table}'."
            )
        sections.append("")

    return "\n".join(sections).strip()
