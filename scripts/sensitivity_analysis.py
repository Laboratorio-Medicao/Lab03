"""RQ07 — Análise de sensibilidade: robustez das classificações DORA entre combinações C1/C2/C3.

Combinações definidas em compute_metrics.py:
  C1: DF=release não-draft/não-prerelease, LT=(a) por release, CFR=(a) workflow failure rate
  C2: DF=release+prerelease,               LT=(b) por commit,  CFR=(b) heurística de correção
  C3: DF=tag,                              LT=(b) por commit,  CFR=(a) workflow failure rate

Para cada par (C1×C2, C1×C3, C2×C3):
  - % de repos que mudaram de categoria DORA geral
  - Cohen's kappa linear (concordância ajustada por acaso)
  - Matriz de transição (heat-map e CSV)

Saída: outputs/sensitivity_dora.csv, outputs/sensitivity_dora.md, outputs/sensitivity_transicao.png

Limitação (documentada no artigo): em C2 e C3 só a unidade do deployment frequency muda de fato; LT(b) e
CFR(b) seguem calculados sobre releases. Repositórios sem episódio de recuperação são classificados com 3
métricas (L10, `n_metricas_dora_c*` < 4).
"""

from __future__ import annotations

import csv
from itertools import combinations
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

RAIZ = Path(__file__).parent.parent
METRICS = RAIZ / "data" / "metrics.csv"
OUT_DIR = RAIZ / "outputs"
OUT_CSV = OUT_DIR / "sensitivity_dora.csv"
OUT_MD = OUT_DIR / "sensitivity_dora.md"
OUT_PNG = OUT_DIR / "sensitivity_transicao.png"

ORDEM = ["Elite", "High", "Medium", "Low"]
COMBINACOES = {"C1": "dora_c1", "C2": "dora_c2", "C3": "dora_c3"}


def _encode(series: pd.Series) -> pd.Series:
    return series.map({v: i for i, v in enumerate(ORDEM)})


def analisar_par(df: pd.DataFrame, nome_a: str, nome_b: str) -> dict:
    col_a, col_b = COMBINACOES[nome_a], COMBINACOES[nome_b]
    sub = df[[col_a, col_b]].dropna()
    n = len(sub)
    mudou = (sub[col_a] != sub[col_b]).sum()
    pct_mudou = mudou / n * 100
    kappa = cohen_kappa_score(sub[col_a], sub[col_b], weights="linear",
                              labels=ORDEM)
    return {
        "par": f"{nome_a}×{nome_b}",
        "n": n,
        "n_mudou": int(mudou),
        "pct_mudou": round(pct_mudou, 1),
        "kappa_linear": round(kappa, 3),
    }


def matriz_transicao(df: pd.DataFrame, nome_a: str, nome_b: str) -> pd.DataFrame:
    col_a, col_b = COMBINACOES[nome_a], COMBINACOES[nome_b]
    sub = df[[col_a, col_b]].dropna()
    mat = pd.crosstab(sub[col_a], sub[col_b], rownames=[nome_a], colnames=[nome_b])
    return mat.reindex(index=ORDEM, columns=ORDEM, fill_value=0)


def figura_transicao(df: pd.DataFrame, pares: list, resultados: list, destino: Path) -> None:
    """Matrizes de transição dos três pares (linha = A, coluna = B), com % de mudança e κ no título."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, len(pares), figsize=(2.4 * len(pares), 2.6))
    for ax, (a, b), r in zip(axs, pares, resultados):
        mat = matriz_transicao(df, a, b)
        ax.imshow(mat.values, cmap="Blues")
        for i in range(len(ORDEM)):
            for j in range(len(ORDEM)):
                v = int(mat.values[i, j])
                ax.text(j, i, v, ha="center", va="center", fontsize=10,
                        color="white" if v > mat.values.max() / 2 else "black")
        ax.set_xticks(range(len(ORDEM)), ORDEM, fontsize=8, rotation=45)
        ax.set_yticks(range(len(ORDEM)), ORDEM, fontsize=8)
        ax.set(xlabel=b, ylabel=a, title=f"{a}×{b}\n{r['pct_mudou']}% mudou, κ={r['kappa_linear']}")
        ax.title.set_fontsize(9)
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


def _md_tabela(df: pd.DataFrame) -> str:
    header = "| " + " | ".join([""] + list(df.columns)) + " |"
    sep = "| " + " | ".join(["---"] * (len(df.columns) + 1)) + " |"
    rows = []
    for idx, row in df.iterrows():
        rows.append("| " + " | ".join([str(idx)] + [str(v) for v in row]) + " |")
    return "\n".join([header, sep] + rows)


def run() -> None:
    df = pd.read_csv(METRICS)
    OUT_DIR.mkdir(exist_ok=True)

    pares = list(combinations(COMBINACOES.keys(), 2))
    resultados = [analisar_par(df, a, b) for a, b in pares]

    # CSV de resumo
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(resultados[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(resultados)

    figura_transicao(df, pares, resultados, OUT_PNG)

    # Relatório Markdown
    linhas = [
        "# RQ07 — Análise de sensibilidade das classificações DORA\n",
        "## Resumo por par de combinações\n",
        "| Par | n | Mudaram | % mudou | κ linear |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in resultados:
        linhas.append(
            f"| {r['par']} | {r['n']} | {r['n_mudou']} | {r['pct_mudou']}% | {r['kappa_linear']} |"
        )

    linhas += ["", "## Matrizes de transição\n",
               "> Linha = classificação em A · Coluna = classificação em B · Célula = nº de repos\n"]

    for a, b in pares:
        mat = matriz_transicao(df, a, b)
        linhas += [f"### {a} → {b}\n", _md_tabela(mat), ""]

    linhas += [
        "## Interpretação do κ linear",
        "",
        "| Faixa | Interpretação |",
        "|---|---|",
        "| < 0,20 | Concordância fraca |",
        "| 0,20–0,40 | Razoável |",
        "| 0,40–0,60 | Moderada |",
        "| 0,60–0,80 | Substancial |",
        "| > 0,80 | Quase perfeita |",
        "",
        "Fonte: `data/metrics.csv` · Script: `scripts/sensitivity_analysis.py`",
    ]

    OUT_MD.write_text("\n".join(linhas), encoding="utf-8")

    # Console
    print(f"{'Par':<10} {'n':>5} {'% mudou':>9} {'κ linear':>9}")
    print("-" * 38)
    for r in resultados:
        print(f"{r['par']:<10} {r['n']:>5} {r['pct_mudou']:>8.1f}% {r['kappa_linear']:>9.3f}")
    print(f"\nGravados: {OUT_CSV.name}, {OUT_MD.name}, {OUT_PNG.name}")


if __name__ == "__main__":
    run()
