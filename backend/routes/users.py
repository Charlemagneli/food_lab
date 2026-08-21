import json
import os
import uuid
from flask import Blueprint, current_app, jsonify, request, session
from werkzeug.utils import secure_filename
from backend.database.db import connect

bp = Blueprint("users", __name__, url_prefix="/api/users")

def save_avatar(file):
    if not file or not file.filename: return None
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    mime_ext = {
        "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
        "image/gif": ".gif", "image/avif": ".avif", "image/bmp": ".bmp",
    }
    allowed_exts = set(mime_ext.values()) | {".jfif"}
    if ext not in allowed_exts:
        ext = mime_ext.get((file.mimetype or "").lower())
    if not ext: return None
    filename = f"avatar-{uuid.uuid4().hex}{ext}"
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
    return f"/images/uploads/{filename}"


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
        # Preserve an avatar uploaded through the dedicated multipart endpoint
        # when a profile form submission does not include avatar_url.
        db.execute("UPDATE users SET username=?,bio=?,interests=?,avatar_url=COALESCE(?, avatar_url) WHERE id=?", (username, bio, json.dumps(interests, ensure_ascii=False), data.get("avatar_url"), uid))
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

@bp.post("/me/avatar")
def upload_avatar():
    uid = session.get("user_id")
    if not uid: return jsonify(error="请先登录"), 401
    avatar_url = save_avatar(request.files.get("avatar"))
    if not avatar_url: return jsonify(error="请上传有效的图片文件（JPG、PNG、WEBP、GIF 等）"), 400
    db = connect(current_app.config["DATABASE_PATH"])
    db.execute("UPDATE users SET avatar_url=? WHERE id=?", (avatar_url, uid)); db.commit()
    row = db.execute("SELECT id,username,email,avatar_url,bio,interests,role,created_at FROM users WHERE id=?", (uid,)).fetchone(); db.close()
    result = dict(row); result["interests"] = json.loads(result.get("interests") or "[]")
    return jsonify(user=result, avatar_url=avatar_url)


@bp.get("/me/recipes")
def my_recipes():
    uid = session.get("user_id")
    if not uid:
        return jsonify(error="请先登录"), 401
    db = connect(current_app.config["DATABASE_PATH"])
    rows = [dict(x) for x in db.execute("SELECT id,title,description,cover_image,cuisine,prep_time,cook_time,status,is_featured,likes_count,favorites_count FROM recipes WHERE author_id=? ORDER BY updated_at DESC", (uid,)).fetchall()]
    db.close()
    return jsonify(items=rows)


@bp.get("/<int:user_id>")
def profile(user_id):
    db = connect(current_app.config["DATABASE_PATH"])
    user = db.execute("SELECT id,username,avatar_url,bio,interests,role,created_at FROM users WHERE id=?", (user_id,)).fetchone()
    if not user: db.close(); return jsonify(error="用户不存在"), 404
    recipes = [dict(x) for x in db.execute("SELECT id,title,description,cover_image,cuisine,prep_time,cook_time,is_featured,likes_count,favorites_count FROM recipes WHERE author_id=? AND status='published' ORDER BY created_at DESC", (user_id,)).fetchall()]
    counts = {"recipes": db.execute("SELECT count(*) FROM recipes WHERE author_id=? AND status='published'", (user_id,)).fetchone()[0], "favorites": db.execute("SELECT count(*) FROM favorites WHERE user_id=?", (user_id,)).fetchone()[0], "likes": db.execute("SELECT count(*) FROM likes l JOIN recipes r ON r.id=l.recipe_id WHERE r.author_id=?", (user_id,)).fetchone()[0]}
    user_data = dict(user)
    user_data["interests"] = json.loads(user_data.get("interests") or "[]")
    user_data["followers"] = db.execute("SELECT count(*) FROM followers WHERE followed_id=?", (user_id,)).fetchone()[0]
    viewer_id = session.get("user_id")
    user_data["is_following"] = bool(viewer_id and db.execute("SELECT 1 FROM followers WHERE follower_id=? AND followed_id=?", (viewer_id, user_id)).fetchone())
    user_data["recipes"] = recipes
    db.close(); return jsonify(user=user_data, counts=counts, recipes=recipes)


@bp.post("/<int:user_id>/follow")
def follow_user(user_id):
    uid = session.get("user_id")
    if not uid: return jsonify(error="请先登录"), 401
    if uid == user_id: return jsonify(error="不能关注自己"), 400
    db = connect(current_app.config["DATABASE_PATH"])
    if not db.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone(): db.close(); return jsonify(error="用户不存在"), 404
    exists = db.execute("SELECT 1 FROM followers WHERE follower_id=? AND followed_id=?", (uid, user_id)).fetchone()
    if exists:
        db.execute("DELETE FROM followers WHERE follower_id=? AND followed_id=?", (uid, user_id)); active = False
    else:
        from backend.database.db import now_iso
        db.execute("INSERT INTO followers(follower_id,followed_id,created_at) VALUES (?,?,?)", (uid, user_id, now_iso())); active = True
    db.commit(); count = db.execute("SELECT count(*) FROM followers WHERE followed_id=?", (user_id,)).fetchone()[0]; db.close()
    return jsonify(active=active, count=count)


@bp.get("/me/favorites")
def my_favorites():
    if not session.get("user_id"): return jsonify(error="请先登录"), 401
    db = connect(current_app.config["DATABASE_PATH"]); rows = [dict(x) for x in db.execute("SELECT r.id,r.title,r.description,r.cover_image,r.cuisine,r.prep_time,r.cook_time,r.is_featured,r.likes_count,r.favorites_count FROM favorites f JOIN recipes r ON r.id=f.recipe_id WHERE f.user_id=? ORDER BY f.created_at DESC", (session["user_id"],)).fetchall()]; db.close(); return jsonify(items=rows)


@bp.get("/favorites")
def favorites_alias():
    return my_favorites()
