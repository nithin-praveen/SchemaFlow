"""Unit tests for Flask REST API endpoints."""

import json
from app import app


def test_index_serves_html():
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"SCHEMA" in resp.data
    assert b"FLOW" in resp.data


def test_api_samples_list():
    client = app.test_client()
    resp = client.get("/api/samples")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert "hospital" in data
    assert "school" in data


def test_api_samples_detail():
    client = app.test_client()
    resp = client.get("/api/samples/school")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "school"
    assert "CREATE TABLE students" in data["sql"]


def test_api_er_endpoint():
    client = app.test_client()
    sql = "CREATE TABLE test_tbl (id INT PRIMARY KEY);"
    resp = client.post("/api/er", json={"sql": sql})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "test_tbl" in data["result"]
    assert "╔" in data["result"]


def test_api_uml_endpoint():
    client = app.test_client()
    sql = "CREATE TABLE test_tbl (id INT PRIMARY KEY);"
    resp = client.post("/api/uml", json={"sql": sql})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "test_tbl" in data["result"]
    assert "┌" in data["result"]


def test_api_describe_endpoint():
    client = app.test_client()
    sql = "CREATE TABLE test_tbl (id INT PRIMARY KEY);"
    resp = client.post("/api/describe", json={"sql": sql})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "Table 'test_tbl'" in data["result"]


def test_api_syntax_error_handling():
    client = app.test_client()
    broken_sql = "CREATE TABLE broken ("
    resp = client.post("/api/er", json={"sql": broken_sql})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data
    assert "Syntax error" in data["error"]


def test_api_chen_endpoint():
    client = app.test_client()
    sql = "CREATE TABLE students (id INT PRIMARY KEY, name VARCHAR(50));"
    resp = client.post("/api/chen", json={"sql": sql})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "students" in data["result"]
    assert "[ RECTANGLE ]" in data["result"]
    assert "( id* [PK] )" in data["result"]


def test_api_er_styles():
    client = app.test_client()
    sql = "CREATE TABLE tbl (id INT PRIMARY KEY);"
    
    # Test chen style explicitly
    resp_chen = client.post("/api/er", json={"sql": sql, "style": "chen"})
    assert resp_chen.status_code == 200
    assert "CHEN CONCEPTUAL" in resp_chen.get_json()["result"]

    # Test relational style explicitly
    resp_rel = client.post("/api/er", json={"sql": sql, "style": "relational"})
    assert resp_rel.status_code == 200
    assert "╔" in resp_rel.get_json()["result"]


def test_api_query_pipeline_presets():
    client = app.test_client()
    resp = client.get("/api/query-pipeline/presets")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "presets" in data
    assert len(data["presets"]) >= 4
    assert "dataset" in data
    assert len(data["dataset"]) == 8


def test_api_query_pipeline_simulate():
    client = app.test_client()
    sql = "SELECT emp_name, salary FROM emp WHERE salary >= 75000;"
    resp = client.post("/api/query-pipeline/simulate", json={"sql": sql})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["final_row_count"] == 2
    assert data["total_steps"] >= 3
    assert len(data["steps"]) == data["total_steps"]
