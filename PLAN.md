# PLAN — gisbr_base (Rodada 1 → v0.1.0: rede viária OSM por Região Metropolitana)

> **Rodada 1 (2026-09-30), ativa.** O repo nasceu vazio, com a estrutura, as regras
> (`GEMINI.md`) e a medição (`medicao/2026-09-30/`). **Nenhum código do pipeline
> existe ainda.** Os scripts em `medicao/2026-09-30/scripts/` são protótipos
> **medidos**: servem de ponto de partida, mas não são o pacote.
>
> **Onde roda:** na máquina do Diego (Pop!_OS, 16 GB, QGIS do sistema). Ver
> `GEMINI.md` §2. Quem executa segue o `GEMINI.md` §3: o forte planeja e revisa, o
> fraco executa.

## Objetivo

Publicar, numa Release do GitHub, **um arquivo por Região Metropolitana** com a
rede viária OSM **veicular** já montada pelo pipeline do gisbr (links, nós e
problemas de topologia). Junto vai um `manifest.json`, que é o contrato com o
plugin. O plugin gisbr deixa de consultar o Overpass e de montar a topologia no
modo RM e passa a **só baixar**. A integração no plugin é rodada do **gisbr**,
não daqui (ver "Fora do escopo").

## O que a medição de 2026-09-30 já provou (VPS, container `qgis/qgis:3.44`, `--memory=3g`)

Relatório completo: `medicao/2026-09-30/RESULTADO.md`. Métricas brutas:
`medicao/2026-09-30/metrics/`.

| | Vitória (município 3205309) | RM Grande Vitória (04701) | RM Belo Horizonte (04501) | RM São Paulo (04901) |
|---|---|---|---|---|
| Ways / nós | 25.261 / 124.692 | 65.105 / 591.498 | 163.259 / 1.475.702 | 435.304 / 2.809.071 |
| Arcos (bbox) / no polígono | 48.375 / 22.040 | 123.995 / 113.644 | 337.146 / 265.715 | 872.182 / 710.876 |
| `compute_osm_network` | 4,8 s | 17,0 s | 56,1 s | **OOM** na verificação geométrica |
| Verificação geométrica | 3,5 s | 11,9 s | 38,9 s | — |
| `montar_camadas` + gravar GPKG | 3,8 s | 13,8 s | 42,9 s | — |
| Pico de RAM | 458 MB | 1.068 MB | 2.336 MB | > 3 GB |
| GPKG / zip -9 | 7,9 / 3,2 MB | 41,1 / 17,1 MB | 97,0 / 40,5 MB | — |

Achados que moldam este plano:

- **M1. A conversão PBF → JSON Overpass está validada.** Em Vitória, Overpass × Geofabrik
  deu ways 25.265 × 25.261, arcos 22.050 × 22.040 e problemas 218 × 218, com a mesma
  distribuição por tipo. A diferença é a data do OSM.
- **M2. O Overpass é o gargalo que se quer eliminar.** Mesmo para um único município,
  a 1ª tentativa deu Gateway Timeout nos 3 mirrors (127,8 s). A 2ª, 60 s depois,
  levou 8,4 s.
- **M3. A memória é o limitante, não o tempo.** Gasto medido: 7–9,5 KB por arco
  (bbox). O custo por arco **cai** com o tamanho. SP (872 mil arcos) deve precisar de
  **~6–7,5 GB (estimativa)**, o que cabe em 16 GB sem folga para desktop pesado aberto.
  O tempo cresce mais que linearmente: a verificação geométrica é a etapa mais cara.
- **M4. O `osmium extract` estourou 3 GB** já na 1ª passada, em qualquer bbox, até
  sobre PBF pré-filtrado. O `osmium tags-filter w/highway` no Sudeste inteiro rodou
  bem (85 s, 2,05 GB). O recorte foi feito com pyosmium (`scripts/pyextract.py`,
  mesmo algoritmo do `complete_ways`): **~4,5 min por RM**, porque cada recorte relê o
  PBF filtrado inteiro. Com N RMs por região, isso vira N × 4,5 min. **Uma passada por
  região para todas as RMs** é o ganho óbvio (passo 4).
- **M5. `*-latest.osm.pbf` da Geofabrik entrou em loop de redirect.** Usar o arquivo
  datado. Sudeste de 2026-09-29: 859.700.004 bytes, 79 s de download.
- **M6. Tamanho total estimado das 84 RMs: 1,4–3,4 GB zipados** (estimativa linear de
  poucos pontos). PBFs regionais: N 152 MB, NE 421 MB, CO 196 MB, SE 819 MB, S 405 MB
  (~2 GB). RMs por região: NE 33, S 23, SE 15, N 10, CO 3.
