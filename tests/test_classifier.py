"""Unit tests for the relationship classifier module."""

from pathlib import Path
from core.parser import parse_sql
from core.classifier import get_direct_relationships, get_many_to_many_relationships


def test_one_to_many_classification():
    sql = """
    CREATE TABLE authors (
        id INT PRIMARY KEY,
        name VARCHAR(100)
    );
    CREATE TABLE books (
        id INT PRIMARY KEY,
        author_id INT,
        title VARCHAR(100),
        FOREIGN KEY (author_id) REFERENCES authors(id)
    );
    """
    schema = parse_sql(sql)
    direct = get_direct_relationships(schema)
    assert len(direct) == 1
    rel = direct[0]
    assert rel.source_table == "authors"
    assert rel.target_table == "books"
    assert rel.cardinality == "1:N"


def test_one_to_one_via_unique():
    sql = """
    CREATE TABLE users (
        id INT PRIMARY KEY,
        username VARCHAR(50)
    );
    CREATE TABLE profiles (
        id INT PRIMARY KEY,
        user_id INT UNIQUE,
        bio TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """
    schema = parse_sql(sql)
    direct = get_direct_relationships(schema)
    assert len(direct) == 1
    assert direct[0].cardinality == "1:1"


def test_one_to_one_via_whole_primary_key():
    sql = """
    CREATE TABLE vehicles (
        id INT PRIMARY KEY,
        plate_no VARCHAR(20)
    );
    CREATE TABLE vehicle_insurance (
        vehicle_id INT PRIMARY KEY,
        policy_no VARCHAR(50),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
    );
    """
    schema = parse_sql(sql)
    direct = get_direct_relationships(schema)
    assert len(direct) == 1
    assert direct[0].cardinality == "1:1"


def test_many_to_many_junction_classification():
    sql = """
    CREATE TABLE students (
        id INT PRIMARY KEY,
        name VARCHAR(50)
    );
    CREATE TABLE clubs (
        id INT PRIMARY KEY,
        title VARCHAR(50)
    );
    CREATE TABLE student_clubs (
        student_id INT,
        club_id INT,
        joined_at DATE,
        PRIMARY KEY (student_id, club_id),
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (club_id) REFERENCES clubs(id)
    );
    """
    schema = parse_sql(sql)
    tbl = schema.tables["student_clubs"]
    assert tbl.is_junction is True
    
    m2m = get_many_to_many_relationships(schema)
    assert len(m2m) == 1
    assert m2m[0].cardinality == "M:N"
    assert m2m[0].junction_table == "student_clubs"
    assert {m2m[0].source_table.lower(), m2m[0].target_table.lower()} == {"students", "clubs"}


def test_all_sample_files_load_and_classify():
    samples_dir = Path("samples")
    expected_samples = ["hospital.sql", "blood_bank.sql", "ration_shop.sql", "school.sql"]
    
    for filename in expected_samples:
        filepath = samples_dir / filename
        assert filepath.exists(), f"Missing sample file {filename}"
        sql_content = filepath.read_text(encoding="utf-8")
        schema = parse_sql(sql_content)
        assert len(schema.tables) >= 3, f"Sample {filename} has fewer tables than expected"
        assert len(schema.relationships) > 0, f"Sample {filename} has no relationships"
        
    # Check specific M:N junction detections in ration_shop and school
    ration_schema = parse_sql((samples_dir / "ration_shop.sql").read_text(encoding="utf-8"))
    assert ration_schema.tables["ration_entries"].is_junction is True
    assert len(get_many_to_many_relationships(ration_schema)) == 1

    school_schema = parse_sql((samples_dir / "school.sql").read_text(encoding="utf-8"))
    assert school_schema.tables["enrolments"].is_junction is True
    assert len(get_many_to_many_relationships(school_schema)) == 1
