"""Completa o cache (releases com `body`, commits e tags) dos repositórios de repos_final.csv.

Só coleta o que falta: JSON por repositório já existente é reaproveitado; releases sem o campo `body`
(coleta anterior à v9) são recoletadas. Não coleta runs (o CFR (a) e a recuperação já estão em
outputs/resultados.csv). Token em GITHUB_TOKEN.

    python -m scripts.recoletar_cache --repos outputs/repos_final.csv --cache cache/
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

log = logging.getLogger("scripts.recoletar_cache")


def _sem_body(cache_dir: Path, full_name: str) -> bool:
    from pipeline.collect_releases import arquivo_cache

    arq = arquivo_cache(cache_dir, full_name)
    if not arq.exists():
        return False
    releases = json.loads(arq.read_text(encoding="utf-8")).get("releases", [])
    return any("body" not in r for r in releases)


def recoletar(repos_csv: Path, cache_dir: Path, inicio: date, fim: date, client, ordem: str = "direta", pular: int = 0) -> dict:
    from pipeline.collect_commits import collect_commits
    from pipeline.collect_releases import arquivo_cache, collect_releases, pares_com_anterior
    from pipeline.collect_tags import collect_tags
    from pipeline.cache import CachedHttpClient

    cliente = CachedHttpClient(client, cache_dir)
    nomes = [l["full_name"] for l in csv.DictReader(repos_csv.open(encoding="utf-8"))]
    if ordem == "reversa":
        nomes = nomes[::-1]
    nomes = nomes[pular:]  # permite várias instâncias (tokens diferentes) em fatias distintas
    ok, erros = 0, []
    for i, nome in enumerate(nomes, 1):
        try:
            if _sem_body(cache_dir, nome):
                arquivo_cache(cache_dir, nome).unlink()
            releases = collect_releases(cliente, nome, cache_dir)
            pares = pares_com_anterior(releases, inicio, fim)
            collect_commits(cliente, nome, pares, cache_dir)
            collect_tags(cliente, nome, cache_dir)
            ok += 1
        except Exception as exc:  # noqa: BLE001 - segue para o próximo e lista no fim
            log.error("[%d/%d] %s: %s", i, len(nomes), nome, exc)
            erros.append(nome)
        if i % 10 == 0:
            log.info("[%d/%d] ok=%d erros=%d", i, len(nomes), ok, len(erros))
    return {"ok": ok, "erros": erros}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repos", default="outputs/repos_final.csv")
    ap.add_argument("--cache", default="cache")
    ap.add_argument("--inicio", default="2025-10-02")
    ap.add_argument("--fim", default="2026-10-02")
    ap.add_argument("--ordem", choices=("direta", "reversa"), default="direta")
    ap.add_argument("--pular", type=int, default=0, help="descarta os N primeiros da ordem escolhida")
    args = ap.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERRO: defina GITHUB_TOKEN", file=sys.stderr)
        sys.exit(1)
    from pipeline.http_client import HttpClient

    r = recoletar(Path(args.repos), Path(args.cache), date.fromisoformat(args.inicio),
                  date.fromisoformat(args.fim), HttpClient(token), args.ordem, args.pular)
    print(f"ok={r['ok']} erros={len(r['erros'])}")
    for n in r["erros"]:
        print("  falhou:", n)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
