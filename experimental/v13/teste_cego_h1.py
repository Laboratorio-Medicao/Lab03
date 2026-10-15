"""Teste cego da H1 (sufixo `-lts`/`-stable`) — localizar candidatas, montar material cego, avaliar depois.

    python -m experimental.v13.teste_cego_h1 localizar [--permitir-api]   # GITHUB_TOKEN no ambiente
    python -m experimental.v13.teste_cego_h1 pacote    [--permitir-api]
    ... três avaliadores rotulam sozinhos (MD gerado) ...
    python -m experimental.v13.teste_cego_h1 avaliar

Regras pré-registradas (antes de qualquer rótulo ou previsão):
- População: TODAS as releases de deploy (`draft=false`, `prerelease=false`) dos 300 repositórios de
  `outputs/repos_final.csv`, publicadas na janela, com release anterior, cuja tag termina em `-lts` ou
  `-stable` (sem diferenciar caixa). **Sem amostragem e sem olhar previsões**: a seleção é só pelo sufixo.
- Excluídas as releases já rotuladas (amostra-ouro e avaliação independente), para não reaproveitar rótulos.
- O material dos avaliadores NÃO traz previsões, versão da heurística nem a hipótese.
- Os dados da amostra congelada e `metricas/heuristica.py` não são tocados.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PASTA = Path(__file__).resolve().parent / "teste_cego"
CANAL = re.compile(r"-(?:lts|stable)$", re.IGNORECASE)


def _csv(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _cliente(permitir_api: bool):
    from scripts.validacao_independente import ClienteEmCamadas, _cliente as mk
    leitura = [Path("/Users/marcos/Developer/Lab03/cache"), RAIZ / "cache" / "validacao_independente"]
    return mk(RAIZ / "cache" / "teste_h1", [p for p in leitura if p.exists()], permitir_api)


def _janela():
    from pipeline.config import load_config
    c = load_config(str(RAIZ / "config.yaml"))
    return c.janela_inicio, c.janela_fim


def ja_rotuladas() -> set[str]:
    ids = set()
    for p in ("data/amostra_ouro/amostra_ouro.csv", "data/validacao_independente/amostra_validacao.csv"):
        ids |= {str(r["release_id"]) for r in _csv(RAIZ / p)}
    return ids


def localizar(permitir_api: bool) -> dict:
    from pipeline.collect_releases import collect_releases, pares_com_anterior
    from pipeline.selection import ApiError
    ini, fim = _janela()
    client = _cliente(permitir_api)
    usados = ja_rotuladas()
    repos = [r["full_name"] for r in _csv(RAIZ / "outputs/repos_final.csv")]
    cand, falhas, varridos = [], [], 0
    for fn in repos:
        try:
            rels = collect_releases(client, fn, None)
        except (ApiError, Exception) as exc:  # noqa: BLE001
            falhas.append({"full_name": fn, "motivo": f"{type(exc).__name__}: {str(exc)[:100]}"})
            continue
        varridos += 1
        for ant, r in pares_com_anterior(rels, ini, fim):
            if ant is None or not CANAL.search(r["tag_name"]):
                continue
            cand.append({"full_name": fn, "release_id": str(r["id"]), "tag_name": r["tag_name"], "base": ant["tag_name"],
                         "published_at": r["published_at"], "release_url": r.get("html_url") or "",
                         "ja_rotulada": "sim" if str(r["id"]) in usados else "nao"})
    PASTA.mkdir(parents=True, exist_ok=True)
    with (PASTA / "candidatas_h1.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cand[0]) if cand else ["full_name"], lineterminator="\n")
        w.writeheader(); w.writerows(cand)
    info = {"criado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "repos_total": len(repos),
            "repos_varridos": varridos, "falhas": falhas, "candidatas_total": len(cand),
            "candidatas_nao_rotuladas": sum(1 for c in cand if c["ja_rotulada"] == "nao"),
            "repos_com_candidatas": sorted({c["full_name"] for c in cand}),
            "respostas_por_origem": client.contagem, "regra": "sufixo -lts/-stable; sem amostragem; sem previsões"}
    (PASTA / "localizacao.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return info


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["localizar"])
    p.add_argument("--permitir-api", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "localizar":
        info = localizar(a.permitir_api)
        print(json.dumps({k: v for k, v in info.items() if k != "repos_com_candidatas"}, ensure_ascii=False, indent=2))
        print("repositórios com candidatas:", info["repos_com_candidatas"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
