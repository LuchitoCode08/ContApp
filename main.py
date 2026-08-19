"""Punto de entrada de ContApp."""
from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from app.config import get_config
from ui.recursos.tema import aplicar_tema
from ui.ventanas.principal import VentanaPrincipal


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ContApp")

    aplicar_tema(app, "claro")

    ventana = VentanaPrincipal()
    ventana.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())