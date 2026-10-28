"""Unit tests for the screen-reader describer."""

from pathlib import Path
from core.parser import parse_sql
from core.describer import describe_schema


def test_describer_outputs_clean_english():
    sql = """
    CREATE TABLE users (
        id INT PRIMARY KEY,
        email VARCHAR(100) UNIQUE NOT NULL
    );
    CREATE TABLE profiles (
        profile_id INT PRIMARY KEY,
        user_id INT UNIQUE,
        bio TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """
    schema = parse_sql(sql)
    desc = describe_schema(schema)
    assert "Table 'users'" in desc
    assert "Table 'profiles'" in desc
    assert "one-to-one relationship" in desc
    assert "Its primary key is 'id'" in desc


def test_describer_junction_table():
    sql = Path("samples/school.sql").read_text(encoding="utf-8")
    schema = parse_sql(sql)
    desc = describe_schema(schema)
    assert "junction" in desc.lower() or "many-to-many" in desc.lower()
    assert "students" in desc
    assert "classes" in desc
    assert "enrolments" in desc


def test_all_samples_have_descriptive_output():
    samples = ["hospital.sql", "blood_bank.sql", "ration_shop.sql", "school.sql"]
    for s in samples:
        sql = Path(f"samples/{s}").read_text(encoding="utf-8")
        schema = parse_sql(sql)
        desc = describe_schema(schema)
        assert len(desc) > 50
        for table_name in schema.tables:
            assert f"Table '{table_name}'" in desc
