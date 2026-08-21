import os
import click
from flask import Flask, jsonify, request, session
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash
from backend.errors import APIError, error_payload
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
    if app.config.get("APP_ENV") == "production":
        secret = str(app.config.get("SECRET_KEY", ""))
        placeholders = {"", "foodlab-development-change-me", "replace-with-a-long-random-value"}
        if secret in placeholders or len(secret) < 32:
            raise RuntimeError("生产环境必须配置至少 32 个字符的随机 SECRET_KEY")
        if not app.config.get("SESSION_COOKIE_SECURE"):
            raise RuntimeError("生产环境必须设置 SESSION_COOKIE_SECURE=1")
        if app.config.get("SEED_DEMO_DATA"):
            raise RuntimeError("生产环境必须设置 SEED_DEMO_DATA=0，禁止创建固定密码测试账号")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_db(app.config["DATABASE_PATH"], seed_demo=app.config.get("SEED_DEMO_DATA", True))
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

    @app.errorhandler(APIError)
    def api_error(error):
        return jsonify(error_payload(error.code, error.message, error.fields)), error.status

    @app.errorhandler(Exception)
    def unexpected_error(error):
        if isinstance(error, HTTPException):
            if request.path.startswith("/api/"):
                code = "method_not_allowed" if error.code == 405 else "http_error"
                return jsonify(error_payload(code, error.description)), error.code
            return error
        app.logger.exception("Unhandled application error")
        if request.path.startswith("/api/"):
            return jsonify(error_payload("internal_error", "服务器暂时无法完成请求")), 500
        raise error

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"): return jsonify(error="资源不存在"), 404
        if request.path.startswith("/images/uploads/") or request.path.startswith("/uploads/"):
            return jsonify(error="资源不存在"), 404
        return app.send_static_file("index.html")

    @app.get("/uploads/<path:name>")
    def uploads(name):
        from flask import send_from_directory
        return send_from_directory(app.config["UPLOAD_FOLDER"], name)

    # Uploaded assets are returned with the public `/images/uploads/` prefix
    # used by the frontend. Keep this explicit route so the upload volume is
    # served correctly in both local Flask and Docker/Nginx deployments.
    @app.get("/images/uploads/<path:name>")
    def image_uploads(name):
        from flask import send_from_directory
        return send_from_directory(app.config["UPLOAD_FOLDER"], name)

    @app.cli.command("create-admin")
    @click.option("--username", prompt="管理员用户名")
    @click.option("--email", prompt="管理员邮箱")
    @click.password_option(confirmation_prompt=True)
    def create_admin(username, email, password):
        """Interactively create the first production administrator."""
        username, email = username.strip(), email.strip().lower()
        if len(username) < 2 or "@" not in email or len(password) < 10:
            raise click.ClickException("用户名至少 2 个字符，密码至少 10 个字符，并填写有效邮箱")
        db = connect(app.config["DATABASE_PATH"])
        if db.execute("SELECT 1 FROM users WHERE username=? OR email=?", (username, email)).fetchone():
            db.close()
            raise click.ClickException("用户名或邮箱已存在")
        from backend.database.db import now_iso
        db.execute("""INSERT INTO users(username,email,password_hash,bio,role,created_at)
            VALUES (?,?,?,?,?,?)""", (username, email, generate_password_hash(password), "", "admin", now_iso()))
        db.commit()
        db.close()
        click.echo("管理员账号已创建")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
