"""Unit tests for the SQL parser module."""

import pytest
from core.parser import parse_sql, SchemaParseError


def test_inline_primary_and_unique_keys():
    sql = """
    CREATE TABLE users (
        user_id INT PRIMARY KEY,
        email VARCHAR(100) UNIQUE NOT NULL,
        username VARCHAR(50) NOT NULL
    );
    """
    schema = parse_sql(sql)
    assert "users" in schema.tables
    users = schema.tables["users"]
    assert users.primary_key == ["user_id"]
    
    uid_col = users.get_column("user_id")
    assert uid_col is not None
    assert uid_col.is_pk is True
    assert uid_col.is_nullable is False
    
    email_col = users.get_column("email")
    assert email_col is not None
    assert email_col.is_unique is True
    assert email_col.is_nullable is False


def test_table_level_and_composite_primary_keys():
    sql = """
    CREATE TABLE order_items (
        order_id INT,
        item_id INT,
        quantity INT NOT NULL,
        PRIMARY KEY (order_id, item_id)
    );
    """
    schema = parse_sql(sql)
    tbl = schema.tables["order_items"]
    assert tbl.primary_key == ["order_id", "item_id"]
    assert tbl.get_column("order_id").is_pk is True
    assert tbl.get_column("item_id").is_pk is True


def test_inline_and_table_foreign_keys():
    sql = """
    CREATE TABLE orders (
        id INT PRIMARY KEY,
        customer_id INT,
        CONSTRAINT fk_cust FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    CREATE TABLE audit_log (
        log_id INT PRIMARY KEY,
        order_id INT REFERENCES orders(id)
    );
    """
    schema = parse_sql(sql)
    orders = schema.tables["orders"]
    assert len(orders.foreign_keys) == 1
    assert orders.foreign_keys[0].column_name == "customer_id"
    assert orders.foreign_keys[0].target_table.lower() == "customers"
    assert orders.foreign_keys[0].target_column == "id"

    audit = schema.tables["audit_log"]
    assert len(audit.foreign_keys) == 1
    assert audit.foreign_keys[0].column_name == "order_id"
    assert audit.foreign_keys[0].target_table.lower() == "orders"


def test_alter_table_foreign_key():
    sql = """
    CREATE TABLE departments (
        dept_id INT PRIMARY KEY,
        dept_name VARCHAR(50)
    );
    CREATE TABLE employees (
        emp_id INT PRIMARY KEY,
        dept_id INT NOT NULL
    );
    ALTER TABLE employees ADD CONSTRAINT fk_emp_dept FOREIGN KEY (dept_id) REFERENCES departments(dept_id);
    """
    schema = parse_sql(sql)
    emp = schema.tables["employees"]
    assert len(emp.foreign_keys) == 1
    assert emp.foreign_keys[0].column_name == "dept_id"
    assert emp.foreign_keys[0].target_table.lower() == "departments"
    assert emp.foreign_keys[0].target_column == "dept_id"


def test_syntax_error_human_message():
    sql = "CREATE TABLE broken (id INT"
    with pytest.raises(SchemaParseError) as exc_info:
        parse_sql(sql)
    msg = str(exc_info.value)
    assert "Syntax error" in msg
    assert "line" in msg.lower()


def test_empty_sql_error():
    with pytest.raises(SchemaParseError) as exc_info:
        parse_sql("   ")
    assert "empty" in str(exc_info.value).lower()
