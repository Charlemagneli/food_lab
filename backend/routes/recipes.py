import json
import os
import re
import uuid
from flask import Blueprint, current_app, jsonify, request, session
from werkzeug.utils import secure_filename
from backend.database.db import connect, now_iso
from backend.services.recipe_service import recipe_detail, recipe_summary

bp = Blueprint("recipes", __name__, url_prefix="/api")


def require_user():
    if not session.get("user_id"):
        return None, (jsonify(error="请先登录"), 401)
    return session["user_id"], None


def save_file(file):
    if not file or not file.filename:
        return None
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return None
    name = f"{uuid.uuid4().hex}{ext}"
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, name))
    return f"/images/uploads/{name}"


def form_data():
    if request.mimetype and request.mimetype.startswith("multipart/"):
        data = request.form.to_dict()
        data["ingredients"] = json.loads(data.get("ingredients", "[]"))
        data["steps"] = json.loads(data.get("steps", "[]"))
        data["tags"] = [x.strip() for x in data.get("tags", "").split(",") if x.strip()]
        data["cover_image"] = save_file(request.files.get("cover_image")) or data.get("cover_image")
        return data
    data = request.get_json(silent=True) or {}
    data.setdefault("ingredients", [])
    data.setdefault("steps", [])
    data.setdefault("tags", [])
    return data


