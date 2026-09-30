"""Build de UMA RM (ou municipio), feito para rodar em subprocesso:
    python -m gisbr_base.processa_rm <id>     # 5 digitos -> chave rm<id>; 7 digitos -> chave = codigo
Le o cache work/cache/osm_overpass_<chave>.json (escrito por converte.py), roda o pipeline do gisbr
(compute_osm_network + montar_camadas, sem copiar nada) e grava work/out/osm_vias_<chave>.gpkg
com osm_{links,nodes,problemas}_<chave> + work/out/<chave>.metrics.json.
Aborta (rc != 0) se o pipeline nao reutilizou o cache (= teria consultado o Overpass)."""
import json
import re
import sys
import time

from .config import WORK_DIR, garante_gisbr
from .malhas import chave_de

OUT = WORK_DIR / "out"


def pico_rss_mb():
    """Pico de RSS DESTE processo. VmHWM zera no exec; ru_maxrss herda o pico do pai
    (o build.py, que segura ~3,5 GB depois do recorte) e mentia para as RMs pequenas."""
    for l in open("/proc/self/status"):
        if l.startswith("VmHWM:"):
            return int(l.split()[1]) // 1024


def main(id_):
    T0 = time.perf_counter()
    garante_gisbr()
    chave = chave_de(id_)
    cache_dir = WORK_DIR / "cache"
    cache_file = cache_dir / f"osm_overpass_{chave}.json"
    if not cache_file.exists():  # sem cache o gisbr iria ao Overpass: nao deixa
        print(f"ERRO: cache {cache_file} ausente", file=sys.stderr)
        return 2

    from qgis.core import Qgis, QgsApplication, QgsFields, QgsJsonUtils, QgsProcessingFeedback
    app = QgsApplication([], False)
    app.initQgis()
    from gisbr.core import osm_pipeline as P
    from gisbr.core import regioes_metropolitanas as rm_csv
    from gisbr.core.diagnostico import _grava_gpkg

    feat = QgsJsonUtils.stringToFeatureList((WORK_DIR / "malhas" / f"{chave}.geojson").read_text(), QgsFields())[0]
    bbox = tuple(json.loads((WORK_DIR / "malhas" / "bboxes.json").read_text())[chave])
    rm = rm_csv.por_id(id_) if len(id_) == 5 else None
    nome = rm["nome"] if rm else chave

    class FB(QgsProcessingFeedback):
        def __init__(self):
            super().__init__()
            self.ev = []
            self.t = time.perf_counter()

        def pushInfo(self, m):
            self.ev.append((round(time.perf_counter() - self.t, 2), m))
            print("[%.1fs] %s" % (time.perf_counter() - self.t, m), flush=True)

        def pushWarning(self, m):
            self.pushInfo("WARN " + m)

    fb = FB()
    t = time.perf_counter()
    dados = P.compute_osm_network(chave, nome, bbox, feat.geometry(), cache_dir=cache_dir,
                                  feedback=fb, rede="veicular")
    t_compute = time.perf_counter() - t
    if not any("OSM: cache reutilizado" in m for _, m in fb.ev):
        print("ERRO: log sem 'OSM: cache reutilizado'; resultado nao vale", file=sys.stderr)
        return 3
    if dados["metadata"].get("erro") or not dados.get("arcos"):
        print(f"ERRO: {dados['metadata'].get('erro') or 'sem arcos no poligono'}", file=sys.stderr)
        return 4

    def primeiro(sub):
        return next((t for t, m in fb.ev if sub in m), None)

    def dif(a, b):
        return None if a is None or b is None else round(b - a, 2)

    t_payload = primeiro("ways encontrados")
    t_topo = primeiro("componentes")
    t_filtro = primeiro("dentro do município") or primeiro("nenhum arco intersecta")
    t_verif = primeiro("verificação (")
    n_ways, n_nos_json = map(int, re.search(r"(\d+) ways encontrados, (\d+) n", next(
        m for _, m in fb.ev if "ways encontrados" in m)).groups())

    t = time.perf_counter()
    layers = P.montar_camadas(dados)
    t_camadas = time.perf_counter() - t
    OUT.mkdir(parents=True, exist_ok=True)
    gpkg = OUT / f"osm_vias_{chave}.gpkg"
    gpkg.unlink(missing_ok=True)
    t = time.perf_counter()
    for nome_cam in ("osm_links", "osm_nodes", "osm_problemas"):
        ok, msg = _grava_gpkg(layers[nome_cam], str(gpkg), f"{nome_cam}_{chave}")
        if not ok:
            print(f"ERRO ao gravar {nome_cam}_{chave}: {msg}", file=sys.stderr)
            return 5
    t_gpkg = time.perf_counter() - t

    metrics = {
        "chave": chave, "bbox": bbox, "qgis_version": Qgis.version(),
        "n_ways": n_ways, "n_nos_json": n_nos_json,
        "n_arcos_todos": len(dados["arcos_todos"]), "n_arcos_poligono": len(dados["arcos"]),
        "n_nos": layers["osm_nodes"].featureCount(), "n_problemas": len(dados["problemas"]),
        "tempos_s": {"compute_total": round(t_compute, 2), "ate_payload": t_payload,
                     "topologia": dif(t_payload, t_topo), "filtro": dif(t_topo, t_filtro),
                     "verificacao": dif(t_filtro, t_verif), "montar_camadas": round(t_camadas, 2),
                     "gravar_gpkg": round(t_gpkg, 2), "total_script": round(time.perf_counter() - T0, 2)},
        "gpkg_bytes": gpkg.stat().st_size,
        "maxrss_mb": pico_rss_mb(),
    }
    (OUT / f"{chave}.metrics.json").write_text(json.dumps(metrics, indent=1))
    print("DONE", json.dumps(metrics), flush=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].isdigit() or len(sys.argv[1]) not in (5, 7):
        sys.exit("uso: python -m gisbr_base.processa_rm <id 5 digitos | codigo 7 digitos>")
    sys.exit(main(sys.argv[1]))
