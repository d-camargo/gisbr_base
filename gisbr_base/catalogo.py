"""Catalogo das RMs (vindo do CSV do gisbr, nunca de memoria)."""
from .config import UF_REGIAO, REGIOES, garante_gisbr


def catalogo():
    """Lista de RMs na ordem D8: por regiao, dentro dela da menor para a maior
    (nº de municipios; empate por id)."""
    garante_gisbr()
    from gisbr.core import regioes_metropolitanas as r
    rms = [{"id": rm["id"], "nome": rm["nome"], "uf": rm["uf"], "codes": r.codes(rm["id"]),
            "regiao_geofabrik": UF_REGIAO[rm["uf"]]} for rm in r.listar_todas()]
    return sorted(rms, key=lambda x: (REGIOES.index(x["regiao_geofabrik"]), len(x["codes"]), x["id"]))
