# RESULTADO — medição OSM por Região Metropolitana (2026-09-30)

Tudo em `WORK=/tmp/claude-1000/-home-diego/a6f504e6-7c2f-4e12-9bda-6463437dc11c/scratchpad/osm-rm/`.
Scripts em `WORK/scripts/`, métricas brutas em `WORK/out/{A,B}/*.metrics.json`, logs em `WORK/logs/`.
Nada foi escrito em `~/projects/gisbr` (montado `:ro`), sem git, sem sudo. Container `docker.io/qgis/qgis:3.44`
com `--memory=3g --memory-swap=3g`; osmium-tool em `iboates/osmium` (1.19.0), idem 3g.

## 0. Mudança de escopo e desvios (leia primeiro)

1. **Escopo (ordem do coordenador durante a execução):** o caminho A (Overpass) foi CANCELADO para as 3 RMs.
   Nenhuma consulta Overpass foi feita para RM. O passo 3 e o passo 5 foram substituídos por UMA verificação de
   conversão em Vitória (ES), `code_muni=3205309`: A (Overpass) vs B (Geofabrik+pyosmium+mesmo pipeline).
2. **IDs reais das RMs** (o plano citava "3101" para BH, que não existe no catálogo): Grande Vitória = `04701`
   (7 municípios), Belo Horizonte = `04501` (34), São Paulo = `04901` (39). Chave de cache `rm04701` etc.
   (Vitória município: chave `3205309`.)
3. **`osmium extract` estourou 3 GB (OOM) — não funcionou como descrito** (ver seção 2). Não elevei o limite.
   Desvio adotado (plano passo 2c, "recorte em Python"): pré-filtro `osmium tags-filter w/highway` uma vez no PBF
   inteiro do Sudeste (funcionou) + recorte bbox `complete_ways` reimplementado em pyosmium
   (`scripts/pyextract.py`, mesmo algoritmo: nós no bbox -> ways com algum nó dentro -> todos os nós dessas ways).
   Como a entrada já é só-highway, o `tags-filter` pós-extract do plano ficou redundante e não foi rodado por RM.
4. **URL `sudeste-latest.osm.pbf`** entra em loop de redirect (301 para a mesma URL com `/` no fim; curl -L
   falha com "Maximum (50) redirects followed"). Baixei o arquivo datado para o qual ela aponta:
   `sudeste-260929.osm.pbf`. (Uma 1ª tentativa de download falhou por isso, sem efeito colateral.)
5. **Overpass e "tentativas":** o conector do plugin tenta em cadeia 3 mirrors por chamada. Contei cada execução de
   `compute_osm_network` como 1 tentativa (2 no máximo, 60 s de intervalo); a 1ª bateu em até 3 mirrors (1 requisição cada).
6. **bbox de Vitória:** a união dos municípios inclui ilhas oceânicas (Trindade/Martin Vaz em Vitória), então o bbox
   do município e da RM Grande Vitória vai a lon -28,85 (extensão ~12 graus, quase tudo oceano). Mantido por ser o
   "extent da união" do plano; vale para A e B igualmente.
7. **São Paulo no caminho B: OOM do pipeline** (seção 3). Não há GPKG/FGB de SP. Critério "3 RMs com números
   medidos" atendido só parcialmente (extração, conversão, topologia e filtro medidos; verificação geométrica morreu).
8. Medição de RAM: `/usr/bin/time -v` (osmium) e `resource.getrusage(RUSAGE_SELF).ru_maxrss` dentro do container
   (pyosmium e pipeline QGIS; o QGIS não tem `/usr/bin/time`). O tempo de export FlatGeobuf não foi medido (só tamanho).
9. Disco livre no fim: 20 GB (>10 GB), então **nenhum PBF foi apagado**.

## 1. Preparação

- Malhas IBGE: 80 municípios (7+34+39) baixados para `malhas/mun/`, união dissolvida em `malhas/rm<id>.geojson`,
  bboxes em `malhas/bboxes.json` (QGIS `unaryUnion`, válidas).
