"""Compara v12 × v13-experimental nos dados já existentes (somente leitura; sem rede).

    python -m experimental.v13.comparar [--cache-dev /caminho/implementar-validacao/cache]

- DESENVOLVIMENTO (300 releases): rótulos de data/amostra_ouro/consenso.csv; commits e notas do cache
  do worktree `implementar-validacao` (não versionado).
- AVALIAÇÃO (200 releases): data/validacao_independente/. A v13 foi formulada **depois** de ver esses
  erros: os números aqui são EXPLORATÓRIOS e PÓS-HOC; não validam a v13 e não devem ser usados para escolher.
Grava `experimental/v13/resultados_exploratorios.md` e `diferencas_v12_v13.csv`.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

from experimental.v13.heuristica_v13 import corretiva as v13
from metricas.heuristica import avaliar as v12

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = Path(__file__).resolve().parent


def _csv(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))


def carregar_desenvolvimento(cache: Path) -> list[dict]:
    ao = RAIZ / "data/amostra_ouro"
    am = _csv(ao / "amostra_ouro.csv")
    cons = {r["item_id"]: r["rotulo_consenso"] for r in _csv(ao / "consenso.csv") if r["dimensao"] == "corretiva"}
    saida = []
    for a in am:
        fn, tag, rid = a["full_name"], a["tag_name"], a["release_id"]
        base = a["compare_url"].split("/compare/", 1)[1][: -len("..." + tag)] if a["compare_url"] else None
        msgs, status = [], "sem_anterior" if base is None else "faltando"
        if base is not None:
            f = cache / "commits" / (fn.lower().replace("/", "__") + ".json")
            d = json.load(open(f))["comparacoes"].get(f"{base}...{tag}") if f.exists() else None
            if d:
                status, msgs = d["status"], [c["message"] for c in d["commits"]] if d["status"] == "ok" else []
        k = hashlib.sha256(json.dumps({"path": f"/repos/{fn}/releases/{rid}", "params": []}, sort_keys=True).encode()).hexdigest()
        nf = cache / f"{k}.json"
        body = ""
        if nf.exists():
            j = json.load(open(nf))
            body = ((j["body"] or {}).get("body") or "") if j["status_code"] == 200 and isinstance(j["body"], dict) else ""
        saida.append({"id": rid, "repo": fn, "tag": tag, "base": base, "msgs": msgs, "body": body, "status": status,
                      "y": cons[rid] == "sim"})
    return saida


def carregar_avaliacao() -> list[dict]:
    L = RAIZ / "data/validacao_independente"
    d = json.load(open(L / "dados_congelados.json"))
    ref = {r["release_id"]: r["consenso"] == "sim" for r in _csv(L / "predicoes_v12.csv")}
    return [{"id": rid, "repo": x["full_name"], "tag": x["tag_name"], "base": x["base"],
             "msgs": [c["message"] for c in x["commits"]] if x["status"] == "ok" else [],
             "body": x.get("body") or "", "status": x["status"], "y": ref[rid]} for rid, x in d.items()]


def prever(rows):
    for r in rows:
        r["p12"] = bool(v12(r["base"], r["tag"], r["msgs"], "v12", notas=r["body"])["heuristic_corrective"])
        r["p13"] = bool(v13(r["base"], r["tag"], r["msgs"], r["body"])["heuristic_corrective"])
    return rows


def metricas(rows, chave):
    tp = sum(1 for r in rows if r["y"] and r[chave]); fp = sum(1 for r in rows if not r["y"] and r[chave])
    fn = sum(1 for r in rows if r["y"] and not r[chave]); tn = len(rows) - tp - fp - fn
    P = tp / (tp + fp) if tp + fp else 0.0; R = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "P": P, "R": R, "F1": 2 * P * R / (P + R) if P + R else 0.0}


def delta_ic(rows, B=5000, seed=11):
    import numpy as np
    rng = np.random.RandomState(seed)
    repos = sorted({r["repo"] for r in rows}); idx = {n: [i for i, r in enumerate(rows) if r["repo"] == n] for n in repos}
    out = []
    for _ in range(B):
        s = [rows[i] for n in rng.choice(repos, len(repos)) for i in idx[n]]
        out.append(metricas(s, "p13")["F1"] - metricas(s, "p12")["F1"])
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cache-dev", default=str(RAIZ.parent / "implementar-validacao" / "cache"))
    a = p.parse_args(argv)
    conj = {"DESENVOLVIMENTO (n=300)": prever(carregar_desenvolvimento(Path(a.cache_dev))),
            "AVALIAÇÃO (n=200) — PÓS-HOC / EXPLORATÓRIO": prever(carregar_avaliacao())}
    linhas = ["# v12 × v13-experimental (H1) — resultados exploratórios", "",
              "> v13 = v12 + sufixo `-lts`/`-stable` não é pré-release. **Não validada.** Formulada depois de ver os erros da",
              "> amostra de avaliação; os números dessa amostra são pós-hoc e **não** são evidência de que a meta foi atingida.", ""]
    dif = []
    for nome, rows in conj.items():
        m12, m13 = metricas(rows, "p12"), metricas(rows, "p13")
        mudou = [r for r in rows if r["p12"] != r["p13"]]
        ic = delta_ic(rows)
        linhas += [f"## {nome}", "", "| versão | TP | FP | FN | TN | Precisão | Recall | F1 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for v, m in (("v12", m12), ("v13-experimental", m13)):
            linhas.append(f"| {v} | {m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} | {m['P']:.3f} | {m['R']:.3f} | {m['F1']:.4f} |")
        linhas += ["", f"- Releases cuja previsão muda: **{len(mudou)}** "
                       f"({sum(1 for r in mudou if r['y'])} positivas no consenso, {sum(1 for r in mudou if not r['y'])} negativas).",
                   f"- ΔF1 (v13 − v12) = {m13['F1'] - m12['F1']:+.4f}; IC95% por repositório [{ic[0]:+.3f}; {ic[1]:+.3f}].", ""]
        for r in mudou:
            dif.append({"amostra": nome.split(" (")[0], "full_name": r["repo"], "tag": r["tag"], "consenso": "sim" if r["y"] else "nao",
                        "v12": "sim" if r["p12"] else "nao", "v13": "sim" if r["p13"] else "nao"})
    linhas += ["## Ressalvas", "",
               "- O desenvolvimento não tem tags `-lts`/`-stable`: efeito nulo ali é **falta de cobertura**, não evidência a favor.",
               "- Na avaliação, o ganho vem de poucos itens de poucos repositórios; está dentro do intervalo de confiança.",
               "- Para validar a v13 é preciso uma amostra nova, independente e rotulada antes de rodar a heurística."]
    (SAIDA / "resultados_exploratorios.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    with (SAIDA / "diferencas_v12_v13.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["amostra", "full_name", "tag", "consenso", "v12", "v13"], lineterminator="\n")
        w.writeheader(); w.writerows(dif)
    print("\n".join(linhas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
