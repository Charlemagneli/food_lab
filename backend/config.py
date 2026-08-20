import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "foodlab-development-change-me")
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "instance" / "foodlab.sqlite3"))
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "frontend" / "images" / "uploads"))
    CONTENT_FILTER_WORDS_FILE = os.getenv(
        "CONTENT_FILTER_WORDS_FILE", str(BASE_DIR / "backend" / "data" / "blocked_words.txt")
    )
    CONTENT_FILTER_EXTRA_WORDS = os.getenv("CONTENT_FILTER_EXTRA_WORDS", "")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
