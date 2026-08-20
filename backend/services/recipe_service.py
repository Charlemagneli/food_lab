from backend.database.db import json_load


def recipe_summary(row):
    if not row:
        return None
    item = dict(row)
    item["author"] = item.pop("author_name", "")
    item["category"] = item.pop("category_name", None)
    # 烹饪时间不再由用户设置；保留字段仅为兼容旧数据，展示时间取准备时间。
    item["total_time"] = int(item.get("prep_time", 0) or 0)
    item["tags"] = json_load(item.pop("tag_list", "[]"))
    return item


def recipe_detail(db, recipe_id, viewer_id=None):
    row = db.execute("""SELECT r.*, u.username AS author_name, u.avatar_url, c.name AS category_name,
        EXISTS(SELECT 1 FROM favorites f WHERE f.recipe_id=r.id AND f.user_id=?) AS is_favorited,
        EXISTS(SELECT 1 FROM likes l WHERE l.recipe_id=r.id AND l.user_id=?) AS is_liked,
        COALESCE((SELECT json_group_array(t.name) FROM recipe_tags rt JOIN tags t ON t.id=rt.tag_id WHERE rt.recipe_id=r.id), '[]') AS tag_list
        FROM recipes r JOIN users u ON u.id=r.author_id LEFT JOIN categories c ON c.id=r.category_id WHERE r.id=?""",
        (viewer_id or -1, viewer_id or -1, recipe_id)).fetchone()
    if not row:
        return None
    result = recipe_summary(row)
    result["ingredients"] = [dict(x) for x in db.execute("""SELECT i.name,ri.amount,ri.unit,ri.position
        FROM recipe_ingredients ri JOIN ingredients i ON i.id=ri.ingredient_id WHERE ri.recipe_id=? ORDER BY ri.position""", (recipe_id,)).fetchall()]
    result["steps"] = [dict(x) for x in db.execute("SELECT position,instruction,image_url FROM steps WHERE recipe_id=? ORDER BY position", (recipe_id,)).fetchall()]
    result["comments"] = [dict(x) for x in db.execute("""SELECT c.id,c.content,c.created_at,u.username,u.avatar_url,
        (SELECT count(*) FROM comment_likes cl WHERE cl.comment_id=c.id) AS likes_count,
        EXISTS(SELECT 1 FROM comment_likes cl WHERE cl.comment_id=c.id AND cl.user_id=?) AS is_liked
        FROM comments c JOIN users u ON u.id=c.user_id WHERE c.recipe_id=? ORDER BY c.created_at DESC""", (viewer_id or -1, recipe_id)).fetchall()]
    return result
