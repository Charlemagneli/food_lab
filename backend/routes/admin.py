from flask import Blueprint, current_app, jsonify, request, session
from backend.database.db import connect, now_iso

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def guard():
    uid = session.get("user_id")
    if not uid: return None, (jsonify(error="请先登录"), 401)
    db = connect(current_app.config["DATABASE_PATH"]); row = db.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone(); db.close()
    if not row or row["role"] != "admin": return None, (jsonify(error="需要管理员权限"), 403)
    return uid, None


@bp.get("/stats")
def stats():
    _, error = guard()
    if error: return error
    db = connect(current_app.config["DATABASE_PATH"]); result = {"users": db.execute("SELECT count(*) FROM users").fetchone()[0], "recipes": db.execute("SELECT count(*) FROM recipes").fetchone()[0], "pending": db.execute("SELECT count(*) FROM recipes WHERE status='pending'").fetchone()[0], "featured": db.execute("SELECT count(*) FROM recipes WHERE is_featured=1 AND status='published'").fetchone()[0], "comments": db.execute("SELECT count(*) FROM comments").fetchone()[0]}; db.close(); return jsonify(data=result)


@bp.get("/recipes")
def pending_recipes():
    _, error = guard()
    if error: return error
    status = request.args.get("status", "").strip()
    params = []
    where = ""
    if status in {"draft", "pending", "published", "rejected"}:
        where = " WHERE r.status=?"
        params.append(status)
    db = connect(current_app.config["DATABASE_PATH"])
    rows = [dict(x) for x in db.execute(f"""SELECT r.id,r.title,r.description,r.cover_image,r.status,r.is_featured,
        r.cuisine,r.meal_type,r.prep_time,r.cook_time,r.created_at,r.updated_at,u.username AS author
        FROM recipes r JOIN users u ON u.id=r.author_id{where} ORDER BY
        CASE r.status WHEN 'pending' THEN 0 WHEN 'published' THEN 1 ELSE 2 END, r.updated_at DESC""", params).fetchall()]
    db.close()
    return jsonify(items=rows)


@bp.patch("/recipes/<int:recipe_id>")
def moderate_recipe(recipe_id):
    _, error = guard()
    if error: return error
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    featured = payload.get("is_featured", payload.get("featured"))
    if status is not None:
        status = str(status).strip()
        if status not in {"published", "rejected", "draft", "pending"}:
            return jsonify(error="无效状态"), 400
    if featured is not None and not isinstance(featured, (bool, int)):
        return jsonify(error="编辑精选状态无效"), 400
    if status is None and featured is None:
        return jsonify(error="请提供审核状态或编辑精选状态"), 400
    db = connect(current_app.config["DATABASE_PATH"])
    if not db.execute("SELECT 1 FROM recipes WHERE id=?", (recipe_id,)).fetchone():
        db.close(); return jsonify(error="菜谱不存在"), 404
    updates, params = [], []
    if status is not None:
        updates.append("status=?"); params.append(status)
    if featured is not None:
        updates.append("is_featured=?"); params.append(1 if bool(featured) else 0)
    updates.append("updated_at=?"); params.append(now_iso()); params.append(recipe_id)
    db.execute(f"UPDATE recipes SET {', '.join(updates)} WHERE id=?", params)
    db.commit()
    row = db.execute("SELECT status,is_featured FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    db.close()
    return jsonify(message="菜谱设置已更新", status=row["status"], is_featured=bool(row["is_featured"]))


@bp.patch("/recipes/<int:recipe_id>/featured")
def set_recipe_featured(recipe_id):
    """独立的编辑精选开关接口，避免和审核状态更新混用。"""
    _, error = guard()
    if error: return error
    payload = request.get_json(silent=True) or {}
    if "is_featured" not in payload:
        return jsonify(error="请提供 is_featured（true 或 false）"), 400
    featured = payload["is_featured"]
    if not isinstance(featured, (bool, int)):
        return jsonify(error="编辑精选状态无效"), 400
    db = connect(current_app.config["DATABASE_PATH"])
    if not db.execute("SELECT 1 FROM recipes WHERE id=?", (recipe_id,)).fetchone():
        db.close(); return jsonify(error="菜谱不存在"), 404
    db.execute("UPDATE recipes SET is_featured=?,updated_at=? WHERE id=?", (1 if bool(featured) else 0, now_iso(), recipe_id))
    db.commit()
    row = db.execute("SELECT is_featured FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    db.close()
    return jsonify(message="编辑精选状态已更新", recipe_id=recipe_id, is_featured=bool(row["is_featured"]))


@bp.get("/users")
def users():
    _, error = guard()
    if error: return error
    db = connect(current_app.config["DATABASE_PATH"]); rows = [dict(x) for x in db.execute("SELECT id,username,email,role,created_at FROM users ORDER BY created_at DESC").fetchall()]; db.close(); return jsonify(items=rows)


@bp.delete("/users/<int:user_id>")
def delete_user(user_id):
    uid, error = guard()
    if error: return error
    if uid == user_id: return jsonify(error="不能删除当前管理员账号"), 400
    db = connect(current_app.config["DATABASE_PATH"]); db.execute("DELETE FROM users WHERE id=?", (user_id,)); db.commit(); db.close(); return jsonify(message="用户已删除")


@bp.get("/comments")
def all_comments():
    _, error = guard()
    if error: return error
    db = connect(current_app.config["DATABASE_PATH"]); rows = [dict(x) for x in db.execute("SELECT c.id,c.content,c.created_at,u.username,r.title FROM comments c JOIN users u ON u.id=c.user_id JOIN recipes r ON r.id=c.recipe_id ORDER BY c.created_at DESC").fetchall()]; db.close(); return jsonify(items=rows)
