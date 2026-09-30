"""Geofabrik: descobre o PBF DATADO (nunca -latest), baixa, confere md5, filtra w/highway."""
import hashlib
import re
import subprocess
import urllib.request
from pathlib import Path

from .config import GEOFABRIK_BASE, WORK_DIR

PBF_DIR = WORK_DIR / "pbf"


def nome_datado(regiao):
    """Nome do PBF mais recente da regiao, ex.: sudeste-260929.osm.pbf.
    A pagina <regiao>.html lista o indice de arquivos datados (so conta o que tem .md5)."""
    html = urllib.request.urlopen(f"{GEOFABRIK_BASE}{regiao}.html", timeout=60).read().decode()
    datas = set(re.findall(rf'href="{regiao}-(\d{{6}})\.osm\.pbf\.md5"', html))
    if not datas:
        raise RuntimeError(f"nenhum PBF datado de {regiao} na pagina da Geofabrik")
    return f"{regiao}-{max(datas)}.osm.pbf"  # YYMMDD ordena como texto


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def baixa(regiao):
    """Baixa (com retomada) e confere o md5. Devolve a fonte para o manifest."""
    import osmium
    nome = nome_datado(regiao)
    dst = PBF_DIR / nome
    PBF_DIR.mkdir(parents=True, exist_ok=True)
    esperado = urllib.request.urlopen(f"{GEOFABRIK_BASE}{nome}.md5", timeout=60).read().split()[0].decode()
    if not (dst.exists() and _md5(dst) == esperado):
        subprocess.run(["curl", "-fsSL", "-C", "-", "-o", str(dst), f"{GEOFABRIK_BASE}{nome}"], check=True)
        if _md5(dst) != esperado:
            raise RuntimeError(f"md5 de {nome} nao confere")
    ts = osmium.FileProcessor(str(dst)).header.get("osmosis_replication_timestamp")
    return {"arquivo": nome, "path": str(dst), "timestamp_osm": ts, "bytes": dst.stat().st_size}


def filtra(regiao, pbf):
    """osmium tags-filter w/highway, 1x por regiao (refaz se o PBF for mais novo)."""
    dst = PBF_DIR / f"{regiao}-highway.osm.pbf"
    if dst.exists() and dst.stat().st_mtime >= Path(pbf).stat().st_mtime:
        return dst
    tmp = PBF_DIR / f"{regiao}-highway.tmp.osm.pbf"
    subprocess.run(["osmium", "tags-filter", str(pbf), "w/highway", "-o", str(tmp), "--overwrite"], check=True)
    tmp.replace(dst)
    return dst
