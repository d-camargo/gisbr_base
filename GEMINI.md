# GEMINI.md — gisbr_base

> **Este arquivo (`GEMINI.md`) é a fonte única das regras deste repo.**
> `CLAUDE.md` e `AGENTS.md` são symlinks relativos para cá. **Edite sempre
> o `GEMINI.md`** — o `agy` não segue symlink e só lê arquivo real, e o
> Edit do Claude Code recusa escrever através de symlink.

Criado em 2026-09-30. Repo: `github.com/d-camargo/gisbr_base`. Na VPS o clone fica
em `~/projects/gisbr-base` (slug com hífen); na máquina do Diego, onde o build roda,
o caminho é livre.

---

## 1. O que é

Base **pré-processada** de dados para o plugin QGIS **gisbr**
(`github.com/d-camargo/gisbr`). Começa pela **rede viária OSM por Região
Metropolitana**. O Overpass não aguenta uma RM inteira, e a topologia em Python
puro dentro do QGIS custa minutos e GB de RAM na máquina do usuário. Por isso este
repo monta a rede **uma vez**, fora do plugin, e publica **um arquivo por RM** na
Release do GitHub. O plugin passa a só baixar o arquivo.

```
Geofabrik (5 PBFs regionais, arquivo DATADO)
  → filtro w/highway (1x por região)
  → recorte complete_ways por bbox de cada RM (1 passada por região)
  → PBF → JSON no formato Overpass → cache do gisbr
  → gisbr.core.osm_pipeline.compute_osm_network (código do gisbr, NÃO copiado)
  → osm_vias_rm<id>.gpkg.zip + manifest.json
  → GitHub Release (asset por RM)
```

O plano vivo está em `PLAN.md`. A medição que fundamentou o desenho está em
`medicao/2026-09-30/RESULTADO.md`. **Leia a medição antes de mudar o pipeline.**

## 2. Onde roda

- **O build roda na máquina do Diego** (Pop!_OS, 16 GB de RAM, QGIS do sistema).
  Não roda na VPS: lá há ~4 GB livres, divididos com o gateway do Hermes, e a RM de
  São Paulo estourou 3 GB (medição 2026-09-30).
- Na VPS só se desenvolve e se testa até o porte da RMBH, sempre em container com
  `--memory=3g`.
- Não há GitHub Actions por enquanto (decisão do Diego em 2026-09-30: build local).

## 3. Divisão de trabalho (regra da casa, vale para qualquer CLI aqui)

Na máquina do Diego não existe o `~/GEMINI.md` da VPS, então a regra vai repetida:

- **O modelo forte planeja e revisa; o fraco executa como subagente.** No `claude`,
  Opus planeja/revisa e Sonnet executa. No `agy`, `gemini-3.1-pro-high` planeja e
  `gemini-3.8-flash-high` executa. No `codex`, o mesmo modelo com effort menor executa.
- **Retorno de subagente é relato, não fato:** confira no `git diff` e nos números
  gerados antes de dar o passo por feito.
- Leitura barata (um `git log`, um `grep`, ler um arquivo) o forte faz direto.

## 4. Regras de trabalho

1. **Reusar o gisbr, nunca copiar.** O pipeline importa `gisbr.core.osm_pipeline`
   de um clone do gisbr fixado num commit (`GISBR_REF` em `gisbr_base/config.py`),
   e esse commit vai para o `manifest.json`. Copiar o código criaria um segundo
   `osm_pipeline` que diverge em silêncio, como aconteceu com o logis. Código
   próprio deste repo: download, recorte, conversão, orquestração e publicação.
   **Nunca** a topologia nem a verificação.
2. **O ponto de injeção é o cache do gisbr.** O `compute_osm_network` lê
   `cache_dir/osm_overpass_<code>.json` quando o arquivo existe. Aqui se escreve
   esse JSON (formato Overpass: `{"elements":[node…, way…]}`) e o pipeline não
   toca a rede. Confira no log a linha `OSM: cache reutilizado`. Sem ela, o build
   consultou o Overpass, e o resultado **não vale**.
3. **Uma RM por subprocesso.** Se uma RM estourar a memória, cai só ela. A falha
   vai para o `manifest.json` (`status: "falhou"`, com o motivo) e o lote segue.
   Ordene da menor para a maior.
4. **IDs de RM são strings de 5 dígitos com zero à esquerda** (`"04501"`, BH). Vêm do
   CSV do gisbr (`gisbr/core/data/regioes_metropolitanas.csv`). **Nunca** tire o
   id de doc ou de memória: o "3101" do doc de medição do gisbr não existe no
   catálogo.
5. **Nomes de camada seguem o modo RM do gisbr** (`Recorte.sufixo` = `rm<id>`):
   `osm_links_rm<id>`, `osm_nodes_rm<id>`, `osm_problemas_rm<id>`. Mudar isso quebra
   o plugin, que vai procurar esses nomes.
6. **Geofabrik: sempre o arquivo datado** (`sudeste-260929.osm.pbf`), nunca
   `*-latest.osm.pbf`. O `latest` entrou em loop de redirect em 2026-09-30, e a
   data do extrato precisa ir para o manifest.
7. **Dados nunca entram no git.** PBF, JSON, GPKG e zip ficam em `work/` (no
   `.gitignore`). O que se publica vai na **Release**, não no repo.
8. **Licenças.** Código: GPL-3.0, porque importa o gisbr, que é GPL-3.0. Dados:
   **ODbL** (derivados do OpenStreetMap). Toda Release e o `manifest.json` levam
   "© OpenStreetMap contributors, ODbL 1.0" e o link
   `https://www.openstreetmap.org/copyright`.
9. **Contrato com o plugin = `manifest.json` + nome dos assets.** Mudou o formato
   (camadas, campos, nome de arquivo)? Suba `schema_version` e registre no
   `CHANGELOG.md`. Um plugin que lê `schema_version` que não conhece deve recusar,
   não adivinhar.
10. **Número medido, não estimado.** Tempo, RAM e tamanho no `manifest.json` e no
    relatório vêm da execução. Onde houver estimativa, escreva que é estimativa.

## 5. Testes

```bash
python3 -m pytest -q tests/
```
Os testes cobrem as partes sem QGIS (catálogo, conversão sobre um PBF mínimo,
manifest). O teste de ponta a ponta é o passo de validação do `PLAN.md` (Vitória,
comparado com o Overpass).
