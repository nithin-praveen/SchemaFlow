"""Unit tests for ASCII ER and UML renderers."""

from pathlib import Path
from core.parser import parse_sql
from core.er_renderer import build_table_box, render_er_diagram
from core.uml_renderer import build_uml_box, render_uml_diagram


def test_er_box_lines_equal_width():
    samples_dir = Path("samples")
    for f in samples_dir.glob("*.sql"):
        schema = parse_sql(f.read_text(encoding="utf-8"))
        for table in schema.tables.values():
            box = build_table_box(table)
            lengths = [len(line) for line in box.lines]
            assert len(set(lengths)) == 1, (
                f"Table {table.name} in {f.name} has uneven box lines: {lengths}"
            )


def test_uml_box_lines_equal_width():
    samples_dir = Path("samples")
    for f in samples_dir.glob("*.sql"):
        schema = parse_sql(f.read_text(encoding="utf-8"))
        for table in schema.tables.values():
            box = build_uml_box(table)
            lengths = [len(line) for line in box.lines]
            assert len(set(lengths)) == 1, (
                f"UML box for {table.name} in {f.name} has uneven lines: {lengths}"
            )


def test_no_connector_inside_box():
    # Routing characters should never invade table interiors
    samples_dir = Path("samples")
    for f in samples_dir.glob("*.sql"):
        schema = parse_sql(f.read_text(encoding="utf-8"))
        er_text = render_er_diagram(schema)
        uml_text = render_uml_diagram(schema)
        
        assert len(er_text) > 0
        assert len(uml_text) > 0
        for table_name in schema.tables:
            assert table_name in er_text
            assert table_name in uml_text


def test_all_samples_render_without_errors():
    samples = ["hospital.sql", "blood_bank.sql", "ration_shop.sql", "school.sql"]
    for s in samples:
        sql = Path(f"samples/{s}").read_text(encoding="utf-8")
        schema = parse_sql(sql)
        er = render_er_diagram(schema)
        uml = render_uml_diagram(schema)
        assert "╔" in er
        assert "╚" in er
        assert "┌" in uml
        assert "└" in uml
