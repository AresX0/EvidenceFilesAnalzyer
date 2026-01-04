from .agent.agent import CaseAgent
from .reports import generate_extended_report


def create_app(db_path: str = None):
    """Create a Flask app exposing lightweight agent and report endpoints.

    Flask is imported lazily so that the package does not require flask
    unless the server is used (keeps core install lightweight).
    """
    try:
        from flask import Flask, jsonify, request
    except Exception as e:
        raise RuntimeError(
            "Flask is required to run the HTTP API. Install `flask` in your environment."
        ) from e

    app = Flask(__name__)
    # store configured DB path so handlers can use it when queries omit `db`
    app.config["DB_PATH"] = db_path

    agent = CaseAgent(db_path=db_path) if db_path else CaseAgent()

    @app.route("/agent/find")
    def agent_find():
        q = request.args.get("query")
        if not q:
            return jsonify({"error": "missing query"}), 400
        try:
            res = agent.find_mentions(q)
            return jsonify({"result": res})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/agent/query")
    def agent_query():
        q = request.args.get("query")
        if not q:
            return jsonify({"error": "missing query"}), 400
        try:
            res = agent.answer_query(q)
            return jsonify(res)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/agent/synopsis")
    def agent_synopsis():
        try:
            res = agent.full_synopsis()
            return jsonify(res)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/agent/summarize")
    def agent_summarize():
        q = request.args.get("query")
        if not q:
            return jsonify({"error": "missing query"}), 400
        model = request.args.get("model", "mistral")
        try:
            res = agent.summarize_with_ollama(q, model=model)
            return jsonify(res)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/reports/people")
    def reports_people():
        # Return the people section of the extended report
        req_db = request.args.get("db")
        db_to_use = req_db or app.config.get("DB_PATH")
        try:
            rpt = generate_extended_report(db_to_use)
            return jsonify(
                {
                    "people": rpt.get("people", []),
                    "top_subjects": rpt.get("top_subjects", []),
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


def run_server(host: str = "127.0.0.1", port: int = 5000, db_path: str = None):
    app = create_app(db_path=db_path)
    app.run(host=host, port=port)
