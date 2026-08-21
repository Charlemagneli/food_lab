from flask import Blueprint, current_app, jsonify, request, session
from backend.database.db import connect, now_iso

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def review_notification(status, title, reason):
    if status == "published":
        return f"你的菜谱《{title}》已通过审核，现已公开发布。"
    if status == "rejected":
        return f"你的菜谱《{title}》未通过审核。原因：{reason}。请修改后重新提交。"
    return None


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
    if status in {"draft", "pending", "published", "rejected", "hidden"}:
        where = " WHERE r.status=?"
        params.append(status)
    db = connect(current_app.config["DATABASE_PATH"])
    rows = [dict(x) for x in db.execute(f"""SELECT r.id,r.title,r.description,r.cover_image,r.status,r.is_featured,
        r.cuisine,r.created_at,r.updated_at,r.reviewed_at,r.rejection_reason,u.username AS author,
        reviewer.username AS reviewer
        FROM recipes r JOIN users u ON u.id=r.author_id LEFT JOIN users reviewer ON reviewer.id=r.reviewed_by{where} ORDER BY
        CASE r.status WHEN 'pending' THEN 0 WHEN 'published' THEN 1 ELSE 2 END, r.updated_at DESC""", params).fetchall()]
    db.close()
    return jsonify(items=rows)


@bp.get("/homepage-featured")
def homepage_featured_settings():
    _, error = guard()
    if error: return error
    db = connect(current_app.config["DATABASE_PATH"])
    setting = db.execute("SELECT value FROM site_settings WHERE key='homepage_featured_recipe_id'").fetchone()
    selected_id = int(setting["value"]) if setting and setting["value"].isdigit() else None
    candidates = [dict(row) for row in db.execute("""SELECT r.id,r.title,r.description,r.cover_image,
        r.cuisine,r.views_count,r.likes_count,u.username AS author,
        (SELECT count(*) FROM comments c WHERE c.recipe_id=r.id) AS comments_count
        FROM recipes r JOIN users u ON u.id=r.author_id
        WHERE r.status='published' AND r.is_featured=1
          AND r.cover_image IS NOT NULL AND trim(r.cover_image)<>''
        ORDER BY r.updated_at DESC""").fetchall()]
    db.close()
    return jsonify(selected_id=selected_id, items=candidates)


@bp.patch("/homepage-featured")
def update_homepage_featured():
    admin_id, error = guard()
    if error: return error
    payload = request.get_json(silent=True) or {}
    try:
        recipe_id = int(payload.get("recipe_id"))
    except (TypeError, ValueError):
        return jsonify(error="请选择首页展示菜谱"), 400
    db = connect(current_app.config["DATABASE_PATH"])
    recipe = db.execute("""SELECT id,title,cover_image FROM recipes
        WHERE id=? AND status='published' AND is_featured=1""", (recipe_id,)).fetchone()
    if not recipe:
        db.close(); return jsonify(error="首页图片只能选择已发布的编辑精选菜谱"), 400
    if not str(recipe["cover_image"] or "").strip():
        db.close(); return jsonify(error="该精选菜谱还没有封面图片"), 400
    db.execute("""INSERT INTO site_settings(key,value,updated_at,updated_by)
        VALUES ('homepage_featured_recipe_id',?,?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value,
        updated_at=excluded.updated_at,updated_by=excluded.updated_by""",
        (str(recipe_id), now_iso(), admin_id))
    db.commit(); db.close()
    return jsonify(message="首页主视觉已更新", recipe_id=recipe_id, title=recipe["title"], cover_image=recipe["cover_image"])


@bp.patch("/recipes/<int:recipe_id>")
def moderate_recipe(recipe_id):
    admin_id, error = guard()
    if error: return error
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    reason = str(payload.get("reason", "")).strip()
    featured = payload.get("is_featured", payload.get("featured"))
    if status is not None:
        status = str(status).strip()
        if status not in {"published", "rejected", "draft", "pending", "hidden"}:
            return jsonify(error="无效状态"), 400
        if status in {"rejected", "hidden"} and not reason:
            return jsonify(error="请填写驳回或隐藏原因"), 400
        if len(reason) > 300:
            return jsonify(error="处理原因不能超过 300 个字符"), 400
    if featured is not None and not isinstance(featured, (bool, int)):
        return jsonify(error="编辑精选状态无效"), 400
    if status is None and featured is None:
        return jsonify(error="请提供审核状态或编辑精选状态"), 400
    db = connect(current_app.config["DATABASE_PATH"])
    recipe = db.execute("SELECT author_id,title,status FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    if not recipe:
        db.close(); return jsonify(error="菜谱不存在"), 404
    updates, params = [], []
    if status is not None:
        updates.append("status=?"); params.append(status)
        if status in {"published", "rejected", "hidden"}:
            updates.extend(["reviewed_at=?", "reviewed_by=?", "rejection_reason=?"]); params.extend([now_iso(), admin_id, reason if status != "published" else ""])
        elif status == "pending":
            updates.extend(["reviewed_at=NULL", "reviewed_by=NULL", "rejection_reason='' "])
        if status == "hidden":
            updates.append("is_featured=0")
    if featured is not None:
        updates.append("is_featured=?"); params.append(1 if bool(featured) else 0)
    updates.append("updated_at=?"); params.append(now_iso()); params.append(recipe_id)
    db.execute(f"UPDATE recipes SET {', '.join(updates)} WHERE id=?", params)
    notification = review_notification(status, recipe["title"], reason) if status != recipe["status"] else None
    if notification:
        db.execute("""INSERT INTO messages(sender_id,recipient_id,message_type,content,created_at)
            VALUES (NULL,?,'platform',?,?)""", (recipe["author_id"], notification, now_iso()))
    db.commit()
    row = db.execute("SELECT status,is_featured,reviewed_at,rejection_reason FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    db.close()
    return jsonify(message="菜谱设置已更新", status=row["status"], is_featured=bool(row["is_featured"]), reviewed_at=row["reviewed_at"], rejection_reason=row["rejection_reason"], notification_sent=bool(notification))


@bp.delete("/recipes/<int:recipe_id>")
def delete_recipe(recipe_id):
    _, error = guard()
    if error: return error
    db = connect(current_app.config["DATABASE_PATH"])
    if not db.execute("SELECT 1 FROM recipes WHERE id=?", (recipe_id,)).fetchone():
        db.close(); return jsonify(error="菜谱不存在"), 404
    db.execute("DELETE FROM recipes WHERE id=?", (recipe_id,)); db.commit(); db.close()
    return jsonify(message="菜谱已删除")


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
