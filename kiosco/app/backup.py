from pathlib import Path
from datetime import datetime
import shutil

from app.db import DB_PATH


def backup_database():
    """
    Crea una copia del archivo kiosco.db en carpeta backups/
    si el archivo existe y no está vacío.
    """

    if not DB_PATH.exists():
        return  # todavía no hay base

    # Evitar copiar si está vacío
    if DB_PATH.stat().st_size == 0:
        return

    backups_dir = DB_PATH.parent.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = backups_dir / f"kiosco_{timestamp}.db"

    shutil.copy2(DB_PATH, backup_file)