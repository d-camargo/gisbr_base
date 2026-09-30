# Plano — medição OSM por Região Metropolitana (2026-09-30)

## Pergunta que a medição responde
Vale criar um projeto separado que pré-processa a rede OSM por RM e publica um
arquivo por RM (em vez de o plugin gisbr consultar o Overpass e montar a
topologia na máquina do usuário)? Para decidir, medir os dois caminhos em 3 RMs.

## Restrições da máquina (VPS) — respeitar
- 2 núcleos, 7 GB de RAM (~4 GB livres; o gateway do Hermes roda aqui), 23 GB livres em disco.
- **Todo processamento pesado dentro de container com `--memory=3g`**: se estourar,
  morre o container, não o host. Registre o OOM como resultado, não contorne.
- Trabalhe SÓ em `WORK=/tmp/claude-1000/-home-diego/a6f504e6-7c2f-4e12-9bda-6463437dc11c/scratchpad/osm-rm/`.
  **Não edite nada em `~/projects/gisbr`** (só leitura; monte read-only no container).
  Nada de git, nada de commit.
- Overpass público: no máximo 1 tentativa + 1 nova tentativa por RM, com 60 s de
  intervalo. Não martele o servidor. Falha/timeout é resultado válido — registre.
- Não instale nada no host com sudo/apt. Não crie repositório.

## RMs (todas no Sudeste, então um único PBF da Geofabrik)
1. RM Grande Vitória (ES) — pequena
2. RM Belo Horizonte (MG) — média (id 3101 no catálogo)
3. RM São Paulo (SP) — grande
Pegue ids e `codes` de `gisbr/core/regioes_metropolitanas.py` (`listar_todas()`, `codes(id_rm)`).

## Código do gisbr a reutilizar SEM modificar
- `gisbr/core/osm_pipeline.py::compute_osm_network(code_muni, nome_muni, bbox, mun_geom, cache_dir=..., rede="veicular")`
  — lê o cache `cache_dir/osm_overpass_{code_muni}.json` se existir, senão chama o Overpass.
  **Esse cache é o ponto de injeção do caminho B**: escreva o JSON no formato Overpass
  nesse nome e o pipeline pula a rede.
- Formato esperado do payload: `{"elements": [{"type":"way","id":..,"nodes":[..],"tags":{..}}, {"type":"node","id":..,"lat":..,"lon":..}]}`
  (ver `_parse_osm_ways` / `_build_nodes_dict`). Query Overpass original em
  `gisbr/core/connectors/osm.py::build_query`: `way["highway"](bbox); >;` — ou seja, todos os ways com `highway` + os nós deles.
- Use `code_muni = "rm<id>"` como chave do cache.
- `mun_geom`: união (QgsGeometry) dos polígonos dos municípios da RM. Fonte das
  geometrias: API de malhas do IBGE,
  `https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{code}?formato=application/vnd.geo+json`
  (uma chamada por município; baixe uma vez para `WORK/malhas/` e reutilize nos dois caminhos).
  `bbox` = extent da união, em (minx, miny, maxx, maxy) EPSG:4674/4326.
- Para gravar o GPKG, ache no `osm_pipeline.py` como `montar_camadas(dados)` / a casca
  `build_osm_municipal_network` gravam as camadas e reproduza a gravação para
  `WORK/out/<caminho>/rm<id>.gpkg` (camadas osm_links, osm_nodes, osm_problemas).

Container: `docker.io/qgis/qgis:3.44` (já baixado), com
`-v ~/projects/gisbr:/gisbr:ro -v $WORK:/work`, `PYTHONPATH=/gisbr`,
`QT_QPA_PLATFORM=offscreen`, e `QgsApplication([], False)` + `initQgis()` no script.
Meça cada etapa com `time.perf_counter()` no script e o pico de memória com
`/usr/bin/time -v` (Maximum resident set size) dentro do container, se existir;
senão `podman stats --no-stream` em amostragem.

## Passos

