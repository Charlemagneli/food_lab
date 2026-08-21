from flask import Blueprint, current_app, jsonify, session

from backend.database.db import connect

bp = Blueprint("messages", __name__, url_prefix="/api/messages")


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify(error="请先登录"), 401)
    return uid, None


@bp.get("")
def system_messages():
    uid, error = current_user()
    if error:
        return error
    db = connect(current_app.config["DATABASE_PATH"])
    items = [dict(row) for row in db.execute("""SELECT id,content,is_read,created_at
        FROM messages WHERE recipient_id=? AND message_type='platform'
        ORDER BY created_at DESC""", (uid,)).fetchall()]
    db.close()
    return jsonify(items=items, unread=sum(1 for item in items if not item["is_read"]))


@bp.get("/unread-count")
def unread_count():
    uid, error = current_user()
    if error:
        return error
    db = connect(current_app.config["DATABASE_PATH"])
    count = db.execute("""SELECT count(*) FROM messages
        WHERE recipient_id=? AND message_type='platform' AND is_read=0""", (uid,)).fetchone()[0]
    db.close()
    return jsonify(count=count)


@bp.patch("/read")
def mark_read():
    uid, error = current_user()
    if error:
        return error
    db = connect(current_app.config["DATABASE_PATH"])
    db.execute("""UPDATE messages SET is_read=1
        WHERE recipient_id=? AND message_type='platform'""", (uid,))
    db.commit()
    db.close()
    return jsonify(message="系统消息已标记为已读")
