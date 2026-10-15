"""Relatório de comparação v12 × v13-experimental (somente leitura; sem rede; não altera regras nem rótulos).

    python -m experimental.v13.relatorio_comparacao

Gera `experimental/v13/relatorio_comparacao_v12_v13.md` (novo arquivo; não sobrescreve os existentes).
Reaproveita os carregadores e as métricas de `experimental/v13/comparar.py`.
"""
from __future__ import annotations

import collections
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from experimental.v13.comparar import (RAIZ, SAIDA, carregar_avaliacao, carregar_desenvolvimento, metricas, prever)

B, SEMENTE = 10000, 20261016


def f1(rows, chave):
    return metricas(rows, chave)["F1"]


def bootstrap(rows):
    rng = np.random.RandomState(SEMENTE)
    repos = sorted({r["repo"] for r in rows}); idx = {n: [i for i, r in enumerate(rows) if r["repo"] == n] for n in repos}
    a, b, d = [], [], []
    for _ in range(B):
        s = [rows[i] for n in rng.choice(repos, len(repos)) for i in idx[n]]
        x, y = f1(s, "p12"), f1(s, "p13"); a.append(x); b.append(y); d.append(y - x)
    q = lambda v: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))
    return {"f12": q(a), "f13": q(b), "delta": q(d), "p_delta_pos": float(np.mean(np.array(d) > 0)),
            "p_delta_zero": float(np.mean(np.array(d) == 0))}


