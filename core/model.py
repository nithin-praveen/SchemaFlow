"""Data models for SchemaFlow representations.

Provides structured, typed dataclasses for tables, columns, constraints,
relationships, and complete database schemas.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Column:
    """Represents a database table column."""
    name: str
    data_type: str
    is_pk: bool = False
    is_unique: bool = False
    is_nullable: bool = True


@dataclass
class ForeignKey:
    """Represents a foreign key constraint on a column."""
    column_name: str
    target_table: str
    target_column: str
    constraint_name: Optional[str] = None


@dataclass
class Relationship:
    """Represents a classified relationship between two tables.
    
    source_table: The referenced parent table (the "one" side in 1:N).
    target_table: The child table referencing the parent (or second entity in M:N).
    cardinality: "1:1", "1:N", or "M:N".
    junction_table: Name of the associative table if this represents an M:N link.
    """
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    cardinality: str  # "1:1", "1:N", or "M:N"
    junction_table: Optional[str] = None


@dataclass
class Table:
    """Represents a database table with columns and constraints."""
    name: str
    columns: List[Column] = field(default_factory=list)
    primary_key: List[str] = field(default_factory=list)
    foreign_keys: List[ForeignKey] = field(default_factory=list)
    is_junction: bool = False

    def get_column(self, col_name: str) -> Optional[Column]:
        """Case-insensitive column lookup."""
        for col in self.columns:
            if col.name.lower() == col_name.lower():
                return col
        return None


@dataclass
class Schema:
    """Represents a complete relational database schema."""
    tables: Dict[str, Table] = field(default_factory=dict)
    relationships: List[Relationship] = field(default_factory=list)

    def get_table(self, table_name: str) -> Optional[Table]:
        """Case-insensitive table lookup."""
        for name, table in self.tables.items():
            if name.lower() == table_name.lower():
                return table
        return None
