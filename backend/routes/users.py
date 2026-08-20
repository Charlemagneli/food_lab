import json
from flask import Blueprint, current_app, jsonify, request, session
from backend.database.db import connect

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.patch("/me")
def update_me():
    uid = session.get("user_id")
    if not uid:
        return jsonify(error="请先登录"), 401
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    bio = str(data.get("bio", "")).strip()
    interests = data.get("interests", [])
    if isinstance(interests, str):
        interests = [item.strip() for item in interests.split(",") if item.strip()]
    interests = [str(item).strip() for item in interests if str(item).strip()][:12]
    if len(username) < 2 or len(username) > 30:
        return jsonify(error="用户名长度需为 2-30 个字符"), 400
    if len(bio) > 300:
        return jsonify(error="个人简介不能超过 300 个字符"), 400
    db = connect(current_app.config["DATABASE_PATH"])
    try:
        db.execute("UPDATE users SET username=?,bio=?,interests=?,avatar_url=? WHERE id=?", (username, bio, json.dumps(interests, ensure_ascii=False), data.get("avatar_url"), uid))
        db.commit()
    except Exception as exc:
        db.close()
        if "UNIQUE" in str(exc):
            return jsonify(error="用户名已存在"), 409
        raise
    row = db.execute("SELECT id,username,email,avatar_url,bio,interests,role,created_at FROM users WHERE id=?", (uid,)).fetchone()
    db.close()
    result = dict(row)
    result["interests"] = json.loads(result.get("interests") or "[]")
    return jsonify(user=result)


@bp.get("/me/recipes")
def my_recipes():
    uid = session.get("user_id")
    if not uid:
        return jsonify(error="请先登录"), 401
    db = connect(current_app.config["DATABASE_PATH"])
    rows = [dict(x) for x in db.execute("SELECT id,title,description,cover_image,cuisine,difficulty,prep_time,cook_time,status,is_featured,likes_count,favorites_count FROM recipes WHERE author_id=? ORDER BY updated_at DESC", (uid,)).fetchall()]
    db.close()
    return jsonify(items=rows)


@bp.get("/<int:user_id>")
def profile(user_id):
    db = connect(current_app.config["DATABASE_PATH"])
    user = db.execute("SELECT id,username,avatar_url,bio,interests,role,created_at FROM users WHERE id=?", (user_id,)).fetchone()
    if not user: db.close(); return jsonify(error="用户不存在"), 404
    recipes = [dict(x) for x in db.execute("SELECT id,title,description,cover_image,cuisine,difficulty,prep_time,cook_time,is_featured,likes_count,favorites_count FROM recipes WHERE author_id=? AND status='published' ORDER BY created_at DESC", (user_id,)).fetchall()]
    counts = {"recipes": db.execute("SELECT count(*) FROM recipes WHERE author_id=? AND status='published'", (user_id,)).fetchone()[0], "favorites": db.execute("SELECT count(*) FROM favorites WHERE user_id=?", (user_id,)).fetchone()[0], "likes": db.execute("SELECT count(*) FROM likes l JOIN recipes r ON r.id=l.recipe_id WHERE r.author_id=?", (user_id,)).fetchone()[0]}
    user_data = dict(user)
    user_data["interests"] = json.loads(user_data.get("interests") or "[]")
    user_data["followers"] = db.execute("SELECT count(*) FROM followers WHERE followed_id=?", (user_id,)).fetchone()[0]
    user_data["recipes"] = recipes
    db.close(); return jsonify(user=user_data, counts=counts, recipes=recipes)


@bp.get("/me/favorites")
def my_favorites():
    if not session.get("user_id"): return jsonify(error="请先登录"), 401
    db = connect(current_app.config["DATABASE_PATH"]); rows = [dict(x) for x in db.execute("SELECT r.id,r.title,r.description,r.cover_image,r.cuisine,r.difficulty,r.prep_time,r.cook_time,r.is_featured,r.likes_count,r.favorites_count FROM favorites f JOIN recipes r ON r.id=f.recipe_id WHERE f.user_id=? ORDER BY f.created_at DESC", (session["user_id"],)).fetchall()]; db.close(); return jsonify(items=rows)


@bp.get("/favorites")
def favorites_alias():
    return my_favorites()
