"""Recorte complete_ways de N bboxes numa so leitura do PBF filtrado da regiao.
Mesmo algoritmo do `osmium extract --strategy complete_ways` (porte de pyextract.py, medicao 2026-09-30):
1. nos dentro de cada bbox; 2. way com algum no dentro entra naquele bbox, com TODOS os nos;
3. escrita: um SimpleWriter por chave. Em pyosmium porque o osmium extract estourou 3 GB (ver CHANGELOG)."""
import resource
import time

import osmium


def recorta(src, bboxes, saidas):
    """src: PBF filtrado. bboxes: {chave: (minx, miny, maxx, maxy)}. saidas: {chave: caminho .osm.pbf}.
    Devolve {chave: {"nos": n, "ways": n}, "_tempos": {...}, "_maxrss_mb": n}."""
    ks = list(bboxes)
    caixas = [(k, *bboxes[k]) for k in ks]
    ux0, uy0 = min(b[1] for b in caixas), min(b[2] for b in caixas)
    ux1, uy1 = max(b[3] for b in caixas), max(b[4] for b in caixas)
    t0 = time.perf_counter()
    dentro = {k: set() for k in ks}
    for o in osmium.FileProcessor(str(src), osmium.osm.NODE):
        loc = o.location
        x, y = loc.lon, loc.lat
        if ux0 <= x <= ux1 and uy0 <= y <= uy1:  # rejeita rapido pelo bbox da uniao
            for k, x0, y0, x1, y1 in caixas:
                if x0 <= x <= x1 and y0 <= y <= y1:
                    dentro[k].add(o.id)
    t1 = time.perf_counter()
    ways = {k: set() for k in ks}
    precisa = {k: set() for k in ks}
    for w in osmium.FileProcessor(str(src), osmium.osm.WAY):
        refs = [n.ref for n in w.nodes]
        for k in ks:
            d = dentro[k]
            if any(r in d for r in refs):
                ways[k].add(w.id)
                precisa[k].update(refs)
    del dentro
    t2 = time.perf_counter()
    qualquer = set().union(*precisa.values())
    writers = {k: osmium.SimpleWriter(str(saidas[k])) for k in ks}
    cont = {k: {"nos": 0, "ways": 0} for k in ks}
    try:
        for o in osmium.FileProcessor(str(src), osmium.osm.NODE | osmium.osm.WAY):
            if o.is_node():
                if o.id in qualquer:
                    for k in ks:
                        if o.id in precisa[k]:
                            writers[k].add_node(o)
                            cont[k]["nos"] += 1
            else:
                for k in ks:
                    if o.id in ways[k]:
                        writers[k].add_way(o)
                        cont[k]["ways"] += 1
    finally:
        for wr in writers.values():
            wr.close()
    t3 = time.perf_counter()
    cont["_tempos"] = {"nos_s": round(t1 - t0, 2), "ways_s": round(t2 - t1, 2),
                       "escrita_s": round(t3 - t2, 2), "total_s": round(t3 - t0, 2)}
    cont["_maxrss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
    return cont
