"""Orquestrador: Geofabrik -> malhas -> recorte -> conversao -> uma RM por subprocesso -> zip -> manifest.
    python build.py [--regiao sudeste ...] [--rm 04501 ...] [--municipio 3205309] [--pular-existentes] [--manter-cache]
Sem --regiao/--rm/--municipio roda as 84 RMs. --municipio e so para validacao (gera gpkg+metrics, fora do manifest)."""
import argparse
import hashlib
import json
import resource
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from gisbr_base import config
from gisbr_base.config import GISBR_REF, MEMORY_MAX, REPO_DIR, SCHEMA_VERSION, WORK_DIR

OUT = WORK_DIR / "out"
ATRIBUICAO = "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright"


def metodo_limite():
    """(prefixo do comando, descricao). systemd-run se funcionar; senao ulimit -v (RLIMIT_AS)."""
    if shutil.which("systemd-run"):
        pre = ["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={MEMORY_MAX}", "-p", "MemorySwapMax=0"]
        if subprocess.run(pre + ["true"], capture_output=True).returncode == 0:
            return pre, f"systemd-run --user --scope MemoryMax={MEMORY_MAX} MemorySwapMax=0"
    return [], f"ulimit -v {MEMORY_MAX} (RLIMIT_AS)"


def roda_rm(id_, pre, log):
    """Roda processa_rm num subprocesso com limite de memoria. Devolve (rc, segundos)."""
    limite = int(MEMORY_MAX.rstrip("G")) << 30
    t = time.perf_counter()
    with open(log, "w") as f:
        rc = subprocess.run(
            pre + [sys.executable, "-m", "gisbr_base.processa_rm", id_], cwd=REPO_DIR, stdout=f, stderr=subprocess.STDOUT,
            preexec_fn=None if pre else (lambda: resource.setrlimit(resource.RLIMIT_AS, (limite, limite)))).returncode
    return rc, round(time.perf_counter() - t, 1)