- **M7. O bbox do município de Vitória vai até lon −28,85** por causa das ilhas
  oceânicas (Trindade). O recorte por bbox fica largo, mas no mar não há via, então
  o custo é só de área. Qualquer RM com ilha oceânica tem o mesmo efeito.
- **M8. `montar_camadas` é quase tão caro quanto a verificação** (37,5 s em BH).
  Essa etapa roda na thread principal no plugin, e aqui roda no subprocesso.

## Decisões

- **D1. Build local, na máquina do Diego**, sem GitHub Actions (decisão do Diego, 2026-09-30).
- **D2. Reusar o gisbr por import, fixado em commit.** `GISBR_REF =
  b82ab1bab2d8cf67d308ccdc599ef31910662866` (`package: gisbr 1.0.1`, 2026-09-30).
  O build clona `github.com/d-camargo/gisbr` em `work/gisbr/` nesse commit e faz
  `sys.path.insert`. Trocar o ref é decisão consciente, registrada no CHANGELOG.
- **D3. Só rede `veicular`** (default do gisbr). A rede pedestre fica para rodada futura.
- **D4. Polígono da RM = união das malhas municipais do IBGE** (API
  `servicodados.ibge.gov.br/api/v3/malhas/municipios/{code}?formato=application/vnd.geo+json`,
  como na medição), com cache em `work/malhas/`. ⚠ O plugin monta o **seu** polígono de
  recorte com `gisbr:read_municipality` (geobr). A diferença na borda deve ser
  desprezível, mas o passo 9 confere.
- **D5. Um asset por RM: `osm_vias_rm<id>.gpkg.zip`**, contendo um GPKG com
  `osm_links_rm<id>`, `osm_nodes_rm<id>` e `osm_problemas_rm<id>` (nomes do modo RM do
  gisbr). Formato GPKG porque o plugin já grava e lê GPKG. FlatGeobuf (39,3 MB contra
  41,1 MB do GPKG na Grande Vitória) não compensa uma segunda leitura.
- **D6. URL estável:** `https://github.com/d-camargo/gisbr_base/releases/latest/download/<asset>`.
  Tag de cada build: `osm-AAAAMMDD`, com a data do extrato Geofabrik, não a data do build.
- **D7. `manifest.json`, schema 1:**
  ```json
  {
    "schema_version": 1,
    "gerado_em": "2026-10-..T..Z",
    "gisbr_ref": "b82ab1b…",
    "qgis_version": "3.x.y",
    "licenca_dados": "ODbL-1.0",
    "atribuicao": "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright",
    "fontes": {"sudeste": {"arquivo": "sudeste-260929.osm.pbf", "timestamp_osm": "2026-09-29T20:22:51Z", "bytes": 859700004}},
    "rede": "veicular",
    "rms": {
      "04501": {"nome": "…", "uf": "MG", "regiao_geofabrik": "sudeste", "status": "ok",
                 "asset": "osm_vias_rm04501.gpkg.zip", "bytes": 0, "sha256": "…",
                 "n_ways": 0, "n_arcos": 0, "n_nos": 0, "n_problemas": 0,
                 "t_build_s": 0.0, "maxrss_mb": 0},
      "04901": {"status": "falhou", "motivo": "OOM (rc 137) na verificação geométrica"}
    }
  }
  ```
- **D8. Ordem do lote:** por região, e dentro da região da menor para a maior RM
  (por nº de municípios, até existir a contagem de arcos do build anterior).
- **D9. Proteção da máquina:** cada RM roda em
  `systemd-run --user --scope -p MemoryMax=12G -p MemorySwapMax=0 python3 …`, para o
  OOM matar a RM e não o desktop. Se não houver `systemd-run`, use `ulimit -v`.
  Registrado no manifest.
- **D10. Periodicidade:** manual, mensal ou quando o gisbr trocar de ref. Guardar as 3
  últimas Releases e apagar as mais antigas à mão.

## Estrutura do repo (criada na rodada 0)

```
gisbr_base/
  GEMINI.md  CLAUDE.md→  AGENTS.md→   regras (fonte única = GEMINI.md)
  PLAN.md                            este plano
  README.md  CHANGELOG.md  LICENSE (GPL-3.0)  .gitignore
  gisbr_base/                        pacote (vazio: só __init__.py)
  tests/                             (vazio)
  medicao/2026-09-30/                medição de origem: RESULTADO.md, plano, scripts, métricas
  work/                              dados e caches (fora do git)
```

