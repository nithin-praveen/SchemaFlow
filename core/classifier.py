"""Deterministic relationship classifier for SchemaFlow.

Applies explicit, viva-friendly rules to classify relational constraints:
1. A foreign key represents a relationship from the referenced parent table
   ("one" side) to the referencing child table ("many" or "one" side).
2. If the foreign key column is marked UNIQUE or comprises the entire primary key,
   the relationship is 1:1 (one-to-one); otherwise it is 1:N (one-to-many).
3. If a table's primary key is composite and composed of two or more foreign keys,
   it is flagged as a junction table (is_junction=True), representing an M:N
   (many-to-many) relationship between the referenced tables.
"""

from typing import List
from core.model import Relationship, Schema, Table


def classify_table_relationships(table: Table, schema: Schema) -> List[Relationship]:
    """Classify all foreign keys defined on a single table into Relationship objects."""
    direct_relationships: List[Relationship] = []
    
    # Identify whether the table is a junction table
    pk_cols_lower = [pk.lower() for pk in table.primary_key]
    fk_cols_map = {fk.column_name.lower(): fk for fk in table.foreign_keys}
    
    # Check if primary key has >= 2 columns and all PK columns are foreign keys
    is_junction = (
        len(pk_cols_lower) >= 2
        and all(pk in fk_cols_map for pk in pk_cols_lower)
    )
    table.is_junction = is_junction

    # For each foreign key, determine cardinality
    for fk in table.foreign_keys:
        col = table.get_column(fk.column_name)
        
        # Rule: 1:1 if FK column is UNIQUE or is the entire primary key
        is_unique_col = col.is_unique if col else False
        is_whole_pk = (
            len(table.primary_key) == 1
            and table.primary_key[0].lower() == fk.column_name.lower()
        )
        
        cardinality = "1:1" if (is_unique_col or is_whole_pk) else "1:N"
        
        direct_relationships.append(
            Relationship(
                source_table=fk.target_table,
                source_column=fk.target_column,
                target_table=table.name,
                target_column=fk.column_name,
                cardinality=cardinality,
                junction_table=table.name if is_junction else None,
            )
        )
        
    return direct_relationships


def classify_schema(schema: Schema) -> Schema:
    """Classifies all relationships and junction tables in the given schema."""
    all_relationships: List[Relationship] = []
    
    # First pass: classify direct table relationships and flag junction tables
    for table in schema.tables.values():
        direct = classify_table_relationships(table, schema)
        all_relationships.extend(direct)
        
    # Second pass: for junction tables, synthesize high-level M:N relationships
    for table in schema.tables.values():
        if table.is_junction and len(table.foreign_keys) >= 2:
            seen_pairs = set()
            for i in range(len(table.foreign_keys)):
                for j in range(i + 1, len(table.foreign_keys)):
                    fk1 = table.foreign_keys[i]
                    fk2 = table.foreign_keys[j]
                    if fk1.target_table.lower() != fk2.target_table.lower():
                        pair_key = tuple(sorted([fk1.target_table.lower(), fk2.target_table.lower()]))
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            all_relationships.append(
                                Relationship(
                                    source_table=fk1.target_table,
                                    source_column=fk1.target_column,
                                    target_table=fk2.target_table,
                                    target_column=fk2.target_column,
                                    cardinality="M:N",
                                    junction_table=table.name,
                                )
                            )
                            
    schema.relationships = all_relationships
    return schema


def get_direct_relationships(schema: Schema) -> List[Relationship]:
    """Returns only 1:1 and 1:N physical foreign key relationships."""
    return [r for r in schema.relationships if r.cardinality in ("1:1", "1:N")]


def get_many_to_many_relationships(schema: Schema) -> List[Relationship]:
    """Returns only synthesized M:N relationships bridged by junction tables."""
    return [r for r in schema.relationships if r.cardinality == "M:N"]
