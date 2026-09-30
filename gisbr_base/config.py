"""Constantes do build e `garante_gisbr()` (clone do gisbr fixado num commit)."""
import os
import subprocess
import sys
from pathlib import Path

GISBR_REPO = "https://github.com/d-camargo/gisbr.git"
GISBR_REF = "b82ab1bab2d8cf67d308ccdc599ef31910662866"  # package: gisbr 1.0.1 (2026-09-30)
REPO_DIR = Path(__file__).resolve().parent.parent
WORK_DIR = Path(os.environ.get("GISBR_BASE_WORK") or REPO_DIR / "work")
MEMORY_MAX = "12G"
SCHEMA_VERSION = 1
GEOFABRIK_BASE = "https://download.geofabrik.de/south-america/brazil/"
GISBR_DIR = WORK_DIR / "gisbr"

REGIOES = ("norte", "nordeste", "centro-oeste", "sudeste", "sul")
UF_REGIAO = {
    **dict.fromkeys(["RO", "AC", "AM", "RR", "PA", "AP", "TO"], "norte"),
    **dict.fromkeys(["MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"], "nordeste"),
    **dict.fromkeys(["MT", "MS", "GO", "DF"], "centro-oeste"),
    **dict.fromkeys(["MG", "ES", "RJ", "SP"], "sudeste"),
    **dict.fromkeys(["PR", "SC", "RS"], "sul"),
}

# 1o digito do codigo IBGE do municipio = macrorregiao (so para --municipio)
DIGITO_REGIAO = {"1": "norte", "2": "nordeste", "3": "sudeste", "4": "sul", "5": "centro-oeste"}


def _git(*args):
    return subprocess.run(["git", "-C", str(GISBR_DIR), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def garante_gisbr():
    """Clona o gisbr em work/gisbr no GISBR_REF e poe no sys.path.
    Idempotente; FALHA se o clone estiver sujo ou em outro commit."""
    if not (GISBR_DIR / ".git").exists():
        GISBR_DIR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", GISBR_REPO, str(GISBR_DIR)], check=True)
        _git("checkout", "--quiet", "--detach", GISBR_REF)
    head = _git("rev-parse", "HEAD")
    if head != GISBR_REF:
        raise RuntimeError(f"gisbr em {head}, esperado {GISBR_REF}: troca de ref e decisao consciente")
    if _git("status", "--porcelain"):
        raise RuntimeError(f"clone do gisbr sujo em {GISBR_DIR}: nao altere o codigo do gisbr")
    if str(GISBR_DIR) not in sys.path:
        sys.path.insert(0, str(GISBR_DIR))
