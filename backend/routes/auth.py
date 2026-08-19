import re
import secrets
from flask import Blueprint, current_app, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from backend.database.db import connect, now_iso

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def user_json(row):
    return {"id": row["id"], "username": row["username"], "email": row["email"], "avatar_url": row["avatar_url"], "bio": row["bio"], "role": row["role"], "created_at": row["created_at"]}


@bp.get("/csrf")
def csrf():
    session.setdefault("csrf_token", secrets.token_urlsafe(24))
    return jsonify({"csrf_token": session["csrf_token"]})


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username, email, password = str(data.get("username", "")).strip(), str(data.get("email", "")).strip().lower(), str(data.get("password", ""))
    if len(username) < 2 or len(username) > 30:
        return jsonify(error="用户名长度需为 2-30 个字符"), 400
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify(error="请输入有效邮箱"), 400
    if len(password) < 6:
        return jsonify(error="密码至少需要 6 个字符"), 400
    db = connect(current_app.config["DATABASE_PATH"])
    try:
        db.execute("INSERT INTO users(username,email,password_hash,created_at) VALUES (?,?,?,?)", (username, email, generate_password_hash(password), now_iso()))
        db.commit()
        row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        session["user_id"] = row["id"]
        session.setdefault("csrf_token", secrets.token_urlsafe(24))
        return jsonify(user_json(row)), 201
    except Exception as exc:
        if "UNIQUE" in str(exc):
            return jsonify(error="用户名或邮箱已存在"), 409
        raise
    finally:
        db.close()


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    identity, password = str(data.get("identity", data.get("email", ""))).strip(), str(data.get("password", ""))
    db = connect(current_app.config["DATABASE_PATH"])
    row = db.execute("SELECT * FROM users WHERE lower(email)=lower(?) OR username=?", (identity, identity)).fetchone()
    db.close()
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify(error="用户名或密码错误"), 401
    session["user_id"] = row["id"]
    session.setdefault("csrf_token", secrets.token_urlsafe(24))
    return jsonify(user_json(row))


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify(message="已退出登录")


@bp.get("/me")
def me():
    uid = session.get("user_id")
    if not uid:
        return jsonify(user=None)
    db = connect(current_app.config["DATABASE_PATH"])
    row = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    db.close()
    return jsonify(user=user_json(row) if row else None)


@bp.post("/change-password")
def change_password():
    uid = session.get("user_id")
    if not uid:
        return jsonify(error="请先登录"), 401
    data = request.get_json(silent=True) or {}
    current = str(data.get("current_password", ""))
    new_password = str(data.get("new_password", ""))
    confirm = str(data.get("confirm_password", ""))
    if len(new_password) < 6:
        return jsonify(error="新密码至少需要 6 个字符"), 400
    if new_password != confirm:
        return jsonify(error="两次输入的新密码不一致"), 400
    db = connect(current_app.config["DATABASE_PATH"])
    row = db.execute("SELECT password_hash FROM users WHERE id=?", (uid,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], current):
        db.close()
        return jsonify(error="当前密码不正确"), 400
    if check_password_hash(row["password_hash"], new_password):
        db.close()
        return jsonify(error="新密码不能与当前密码相同"), 400
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_password), uid))
    db.commit()
    db.close()
    return jsonify(message="密码已修改，请重新登录")