- Geofabrik Sudeste: `sudeste-260929.osm.pbf`, **859.700.004 bytes (819 MiB)**, download **79,4 s** (~10,8 MB/s).
  Data do extrato (`osmosis_replication_timestamp` / `timestamp`): **2026-09-29T20:22:51Z** (seq 2476).
  Conteúdo: 142.021.758 nós, 9.362.773 ways, 158.214 relações.
- RMs (bbox EPSG:4674 minx,miny,maxx,maxy):
  - 04701 Grande Vitória: -40.7022, -20.7652, -28.8476, -19.8512
  - 04501 Belo Horizonte: -44.6589, -20.4867, -43.478, -19.0593
  - 04901 São Paulo: -47.2084, -24.0643, -45.6948, -23.1834

## 2. Ferramenta osmium

- (a) **imagem `docker.io/iboates/osmium` (osmium 1.19.0) funcionou** para `tags-filter`, `fileinfo`.
- `osmium tags-filter w/highway` no Sudeste inteiro: **84,9 s, pico RSS 2,05 GB** (cgroup 2,36 GB), saída
  `sudeste-highway.osm.pbf` = 287.140.003 bytes. Feito uma vez (compartilhado pelas RMs).
- **`osmium extract -b ... --strategy complete_ways` = OOM (SIGKILL, rc 9/137) em todas as tentativas**, já na
  "First pass", RSS 3,14 GB (teto do cgroup): RM Grande Vitória (bbox ~12 x 0,9 graus) em 44 s; município de Vitória
  em 26 s; bbox minúsculo (0,15 x 0,10 graus) em 28 s; e também sobre o PBF já prefiltrado (10 s). Ou seja, o pico não
  depende do tamanho do bbox nem do arquivo de entrada nesta versão/máquina. Registrado como resultado, sem contornar o limite.
- pyosmium 4.3.1 (`pip install --target WORK/pylibs osmium` dentro do container QGIS, sem sudo) usado para o
  recorte (`pyextract.py`) e a conversão PBF->JSON Overpass (`pbf2overpass.py`: só ways com `highway` + nós referenciados).

## 3. Tabela principal

Caminho B (pré-processado), por etapa. "Tempo pipeline" = `compute_osm_network` (cache_B, log confirmou
"cache reutilizado"; não tocou a rede). Tempos em segundos.

| Etapa / métrica | Vitória município (3205309) | RM Grande Vitória (04701) | RM Belo Horizonte (04501) | RM São Paulo (04901) |
|---|---|---|---|---|
| Recorte bbox (pyextract, 3 varreduras do PBF highway) | 255,7 | 266,9 | 275,6 | 275,7 |
| Pico RAM recorte (MB) | 156 | 213 | 372 | 620 |
| `.osm.pbf` do recorte (bytes) | 1.670.547 | 5.962.155 | 13.786.179 | 34.583.088 |
| Conversão PBF->JSON (s) | 1,81 | 7,06 | 18,65 | 39,9 |
| Pico RAM conversão (MB) | 33 | 48 | 71 | 76 |
| JSON formato Overpass (bytes) | 13.945.673 | 56.439.479 | 137.952.502 | 286.041.656 |
| Ways / nós no JSON | 25.261 / 124.692 | 65.105 / 591.498 | 163.259 / 1.475.702 | 435.304 / 2.809.071 |
| Carga do JSON + parse (s) | 0,28 | 1,46 | 4,34 | 10,9 |
| Topologia `constroi_arcos`+`diagnostica` (s) | 0,65 | 2,51 | 9,93 | ~24,0 (de 10,9 a 34,9 no log) |
| Filtro pelo polígono (s) | 0,33 | 1,14 | 2,79 | ~6,9 |
| Verificação geométrica (s) | 3,50 | 11,87 | 38,9 | **OOM (container morto, rc 137)** |
| Tempo total `compute_osm_network` (s) | 4,78 | 17,04 | 56,11 | n/d |
| Montar camadas (s) / gravar GPKG (s) | 3,30 / 0,54 | 11,7 / 2,05 | 37,5 / 5,38 | n/d |
| Pico RAM do script do pipeline (MB) | 458 | 1.068 | 2.336 | >= 3.072 (teto do container; OOM) |
| Arcos (todos no bbox) | 48.375 | 123.995 | 337.146 | 872.182 |
| Arcos no município/RM (osm_links) | 22.040 | 113.644 | 265.715 | 710.876 |
| Nós gravados (osm_nodes) | 17.064 | 83.547 | 194.838 | n/d |
| Problemas (osm_problemas) | 218 | 625 | 874 | n/d |
| Componentes (veicular) | 32 | 31 | 99 | 231 |
| GPKG (bytes) | 7.852.032 | 41.062.400 | 97.042.432 | n/d |
| GPKG `zip -9` (bytes) | 3.181.286 | 17.105.937 | 40.503.572 | n/d |
| `osm_links` FlatGeobuf (bytes) | 7.392.864 | 39.288.744 | 92.812.232 | n/d |

