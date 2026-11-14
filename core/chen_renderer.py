"""Deterministic ASCII Peter Chen Conceptual ER Diagram Renderer.

Transforms Schema models into classical textbook Chen ER diagrams:
- Rectangles (┌ ─ ┐ │ └ ┘) represent Entity Sets.
- Double Rectangles (╔ ═ ╗ ║ ╚ ╝) represent Weak Entity Sets.
- Diamonds (/\\ < > \\/) represent Relationship Sets.
- Ellipses (( attribute )) represent Attributes, with key attributes marked (* [PK]).
- Connecting lines with explicit Cardinality Ratios (1, N, M).
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from core.grid import Box, GridCanvas
from core.model import Column, ForeignKey, Schema, Table


def make_entity_box(table: Table) -> Box:
    """Builds a rendered ASCII rectangle box for an entity set."""
    title = f" {table.name} "
    w = max(len(title) + 4, 18)
    if w % 2 != 0:
        w += 1

    # Check if weak entity (child in 1:1 identifying relationship)
    is_weak = False
    for fk in table.foreign_keys:
        col = table.get_column(fk.column_name)
        if col and (col.is_unique or table.primary_key == [fk.column_name]):
            is_weak = True
            break

    if is_weak:
        top = "╔" + ("═" * (w - 2)) + "╗"
        mid = "║" + title.center(w - 2) + "║"
        bot = "╚" + ("═" * (w - 2)) + "╝"
    else:
        top = "┌" + ("─" * (w - 2)) + "┐"
        mid = "│" + title.center(w - 2) + "│"
        bot = "└" + ("─" * (w - 2)) + "┘"

    return Box(name=table.name, lines=[top, mid, bot])


def make_diamond_box(rel_name: str, box_id: str) -> Box:
    """Builds a rendered 5-line ASCII diamond box for a relationship set."""
    t = f" {rel_name.upper()} "
    if len(t) % 2 != 0:
        t += " "
    w = len(t) + 2
    mid = w // 2

    line0 = " " * (mid - 1) + "/\\" + " " * (w - mid - 1)
    line1 = " " * (mid - 2) + "/  \\" + " " * (w - mid - 2)
    line2 = f"<{t}>"
    line3 = " " * (mid - 2) + "\\  /" + " " * (w - mid - 2)
    line4 = " " * (mid - 1) + "\\/" + " " * (w - mid - 1)

    return Box(name=box_id, lines=[line0, line1, line2, line3, line4])


def _derive_relationship_verb(
    parent: str,
    child: str,
    fk: ForeignKey,
    is_1_to_1: bool,
) -> str:
    """Derives an intuitive Chen relationship verb."""
    p_lower = parent.lower()
    c_lower = child.lower()

    # Domain-specific standard verbs for known entities
    if "patient" in p_lower and "apt" in c_lower:
        return "BOOKS"
    if "doctor" in p_lower and "apt" in c_lower:
        return "TREATS"
    if "donor" in p_lower and "donation" in c_lower:
        return "DONATES"
    if "donation" in p_lower and "transfusion" in c_lower:
        return "USED_IN"
    if "recipient" in p_lower and "transfusion" in c_lower:
        return "RECEIVES"
    if "shop" in p_lower and "famil" in c_lower:
        return "SERVES"
    if "student" in p_lower and "class" in c_lower:
        return "ENROLS"

    # Try extracting from foreign key constraint name
    if fk.constraint_name:
        clean = (
            fk.constraint_name.lower()
            .replace("fk_", "")
            .replace("fk", "")
            .strip("_")
        )
        if clean and len(clean) <= 12:
            return clean.upper()

    return "HAS" if is_1_to_1 else "RELATES"


def extract_chen_elements(schema: Schema) -> Tuple[Dict[str, Table], List[Dict[str, Any]]]:
    """Separates entities and extracts conceptual Chen relationships from Schema."""
    entities: Dict[str, Table] = {}
    relationships: List[Dict[str, Any]] = []

    # 1. Classify junction tables as Many-to-Many Relationships
    for t_name, table in schema.tables.items():
        if table.is_junction and len(table.foreign_keys) >= 2:
            fk1 = table.foreign_keys[0]
            fk2 = table.foreign_keys[1]
            rel_attrs = [
                c
                for c in table.columns
                if not c.is_pk
                and c.name.lower() not in {fk1.column_name.lower(), fk2.column_name.lower()}
            ]
            relationships.append({
                "name": table.name.upper(),
                "id": f"rel_j_{table.name}",
                "entity_a": fk1.target_table,
                "card_a": "M",
                "entity_b": fk2.target_table,
                "card_b": "N",
                "table": table,
                "attrs": rel_attrs,
            })
        else:
            entities[t_name] = table

    # 2. Direct Foreign Key relationships between regular entity tables
    rel_count = 0
    for t_name, table in entities.items():
        for fk in table.foreign_keys:
            parent_table = fk.target_table
            parent_matches = [k for k in entities if k.lower() == parent_table.lower()]
            if parent_matches:
                parent_key = parent_matches[0]
                col = table.get_column(fk.column_name)
                is_1_to_1 = (col and col.is_unique) or (table.primary_key == [fk.column_name])
                card_b = "1" if is_1_to_1 else "N"
                verb = _derive_relationship_verb(parent_key, t_name, fk, is_1_to_1)

                rel_count += 1
                relationships.append({
                    "name": verb,
                    "id": f"rel_d_{rel_count}_{verb}",
                    "entity_a": parent_key,
                    "card_a": "1",
                    "entity_b": t_name,
                    "card_b": card_b,
                    "table": None,
                    "attrs": [],
                })

    return entities, relationships


def render_chen_diagram(schema: Schema) -> str:
    """Renders a complete ASCII Peter Chen Conceptual ER Diagram."""
    if not schema.tables:
        return "(Empty Schema: No tables found)"

    entities, relationships = extract_chen_elements(schema)

    # Build boxes
    entity_boxes: Dict[str, Box] = {
        e_name: make_entity_box(tbl) for e_name, tbl in entities.items()
    }
    diamond_boxes: Dict[str, Box] = {
        r["id"]: make_diamond_box(r["name"], r["id"]) for r in relationships
    }

    # Assign level (column index) to entities and diamonds
    entity_levels: Dict[str, int] = {}
    child_entities = {r["entity_b"].lower() for r in relationships}

    for e_name in entities:
        if e_name.lower() not in child_entities:
            entity_levels[e_name.lower()] = 0

    if not entity_levels and entities:
        first_e = list(entities.keys())[0]
        entity_levels[first_e.lower()] = 0

    # Propagate levels
    for _ in range(10):
        changed = False
        for r in relationships:
            ea = r["entity_a"].lower()
            eb = r["entity_b"].lower()
            if ea in entity_levels and eb not in entity_levels:
                entity_levels[eb] = entity_levels[ea] + 2
                changed = True
            elif eb in entity_levels and ea not in entity_levels:
                entity_levels[ea] = max(0, entity_levels[eb] - 2)
                changed = True
        if not changed:
            break

    # Unassigned fallback
    for e_name in entities:
        if e_name.lower() not in entity_levels:
            entity_levels[e_name.lower()] = 0

    # Ensure connected entities are at different levels so diamonds sit between them
    for r in relationships:
        ea = r["entity_a"].lower()
        eb = r["entity_b"].lower()
        if entity_levels.get(ea, 0) == entity_levels.get(eb, 0):
            entity_levels[eb] = entity_levels.get(ea, 0) + 2

    # Group into columns
    cols: Dict[int, List[Tuple[str, str, Box]]] = {}
    for e_name, box in entity_boxes.items():
        lvl = entity_levels.get(e_name.lower(), 0)
        cols.setdefault(lvl, []).append(("entity", e_name, box))

    for r in relationships:
        ea = r["entity_a"].lower()
        eb = r["entity_b"].lower()
        lvl_a = entity_levels.get(ea, 0)
        lvl_b = entity_levels.get(eb, 2)
        d_lvl = (lvl_a + lvl_b) // 2
        if d_lvl % 2 == 0:
            d_lvl += 1
        cols.setdefault(d_lvl, []).append(("diamond", r["id"], diamond_boxes[r["id"]]))

    sorted_levels = sorted(cols.keys())

    # Calculate column widths and x offsets
    col_x: Dict[int, int] = {}
    curr_x = 4
    for lvl in sorted_levels:
        max_w = max(item[2].width for item in cols[lvl])
        col_x[lvl] = curr_x
        curr_x += max_w + 12

    # Calculate y offsets and box positions
    max_h = 25
    positions: Dict[str, Tuple[int, int]] = {}
    for lvl in sorted_levels:
        items = cols[lvl]
        curr_y = 2
        for item_type, item_id, box in items:
            # Align centers: diamond center is at y+2; entity center is at y+1.
            # So offset entity by +1 to achieve straight horizontal connector lines.
            y_pos = curr_y + (1 if item_type == "entity" else 0)
            positions[item_id] = (col_x[lvl], y_pos)
            curr_y += box.height + 4
        max_h = max(max_h, curr_y + 4)

    total_w = curr_x + 10
    canvas = GridCanvas(max(total_w, 90), max_h)

    # Place boxes
    all_boxes = {**entity_boxes, **diamond_boxes}
    for box_id, box in all_boxes.items():
        if box_id in positions:
            x, y = positions[box_id]
            canvas.place_box(box, x, y)

    # Helper for case-insensitive box lookup
    def get_entity_box(target_name: str) -> Optional[Box]:
        b = entity_boxes.get(target_name)
        if b:
            return b
        for k, val in entity_boxes.items():
            if k.lower() == target_name.lower():
                return val
        return None

    # Route connectors
    for r in relationships:
        box_a = get_entity_box(r["entity_a"])
        box_d = diamond_boxes.get(r["id"])
        box_b = get_entity_box(r["entity_b"])

        if box_a and box_d:
            canvas.draw_connector(
                box_from=box_a,
                box_to=box_d,
                source_label=r["card_a"],
                target_label="",
                is_crow_foot=False,
            )
        if box_d and box_b:
            canvas.draw_connector(
                box_from=box_d,
                box_to=box_b,
                source_label="",
                target_label=r["card_b"],
                is_crow_foot=False,
            )

    rendered_graph = canvas.render()

    # Educational Banner & Legend
    header = (
        "╔══════════════════════════════════════════════════════════════════════════════════╗\n"
        "║                 CHEN CONCEPTUAL ENTITY-RELATIONSHIP (ER) MODEL                   ║\n"
        "╠══════════════════════════════════════════════════════════════════════════════════╣\n"
        "║  [ RECTANGLE ]    = Entity Set             < DIAMOND >   = Relationship Set      ║\n"
        "║  ╔ DOUBLE-BOX ╗   = Weak Entity Set        ( ELLIPSE )   = Attribute             ║\n"
        "║  * / [PK]         = Key Attribute          [UQ]          = Unique Attribute      ║\n"
        "║  1, N, M          = Cardinality Ratio (One-to-One, One-to-Many, Many-to-Many)    ║\n"
        "╚══════════════════════════════════════════════════════════════════════════════════╝"
    )

    # Attributes Section
    attr_section = [
        "════════════════════════════════════════════════════════════════════════════════════",
        "                     ENTITY & RELATIONSHIP ATTRIBUTES (ELLIPSES)                    ",
        "════════════════════════════════════════════════════════════════════════════════════",
    ]

    for e_name, table in entities.items():
        is_weak = any(
            col.is_unique
            for col in [table.get_column(fk.column_name) for fk in table.foreign_keys]
            if col
        )
        tag = "[WEAK ENTITY]" if is_weak else "[ENTITY]"
        attr_section.append(f"\n┌── {tag} {table.name}")

        attr_lines: List[str] = []
        curr_line = "│   "
        for col in table.columns:
            if col.is_pk:
                bubble = f"( {col.name}* [PK] )"
            elif col.is_unique:
                bubble = f"( {col.name} [UQ] )"
            else:
                bubble = f"( {col.name} )"

            if len(curr_line) + len(bubble) + 2 > 80:
                attr_lines.append(curr_line)
                curr_line = "│   " + bubble + "  "
            else:
                curr_line += bubble + "  "
        if curr_line.strip() != "│":
            attr_lines.append(curr_line)
        attr_section.extend(attr_lines)

    for r in relationships:
        extra_attrs = r.get("attrs", [])
        if extra_attrs:
            attr_section.append(f"\n┌── [RELATIONSHIP ATTRIBUTES] <{r['name']}>")
            curr_line = "│   "
            for col in extra_attrs:
                bubble = f"( {col.name} )"
                if len(curr_line) + len(bubble) + 2 > 80:
                    attr_section.append(curr_line)
                    curr_line = "│   " + bubble + "  "
                else:
                    curr_line += bubble + "  "
            if curr_line.strip() != "│":
                attr_section.append(curr_line)

    return header + "\n\n" + rendered_graph + "\n\n" + "\n".join(attr_section)
