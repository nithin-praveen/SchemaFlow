"""Deterministic SQL DDL parser for SchemaFlow using sqlglot (MySQL dialect).

Extracts table names, columns, data types, constraints (PRIMARY KEY, UNIQUE,
NOT NULL), and foreign keys from CREATE TABLE and ALTER TABLE statements.
Converts syntax issues into readable human-friendly error messages without
exposing Python tracebacks.
"""

from typing import Any, List, Optional
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from core.classifier import classify_schema
from core.model import Column, ForeignKey, Schema, Table


class SchemaParseError(Exception):
    """Raised when SQL parsing fails or contains invalid syntax."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col

    def __str__(self) -> str:
        if self.line is not None and self.col is not None:
            return f"Syntax error near line {self.line}, column {self.col}: {self.message}"
        if self.line is not None:
            return f"Syntax error near line {self.line}: {self.message}"
        return f"Syntax error: {self.message}"


def _clean_name(name: Optional[str]) -> str:
    """Strips quotes, backticks and whitespace from SQL identifiers."""
    if not name:
        return ""
    return str(name).strip("`\"' ")


def _extract_table_name(schema_or_table: Any) -> str:
    """Extracts the table name from a Schema or Table AST node."""
    if hasattr(schema_or_table, "this") and hasattr(schema_or_table.this, "name"):
        return _clean_name(schema_or_table.this.name)
    if hasattr(schema_or_table, "name"):
        return _clean_name(schema_or_table.name)
    return _clean_name(str(schema_or_table))


def _extract_foreign_key_details(fk_expr: exp.ForeignKey, constraint_name: Optional[str] = None) -> List[ForeignKey]:
    """Extracts ForeignKey instances from an exp.ForeignKey AST node."""
    fks: List[ForeignKey] = []
    source_cols = [_clean_name(col.name) for col in fk_expr.expressions if hasattr(col, "name")]
    ref = fk_expr.args.get("reference")
    if not ref:
        return fks

    # Reference target table and target columns
    target_table = ""
    target_cols: List[str] = []
    if isinstance(ref.this, exp.Schema):
        target_table = _extract_table_name(ref.this.this)
        target_cols = [_clean_name(c.name) for c in ref.this.expressions if hasattr(c, "name")]
    elif isinstance(ref.this, exp.Table):
        target_table = _extract_table_name(ref.this)
        target_cols = [_clean_name(c.name) for c in ref.expressions if hasattr(c, "name")]
    else:
        target_table = _clean_name(ref.this.name if hasattr(ref.this, "name") else str(ref.this))

    for idx, col_name in enumerate(source_cols):
        target_col = target_cols[idx] if idx < len(target_cols) else "id"
        fks.append(
            ForeignKey(
                column_name=col_name,
                target_table=target_table,
                target_column=target_col,
                constraint_name=constraint_name,
            )
        )
    return fks


def _parse_create_table(stmt: exp.Create, schema: Schema) -> None:
    """Parses a CREATE TABLE statement into a Table dataclass."""
    table_node = stmt.this
    table_name = _extract_table_name(table_node)
    if not table_name:
        return

    # Check if table already recorded (or retrieve existing)
    table = schema.get_table(table_name)
    if not table:
        table = Table(name=table_name)
        schema.tables[table_name] = table

    # Inspect all items inside the table definition
    expressions = table_node.expressions if hasattr(table_node, "expressions") else []
    for expr in expressions:
        if isinstance(expr, exp.ColumnDef):
            col_name = _clean_name(expr.name)
            col_type = expr.kind.sql(dialect="mysql").upper() if expr.kind else "TEXT"
            is_pk = False
            is_unique = False
            is_nullable = True

            # Inline constraints
            for c in (expr.constraints or []):
                kind = c.kind
                if isinstance(kind, exp.PrimaryKeyColumnConstraint):
                    is_pk = True
                    is_nullable = False
                elif isinstance(kind, exp.UniqueColumnConstraint):
                    is_unique = True
                elif isinstance(kind, exp.NotNullColumnConstraint):
                    is_nullable = False
                elif isinstance(kind, exp.Reference):
                    # Inline REFERENCES table(column)
                    target_table = ""
                    target_col = "id"
                    if isinstance(kind.this, exp.Schema):
                        target_table = _extract_table_name(kind.this.this)
                        if kind.this.expressions:
                            target_col = _clean_name(kind.this.expressions[0].name)
                    elif isinstance(kind.this, exp.Table):
                        target_table = _extract_table_name(kind.this)
                    table.foreign_keys.append(
                        ForeignKey(
                            column_name=col_name,
                            target_table=target_table,
                            target_column=target_col,
                        )
                    )

            if is_pk and col_name not in table.primary_key:
                table.primary_key.append(col_name)

            table.columns.append(
                Column(
                    name=col_name,
                    data_type=col_type,
                    is_pk=is_pk,
                    is_unique=is_unique,
                    is_nullable=is_nullable,
                )
            )

        elif isinstance(expr, exp.PrimaryKey):
            # Table-level PRIMARY KEY (col1, col2, ...)
            for pk_col in expr.expressions:
                pk_name = _clean_name(pk_col.name)
                if pk_name and pk_name not in table.primary_key:
                    table.primary_key.append(pk_name)

        elif isinstance(expr, exp.UniqueColumnConstraint):
            # Table-level UNIQUE (col)
            uq_cols = []
            if hasattr(expr.this, "expressions"):
                uq_cols = [_clean_name(c.name) for c in expr.this.expressions]
            elif hasattr(expr, "expressions"):
                uq_cols = [_clean_name(c.name) for c in expr.expressions]
            if len(uq_cols) == 1:
                col = table.get_column(uq_cols[0])
                if col:
                    col.is_unique = True

        elif isinstance(expr, exp.ForeignKey):
            # Table-level FOREIGN KEY (col) REFERENCES ...
            fks = _extract_foreign_key_details(expr)
            table.foreign_keys.extend(fks)

        elif isinstance(expr, exp.Constraint):
            # CONSTRAINT <name> FOREIGN KEY ... or UNIQUE ...
            c_name = _clean_name(expr.name)
            for sub_expr in expr.expressions:
                if isinstance(sub_expr, exp.ForeignKey):
                    fks = _extract_foreign_key_details(sub_expr, constraint_name=c_name)
                    table.foreign_keys.extend(fks)
                elif isinstance(sub_expr, exp.PrimaryKey):
                    for pk_col in sub_expr.expressions:
                        pk_name = _clean_name(pk_col.name)
                        if pk_name and pk_name not in table.primary_key:
                            table.primary_key.append(pk_name)
                elif isinstance(sub_expr, exp.UniqueColumnConstraint):
                    uq_cols = []
                    if hasattr(sub_expr.this, "expressions"):
                        uq_cols = [_clean_name(c.name) for c in sub_expr.this.expressions]
                    if len(uq_cols) == 1:
                        col = table.get_column(uq_cols[0])
                        if col:
                            col.is_unique = True


def _parse_alter_table(stmt: exp.Alter, schema: Schema) -> None:
    """Parses an ALTER TABLE statement adding foreign keys."""
    table_name = _clean_name(stmt.this.name if hasattr(stmt.this, "name") else str(stmt.this))
    table = schema.get_table(table_name)
    if not table:
        table = Table(name=table_name)
        schema.tables[table_name] = table

    actions = stmt.args.get("actions", [])
    for action in actions:
        if isinstance(action, exp.AddConstraint):
            for sub in action.expressions:
                if isinstance(sub, exp.ForeignKey):
                    table.foreign_keys.extend(_extract_foreign_key_details(sub))
                elif isinstance(sub, exp.Constraint):
                    c_name = _clean_name(sub.name)
                    for inner in sub.expressions:
                        if isinstance(inner, exp.ForeignKey):
                            table.foreign_keys.extend(_extract_foreign_key_details(inner, constraint_name=c_name))


def parse_sql(sql_text: str) -> Schema:
    """Parses SQL text containing CREATE TABLE and ALTER TABLE statements into a Schema.
    
    Raises:
        SchemaParseError: On invalid syntax or parsing errors with line & column info.
    """
    if not sql_text or not sql_text.strip():
        raise SchemaParseError("Input SQL script is empty. Please provide CREATE TABLE statements.")

    try:
        statements = sqlglot.parse(sql_text, read="mysql")
    except ParseError as err:
        line = None
        col = None
        desc = "Invalid SQL syntax"
        if hasattr(err, "errors") and err.errors:
            e = err.errors[0]
            desc = e.get("description", str(err))
            line = e.get("line")
            col = e.get("col")
        raise SchemaParseError(desc, line=line, col=col) from None
    except Exception as exc:
        raise SchemaParseError(f"Failed to parse SQL: {str(exc)}") from None

    schema = Schema()

    for stmt in statements:
        if stmt is None:
            continue
        if isinstance(stmt, exp.Create):
            _parse_create_table(stmt, schema)
        elif isinstance(stmt, exp.Alter):
            _parse_alter_table(stmt, schema)

    if not schema.tables:
        raise SchemaParseError("No valid CREATE TABLE statements found in the SQL script.")

    # Synchronize primary key flags on columns
    for table in schema.tables.values():
        for pk_col_name in table.primary_key:
            col = table.get_column(pk_col_name)
            if col:
                col.is_pk = True
                col.is_nullable = False

    # Apply relationship classifier rules
    classify_schema(schema)
    return schema
