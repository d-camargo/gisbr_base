from collections import Counter

from gisbr_base.catalogo import catalogo
from gisbr_base.config import UF_REGIAO

RMS = catalogo()


def test_84_rms_ids_de_5_digitos():
    assert len(RMS) == 84
    assert all(len(r["id"]) == 5 and r["id"].isdigit() for r in RMS)
    assert len({r["id"] for r in RMS}) == 84


def test_toda_uf_mapeada():
    assert all(r["uf"] in UF_REGIAO for r in RMS)
    assert all(r["codes"] for r in RMS)


def test_contagem_por_regiao():
    assert Counter(r["regiao_geofabrik"] for r in RMS) == {
        "nordeste": 33, "sul": 23, "sudeste": 15, "norte": 10, "centro-oeste": 3}


def test_ids_conhecidos():
    por = {r["id"]: r for r in RMS}
    assert por["04501"]["uf"] == "MG" and len(por["04501"]["codes"]) == 34
    assert "3205309" in por["04701"]["codes"]
