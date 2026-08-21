"""Create a consistent SQLite and upload snapshot for scheduled production backups."""

import shutil
import sqlite3
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from backend.config import Config


def create_backup(database_path, upload_folder, backup_folder):
    target = Path(backup_folder) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target.mkdir(parents=True, exist_ok=False)
    database_copy = target / "foodlab.sqlite3"
    source = sqlite3.connect(database_path)
    destination = sqlite3.connect(database_copy)
    with destination:
        source.backup(destination)
    destination.close(); source.close()
    upload_archive = target / "uploads.tar.gz"
    with tarfile.open(upload_archive, "w:gz") as archive:
        archive.add(upload_folder, arcname="uploads")
    return target


if __name__ == "__main__":
    result = create_backup(Config.DATABASE_PATH, Config.UPLOAD_FOLDER, Config.BACKUP_FOLDER)
    print(result)
