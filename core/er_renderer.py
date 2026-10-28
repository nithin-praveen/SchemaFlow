"""Deterministic ASCII ER diagram renderer for SchemaFlow schemas.

Transforms Schema models into high-clarity ASCII ER diagrams:
- Double-line Unicode boxes (╔ ═ ╗ ║ ╠ ╣ ╚ ╝) for tables.
- Shaded headers (▓) for identified junction tables.
- Uniform row formatting with [PK] and [FK] indicators.
- Center-out grid layout with the most-connected table at the core.
- Obstacle-avoiding BFS routed connectors with '1', 'N', and crow's-foot (<) markers.
"""

from typing import Dict, List, Tuple
from core.classifier import get_direct_relationships
from core.grid import Box, GridCanvas
from core.model import Schema, Table


def build_table_box(table: Table) -> Box:
    """Builds a rendered double-line ASCII Box for a given Table."""
    header_title = f" {table.name} "
    rows: List[str] = []
    fk_cols = {fk.column_name.lower() for fk in table.foreign_keys}

    # Format each column row
    for col in table.columns:
        is_fk = col.name.lower() in fk_cols
        if col.is_pk and is_fk:
            tag = "[PK][FK]"
        elif col.is_pk:
            tag = "[PK]"
        elif is_fk:
            tag = "[FK]"
        elif col.is_unique:
            tag = "[UQ]"
        else:
            tag = ""

        rows.append(f"{tag:<8} {col.name:<18} {col.data_type}")

    inner_width = max(
        len(header_title),
        max(len(r) for r in rows) if rows else 0,
        26,
    ) + 2

    top_border = "╔" + ("═" * inner_width) + "╗"

    if table.is_junction:
        remainder = inner_width - len(header_title)
        pad_left = remainder // 2
        pad_right = remainder - pad_left
        header_line = "║" + ("▓" * pad_left) + header_title + ("▓" * pad_right) + "║"
    else:
        header_line = "║" + header_title.center(inner_width) + "║"

    separator = "╠" + ("═" * inner_width) + "╣"
    bottom_border = "╚" + ("═" * inner_width) + "╝"

    body_lines = ["║ " + r.ljust(inner_width - 2) + " ║" for r in rows]

    box_lines = [top_border, header_line, separator] + body_lines + [bottom_border]
    return Box(name=table.name, lines=box_lines)


def calculate_er_layout(
    tables: List[Table],
    boxes: Dict[str, Box],
    schema: Schema,
) -> Tuple[Dict[str, Tuple[int, int]], int, int]:
    """Computes non-overlapping positions for boxes on the grid canvas."""
    # Count connections for center-out priority
    degree: Dict[str, int] = {t.name: 0 for t in tables}
    for r in schema.relationships:
        if r.source_table in degree:
            degree[r.source_table] += 1
        if r.target_table in degree:
            degree[r.target_table] += 1

    sorted_tables = sorted(tables, key=lambda t: degree.get(t.name, 0), reverse=True)
    n = len(sorted_tables)
    positions: Dict[str, Tuple[int, int]] = {}

    if n == 1:
        t0 = sorted_tables[0]
        positions[t0.name] = (4, 2)
        total_w = boxes[t0.name].width + 10
        total_h = boxes[t0.name].height + 5
        return positions, total_w, total_h

    if n == 2:
        b0 = boxes[sorted_tables[0].name]
        b1 = boxes[sorted_tables[1].name]
        positions[sorted_tables[0].name] = (4, 2)
        positions[sorted_tables[1].name] = (4 + b0.width + 16, 2)
        total_w = 4 + b0.width + 16 + b1.width + 10
        total_h = max(b0.height, b1.height) + 6
        return positions, total_w, total_h

    if n == 3:
        # Center-out: place highest-degree in center, others left and right
        b_left = boxes[sorted_tables[1].name]
        b_center = boxes[sorted_tables[0].name]
        b_right = boxes[sorted_tables[2].name]

        x_left = 4
        x_center = x_left + b_left.width + 16
        x_right = x_center + b_center.width + 16

        max_h = max(b_left.height, b_center.height, b_right.height)
        y_left = 2 + (max_h - b_left.height) // 2
        y_center = 2 + (max_h - b_center.height) // 2
        y_right = 2 + (max_h - b_right.height) // 2

        positions[sorted_tables[1].name] = (x_left, y_left)
        positions[sorted_tables[0].name] = (x_center, y_center)
        positions[sorted_tables[2].name] = (x_right, y_right)

        total_w = x_right + b_right.width + 10
        total_h = max_h + 6
        return positions, total_w, total_h

    # 4 or more tables: 2-column center-out grid
    cols = 2
    grid_rows: List[List[Table]] = []
    curr: List[Table] = []
    for t in sorted_tables:
        curr.append(t)
        if len(curr) == cols:
            grid_rows.append(curr)
            curr = []
    if curr:
        grid_rows.append(curr)

    col_widths = [0] * cols
    row_heights: List[int] = []

    for row in grid_rows:
        row_heights.append(max(boxes[t.name].height for t in row))
        for c_idx, t in enumerate(row):
            col_widths[c_idx] = max(col_widths[c_idx], boxes[t.name].width)

    x_offsets = [4]
    for c in range(1, cols):
        x_offsets.append(x_offsets[c - 1] + col_widths[c - 1] + 18)

    y_offsets = [2]
    for r in range(1, len(row_heights)):
        y_offsets.append(y_offsets[r - 1] + row_heights[r - 1] + 8)

    for r_idx, row in enumerate(grid_rows):
        for c_idx, t in enumerate(row):
            positions[t.name] = (x_offsets[c_idx], y_offsets[r_idx])

    total_w = x_offsets[-1] + col_widths[-1] + 12
    total_h = y_offsets[-1] + row_heights[-1] + 8
    return positions, total_w, total_h


def render_er_diagram(schema: Schema) -> str:
    """Renders a complete ASCII ER diagram from a Schema model."""
    if not schema.tables:
        return "(Empty Schema: No tables found)"

    tables = list(schema.tables.values())
    boxes = {t.name: build_table_box(t) for t in tables}

    positions, total_w, total_h = calculate_er_layout(tables, boxes, schema)
    # Ensure canvas is spacious enough for BFS navigation
    canvas = GridCanvas(max(total_w, 80), max(total_h, 25))

    for t_name, box in boxes.items():
        x, y = positions[t_name]
        canvas.place_box(box, x, y)

    # Route connectors for direct relationships
    direct_rels = get_direct_relationships(schema)
    for r in direct_rels:
        box_from = boxes.get(r.source_table)
        box_to = boxes.get(r.target_table)
        if box_from and box_to:
            is_1_to_1 = (r.cardinality == "1:1")
            target_label = "1" if is_1_to_1 else "N"
            canvas.draw_connector(
                box_from=box_from,
                box_to=box_to,
                source_label="1",
                target_label=target_label,
                is_crow_foot=not is_1_to_1,
            )

    return canvas.render()
