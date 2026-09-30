"""Roda compute_osm_network + grava GPKG e mede.  uso: run_path.py A|B RMID
Dentro do container QGIS. A: cache_A vazio (Overpass). B: cache_B preenchido."""
import json, os, sys, time, resource, shutil
sys.path.insert(0, '/gisbr')
path, rid = sys.argv[1], sys.argv[2]
code = rid if len(rid) == 7 else "rm" + rid
W = '/work'
T0 = time.perf_counter()

from qgis.core import (QgsApplication, QgsGeometry, QgsJsonUtils, QgsFields, QgsProcessingFeedback,
                       QgsVectorFileWriter, QgsProject)
QgsApplication.setPrefixPath('/usr', True)
app = QgsApplication([], False)
app.initQgis()
from gisbr.core import osm_pipeline as P

feat = QgsJsonUtils.stringToFeatureList(open(f'{W}/malhas/{code}.geojson').read(), QgsFields())[0]
mun_geom = feat.geometry()
bb = json.load(open(f'{W}/malhas/bboxes.json'))[rid]
bbox = tuple(bb)


class FB(QgsProcessingFeedback):
    def __init__(self):
        super().__init__()
        self.ev = []
        self.t = time.perf_counter()

    def pushInfo(self, m):
        self.ev.append((round(time.perf_counter() - self.t, 2), m))
        print('[%.1fs] %s' % (time.perf_counter() - self.t, m), flush=True)

    def pushWarning(self, m):
        self.pushInfo('WARN ' + m)


fb = FB()
cache_dir = f'{W}/cache_{path}'
cache_file = f'{cache_dir}/osm_overpass_{code}.json'
pre_existia = os.path.exists(cache_file)
t_start = time.perf_counter()
dados = P.compute_osm_network(code, code, bbox, mun_geom, cache_dir=cache_dir, feedback=fb, rede="veicular")
t_compute = time.perf_counter() - t_start
md = dados["metadata"]

def first_t(sub):
    for t, m in fb.ev:
        if sub in m:
            return t
    return None

t_fetch_end = first_t("ways encontrados")
t_topo_end = first_t("componentes")
t_filt_end = first_t("dentro do município") or first_t("nenhum arco intersecta")
t_ver_end = first_t("verificação (")
res = {
    "path": path, "rm": rid, "bbox": bbox, "cache_reutilizado": any("cache reutilizado" in m for _, m in fb.ev),
    "cache_preexistia": pre_existia,
    "t_compute_total_s": round(t_compute, 2),
    "t_ate_payload_s": t_fetch_end,  # Overpass/cache + parse json
    "t_topologia_s": None if None in (t_fetch_end, t_topo_end) else round(t_topo_end - t_fetch_end, 2),
    "t_filtro_s": None if None in (t_topo_end, t_filt_end) else round(t_filt_end - t_topo_end, 2),
    "t_verificacao_s": None if None in (t_filt_end, t_ver_end) else round(t_ver_end - t_filt_end, 2),
    "erro": md.get("erro"), "metadata": {k: v for k, v in md.items() if k != "bbox"},
    "eventos": fb.ev,
}
if os.path.exists(cache_file):
    res["json_bytes"] = os.path.getsize(cache_file)
    pl = json.load(open(cache_file))
    els = pl["elements"]
    res["n_ways"] = sum(1 for e in els if e.get("type") == "way")
    res["n_nodes_json"] = sum(1 for e in els if e.get("type") == "node")
    del pl, els

if dados["arcos_todos"]:
    res["n_arcos_todos"] = len(dados["arcos_todos"])
    res["n_arcos_municipio"] = len(dados["arcos"] or [])
    res["n_problemas"] = None if dados["problemas"] is None else len(dados["problemas"])
    t = time.perf_counter()
    layers = P.montar_camadas(dados)
    res["t_montar_camadas_s"] = round(time.perf_counter() - t, 2)
    outdir = f'{W}/out/{path}'
    os.makedirs(outdir, exist_ok=True)
    gp = f'{outdir}/{code}.gpkg'
    if os.path.exists(gp):
        os.remove(gp)
    t = time.perf_counter()
    ctx = QgsProject.instance().transformContext()
    for nome in ("osm_links", "osm_nodes", "osm_problemas"):
        lyr = layers.get(nome)
        if lyr is None:
            res.setdefault("camadas_ausentes", []).append(nome)
            continue
        o = QgsVectorFileWriter.SaveVectorOptions()
        o.driverName = "GPKG"
        o.layerName = nome
        o.actionOnExistingFile = (QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
                                  if os.path.exists(gp) else QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile)
        r = QgsVectorFileWriter.writeAsVectorFormatV3(lyr, gp, ctx, o)
        res.setdefault("gravacao", {})[nome] = [int(r[0]), lyr.featureCount()]
    res["t_gravar_gpkg_s"] = round(time.perf_counter() - t, 2)
    if os.path.exists(gp):
        res["gpkg_bytes"] = os.path.getsize(gp)

res["t_total_script_s"] = round(time.perf_counter() - T0, 2)
res["maxrss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
os.makedirs(f'{W}/out/{path}', exist_ok=True)
json.dump(res, open(f'{W}/out/{path}/{code}.metrics.json', 'w'), indent=1, default=str)
print("DONE", {k: v for k, v in res.items() if k not in ("eventos", "metadata")})
