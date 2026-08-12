"""Tests unitarios de `services/backup_service.py`.

Cubre:
- `backup_antes_de_escribir()` crea backups organizados por proceso.
- `listar_backups()` lista backups agrupados.
- `tiene_backup()` / `ruta_backup()` detectan backups existentes.
- `restaurar_backup()` restaura el contenido del backup.
- Restaurar sin backup disponible lanza FileNotFoundError.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from services.backup_service import BackupService


def test_backup_antes_de_escribir_crea_backup_por_proceso(tmp_path: Path) -> None:
    """El backup se guarda en la carpeta del proceso."""
    svc = BackupService(carpeta_backups=tmp_path / "backups")
    ruta = tmp_path / "jsons" / "comprobante" / "datos.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"v1": True}), encoding="utf-8")

    backup = svc.backup_antes_de_escribir(ruta, {"v2": True}, proceso="comprobante")

    assert backup is not None
    assert backup.parent == tmp_path / "backups" / "comprobante"
    assert backup.name == "datos.json"
    assert json.loads(backup.read_text(encoding="utf-8")) == {"v1": True}


def test_listar_backups_sin_proceso_lista_todos(tmp_path: Path) -> None:
    """listar_backups devuelve todos los backups ordenados por fecha."""
    svc = BackupService(carpeta_backups=tmp_path / "backups")
    (tmp_path / "backups" / "comprobante").mkdir(parents=True)
    (tmp_path / "backups" / "fierro").mkdir(parents=True)

    b1 = tmp_path / "backups" / "comprobante" / "a.json"
    b2 = tmp_path / "backups" / "fierro" / "b.json"
    b1.write_text("{}", encoding="utf-8")
    b2.write_text("{}", encoding="utf-8")

    backups = svc.listar_backups()

    assert len(backups) == 2
    assert b1 in backups
    assert b2 in backups


def test_tiene_backup_true_false(tmp_path: Path) -> None:
    """tiene_backup refleja la existencia del backup."""
    svc = BackupService(carpeta_backups=tmp_path / "backups")
    (tmp_path / "backups" / "comprobante").mkdir(parents=True)
    (tmp_path / "backups" / "comprobante" / "datos.json").write_text(
        "{}", encoding="utf-8"
    )

    ruta = tmp_path / "jsons" / "comprobante" / "datos.json"
    assert svc.tiene_backup(ruta, proceso="comprobante") is True

    ruta_otra = tmp_path / "jsons" / "comprobante" / "otro.json"
    assert svc.tiene_backup(ruta_otra, proceso="comprobante") is False


def test_restaurar_backup_recupera_version_anterior(tmp_path: Path) -> None:
    """restaurar_backup sobrescribe el JSON con el backup."""
    svc = BackupService(carpeta_backups=tmp_path / "backups")
    ruta = tmp_path / "jsons" / "comprobante" / "datos.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"v": "actual"}), encoding="utf-8")

    # Simulamos una edicion previa: el backup guarda la version anterior.
    svc.backup_antes_de_escribir(ruta, {"v": "nueva"}, proceso="comprobante")
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"v": "nueva"}

    restaurado = svc.restaurar_backup(ruta, proceso="comprobante")

    assert restaurado == ruta
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"v": "actual"}


def test_restaurar_backup_sin_backup_lanza_error(tmp_path: Path) -> None:
    """Si no hay backup, restaurar_backup lanza FileNotFoundError."""
    svc = BackupService(carpeta_backups=tmp_path / "backups")
    ruta = tmp_path / "jsons" / "comprobante" / "datos.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"v": "actual"}), encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        svc.restaurar_backup(ruta, proceso="comprobante")


# ============================================================
# Migracion de backups huérfanos (legacy jsons/<proc>/.backups/)
# ============================================================


def test_migrar_backups_huerfanos_mueve_archivos(tmp_path: Path) -> None:
    """Los backups de jsons/<proc>/.backups/ pasan a data/backups/<proc>/."""
    svc = BackupService(carpeta_backups=tmp_path / "backups")
    legacy_dir = tmp_path / "jsons" / "comprobante" / ".backups"
    legacy_dir.mkdir(parents=True)
    legacy = legacy_dir / "datos.json"
    legacy.write_text(json.dumps({"v": "legacy"}), encoding="utf-8")

    stats = svc.migrar_backups_huerfanos(tmp_path / "jsons")

    assert stats["movidos"] == 1
    destino = tmp_path / "backups" / "comprobante" / "datos.json"
    assert destino.exists()
    assert json.loads(destino.read_text(encoding="utf-8")) == {"v": "legacy"}
    assert not legacy.exists()
    assert not legacy_dir.exists()


def test_migrar_backups_huerfanos_conserva_mas_reciente_destino_viejo(
    tmp_path: Path,
) -> None:
    """Si el destino es mas viejo, el backup legacy lo reemplaza."""
    import time

    svc = BackupService(carpeta_backups=tmp_path / "backups")
    jsons_dir = tmp_path / "jsons"
    legacy_dir = jsons_dir / "comprobante" / ".backups"
    legacy_dir.mkdir(parents=True)
    legacy = legacy_dir / "datos.json"
    legacy.write_text(json.dumps({"v": "legacy"}), encoding="utf-8")

    destino = tmp_path / "backups" / "comprobante" / "datos.json"
    destino.parent.mkdir(parents=True)
    destino.write_text(json.dumps({"v": "viejo"}), encoding="utf-8")
    # Forzar que el destino sea mas viejo.
    time.sleep(0.05)
    legacy.write_text(json.dumps({"v": "legacy"}), encoding="utf-8")

    stats = svc.migrar_backups_huerfanos(jsons_dir)

    assert stats["movidos"] == 1
    assert json.loads(destino.read_text(encoding="utf-8")) == {"v": "legacy"}


def test_migrar_backups_huerfanos_ignora_destino_mas_reciente(
    tmp_path: Path,
) -> None:
    """Si el destino es mas nuevo, el backup legacy se descarta."""
    import time

    svc = BackupService(carpeta_backups=tmp_path / "backups")
    jsons_dir = tmp_path / "jsons"
    legacy_dir = jsons_dir / "comprobante" / ".backups"
    legacy_dir.mkdir(parents=True)
    legacy = legacy_dir / "datos.json"
    legacy.write_text(json.dumps({"v": "legacy"}), encoding="utf-8")

    destino = tmp_path / "backups" / "comprobante" / "datos.json"
    destino.parent.mkdir(parents=True)
    time.sleep(0.05)
    destino.write_text(json.dumps({"v": "nuevo"}), encoding="utf-8")

    stats = svc.migrar_backups_huerfanos(jsons_dir)

    assert stats["omitidos"] == 1
    assert stats["movidos"] == 0
    assert json.loads(destino.read_text(encoding="utf-8")) == {"v": "nuevo"}
    assert not legacy.exists()


def test_migrar_backups_huerfanos_sin_backups_es_noop(tmp_path: Path) -> None:
    """Si no hay carpetas .backups, la migracion no hace nada."""
    svc = BackupService(carpeta_backups=tmp_path / "backups")
    stats = svc.migrar_backups_huerfanos(tmp_path / "jsons")
    assert stats == {"movidos": 0, "omitidos": 0, "errores": 0, "dirs_limpios": 0}
