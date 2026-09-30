import build

NOVO = {"schema_version": 1, "gisbr_ref": "abc", "gerado_em": "t2", "fontes": {"sudeste": {"arquivo": "sudeste-2.osm.pbf"}},
        "rms": {"04701": {"status": "ok", "asset": "osm_vias_rm04701.gpkg.zip"}}}


def test_merge_acumula_execucoes_parciais():
    antigo = {"schema_version": 1, "gisbr_ref": "abc", "gerado_em": "t1",
              "fontes": {"sul": {"arquivo": "sul-1.osm.pbf"}}, "rms": {"04301": {"status": "ok"}}}
    m = build.mescla_manifest(antigo, NOVO)
    assert set(m["rms"]) == {"04301", "04701"} and set(m["fontes"]) == {"sul", "sudeste"}
    assert m["gerado_em"] == "t2"


def test_falha_registrada_e_sobrescreve_ok():
    antigo = {**NOVO, "rms": {"04901": {"status": "ok"}}}
    novo = {**NOVO, "rms": {"04901": {"status": "falhou", "motivo": "OOM (rc 137)"}}}
    m = build.mescla_manifest(antigo, novo)
    assert m["rms"]["04901"] == {"status": "falhou", "motivo": "OOM (rc 137)"}


def test_ref_diferente_descarta_antigo():
    m = build.mescla_manifest({**NOVO, "gisbr_ref": "velho", "rms": {"09999": {"status": "ok"}}}, NOVO)
    assert set(m["rms"]) == {"04701"}
