import os
from flask import Flask, send_from_directory, jsonify
from app.config import SECRET_KEY, BASE_DIR
from app.database import init_db
from app.routes.auth_routes import auth_bp
from app.routes.doc_routes import doc_bp
from app.routes.quiz_routes import quiz_bp
from app.routes.analytics_routes import analytics_bp
from app.routes.admin_routes import admin_bp

def create_app(test_config=None):
    static_folder = str(BASE_DIR / "static")
    app = Flask(__name__, static_folder=static_folder, static_url_path="/static")
    app.config["SECRET_KEY"] = SECRET_KEY

    if test_config:
        app.config.update(test_config)

    # Initialize SQLite database
    init_db()

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(doc_bp, url_prefix="/api/documents")
    app.register_blueprint(quiz_bp, url_prefix="/api/quiz")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "healthy",
            "system": "AutoQuiz: Smart Exam Quizzer System Using RAG",
            "version": "1.0 Approved"
        }), 200

    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return jsonify({
            "error": getattr(e, "description", str(e)),
            "status_code": getattr(e, "code", 500)
        }), getattr(e, "code", 500)

    @app.errorhandler(Exception)
    def handle_global_exception(e):
        code = getattr(e, "code", 500)
        desc = getattr(e, "description", str(e))
        return jsonify({"error": desc, "status_code": code}), code

    # Frontend Single-Page App delivery
    @app.route("/", methods=["GET"])
    def index():
        return send_from_directory(static_folder, "index.html")

    @app.route("/<path:path>", methods=["GET"])
    def serve_static(path):
        target_path = os.path.join(static_folder, path)
        if os.path.exists(target_path):
            return send_from_directory(static_folder, path)
        return send_from_directory(static_folder, "index.html")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

