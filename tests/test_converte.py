import json

import pytest

from gisbr_base.config import garante_gisbr
from gisbr_base.converte import converte
from .pbf_minimo import escreve


def test_converte_pbf_minimo(tmp_path):
    pbf, dst = tmp_path / "m.osm.pbf", tmp_path / "osm_overpass_teste.json"
    escreve(pbf, {1: (-40.30, -20.30), 2: (-40.31, -20.30), 3: (-40.31, -20.31)},
            {10: ([1, 2, 3], {"highway": "residential", "name": "Rua A"}),
             11: ([1, 2], {"building": "yes"})})  # sem highway: fica de fora
    r = converte(pbf, dst)
    assert (r["nos"], r["ways"]) == (3, 1)
    payload = json.loads(dst.read_text())
    tipos = [e["type"] for e in payload["elements"]]
    assert tipos == ["node"] * 3 + ["way"]
    assert [e["id"] for e in payload["elements"] if e["type"] == "way"] == [10]

    # o pipeline do gisbr aceita o formato
    pytest.importorskip("qgis.core")
    garante_gisbr()
    from gisbr.core import osm_pipeline as P
    ways = P._parse_osm_ways(payload)
    nodes = P._build_nodes_dict(payload)
    assert len(ways) == 1 and len(nodes) == 3
    assert nodes[1] == pytest.approx((-40.30, -20.30))