### 1. Preparação
- Geometrias IBGE dos municípios das 3 RMs → `WORK/malhas/rm<id>.geojson` (união já dissolvida) + bbox.
- Baixar `https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf`
  para `WORK/pbf/`. Registrar tamanho, tempo de download e a data do extrato
  (`sudeste-latest.osm.pbf` → cabeçalho `osmosis_replication_timestamp`, ou a página `sudeste.html`).

### 2. Ferramenta osmium (escolha a primeira que funcionar, registre qual)
a. imagem de container com osmium-tool (ex.: `docker.io/iboates/osmium`), ou
b. `apt-get download osmium-tool` + `dpkg -x` para um diretório local (sem root; cheque libs com `ldd`), ou
c. `pip install osmium` (pyosmium) num venv dentro de `WORK/` e fazer o recorte em Python.
Para converter PBF → JSON formato Overpass use pyosmium (pode ser `pip install osmium`
dentro do container QGIS, com `--break-system-packages` se preciso) — script
`WORK/pbf2overpass.py`: só ways com tag `highway` + todos os nós referenciados.

> **Revisão 2026-09-30:** caminho A por RM CANCELADO (a decisão de pré-processar já
> está tomada; o baseline não muda nada). Passos 3 e 5 viram uma única verificação
> A×B no município de Vitória (3205309), só para validar a conversão PBF→JSON.

### 3. Caminho A — como o plugin faz hoje (Overpass + pipeline) [CANCELADO por RM]
Para cada RM: `compute_osm_network` sem cache (cache_dir vazio próprio `WORK/cache_A/`),
`rede="veicular"`. Medir: tempo Overpass, tamanho do JSON, tempo de topologia
(`constroi_arcos`+`diagnostica`), tempo da verificação geométrica, pico de RAM,
nº de ways/nós/arcos/problemas, tamanho do GPKG. Se o Overpass falhar/der timeout,
registre a mensagem e o tempo até a falha, e siga para a próxima RM.

### 4. Caminho B — pré-processado (Geofabrik + osmium + mesmo pipeline)
Para cada RM:
- `osmium extract -b <bbox> --strategy complete_ways` do PBF do Sudeste → `rm<id>.osm.pbf` (bbox, igual ao Overpass, para os números serem comparáveis; o pipeline recorta pelo polígono depois).
- `osmium tags-filter ... w/highway` (mantendo os nós referenciados).
- `pbf2overpass.py` → `WORK/cache_B/osm_overpass_rm<id>.json`.
- `compute_osm_network` com `cache_dir=WORK/cache_B/` (não pode tocar a rede — confira no log "cache reutilizado").
- Medir cada etapa (extract, filter, conversão, topologia, verificação), pico de RAM, contagens, tamanho do GPKG e do GPKG zipado (`zip -9`), e também exportar
  `osm_links` para FlatGeobuf (`ogr2ogr -f FlatGeobuf`) e registrar o tamanho.

### 5. Consistência A × B
Onde os dois caminhos rodaram: comparar nº de ways, arcos e problemas. Diferença
pequena (< ~2%) é esperada (datas diferentes do OSM). Diferença grande = bug na
conversão — investigar antes de reportar números do B.

### 6. Extrapolação para as 84 RMs
Com os 3 pontos (arcos × tempo, arcos × tamanho do GPKG zipado), estimar tempo total
de build e espaço total das 84 RMs. Diga claramente que é estimativa linear de 3 pontos.
Liste também os PBFs regionais da Geofabrik necessários para cobrir as 84 RMs
(norte, nordeste, centro-oeste, sudeste, sul) com os tamanhos atuais (só HEAD/página, sem baixar).

### 7. Relatório
Escreva `WORK/RESULTADO.md` com: tabela por RM × caminho × etapa (tempo, RAM, contagens,
tamanhos), a checagem de consistência, a extrapolação, a ferramenta osmium usada, e
tudo que deu errado. Números medidos, não estimados, exceto a seção 6.
Guarde os scripts em `WORK/scripts/`. No fim, apague os `.osm.pbf` grandes do Sudeste
**só se** o disco livre ficar abaixo de 10 GB (registre).

## Critério de "pronto"
`RESULTADO.md` existe, tem as 3 RMs no caminho B com números medidos, e o caminho A
tem número ou falha registrada para cada RM.
