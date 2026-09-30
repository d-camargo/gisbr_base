# Changelog

## [Unreleased]
- Estrutura inicial do repo, regras (GEMINI.md), plano da rodada 1 (PLAN.md) e medição de origem (medicao/2026-09-30/).
- Passos 2 a 7 do PLAN.md: `gisbr_base/{config,catalogo,geofabrik,malhas,recorte,converte,processa_rm}.py`, `build.py` e `tests/` (9 testes, sem precisar de rede). `GISBR_REF` = b82ab1bab2d8cf67d308ccdc599ef31910662866.
- Geofabrik: o nome datado sai da pagina `<regiao>.html` (indice de arquivos, so vale o que tem `.md5`); `latest` nunca e usado. Filtro `w/highway` do Sudeste: 8,6 s na maquina local (85 s no container de 3 GB da medicao).
- `build.py --municipio` e so validacao: gera gpkg + metrics, nao entra em `rms` do manifest. `manifest.json` faz merge entre execucoes; se o `gisbr_ref` ou o `schema_version` mudar, as entradas antigas sao descartadas.

### Medicao do Passo 4 (2026-09-30, Pop!_OS, 16 GB, Sudeste `sudeste-260929.osm.pbf`, filtrado w/highway)
- `osmium extract --config` (complete_ways, as 15 RMs do Sudeste, osmium 1.16.0) sob `systemd-run --user --scope -p MemoryMax=12G -p MemorySwapMax=0`: **morto por SIGKILL em 5,9 s, pico RSS 12,56 GB** (bateu no teto). Nao cabe, nao usado.
- `osmium extract -b` com UM bbox, mesma maquina: 04701 2,84 s / 3,62 GB; 04901 4,12 s / 3,81 GB; 04501 2,71 s / 3,75 GB. O recorte de 04701 tem os mesmos 65.105 ways e 591.498 nos do pyextract (conjuntos de ids iguais). O OOM da medicao original (teto de 3 GB) era esse pico de ~3,6 GB. Fica registrado como alternativa: um `osmium extract` por RM, em sequencia, seria mais rapido que o pyosmium (~3 s contra 252 s para as 15 RMs). Nao foi adotado nesta rodada (o plano manda pyosmium multi-bbox).
- `pyextract.py` original, 04701: 140,4 s (nos 55,3 + ways 29,8 + escrita 55,3), pico 255 MB.
- `recorte.py` multi-bbox, **15 RMs do Sudeste numa leitura**: 252,1 s (nos 73,1 + ways 65,0 + escrita 114,0), pico 2.833 MB. Sao 16,8 s por RM contra 140 s por RM em recortes isolados. BH 163.259 ways / 1.475.702 nos e SP 435.304 / 2.809.071 batem com a medicao de 2026-09-30.
- Criterio do Passo 4: 04701 pelo caminho multi-bbox x `pyextract.py` no mesmo extrato: conjuntos de ids de nos (591.498) e de ways (65.105) **identicos**.

### Execucao real (mesmo extrato `sudeste-260929`, timestamp OSM 2026-09-29T20:22:51Z, 859.700.004 bytes)
- `build.py --rm 04701`: 65.105 ways, 591.498 nos, 123.995 arcos no bbox, 113.644 no poligono, 83.547 nos gravados, 625 problemas; GPKG 41.062.400 B (identico ao da medicao), zip -9 17.058.825 B; subprocesso 21,2 s, pico 995 MB; log com `OSM: cache reutilizado`.
- `build.py --municipio 3205309`: 25.261 ways, 124.692 nos, 48.375 arcos no bbox, 22.040 no poligono, 17.064 nos, 218 problemas; GPKG 7.852.032 B; pico 435 MB. Iguais ao caminho B da medicao (o extrato e o mesmo). A comparacao com o Overpass (Passo 8) nao foi refeita aqui.
