"""Flask application and REST API for SchemaFlow.

Serves the offline Metropolis-styled web client and provides deterministic
endpoints for ER diagram rendering, UML generation, schema narration,
and sample retrieval.
"""

from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from core.describer import describe_schema
from core.er_renderer import render_er_diagram
from core.parser import parse_sql, SchemaParseError
from core.uml_renderer import render_uml_diagram

app = Flask(__name__, static_folder="static", static_url_path="")
SAMPLES_DIR = Path(__file__).parent / "samples"


@app.route("/")
def index():
    """Serves the main terminal web client."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/samples", methods=["GET"])
def list_samples():
    """Lists all available sample schema names."""
    if not SAMPLES_DIR.exists():
        return jsonify([])
    samples = [f.stem for f in SAMPLES_DIR.glob("*.sql")]
    return jsonify(sorted(samples))


@app.route("/api/samples/<name>", methods=["GET"])
def get_sample(name: str):
    """Retrieves SQL text for a specific sample schema."""
    filename = f"{name}.sql"
    filepath = SAMPLES_DIR / filename
    if not filepath.exists():
        return jsonify({"error": f"Sample schema '{name}' not found"}), 404
    try:
        content = filepath.read_text(encoding="utf-8")
        return jsonify({"name": name, "sql": content})
    except Exception as exc:
        return jsonify({"error": f"Failed to read sample: {str(exc)}"}), 500


@app.route("/api/er", methods=["POST"])
def api_er():
    """Renders ASCII ER diagram from provided SQL DDL."""
    data = request.get_json(silent=True) or {}
    sql_text = data.get("sql", "")
    try:
        schema = parse_sql(sql_text)
        diagram = render_er_diagram(schema)
        return jsonify({"result": diagram})
    except SchemaParseError as err:
        return jsonify({"error": str(err)}), 400
    except Exception as exc:
        return jsonify({"error": f"Internal processing error: {str(exc)}"}), 500


@app.route("/api/uml", methods=["POST"])
def api_uml():
    """Renders ASCII UML Class diagram from provided SQL DDL."""
    data = request.get_json(silent=True) or {}
    sql_text = data.get("sql", "")
    try:
        schema = parse_sql(sql_text)
        diagram = render_uml_diagram(schema)
        return jsonify({"result": diagram})
    except SchemaParseError as err:
        return jsonify({"error": str(err)}), 400
    except Exception as exc:
        return jsonify({"error": f"Internal processing error: {str(exc)}"}), 500


@app.route("/api/describe", methods=["POST"])
def api_describe():
    """Generates screen-reader plain English description from SQL DDL."""
    data = request.get_json(silent=True) or {}
    sql_text = data.get("sql", "")
    try:
        schema = parse_sql(sql_text)
        description = describe_schema(schema)
        return jsonify({"result": description})
    except SchemaParseError as err:
        return jsonify({"error": str(err)}), 400
    except Exception as exc:
        return jsonify({"error": f"Internal processing error: {str(exc)}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