## Passos

### Passo 1 — Ambiente local (Diego, na máquina local)
- `sudo apt install osmium-tool python3-venv gh` (e confirmar `python3 -c "import qgis.core"`).
- `python3 -m venv --system-site-packages .venv && .venv/bin/pip install osmium pytest`.
  `--system-site-packages` é o que deixa o venv enxergar o `qgis` do sistema.
- `gh auth status` com permissão de escrita em `d-camargo/gisbr_base` (Releases).
- **Pronto quando:** `.venv/bin/python -c "import qgis.core, osmium; print(qgis.core.Qgis.version())"` imprime a versão.

### Passo 2 — `gisbr_base/config.py` e `gisbr_base/catalogo.py`
- `config.py`: `GISBR_REF`, `WORK_DIR` (default `./work`), `MEMORY_MAX` (default `12G`),
  `SCHEMA_VERSION = 1`, o mapa UF → região Geofabrik (`norte`, `nordeste`,
  `centro-oeste`, `sudeste`, `sul`) e a URL base
  `https://download.geofabrik.de/south-america/brazil/`.
- `garante_gisbr()`: clona o gisbr em `work/gisbr/` e faz checkout de `GISBR_REF`. É
  idempotente e **falha** se o checkout estiver sujo ou em outro commit.
- `catalogo.py`: lê `work/gisbr/gisbr/core/data/regioes_metropolitanas.csv` (via
  `gisbr.core.regioes_metropolitanas.listar_todas()`) e devolve as RMs com
  `id` (str de 5 dígitos), `nome`, `uf`, `codes`, `regiao_geofabrik`.
- **Testes:** 84 RMs, ids com 5 dígitos, toda UF mapeada para uma região, e a contagem
  por região bate com M6 (NE 33, S 23, SE 15, N 10, CO 3).

### Passo 3 — Geofabrik e malhas (`gisbr_base/geofabrik.py`, `gisbr_base/malhas.py`)
- `geofabrik.py`: descobre o **nome datado** do PBF de cada região (página
  `<regiao>.html` ou listagem do diretório; **nunca** `-latest`, ver M5), baixa com
  retomada (`curl -C -`) para `work/pbf/`, confere o `.md5` e lê o timestamp do
  cabeçalho (`osmosis_replication_timestamp`) com pyosmium.
- Filtro 1x por região: `osmium tags-filter <pbf> w/highway -o work/pbf/<regiao>-highway.osm.pbf`
  (M4: 85 s e 2 GB no Sudeste).
- `malhas.py`: baixa as malhas municipais do IBGE (D4), grava a união por RM em
  `work/malhas/rm<id>.geojson` e o bbox em `work/malhas/bboxes.json`. Base:
  `medicao/2026-09-30/scripts/prep_malhas.py` e `malhas.py`. São 1.377 municípios:
  guarde o cache e não baixe de novo o que já existe.

### Passo 4 — Recorte em UMA passada por região (`gisbr_base/recorte.py`)
- Generalize `medicao/2026-09-30/scripts/pyextract.py` para **N bboxes numa só
  leitura** do PBF filtrado da região. O algoritmo continua o `complete_ways`:
  1. passada de nós: para cada bbox, o conjunto de nós dentro;
  2. passada de ways: way com algum nó dentro de um bbox entra naquele bbox, com todos os nós;
  3. passada de escrita: um `SimpleWriter` por RM.
- Antes, **meça** se `osmium extract --config` com todas as RMs da região cabe em
  16 GB (o M4 foi com teto de 3 GB). Se couber, use; se não, fique no pyosmium.
  Registre o resultado no CHANGELOG.
- **Pronto quando:** o recorte da RM 04701 pelo caminho multi-bbox tem os **mesmos**
  ways e nós do `pyextract.py` da medição (65.105 ways, 591.498 nós no extrato de
  2026-09-29, ou compare os dois caminhos no mesmo extrato).

### Passo 5 — Conversão (`gisbr_base/converte.py`)
- Porte de `medicao/2026-09-30/scripts/pbf2overpass.py` (streaming, só ways com
  `highway` e os nós com location válida) para `work/cache/osm_overpass_rm<id>.json`.
- **Teste** sobre um PBF mínimo gerado no próprio teste (pyosmium `SimpleWriter`,
  3 nós e 2 ways, um deles sem `highway`): o JSON tem o formato que
  `_parse_osm_ways`/`_build_nodes_dict` do gisbr aceitam, e o way sem `highway` fica de fora.

