from gisbr_base.recorte import recorta
from .pbf_minimo import escreve, le


def test_multi_bbox_complete_ways(tmp_path):
    src = tmp_path / "src.osm.pbf"
    nos = {1: (0.1, 0.1), 2: (0.2, 0.2), 3: (5.0, 5.0),   # way 10 cruza a borda de A
           4: (10.1, 10.1), 5: (10.2, 10.2),              # way 11 so em B
           6: (20.0, 20.0), 7: (20.1, 20.1),              # way 12 fora de tudo
           8: (0.3, 0.3), 9: (10.3, 10.3)}                # way 13 liga A a B: entra nos dois
    ways = {10: ([1, 2, 3], {"highway": "primary"}), 11: ([4, 5], {"highway": "residential"}),
            12: ([6, 7], {"highway": "service"}), 13: ([8, 9], {"highway": "track"})}
    escreve(src, nos, ways)
    caixas = {"A": (0, 0, 1, 1), "B": (10, 10, 11, 11)}
    r = recorta(src, caixas, {k: tmp_path / f"{k}.osm.pbf" for k in caixas})
    assert le(tmp_path / "A.osm.pbf") == ({1, 2, 3, 8, 9}, {10, 13})
    assert le(tmp_path / "B.osm.pbf") == ({4, 5, 8, 9}, {11, 13})
    assert r["A"] == {"nos": 5, "ways": 2} and r["B"] == {"nos": 4, "ways": 2}