def zipa(gpkg, dst):
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(gpkg, arcname=Path(gpkg).name)
    h = hashlib.sha256()
    with open(dst, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def mescla_manifest(antigo, novo):
    """Junta `novo` (fontes/rms desta execucao) ao manifest existente: execucoes parciais acumulam.
    Se o gisbr_ref ou o schema mudou, as entradas antigas nao valem e sao descartadas."""
    base = antigo or {}
    if base.get("gisbr_ref") != novo["gisbr_ref"] or base.get("schema_version") != novo["schema_version"]:
        base = {}
    m = {**base, **{k: v for k, v in novo.items() if k not in ("fontes", "rms")}}
    m["fontes"] = {**base.get("fontes", {}), **novo["fontes"]}
    m["rms"] = {**base.get("rms", {}), **novo["rms"]}
    return m


def carrega_manifest():
    p = OUT / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else None


def grava_manifest(novo):
    m = mescla_manifest(carrega_manifest(), novo)
    (OUT / "manifest.json").write_text(json.dumps(m, indent=2, ensure_ascii=False))
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regiao", nargs="+", choices=config.REGIOES)
    ap.add_argument("--rm", nargs="+", metavar="ID5")
    ap.add_argument("--municipio", nargs="+", metavar="COD7")
    ap.add_argument("--pular-existentes", action="store_true")
    ap.add_argument("--manter-cache", action="store_true")
    a = ap.parse_args(argv)

    config.garante_gisbr()
    from gisbr_base import catalogo, converte, geofabrik, malhas, recorte
    rms = catalogo.catalogo()  # ordem D8
    por_id = {r["id"]: r for r in rms}
    for i in a.rm or []:
        if i not in por_id:
            ap.error(f"RM {i} nao existe no catalogo (ids de 5 digitos)")
    for c in a.municipio or []:
        if not (c.isdigit() and len(c) == 7 and c[0] in config.DIGITO_REGIAO):
            ap.error(f"municipio {c}: codigo IBGE de 7 digitos")
    if a.rm:
        sel = [r for r in rms if r["id"] in a.rm]
    elif a.regiao:
        sel = [r for r in rms if r["regiao_geofabrik"] in a.regiao]
    else:
        sel = [] if a.municipio else rms
    # itens: (id, chave, regiao, rm ou None)
    itens = [(r["id"], malhas.chave_de(r["id"]), r["regiao_geofabrik"], r) for r in sel]
    itens += [(c, c, config.DIGITO_REGIAO[c[0]], None) for c in a.municipio or []]

    OUT.mkdir(parents=True, exist_ok=True)
    man = carrega_manifest() or {}
    if a.pular_existentes:
        def feito(i):
            if i[3]:
                e = man.get("rms", {}).get(i[0], {})
                return e.get("status") == "ok" and (OUT / f"osm_vias_{i[1]}.gpkg.zip").exists()
            return (OUT / f"osm_vias_{i[1]}.gpkg").exists() and (OUT / f"{i[1]}.metrics.json").exists()
        pulados = [i[1] for i in itens if feito(i)]
        itens = [i for i in itens if not feito(i)]
        if pulados:
            print("pulando (ja prontos):", ", ".join(pulados))
    if not itens:
        print("nada a fazer")
        return 0

    pre, metodo = metodo_limite()
    print(f"limite de memoria: {metodo}")
    malhas.prepara([i[0] for i in itens])
    from qgis.core import Qgis
    bboxes = json.loads((malhas.MALHAS / "bboxes.json").read_text())
    novo = {"schema_version": SCHEMA_VERSION, "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "gisbr_ref": GISBR_REF, "qgis_version": Qgis.version(), "licenca_dados": "ODbL-1.0",
            "atribuicao": ATRIBUICAO, "rede": "veicular", "memoria_max": MEMORY_MAX, "limite_memoria": metodo,
            "fontes": {}, "rms": {}}
    falhas = 0
    for regiao in [g for g in config.REGIOES if any(i[2] == g for i in itens)]:
        grupo = [i for i in itens if i[2] == regiao]
        try:
            fonte = geofabrik.baixa(regiao)
            novo["fontes"][regiao] = {k: fonte[k] for k in ("arquivo", "timestamp_osm", "bytes")}
            filtrado = geofabrik.filtra(regiao, fonte["path"])
            pasta = WORK_DIR / "recorte"
            pasta.mkdir(exist_ok=True)
            saidas = {i[1]: pasta / f"{i[1]}.osm.pbf" for i in grupo}
            r = recorte.recorta(filtrado, {i[1]: bboxes[i[1]] for i in grupo}, saidas)
            print(f"recorte {regiao}: {len(grupo)} bbox(es) em {r['_tempos']['total_s']} s, pico {r['_maxrss_mb']} MB", flush=True)
        except Exception as e:  # a regiao inteira cai, o lote segue
            print(f"FALHOU regiao {regiao}: {e}", flush=True)
            for i in grupo:
                if i[3]:
                    novo["rms"][i[0]] = {"status": "falhou", "motivo": f"regiao {regiao}: {e}"}
                falhas += 1
            grava_manifest(novo)
            continue
        for id_, chave, _, rm in grupo:
            cache = WORK_DIR / "cache" / f"osm_overpass_{chave}.json"
            cache.parent.mkdir(exist_ok=True)
            print(f"== {chave}", flush=True)
            try:
                c = converte.converte(saidas[chave], cache)
                print(f"conversao: {c['ways']} ways, {c['nos']} nos, {c['s']} s", flush=True)
                (OUT / f"osm_vias_{chave}.gpkg").unlink(missing_ok=True)
                (OUT / f"{chave}.metrics.json").unlink(missing_ok=True)
                rc, seg = roda_rm(id_, pre, OUT / f"{chave}.log")
                if rc != 0:
                    ult = next((l for l in reversed((OUT / f"{chave}.log").read_text().splitlines()) if l.strip()), "")
                    raise RuntimeError(f"OOM (rc {rc})" if rc in (137, -9) else f"rc {rc}: {ult[:200]}")
                m = json.loads((OUT / f"{chave}.metrics.json").read_text())
                if rm:
                    zp = OUT / f"osm_vias_{chave}.gpkg.zip"
                    sha = zipa(OUT / f"osm_vias_{chave}.gpkg", zp)
                    novo["rms"][id_] = {
                        "nome": rm["nome"], "uf": rm["uf"], "regiao_geofabrik": regiao, "fonte": novo["fontes"][regiao]["arquivo"],
                        "status": "ok", "asset": zp.name, "bytes": zp.stat().st_size, "sha256": sha,
                        "n_ways": m["n_ways"], "n_arcos": m["n_arcos_poligono"], "n_arcos_bbox": m["n_arcos_todos"],
                        "n_nos": m["n_nos"], "n_problemas": m["n_problemas"], "t_build_s": seg, "maxrss_mb": m["maxrss_mb"]}
                print(f"ok {chave}: {seg} s no subprocesso, pico {m['maxrss_mb']} MB", flush=True)
            except Exception as e:
                falhas += 1
                print(f"FALHOU {chave}: {e}", flush=True)
                if rm:
                    novo["rms"][id_] = {"nome": rm["nome"], "uf": rm["uf"], "regiao_geofabrik": regiao,
                                        "status": "falhou", "motivo": str(e)}
            finally:
                if not a.manter_cache:
                    cache.unlink(missing_ok=True)
                    saidas[chave].unlink(missing_ok=True)
            if rm:
                grava_manifest(novo)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
