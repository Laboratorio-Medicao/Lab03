"""RQ02: divergência entre LT(a) (por release) e LT(b) (por commit) por repositório (Issue #42).

As medianas *entre repositórios* de LT(a) e LT(b) quase coincidem, mas isso não diz que as variantes
concordam repositório a repositório. Esta análise compara as duas variantes por repositório, só com
`data/metrics.csv`:

    python -m analysis.rq02_divergencia [--csv data/metrics.csv] [--saida outputs/analise]

Saídas: `rq02_divergencia.csv` (indicadores), `rq02_divergencia.png` (dispersão LT(a) × LT(b) em escala log
e histograma de log2(LT(a)/LT(b))). O CSV não traz os commits individuais, então a hipótese do commit
"esquecido" (um commit antigo infla (a) e quase não afeta (b)) **não** é testável aqui; os indicadores
descrevem o tamanho e o sentido da divergência, sem atribuir causa.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from analysis import common  # noqa: E402

A, B = "lt_release_median_h", "lt_commit_median_h"


def indicadores(df: pd.DataFrame) -> pd.DataFrame:
    d = df[[A, B, "n_releases_avaliadas"]].dropna()
    d = d[(d[A] > 0) & (d[B] > 0)]
    razao = d[A] / d[B]
    q1, med, q3 = common.quartis(razao)
    w = stats.wilcoxon(d[A], d[B])
    rho = stats.spearmanr(np.log2(razao), d["n_releases_avaliadas"])
    linhas = [
        ("n", len(d)),
        ("razao_mediana", med), ("razao_q1", q1), ("razao_q3", q3),
        ("prop_a_maior_que_2b", float((razao > 2).mean())),
        ("prop_a_menor_que_b", float((razao < 1).mean())),
        ("prop_b_maior_que_2a", float((razao < 0.5).mean())),
        ("prop_entre_metade_e_dobro", float(((razao >= 0.5) & (razao <= 2)).mean())),
        ("wilcoxon_pareado_estatistica", float(w.statistic)), ("wilcoxon_pareado_p", float(w.pvalue)),
        ("spearman_log_razao_vs_n_releases_rho", float(rho.statistic)),
        ("spearman_log_razao_vs_n_releases_p", float(rho.pvalue)),
        ("mediana_lt_a_h", float(d[A].median())), ("mediana_lt_b_h", float(d[B].median())),
    ]
    return pd.DataFrame(linhas, columns=["indicador", "valor"])


def figura(df: pd.DataFrame, destino: Path) -> None:
    d = df[[A, B]].dropna()
    d = d[(d[A] > 0) & (d[B] > 0)]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.4, 2.9))
    ax1.scatter(d[B], d[A], s=12, alpha=0.5, color="#4c78a8", edgecolor="none")
    lim = [min(d.min()), max(d.max())]
    ax1.plot(lim, lim, color="#e45756", lw=1.2, label="LT(a) = LT(b)")
    ax1.set(xscale="log", yscale="log", xlabel="LT(b) por commit (h)", ylabel="LT(a) por release (h)")
    ax1.legend(frameon=False, fontsize=8)
    lr = np.log2(d[A] / d[B])
    ax2.hist(lr, bins=30, color="#72b7b2", edgecolor="white")
    ax2.axvline(0, color="#e45756", lw=1.2)
    ax2.set(xlabel="log$_2$(LT(a)/LT(b))", ylabel="repositórios")
    fig.suptitle(f"RQ02 — LT(a) × LT(b) por repositório (n={len(d)})", fontsize=10)
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


def executar(csv: Path, saida: Path) -> pd.DataFrame:
    saida.mkdir(parents=True, exist_ok=True)
    df = common.ler_metricas(csv)
    ind = indicadores(df)
    ind.to_csv(saida / "rq02_divergencia.csv", index=False)
    figura(df, saida / "rq02_divergencia.png")
    return ind


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=common.CSV_PADRAO)
    ap.add_argument("--saida", type=Path, default=common.SAIDA_PADRAO)
    a = ap.parse_args(argv)
    print(executar(a.csv, a.saida).to_string(index=False, float_format=lambda v: f"{v:.4g}"))


if __name__ == "__main__":
    main()
