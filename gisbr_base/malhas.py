"""Malhas municipais do IBGE (D4): cache por municipio, uniao por RM, bbox.
Chave: 'rm<id>' (id de 5 digitos) ou o proprio codigo IBGE (7 digitos)."""
import gzip
import json
import time
import urllib.request

from .config import WORK_DIR, garante_gisbr

MALHAS = WORK_DIR / "malhas"
_app = None  # QgsApplication precisa ficar viva
_URL = "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{}?formato=application/vnd.geo+json"


def chave_de(id_):
    return id_ if len(id_) == 7 else f"rm{id_}"


def baixa_municipio(code):
    p = MALHAS / "mun" / f"{code}.geojson"
    if p.exists():
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    for t in range(3):
        try:
            req = urllib.request.Request(_URL.format(code), headers={"User-Agent": "gisbr_base"})
            p.write_bytes(urllib.request.urlopen(req, timeout=60).read())
            return p
        except Exception as e:
            print(f"malha {code}: erro {e}", flush=True)
            time.sleep(3)
    raise RuntimeError(f"nao consegui baixar a malha de {code}")


def prepara(ids):
    """Gera work/malhas/<chave>.geojson e faz merge do bbox em bboxes.json.
    `ids`: ids de RM (5 digitos) e/ou codigos de municipio (7). Pula o que ja existe."""
    garante_gisbr()
    from gisbr.core import regioes_metropolitanas as r
    bb_path = MALHAS / "bboxes.json"
    bboxes = json.loads(bb_path.read_text()) if bb_path.exists() else {}
    from qgis.core import QgsApplication, QgsFields, QgsGeometry, QgsJsonUtils
    global _app
    if _app is None:
        _app = QgsApplication([], False)
        _app.initQgis()
    for id_ in ids:
        k = chave_de(id_)
        if (MALHAS / f"{k}.geojson").exists() and k in bboxes:
            continue
        codes = [id_] if len(id_) == 7 else r.codes(id_)
        geoms = []
        for c in codes:
            b = baixa_municipio(c).read_bytes()
            d = (gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b).decode()
            geoms += [f.geometry() for f in QgsJsonUtils.stringToFeatureList(d, QgsFields())]
        u = QgsGeometry.unaryUnion(geoms)
        bb = u.boundingBox()
        bboxes[k] = [bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()]
        (MALHAS / f"{k}.geojson").write_text(json.dumps(
            {"type": "Feature", "properties": {"chave": k, "n_mun": len(geoms)},
             "geometry": json.loads(u.asJson(7))}))
        print(f"malha {k}: {len(geoms)} feicoes, valida={u.isGeosValid()}", flush=True)
        bb_path.write_text(json.dumps(bboxes, indent=1))
    return bboxes
