import os
from flask import Flask, jsonify, request, session
from backend.config import Config
from backend.database.db import init_db, connect
from backend.routes.auth import bp as auth_bp
from backend.routes.recipes import bp as recipes_bp
from backend.routes.users import bp as users_bp
from backend.routes.admin import bp as admin_bp
from backend.routes.messages import bp as messages_bp


def create_app(config_class=Config):
    app = Flask(__name__, static_folder="../frontend", static_url_path="/")
    app.config.from_object(config_class)
    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_db(app.config["DATABASE_PATH"])
    app.register_blueprint(auth_bp); app.register_blueprint(recipes_bp); app.register_blueprint(users_bp); app.register_blueprint(admin_bp); app.register_blueprint(messages_bp)

    @app.before_request
    def csrf_protect():
        if request.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.path not in {"/api/auth/login", "/api/auth/register"}:
            expected = session.get("csrf_token")
            supplied = request.headers.get("X-CSRF-Token")
            if expected and supplied != expected:
                return jsonify(error="CSRF 校验失败，请刷新页面后重试"), 403

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error="上传文件不能超过 8MB"), 413

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"): return jsonify(error="资源不存在"), 404
        return app.send_static_file("index.html")

    @app.get("/uploads/<path:name>")
    def uploads(name):
        from flask import send_from_directory
        return send_from_directory(app.config["UPLOAD_FOLDER"], name)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
