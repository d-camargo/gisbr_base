"""PBF (ja filtrado w/highway) -> JSON formato Overpass (streaming).
uso: pbf2overpass.py in.osm.pbf out.json
Saida: {"elements":[nodes..., ways...]}. So ways com tag highway; nos referenciados.
"""
import json, sys, time, resource
import osmium

src, dst = sys.argv[1], sys.argv[2]
t0 = time.perf_counter()
n_nodes = n_ways = 0
with open(dst, "w", encoding="utf-8") as out:
    out.write('{"version":0.6,"generator":"pbf2overpass","elements":[')
    first = True
    fp = osmium.FileProcessor(src, osmium.osm.NODE | osmium.osm.WAY)
    for o in fp:
        if o.is_node():
            if not o.location.valid():
                continue
            el = {"type": "node", "id": o.id, "lat": o.location.lat, "lon": o.location.lon}
            n_nodes += 1
        else:
            tags = {t.k: t.v for t in o.tags}
            if "highway" not in tags:
                continue
            el = {"type": "way", "id": o.id, "nodes": [n.ref for n in o.nodes], "tags": tags}
            n_ways += 1
        if not first:
            out.write(",")
        first = False
        out.write(json.dumps(el, ensure_ascii=False, separators=(",", ":")))
    out.write("]}")
dt = time.perf_counter() - t0
print(json.dumps({"nodes": n_nodes, "ways": n_ways, "s": round(dt, 2),
                  "maxrss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024}))
