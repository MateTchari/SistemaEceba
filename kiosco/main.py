from __future__ import annotations

import sys

print(">>> entrando a main.py")

from PySide6.QtWidgets import QApplication
print(">>> import QApplication OK")

from app.db import init_db
print(">>> import init_db OK")

from app.ui_main import MainWindow
print(">>> import MainWindow OK")


def main():
    print(">>> entrando a main()")
    init_db()
    print(">>> init_db OK")

    app = QApplication(sys.argv)
    print(">>> QApplication creada")

    ventana = MainWindow()
    print(">>> MainWindow instanciada")

    ventana.show()
    print(">>> ventana.show() OK")

    sys.exit(app.exec())


if __name__ == "__main__":
    print(">>> ejecutando bloque _main_")
    main()