"""Equivalente Python (pyosmium) de `osmium extract -b BBOX --strategy complete_ways`
sobre o PBF ja filtrado w/highway. Usado porque o osmium-tool extract estoura 3 GB (OOM).
uso: pyextract.py in.osm.pbf out.osm.pbf minx miny maxx maxy
Algoritmo identico ao complete_ways: passo 1 = nos dentro do bbox -> ways com algum no dentro
-> todos os nos dessas ways; passo 2 = escreve nos e ways selecionados (PBF ordenado)."""
import sys, time, json, resource
import osmium

src, dst = sys.argv[1], sys.argv[2]
minx, miny, maxx, maxy = map(float, sys.argv[3:7])
t0 = time.perf_counter()

inside = set()
for o in osmium.FileProcessor(src, osmium.osm.NODE):
    loc = o.location
    if minx <= loc.lon <= maxx and miny <= loc.lat <= maxy:
        inside.add(o.id)
t1 = time.perf_counter()
way_ids = set()
need = set()
for w in osmium.FileProcessor(src, osmium.osm.WAY):
    refs = [n.ref for n in w.nodes]
    if any(r in inside for r in refs):
        way_ids.add(w.id)
        need.update(refs)
del inside
t2 = time.perf_counter()
nn = nw = 0
with osmium.SimpleWriter(dst) as wr:
    for o in osmium.FileProcessor(src, osmium.osm.NODE | osmium.osm.WAY):
        if o.is_node():
            if o.id in need:
                wr.add_node(o); nn += 1
        else:
            if o.id in way_ids:
                wr.add_way(o); nw += 1
t3 = time.perf_counter()
print(json.dumps({"pass1_nodes_s": round(t1 - t0, 2), "pass1_ways_s": round(t2 - t1, 2),
                  "write_s": round(t3 - t2, 2), "total_s": round(t3 - t0, 2),
                  "nodes": nn, "ways": nw,
                  "maxrss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024}))