### Passo 6 — Build de uma RM (`gisbr_base/processa_rm.py`)
- Entry point de subprocesso: `python -m gisbr_base.processa_rm <id_rm>`. Base:
  `medicao/2026-09-30/scripts/run_path.py`.
- `QgsApplication([], False)` + `initQgis()`. Chama
  `compute_osm_network("rm<id>", nome, bbox, mun_geom, cache_dir=work/cache, rede="veicular")`,
  depois `montar_camadas(dados)`, e grava o GPKG com as 3 camadas de nome
  `osm_*_rm<id>` (D5). Use a mesma função de gravação que o gisbr usa na casca
  `build_osm_municipal_network`. Se ela não for importável isoladamente, reproduza só a
  gravação, **nunca** o cálculo.
- **Aborte com erro** se o log não tiver `OSM: cache reutilizado` (regra 2 do GEMINI.md).
- Escreve `work/out/rm<id>.metrics.json` com contagens, tempos por etapa e
  `maxrss_mb` (`resource.getrusage`, M3).

### Passo 7 — Orquestrador (`build.py` na raiz)
- `python build.py [--regiao sudeste] [--rm 04501 ...] [--pular-existentes]`.
- Sequência: `garante_gisbr` → catálogo → Geofabrik (baixa + filtra) → malhas →
  recorte multi-bbox → conversão → **uma RM por subprocesso** com o limite de memória
  do D9 → zip + sha256 → `work/out/manifest.json` (D7).
- Falha de uma RM (rc ≠ 0, rc 137 = OOM) entra no manifest como `falhou`, com o motivo,
  e o lote segue.
- Apaga o JSON de cache de cada RM depois do build (286 MB só em SP), a menos que
  `--manter-cache`.

### Passo 8 — Validação contra o Overpass (portão, antes de qualquer lote)
- Rode **Vitória município (3205309)** pelo `build.py` e pelo Overpass (a
  `compute_osm_network` do gisbr sem cache), como na medição. Critério: diferença
  < 2% em ways, arcos e problemas (M1 deu < 0,05%). Registre os números no CHANGELOG.
- Até 2 tentativas no Overpass, com 60 s de intervalo (M2). Se as duas falharem, repita
  outro dia. **Não** pule o portão.

### Passo 9 — Portão de memória: São Paulo sozinha
- `python build.py --rm 04901` com o desktop leve.
- Registre pico de RAM, tempo por etapa e tamanho. **Se passar de 12 GB ou der OOM:**
  pare e traga os números para o plano. A saída seria otimizar a verificação no
  **gisbr**, com o gisbr como dono do código, e **não** aqui.
- Confira também, abrindo o GPKG de uma RM no QGIS com o plugin gisbr em modo RM, que
  os arcos da borda batem com o polígono do plugin (D4).

### Passo 10 — Lote completo e Release
- `python build.py` (as 5 regiões). Estimativa: horas. Rode quando a máquina puder
  ficar ligada.
- Publicar: `gh release create osm-AAAAMMDD work/out/*.gpkg.zip work/out/manifest.json`
  com nota de release que traz a atribuição ODbL, o `gisbr_ref`, a data de cada extrato
  e a lista de RMs com `falhou`.
- Confira que `…/releases/latest/download/manifest.json` responde 200 e que o sha256 de
  um asset baixado bate com o do manifest.
- Versão do repo: **0.1.0** no CHANGELOG, com tag de código `v0.1.0`, que é
  **diferente** da tag de dados `osm-AAAAMMDD`.

## Fora do escopo desta rodada

- **Integração no plugin gisbr** (rodada do gisbr): no modo RM, `osm_vias` passa a
  baixar `osm_vias_rm<id>.gpkg.zip` via manifest, conferir `schema_version` e `sha256` e
  copiar as camadas para o GPKG do usuário. Hoje `osm_vias`/`osm_pois` pulam no modo RM
  (D8 da rodada 19 do gisbr).
- `osm_pois` por RM, rede pedestre, RIDEs (a API do IBGE não traz RIDE), download por
  município.
- GitHub Actions (D1).

## Riscos

- **SP pode não caber nem em 16 GB** (M3 é estimativa). O portão é o passo 9.
- **Rio de Janeiro, Campinas, Porto Alegre, Recife, Salvador e Fortaleza** podem ser do
  porte de SP. Tratamento: falha registrada no manifest, sem derrubar o lote.
- **O ref do gisbr envelhece.** Quando o `osm_pipeline` mudar no gisbr, a base publicada
  fica com o comportamento antigo até o próximo build. O `gisbr_ref` no manifest deixa
  isso visível.
