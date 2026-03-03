import sys
from PySide6.QtWidgets import QApplication

from app.db import init_db
from app.ui_main import MainWindow
from app.backup import backup_database

def main():
    init_db()
    backup_database()   # 👈 se ejecuta al abrir

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()