Tipos de problema (B): Vitória-mun: ilha 14, mao_unica_sem_saida 12, ponta_quase_conectada 192 (1.552 pontas soltas
não listadas); RM Vitória: ilha 22, mao_unica_sem_saida 105, ponta_quase_conectada 498 (9.503 não listadas);
BH: cruzamento_sem_no 1, ilha 52, mao_unica_sem_saida 123, ponta_quase_conectada 698 (28.808 não listadas).
Observação: GPKG com `zip -9` tem ~40% do tamanho do GPKG; FlatGeobuf de só `osm_links` ~ 95% do GPKG (que tem 3 camadas).

Caminho A (Overpass): **somente Vitória município**, conforme a mudança de escopo. Para as 3 RMs: NÃO EXECUTADO (cancelado).

| Vitória município (3205309) — caminho A | valor |
|---|---|
| Tentativa 1 | FALHOU em 127,8 s: overpass-api.de "Gateway Timeout"; kumi.systems e private.coffee "Operation canceled" |
| Tentativa 2 (60 s depois) | OK. Overpass até payload+parse: 4,12 s |
| JSON (bytes) | 15.976.930 |
| Topologia / filtro / verificação (s) | 0,67 / 0,33 / 3,29 |
| Total `compute_osm_network` (s) | 8,43 |
| Montar camadas / gravar GPKG (s) | 3,05 / 0,51 |
| Pico RAM (MB) | 492 |
| GPKG / zip -9 / FGB `osm_links` (bytes) | 7.835.648 / 3.181.232 / 7.396.240 |

## 4. Consistência A x B (Vitória município, única verificação, validação da conversão PBF->JSON)

| Métrica | A (Overpass, 2026-09-30 ~17:22) | B (Geofabrik 2026-09-29 20:22Z) | Diferença |
|---|---|---|---|
| Ways | 25.265 | 25.261 | -0,016% |
| Nós no JSON | 124.721 | 124.692 | -0,023% |
| Arcos (bbox) | 48.385 | 48.375 | -0,021% |
| Arcos no município | 22.050 | 22.040 | -0,045% |
| Nós gravados (osm_nodes) | 17.071 | 17.064 | -0,041% |
| Problemas | 218 | 218 | 0 |
| Problemas por tipo | ilha 14, mao_unica 12, ponta_quase 192 | idem | 0 |

Diferença bem abaixo de 2%, compatível com extratos de datas diferentes (~20 h de intervalo). A conversão
PBF->JSON (e o recorte pyosmium) está validada para este município. Os `descartados` (tipos de highway sem rede
veicular, p.ex. construction 12, corridor 15, proposed 31) são idênticos nos dois caminhos. O JSON do B é ~13% menor
porque não carrega tags de nós nem metadados do Overpass.
Limite da validação: um município pequeno; não validou BH/SP contra o Overpass (caminho A cancelado nas RMs).

