import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

_ENGINES = {}

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
 email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, avatar_url TEXT,
 bio TEXT NOT NULL DEFAULT '', interests TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'user', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS followers (
 follower_id INTEGER NOT NULL, followed_id INTEGER NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(follower_id, followed_id), CHECK(follower_id <> followed_id),
 FOREIGN KEY(follower_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY(followed_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS categories (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, slug TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS recipes (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
 cover_image TEXT, author_id INTEGER NOT NULL, cuisine TEXT NOT NULL DEFAULT '', meal_type TEXT NOT NULL DEFAULT '',
 category_id INTEGER, difficulty TEXT NOT NULL DEFAULT '简单', prep_time INTEGER NOT NULL DEFAULT 0,
 cook_time INTEGER NOT NULL DEFAULT 0, servings REAL NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'pending',
 is_featured INTEGER NOT NULL DEFAULT 0,
 views_count INTEGER NOT NULL DEFAULT 0, likes_count INTEGER NOT NULL DEFAULT 0,
 favorites_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 FOREIGN KEY(author_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS ingredients (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS recipe_ingredients (
 id INTEGER PRIMARY KEY AUTOINCREMENT, recipe_id INTEGER NOT NULL, ingredient_id INTEGER NOT NULL,
 amount TEXT NOT NULL DEFAULT '', unit TEXT NOT NULL DEFAULT '', position INTEGER NOT NULL DEFAULT 0,
 FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
 FOREIGN KEY(ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS steps (
 id INTEGER PRIMARY KEY AUTOINCREMENT, recipe_id INTEGER NOT NULL, position INTEGER NOT NULL,
 instruction TEXT NOT NULL, image_url TEXT, FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS tags (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, slug TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS recipe_tags (
 recipe_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, PRIMARY KEY(recipe_id, tag_id),
 FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
 FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS favorites (
 user_id INTEGER NOT NULL, recipe_id INTEGER NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(user_id, recipe_id), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS likes (
 user_id INTEGER NOT NULL, recipe_id INTEGER NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(user_id, recipe_id), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS comments (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, recipe_id INTEGER NOT NULL,
 content TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS comment_likes (
 user_id INTEGER NOT NULL, comment_id INTEGER NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(user_id, comment_id), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
 FOREIGN KEY(comment_id) REFERENCES comments(id) ON DELETE CASCADE
);
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    key = str(Path(path).resolve())
    engine = _ENGINES.setdefault(key, create_engine(f"sqlite:///{key}", connect_args={"check_same_thread": False}, poolclass=NullPool))
    db = engine.raw_connection()
    db.driver_connection.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db(path):
    db = connect(path)
    db.executescript(SCHEMA)
    columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()}
    if "interests" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN interests TEXT NOT NULL DEFAULT ''")
    recipe_columns = {row["name"] for row in db.execute("PRAGMA table_info(recipes)").fetchall()}
    if "is_featured" not in recipe_columns:
        db.execute("ALTER TABLE recipes ADD COLUMN is_featured INTEGER NOT NULL DEFAULT 0")
    seed(db)
    db.commit()
    db.close()


def seed(db):
    categories = [
        ("中餐", "chinese"), ("西餐", "western"), ("日料", "japanese"),
        ("韩餐", "korean"), ("东南亚", "southeast-asian"), ("甜品", "dessert"),
        ("饮料", "drinks"), ("早餐", "breakfast"), ("汤", "soup"),
        ("主食", "staple"), ("小吃", "snack")
    ]
    db.executemany("INSERT OR IGNORE INTO categories(name, slug) VALUES (?, ?)", categories)
    from werkzeug.security import generate_password_hash
    admin_hash = generate_password_hash("FoodLab-admin-123")
    db.execute("INSERT OR IGNORE INTO users(username,email,password_hash,bio,role,created_at) VALUES (?,?,?,?,?,?)",
               ("FoodLab 管理员", "admin@foodlab.local", admin_hash, "守护食研所社区", "admin", now_iso()))
    test_user_hash = generate_password_hash("FoodLab-user-123")
    db.execute("INSERT OR IGNORE INTO users(username,email,password_hash,bio,role,created_at) VALUES (?,?,?,?,?,?)",
               ("FoodLab 测试用户", "user@foodlab.local", test_user_hash, "用于体验食研所普通用户功能", "user", now_iso()))
    existing_admin = db.execute("SELECT password_hash FROM users WHERE email=?", ("admin@foodlab.local",)).fetchone()
    if existing_admin and "$foodlab$" in existing_admin["password_hash"]:
        db.execute("UPDATE users SET password_hash=? WHERE email=?", (admin_hash, "admin@foodlab.local"))
    author = db.execute("SELECT id FROM users WHERE email=?", ("admin@foodlab.local",)).fetchone()[0]
    cat = db.execute("SELECT id FROM categories WHERE slug='chinese'").fetchone()[0]
    if not db.execute("SELECT 1 FROM recipes LIMIT 1").fetchone():
        recipes = [
            ("番茄炒蛋", "酸甜开胃的家常快手菜，十分钟就能端上餐桌。", "", author, "中餐", "晚餐", cat, "简单", 5, 10, 2, "published", 1, 128, 24, 18),
            ("香煎鸡胸肉沙拉", "清爽高蛋白的一人食，适合工作日的轻盈午餐。", "", author, "西餐", "午餐", None, "简单", 10, 15, 1, "published", 0, 86, 19, 12),
            ("南瓜奶油浓汤", "烤南瓜与奶油交织出的温暖滋味。", "", author, "西餐", "晚餐", None, "中等", 15, 25, 3, "published", 0, 72, 16, 9),
        ]
        db.executemany("""INSERT INTO recipes(title,description,cover_image,author_id,cuisine,meal_type,category_id,difficulty,prep_time,cook_time,servings,status,is_featured,views_count,likes_count,favorites_count,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, ?, ?, ?)""", [r + (now_iso(), now_iso()) for r in recipes])
        for recipe in db.execute("SELECT id,title FROM recipes").fetchall():
            names = {"番茄炒蛋": [("鸡蛋", "3", "个"), ("番茄", "2", "个"), ("食用油", "适量", "")],
                     "香煎鸡胸肉沙拉": [("鸡胸肉", "1", "块"), ("生菜", "100", "克"), ("橄榄油", "1", "勺")],
                     "南瓜奶油浓汤": [("南瓜", "300", "克"), ("淡奶油", "100", "毫升"), ("黑胡椒", "少许", "")]}[recipe["title"]]
            for pos, (name, amount, unit) in enumerate(names):
                db.execute("INSERT OR IGNORE INTO ingredients(name) VALUES (?)", (name,))
                iid = db.execute("SELECT id FROM ingredients WHERE name=?", (name,)).fetchone()[0]
                db.execute("INSERT INTO recipe_ingredients(recipe_id,ingredient_id,amount,unit,position) VALUES (?,?,?,?,?)", (recipe["id"], iid, amount, unit, pos))
            steps = {"番茄炒蛋": ["番茄洗净切块，鸡蛋加少许盐打散。", "热锅下油，先将鸡蛋炒至凝固后盛出。", "番茄炒出汁水，倒回鸡蛋翻匀即可。"],
                     "香煎鸡胸肉沙拉": ["鸡胸肉用盐和黑胡椒腌制十分钟。", "平底锅小火煎至两面金黄并熟透。", "搭配生菜和橄榄油摆盘。"],
                     "南瓜奶油浓汤": ["南瓜去皮切块后蒸熟。", "南瓜加少量清水搅打成泥并煮沸。", "关火拌入淡奶油和黑胡椒。"]}[recipe["title"]]
            for pos, instruction in enumerate(steps, 1):
                db.execute("INSERT INTO steps(recipe_id,position,instruction) VALUES (?,?,?)", (recipe["id"], pos, instruction))
            tag_names = ["家常菜", "快手菜"] if recipe["title"] == "番茄炒蛋" else ["清爽", "一人食"]
            for name in tag_names:
                slug = name.lower().replace(" ", "-")
                db.execute("INSERT OR IGNORE INTO tags(name,slug) VALUES (?,?)", (name, slug))
                tid = db.execute("SELECT id FROM tags WHERE name=?", (name,)).fetchone()[0]
                db.execute("INSERT OR IGNORE INTO recipe_tags(recipe_id,tag_id) VALUES (?,?)", (recipe["id"], tid))


@contextmanager
def transaction(path):
    db = connect(path)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def json_load(value, default=None):
    try:
        return json.loads(value) if value else (default if default is not None else [])
    except (TypeError, ValueError):
        return default if default is not None else []
