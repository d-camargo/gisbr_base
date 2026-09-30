"""PBF recortado -> JSON formato Overpass (porte de pbf2overpass.py), no cache do gisbr.
Saida: work/cache/osm_overpass_<chave>.json = {"elements":[nos..., ways...]}.
So ways com `highway` e nos com location valida (streaming)."""
import json
import os
import time

import osmium

from .config import WORK_DIR

CACHE_DIR = WORK_DIR / "cache"


def converte(src, dst):
    """Converte `src` (.osm.pbf) em `dst` (.json). Devolve contagens e tempo."""
    t0 = time.perf_counter()
    n_nos = n_ways = 0
    tmp = f"{dst}.tmp"  # so vira cache do gisbr quando completo
    with open(tmp, "w", encoding="utf-8") as out:
        out.write('{"version":0.6,"generator":"gisbr_base","elements":[')
        primeiro = True
        for o in osmium.FileProcessor(str(src), osmium.osm.NODE | osmium.osm.WAY):
            if o.is_node():
                if not o.location.valid():
                    continue
                el = {"type": "node", "id": o.id, "lat": o.location.lat, "lon": o.location.lon}
                n_nos += 1
            else:
                tags = {t.k: t.v for t in o.tags}
                if "highway" not in tags:
                    continue
                el = {"type": "way", "id": o.id, "nodes": [n.ref for n in o.nodes], "tags": tags}
                n_ways += 1
            if not primeiro:
                out.write(",")
            primeiro = False
            out.write(json.dumps(el, ensure_ascii=False, separators=(",", ":")))
        out.write("]}")
    os.replace(tmp, dst)
    return {"nos": n_nos, "ways": n_ways, "s": round(time.perf_counter() - t0, 2),
            "bytes": os.path.getsize(dst)}
