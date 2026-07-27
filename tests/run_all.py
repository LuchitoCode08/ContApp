"""Runner de toda la suite de tests del proyecto.

Uso: ``python -m tests.run_all`` desde la raiz del repo.

Equivale a ``pytest tests/`` pero con un print final mas visible y
exit code explicito. Pensado para correr desde terminal sin tener
que recordar la flag de pytest.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def main() -> int:
    print("[tests] Ejecutando suite completa con pytest...")
    resultado = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v"],
        cwd=str(RAIZ),
        capture_output=False,
    )
    if resultado.returncode == 0:
        print("\n[tests] [OK] Todos los tests pasaron.")
    else:
        print(
            f"\n[tests] [FAIL] pytest retorno "
            f"{resultado.returncode}.",
        )
    return resultado.returncode


if __name__ == "__main__":
    raise SystemExit(main())