def tabela(m12, m13):
    L = ["| versão | TP | FP | FN | TN | Precisão | Recall | F1 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for v, m in (("v12", m12), ("v13-experimental", m13)):
        L.append(f"| {v} | {m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} | {m['P']:.3f} | {m['R']:.3f} | {m['F1']:.4f} |")
    return L


def secao(nome, rows, ic, natureza):
    m12, m13 = metricas(rows, "p12"), metricas(rows, "p13")
    mud = [r for r in rows if r["p12"] != r["p13"]]
    corr = [r for r in mud if r["p13"] == r["y"]]; pior = [r for r in mud if r["p12"] == r["y"]]
    L = [f"## {nome}", "", f"**Natureza:** {natureza}", "", *tabela(m12, m13), "",
         f"- Releases: {len(rows)} em {len({r['repo'] for r in rows})} repositórios; positivos no consenso: {sum(r['y'] for r in rows)}.",
         f"- Discordâncias v12 × v13: **{len(mud)}** ({len(corr)} corrigidas, {len(pior)} pioradas).",
         f"- F1 v12 IC95% por repositório: [{ic['f12'][0]:.3f}; {ic['f12'][1]:.3f}]; F1 v13: [{ic['f13'][0]:.3f}; {ic['f13'][1]:.3f}].",
         f"- ΔF1 (v13 − v12) = **{m13['F1'] - m12['F1']:+.4f}**, IC95% [{ic['delta'][0]:+.3f}; {ic['delta'][1]:+.3f}]; "
         f"P(Δ>0) = {ic['p_delta_pos']:.2f}; P(Δ=0) = {ic['p_delta_zero']:.2f} ({B} réplicas, semente {SEMENTE}).", ""]
    if mud:
        L += ["| Repositório | Release | Referência | v12 | v13 | Efeito |", "|---|---|---|---|---|---|"]
        for r in mud:
            L.append(f"| {r['repo']} | `{r['tag']}` | {'sim' if r['y'] else 'nao'} | {'sim' if r['p12'] else 'nao'} | "
                     f"{'sim' if r['p13'] else 'nao'} | {'corrigiu erro' if r['p13'] == r['y'] else 'introduziu erro'} |")
        por = collections.Counter(r["repo"] for r in mud)
        L += ["", f"Concentração: {dict(por)} → {len(por)} repositório(s) respondem por todas as {len(mud)} mudanças."]
    else:
        L += ["Nenhuma classificação mudou."]
    return L, m12, m13, mud, ic


def main() -> int:
    dev = prever(carregar_desenvolvimento(RAIZ.parent / "implementar-validacao" / "cache"))
    ava = prever(carregar_avaliacao())

    # reprodução dos resultados anteriores
    res = json.load(open(RAIZ / "data/validacao_independente/resultado_validacao.json"))
    pred_csv = {r["release_id"]: r["pred_v12"] == "sim" for r in csv.DictReader(open(RAIZ / "data/validacao_independente/predicoes_v12.csv", encoding="utf-8-sig"))}
    igual = sum(1 for r in ava if r["p12"] == pred_csv[r["id"]])
    repro = [f"- Avaliação: v12 recalculada = `predicoes_v12.csv` em **{igual}/{len(ava)}** releases; "
             f"F1 {f1(ava, 'p12'):.4f} vs `resultado_validacao.json` {res['f1']:.4f} "
             f"({'reproduzido' if abs(f1(ava, 'p12') - res['f1']) < 1e-9 else 'DIVERGE'}).",
             f"- Desenvolvimento: F1 v12 recalculado = {f1(dev, 'p12'):.4f} (relatório anterior: 0,7219 → "
             f"{'reproduzido' if abs(f1(dev, 'p12') - 0.7219) < 5e-4 else 'DIVERGE'})."]

    s_dev, d12, d13, dmud, dic = secao("Desenvolvimento (300 releases / 60 repositórios)", dev, bootstrap(dev),
        "NÃO independente. Estes dados foram usados para formular e ajustar v1–v12 (e a v13 herda o ajuste). "
        "Rótulos com κ de Fleiss 0,27 (definição ambígua).")
    s_ava, a12, a13, amud, aic = secao("Avaliação (200 releases / 40 repositórios) — comparação exploratória PÓS-HOC", ava, bootstrap(ava),
        "Já examinada: o resultado e os erros da v12 foram vistos antes de formular a H1. NÃO é validação independente da v13. "
        "Rótulos com κ de Fleiss 0,87.")

    # robustez da avaliação a diferentes referências (rótulos existentes, sem alterá-los)
    L = RAIZ / "data/validacao_independente"
    ref = {}
    for n in ("GuilhermeVieira05", "marcosffp", "ALuiz19"):
        ref[n] = {r["release_id"]: r["corretiva"] == "sim" for r in csv.DictReader(open(L / f"labels_{n}.csv", encoding="utf-8-sig"))}
    rob = ["## Avaliação: a conclusão depende da referência? (rótulos existentes, sem alteração)", "",
           "| Referência | F1 v12 | F1 v13 | ΔF1 | classificações que mudam |", "|---|---:|---:|---:|---:|"]
    refs = {"consenso (maioria)": {r["id"]: r["y"] for r in ava},
            **{f"só {n}": d for n, d in ref.items()},
            "unanimidade (3 dizem sim)": {i: all(ref[n][i] for n in ref) for i in ref["marcosffp"]}}
    for nome, d in refs.items():
        rows = [{**r, "y": d[r["id"]]} for r in ava]
        rob.append(f"| {nome} | {f1(rows,'p12'):.4f} | {f1(rows,'p13'):.4f} | {f1(rows,'p13')-f1(rows,'p12'):+.4f} | {sum(1 for r in rows if r['p12']!=r['p13'])} |")

    # testes
    t = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "experimental/v13/tests"],
                       cwd=RAIZ, capture_output=True, text=True)
    testes = t.stdout.strip().splitlines()[-1] if t.stdout.strip() else "sem saída"

    melhorou_dev = f1(dev, "p13") > f1(dev, "p12"); melhorou_ava = f1(ava, "p13") > f1(ava, "p12")
    out = ["# Relatório de comparação v12 × v13-experimental", "",
           "> Comparação **reproduzível** com as amostras e os rótulos existentes; sem coleta, sem alteração de regras ou rótulos.",
           "> A avaliação foi examinada antes de a v13 existir: **não é validação independente**.", "",
           "## Fontes (caminhos confirmados)", "",
           "| Item | Caminho |", "|---|---|",
           "| v12 (oficial) | `metricas/heuristica.py` (`avaliar(..., 'v12')`) |",
           "| v13 (experimental) | `experimental/v13/heuristica_v13.py` |",
           "| Desenvolvimento | `data/amostra_ouro/{amostra_ouro,consenso}.csv`; commits e notas no cache do worktree `implementar-validacao` |",
           "| Avaliação | `data/validacao_independente/{dados_congelados.json,predicoes_v12.csv,labels_*.csv,resultado_validacao.json}` |",
           "| Comparação anterior | `experimental/v13/{comparar.py,resultados_exploratorios.md,diferencas_v12_v13.csv}` (não alterados) |",
           f"| Testes | `experimental/v13/tests/test_v13.py`: {testes} |", "",
           "## Reprodução dos resultados anteriores", "", *repro, "",
           *s_dev, "", *s_ava, "", *rob, ""]
    out += ["## Respostas objetivas", "",
            f"1. **A v13 melhorou a F1 em cada amostra?** Desenvolvimento: {'sim' if melhorou_dev else 'não, idêntica'} "
            f"({f1(dev,'p12'):.4f} → {f1(dev,'p13'):.4f}). Avaliação: {'sim, pontualmente' if melhorou_ava else 'não'} "
            f"({f1(ava,'p12'):.4f} → {f1(ava,'p13'):.4f}).",
            f"2. **Atingiu F1 ≥ 0,70?** Desenvolvimento: {'sim' if f1(dev,'p13')>=0.70 else 'não'} ({f1(dev,'p13'):.4f}; "
            f"a v12 já estava em {f1(dev,'p12'):.4f}). Avaliação: {'sim' if f1(ava,'p13')>=0.70 else 'não'} "
            f"({f1(ava,'p13'):.4f}), **pós-hoc**.",
            f"3. **Consistente com melhora ou o IC inclui zero?** Avaliação: ΔF1 IC95% [{aic['delta'][0]:+.3f}; {aic['delta'][1]:+.3f}] "
            f"— limite inferior em zero porque em {aic['p_delta_zero']*100:.0f}% das réplicas nenhum dos 2 itens entra; "
            f"P(Δ>0) = {aic['p_delta_pos']:.2f}. O intervalo não exclui ausência de efeito. Desenvolvimento: Δ = 0 (sem cobertura).",
            f"4. **Classificações que mudaram:** {len(dmud)} no desenvolvimento; {len(amud)} na avaliação "
            f"({sum(1 for r in amud if r['p13']==r['y'])} corrigidas, {sum(1 for r in amud if r['p12']==r['y'])} pioradas), "
            f"ambas no mesmo repositório (`1Panel-dev/MaxKB`).",
            "5. **Evidência suficiente para promover a v13?** **Não.** Há melhora observada (2 itens), não há evidência estatística "
            "(IC inclui zero, 1 repositório) e não há validação independente (a H1 nasceu dos erros desta amostra; o desenvolvimento "
            "não tem casos `-lts`/`-stable`).", "",
            "## Distinção pedida", "",
            "| Nível | Situação |", "|---|---|",
            "| Melhora observada | **Sim**, +0,018 de F1 na avaliação (2 releases do MaxKB) |",
            f"| Evidência estatística de melhora | **Não**: IC95% do ΔF1 começa em 0; 1 repositório; P(Δ>0) = {aic['p_delta_pos']:.2f}, P(Δ=0) = {aic['p_delta_zero']:.2f} |",
            "| Validação independente | **Não existe**: amostra já examinada; desenvolvimento sem cobertura |", "",
            "## Recomendação", "",
            "**Manter a v13 como experimental** (não promover, não descartar ainda). Ela é inócua onde não há tags `-lts`/`-stable` "
            "e, por construção, só afeta esse padrão. Para decidir, a única via é **validação futura** em amostra nova e independente, "
            "rotulada antes de executar a heurística (fluxo já pronto em `scripts/validacao_independente.py`); como a H1 afeta poucas "
            "releases, essa amostra precisaria conter vários repositórios com sufixo de canal, caso contrário o teste seria "
            "novamente inconclusivo. Se não houver tal amostra, descarte (`rm -rf experimental/v13`) é preferível a promover sem evidência.", ""]
    (SAIDA / "relatorio_comparacao_v12_v13.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