def list_query(db, include_unpublished=False):
    q = request.args.get("q", "").strip()
    where, params = ["1=1"], []
    if not include_unpublished:
        where.append("r.status='published'")
    if q:
        where.append("(r.title LIKE ? OR r.description LIKE ? OR r.cuisine LIKE ? OR r.meal_type LIKE ? OR u.username LIKE ? OR EXISTS (SELECT 1 FROM recipe_ingredients ri JOIN ingredients i ON i.id=ri.ingredient_id WHERE ri.recipe_id=r.id AND i.name LIKE ?) OR EXISTS (SELECT 1 FROM recipe_tags rt JOIN tags t ON t.id=rt.tag_id WHERE rt.recipe_id=r.id AND t.name LIKE ?))")
        params += [f"%{q}%"] * 7
    for field, col in (("cuisine", "r.cuisine"), ("meal_type", "r.meal_type"), ("difficulty", "r.difficulty")):
        if request.args.get(field):
            where.append(f"{col}=?"); params.append(request.args[field])
    if request.args.get("category"):
        where.append("(c.slug=? OR c.name=?)"); params += [request.args["category"], request.args["category"]]
    if request.args.get("max_time") and request.args["max_time"].isdigit():
        where.append("(r.prep_time+r.cook_time)<=?"); params.append(int(request.args["max_time"]))
    sort = request.args.get("sort", "latest")
    order = {"latest": "r.created_at DESC", "popular": "r.views_count DESC", "likes": "r.likes_count DESC", "favorites": "r.favorites_count DESC", "views": "r.views_count DESC"}.get(sort, "r.created_at DESC")
    try:
        page = max(1, int(request.args.get("page", 1) or 1)); per_page = min(50, max(1, int(request.args.get("per_page", 12) or 12)))
    except ValueError:
        page, per_page = 1, 12
    total = db.execute(f"SELECT count(*) FROM recipes r JOIN users u ON u.id=r.author_id LEFT JOIN categories c ON c.id=r.category_id WHERE {' AND '.join(where)}", params).fetchone()[0]
    rows = db.execute(f"""SELECT r.*,u.username AS author_name,c.name AS category_name,
      COALESCE((SELECT json_group_array(t.name) FROM recipe_tags rt JOIN tags t ON t.id=rt.tag_id WHERE rt.recipe_id=r.id),'[]') tag_list
      FROM recipes r JOIN users u ON u.id=r.author_id LEFT JOIN categories c ON c.id=r.category_id
      WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ? OFFSET ?""", params + [per_page, (page-1)*per_page]).fetchall()
    return [recipe_summary(row) for row in rows], {"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1)//per_page}


@bp.get("/health")
def health():
    return jsonify(status="ok", service="foodlab-api")


@bp.get("/categories")
def categories():
    db = connect(current_app.config["DATABASE_PATH"])
    rows = [dict(x) for x in db.execute("SELECT * FROM categories ORDER BY id").fetchall()]
    db.close()
    return jsonify(items=rows)


@bp.get("/recipes")
def recipes():
    db = connect(current_app.config["DATABASE_PATH"])
    items, pagination = list_query(db)
    db.close()
    return jsonify(items=items, pagination=pagination)


@bp.get("/recipes/<int:recipe_id>")
def get_recipe(recipe_id):
    db = connect(current_app.config["DATABASE_PATH"])
    row = db.execute("SELECT status,author_id FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    if not row:
        db.close(); return jsonify(error="菜谱不存在"), 404
    uid = session.get("user_id")
    if row["status"] != "published" and uid != row["author_id"]:
        db.close(); return jsonify(error="菜谱不存在"), 404
    db.execute("UPDATE recipes SET views_count=views_count+1 WHERE id=?", (recipe_id,)); db.commit()
    data = recipe_detail(db, recipe_id, uid)
    db.close()
    return jsonify(data=data)


def replace_relations(db, recipe_id, data):
    db.execute("DELETE FROM recipe_ingredients WHERE recipe_id=?", (recipe_id,))
    for pos, item in enumerate(data.get("ingredients", [])):
        name = str(item.get("name", "")).strip()
        if not name: continue
        db.execute("INSERT OR IGNORE INTO ingredients(name) VALUES (?)", (name,))
        iid = db.execute("SELECT id FROM ingredients WHERE name=?", (name,)).fetchone()[0]
        db.execute("INSERT INTO recipe_ingredients(recipe_id,ingredient_id,amount,unit,position) VALUES (?,?,?,?,?)", (recipe_id, iid, str(item.get("amount", "")), str(item.get("unit", "")), pos))
    db.execute("DELETE FROM steps WHERE recipe_id=?", (recipe_id,))
    for pos, item in enumerate(data.get("steps", []), 1):
        text = str(item.get("instruction", item.get("text", ""))).strip()
        if text: db.execute("INSERT INTO steps(recipe_id,position,instruction,image_url) VALUES (?,?,?,?)", (recipe_id, pos, text, item.get("image_url")))
    db.execute("DELETE FROM recipe_tags WHERE recipe_id=?", (recipe_id,))
    for name in data.get("tags", []):
        name = str(name).strip()
        if not name: continue
        slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", name.lower()).strip("-") or uuid.uuid4().hex[:8]
        db.execute("INSERT OR IGNORE INTO tags(name,slug) VALUES (?,?)", (name, slug))
        tid = db.execute("SELECT id FROM tags WHERE name=?", (name,)).fetchone()[0]
        db.execute("INSERT OR IGNORE INTO recipe_tags(recipe_id,tag_id) VALUES (?,?)", (recipe_id, tid))


@bp.post("/recipes")
def create_recipe():
    uid, error = require_user()
    if error: return error
    data = form_data()
    title = str(data.get("title", "")).strip()
    if not title or len(title) > 120: return jsonify(error="菜谱名称不能为空且不能超过 120 个字符"), 400
    db = connect(current_app.config["DATABASE_PATH"])
    status = "draft" if data.get("status") == "draft" else "pending"
    now = now_iso()
    cur = db.execute("""INSERT INTO recipes(title,description,cover_image,author_id,cuisine,meal_type,category_id,difficulty,prep_time,cook_time,servings,status,created_at,updated_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (title, str(data.get("description", "")), data.get("cover_image"), uid, str(data.get("cuisine", "")), str(data.get("meal_type", "")), data.get("category_id") or None, str(data.get("difficulty", "简单")), int(data.get("prep_time", 0) or 0), int(data.get("cook_time", 0) or 0), float(data.get("servings", 2) or 2), status, now, now))
    replace_relations(db, cur.lastrowid, data); db.commit(); item = recipe_detail(db, cur.lastrowid, uid); db.close()
    return jsonify(data=item), 201


@bp.route("/recipes/<int:recipe_id>", methods=["PUT", "PATCH"])
def update_recipe(recipe_id):
    uid, error = require_user()
    if error: return error
    db = connect(current_app.config["DATABASE_PATH"]); row = db.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    if not row: db.close(); return jsonify(error="菜谱不存在"), 404
    user = db.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
    if row["author_id"] != uid and user["role"] != "admin": db.close(); return jsonify(error="没有权限"), 403
    data = form_data(); now = now_iso(); status = "draft" if data.get("status") == "draft" else ("pending" if user["role"] != "admin" else data.get("status", row["status"]))
    db.execute("""UPDATE recipes SET title=?,description=?,cover_image=COALESCE(?,cover_image),cuisine=?,meal_type=?,category_id=?,difficulty=?,prep_time=?,cook_time=?,servings=?,status=?,updated_at=? WHERE id=?""", (str(data.get("title", row["title"])).strip(), str(data.get("description", row["description"])), data.get("cover_image"), str(data.get("cuisine", row["cuisine"])), str(data.get("meal_type", row["meal_type"])), data.get("category_id") or None, str(data.get("difficulty", row["difficulty"])), int(data.get("prep_time", row["prep_time"]) or 0), int(data.get("cook_time", row["cook_time"]) or 0), float(data.get("servings", row["servings"]) or 2), status, now, recipe_id))
    replace_relations(db, recipe_id, data); db.commit(); item = recipe_detail(db, recipe_id, uid); db.close(); return jsonify(data=item)


@bp.delete("/recipes/<int:recipe_id>")
def delete_recipe(recipe_id):
    uid, error = require_user()
    if error: return error
    db = connect(current_app.config["DATABASE_PATH"]); row = db.execute("SELECT author_id FROM recipes WHERE id=?", (recipe_id,)).fetchone(); role = db.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
    if not row: db.close(); return jsonify(error="菜谱不存在"), 404
    if row["author_id"] != uid and role["role"] != "admin": db.close(); return jsonify(error="没有权限"), 403
    db.execute("DELETE FROM recipes WHERE id=?", (recipe_id,)); db.commit(); db.close(); return jsonify(message="菜谱已删除")


@bp.route("/recipes/<int:recipe_id>/favorite", methods=["POST", "DELETE"])
def favorite(recipe_id):
    uid, error = require_user()
    if error: return error
    db = connect(current_app.config["DATABASE_PATH"]); exists = db.execute("SELECT 1 FROM favorites WHERE user_id=? AND recipe_id=?", (uid, recipe_id)).fetchone()
    if exists or request.method == "DELETE":
        db.execute("DELETE FROM favorites WHERE user_id=? AND recipe_id=?", (uid, recipe_id)); active = False
    else:
        db.execute("INSERT INTO favorites VALUES (?,?,?)", (uid, recipe_id, now_iso())); active = True
    db.execute("UPDATE recipes SET favorites_count=(SELECT count(*) FROM favorites WHERE recipe_id=?) WHERE id=?", (recipe_id, recipe_id)); db.commit(); count = db.execute("SELECT favorites_count FROM recipes WHERE id=?", (recipe_id,)).fetchone()[0]; db.close(); return jsonify(active=active, count=count)


@bp.route("/recipes/<int:recipe_id>/like", methods=["POST", "DELETE"])
def like(recipe_id):
    uid, error = require_user()
    if error: return error
    db = connect(current_app.config["DATABASE_PATH"]); exists = db.execute("SELECT 1 FROM likes WHERE user_id=? AND recipe_id=?", (uid, recipe_id)).fetchone()
    if exists or request.method == "DELETE":
        db.execute("DELETE FROM likes WHERE user_id=? AND recipe_id=?", (uid, recipe_id)); active = False
    else:
        db.execute("INSERT INTO likes VALUES (?,?,?)", (uid, recipe_id, now_iso())); active = True
    db.execute("UPDATE recipes SET likes_count=(SELECT count(*) FROM likes WHERE recipe_id=?) WHERE id=?", (recipe_id, recipe_id)); db.commit(); count = db.execute("SELECT likes_count FROM recipes WHERE id=?", (recipe_id,)).fetchone()[0]; db.close(); return jsonify(active=active, count=count)


@bp.get("/recipes/<int:recipe_id>/comments")
def comments(recipe_id):
    db = connect(current_app.config["DATABASE_PATH"]); rows = [dict(x) for x in db.execute("SELECT c.id,c.content,c.created_at,u.username,u.avatar_url,(SELECT count(*) FROM comment_likes cl WHERE cl.comment_id=c.id) likes_count FROM comments c JOIN users u ON u.id=c.user_id WHERE c.recipe_id=? ORDER BY c.created_at DESC", (recipe_id,)).fetchall()]; db.close(); return jsonify(items=rows)


@bp.post("/recipes/<int:recipe_id>/comments")
def add_comment(recipe_id):
    uid, error = require_user()
    if error: return error
    content = str((request.get_json(silent=True) or {}).get("content", "")).strip()
    if not content or len(content) > 500: return jsonify(error="评论不能为空且不能超过 500 个字符"), 400
    db = connect(current_app.config["DATABASE_PATH"]); db.execute("INSERT INTO comments(user_id,recipe_id,content,created_at) VALUES (?,?,?,?)", (uid, recipe_id, content, now_iso())); db.commit(); db.close(); return jsonify(message="评论已发布"), 201


@bp.delete("/comments/<int:comment_id>")
def delete_comment(comment_id):
    uid, error = require_user()
    if error: return error
    db = connect(current_app.config["DATABASE_PATH"]); row = db.execute("SELECT user_id FROM comments WHERE id=?", (comment_id,)).fetchone(); role = db.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
    if not row: db.close(); return jsonify(error="评论不存在"), 404
    if row["user_id"] != uid and role["role"] != "admin": db.close(); return jsonify(error="没有权限"), 403
    db.execute("DELETE FROM comments WHERE id=?", (comment_id,)); db.commit(); db.close(); return jsonify(message="评论已删除")


@bp.route("/comments/<int:comment_id>/like", methods=["POST", "DELETE"])
def like_comment(comment_id):
    uid, error = require_user()
    if error: return error
    db = connect(current_app.config["DATABASE_PATH"])
    exists = db.execute("SELECT 1 FROM comment_likes WHERE user_id=? AND comment_id=?", (uid, comment_id)).fetchone()
    if exists or request.method == "DELETE":
        db.execute("DELETE FROM comment_likes WHERE user_id=? AND comment_id=?", (uid, comment_id)); active = False
    else:
        db.execute("INSERT INTO comment_likes VALUES (?,?,?)", (uid, comment_id, now_iso())); active = True
    db.commit(); count = db.execute("SELECT count(*) FROM comment_likes WHERE comment_id=?", (comment_id,)).fetchone()[0]; db.close()
    return jsonify(active=active, count=count)