## 5. Extrapolação para as 84 RMs — ESTIMATIVA LINEAR A PARTIR DE POUCOS PONTOS, não medição

Pontos usados: 3 RMs/municípios que rodaram o pipeline completo (Vitória-mun, RM Vitória, BH), mais SP só parcial.
Nº de arcos das outras RMs é DESCONHECIDO (não medi); por isso dou cenários por arco médio, não um total único.

- Tempo do pipeline (B, 1 núcleo efetivo): 0,099 / 0,137 / 0,166 ms por arco (4,78 s/48k, 17,04 s/124k,
  56,1 s/337k): **é superlinear** (~n^1,2), então linear subestima RMs grandes.
  Cenários: 84 RMs do porte da RM Vitória (~124k arcos) = 84 x 17 s = **~24 min**; do porte de BH (~337k) =
  84 x 56 s = **~79 min**.
- Tamanho publicável (GPKG `zip -9`): ~120-138 bytes por arco no bbox (17,1 MB/124k; 40,5 MB/337k).
  Porte RM Vitória: 84 x 17,1 MB = **~1,4 GB**; porte BH: 84 x 40,5 MB = **~3,4 GB**. (FlatGeobuf só de links seria
  ~2x o zip.)
- **RAM é o limitante:** ~7-9 KB por arco no script (1.068 MB/124k; 2.336 MB/337k). No teto de 3 GB cabem
  ~350-430 mil arcos; SP (872 mil arcos) estourou. Toda RM acima desse porte exige mais RAM ou um passo de
  verificação menos hungry — mudança de design que não testei.
- Recorte bbox por RM: ~270 s medidos, dominados pela varredura do PBF (implementação pyosmium, não osmium-tool).
  Escalando pelo tamanho do PBF regional e pelo nº de RMs por região (NE 33, S 23, SE 15, N 10, CO 3; UF da RM
  assumida como a listada no catálogo), ~84 recortes independentes ~ **3,4 h** + 5 pré-filtros (~85 s para o Sudeste,
  ~3,5 min no total escalando por tamanho). Um recorte em lote (uma varredura, várias bboxes) não foi medido.
- Conversão PBF->JSON é desprezível (<= 40 s mesmo em SP).

PBFs regionais da Geofabrik necessários (página `south-america/brazil.html`, 2026-09-30, sem baixar):

| Região | Tamanho | RMs (catálogo) | Municípios |
|---|---|---|---|
| Norte | 152 MB | 10 | 73 |
| Nordeste | 421 MB | 33 | 390 |
| Centro-Oeste | 196 MB | 3 | 34 |
| Sudeste | 819 MB (859.700.004 B medido) | 15 | 343 |
| Sul | 405 MB | 23 | 537 |
| **Total** | **~1.993 MB (~2 GB)** | **84** | 1.377 |

RMs que cruzam fronteira de região (se houver) não foram tratadas; a contagem por região usa a UF do catálogo.

## 6. O que deu errado / foi desviado (resumo)

- `osmium extract` OOM em 3 GB (3 tamanhos de bbox, entrada crua e prefiltrada) -> recorte via pyosmium (desvio).
- Pipeline de SP (B) OOM no 3 GB durante a verificação geométrica (container rc 137 após "710876 arcos dentro do
  município"); sem GPKG/FGB de SP.
- Overpass (Vitória-mun, tentativa 1): Gateway Timeout em 127,8 s; tentativa 2 OK.
- URL `sudeste-latest.osm.pbf` com loop de redirect; usado o arquivo datado.
- IDs de RM diferentes do plano (04501 em vez de "3101").
- Caminho A nas 3 RMs cancelado por ordem do coordenador; passo 5 reduzido a Vitória município.
- Tempo de export FlatGeobuf não medido (`bc` ausente no container); só tamanhos.
- Nenhum PBF apagado (disco livre 20 GB).
