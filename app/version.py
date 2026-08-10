"""Version y metadata de ContApp.

Single source of truth para la version actual de la app.
Tanto el codigo (badge en sidebar) como el instalador Inno Setup
como el workflow de release leen de aca.
"""
from __future__ import annotations


# Version actual de ContApp (semver: MAJOR.MINOR.PATCH).
# Para bump:
#   - bug fix        -> MAJOR.MINOR.PATCH+1
#   - feature nueva  -> MAJOR.MINOR+1.0
#   - breaking       -> MAJOR+1.0.0
__version__: str = "1.0.3"

# Nombre publico de la app.
APP_NAME: str = "ContApp"

# Repo de GitHub donde se publican los releases.
# Lo usa el updater para consultar la ultima version disponible.
GITHUB_REPO: str = "LuchitoCode08/ContApp"

# URL base de la API publica de GitHub.
GITHUB_API_BASE: str = "https://api.github.com"


def user_agent() -> str:
    """Devuelve el User-Agent que identifica a ContApp ante la API de GitHub.

    GitHub recomienda identificar el cliente. Sin User-Agent explicito,
    algunos endpoints limitan el rate.
    """
    return f"{APP_NAME}/{__version__}"
