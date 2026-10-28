"""Deterministic ASCII UML class diagram renderer for SchemaFlow.

Renders database tables as UML Class diagrams:
- Single-line Unicode boxes (┌ ─ ┐ │ ├ ┤ └ ┘) for classes.
- Attributes formatted as '+ name : TYPE <<PK>> <<FK>>'.
- Association connectors with UML multiplicity notations ('1', '0..1', '0..*').
"""

from typing import List
from core.classifier import get_direct_relationships
from core.er_renderer import calculate_er_layout
from core.grid import Box, GridCanvas
from core.model import Schema, Table


def build_uml_box(table: Table) -> Box:
    """Builds a rendered ASCII UML Class Box for a Table."""
    header_title = f" {table.name} "
    rows: List[str] = []
    fk_cols = {fk.column_name.lower() for fk in table.foreign_keys}

    for col in table.columns:
        is_fk = col.name.lower() in fk_cols
        markers: List[str] = []
        if col.is_pk:
            markers.append("<<PK>>")
        if is_fk:
            markers.append("<<FK>>")
        if col.is_unique and not col.is_pk:
            markers.append("<<UQ>>")

        marker_str = f" {' '.join(markers)}" if markers else ""
        rows.append(f"+ {col.name} : {col.data_type}{marker_str}")

    inner_width = max(
        len(header_title),
        max(len(r) for r in rows) if rows else 0,
        26,
    ) + 2

    top_border = "┌" + ("─" * inner_width) + "┐"
    header_line = "│" + header_title.center(inner_width) + "│"
    separator = "├" + ("─" * inner_width) + "┤"
    bottom_border = "└" + ("─" * inner_width) + "┘"

    body_lines = ["│ " + r.ljust(inner_width - 2) + " │" for r in rows]

    box_lines = [top_border, header_line, separator] + body_lines + [bottom_border]
    return Box(name=table.name, lines=box_lines)


def render_uml_diagram(schema: Schema) -> str:
    """Renders a complete ASCII UML class diagram from a Schema model."""
    if not schema.tables:
        return "(Empty Schema: No tables found)"

    tables = list(schema.tables.values())
    boxes = {t.name: build_uml_box(t) for t in tables}

    positions, total_w, total_h = calculate_er_layout(tables, boxes, schema)
    canvas = GridCanvas(max(total_w, 80), max(total_h, 25))

    for t_name, box in boxes.items():
        x, y = positions[t_name]
        canvas.place_box(box, x, y)

    # Route UML association lines
    direct_rels = get_direct_relationships(schema)
    for r in direct_rels:
        box_from = boxes.get(r.source_table)
        box_to = boxes.get(r.target_table)
        if box_from and box_to:
            is_1_to_1 = (r.cardinality == "1:1")
            target_label = "1" if is_1_to_1 else "0..*"
            canvas.draw_connector(
                box_from=box_from,
                box_to=box_to,
                source_label="1",
                target_label=target_label,
                is_crow_foot=False,
            )

    return canvas.render()
