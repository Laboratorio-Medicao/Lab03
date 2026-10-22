"""Figuras compostas do artigo (Issue #42): painéis compactos para o limite de 10 páginas.

Redesenha, a partir de `data/metrics.csv` e dos CSVs de `outputs/analise/`, as mesmas medidas já publicadas
(nenhum número novo) em dois painéis de largura de página:

    python -m analysis.figuras_artigo [--csv data/metrics.csv] [--saida outputs/analise]

Saídas: `fig_rq01_rq02_rq04.png` (DF; LT(a) × LT(b); recuperação) e `fig_rq05.png` (DF × CFR (a) e (b)).
Os gráficos individuais de `rq01_rq04.py`, `rq02_divergencia.py` e `rq05_spearman.py` continuam sendo gerados.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from analysis import common  # noqa: E402
from analysis.rq05_spearman import X, _mediana_por_faixa  # noqa: E402

COR, DEST = "#4c78a8", "#e45756"
plt.rcParams.update({"font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5})


def _pt(v: float, casas: int = 2) -> str:
    return f"{v:.{casas}f}".replace(".", ",")


def _hist_log(ax, serie: pd.Series, titulo: str, xlabel: str, casas: int) -> None:
    s = serie.dropna()
    q1, med, q3 = common.quartis(s)
    ax.hist(s, bins=np.logspace(np.log10(s.min()), np.log10(s.max()), 26), color=COR, edgecolor="white", lw=0.4)
    ax.set_xscale("log")
    ax.axvspan(q1, q3, color=DEST, alpha=0.15)
    ax.axvline(med, color=DEST, lw=1.6)
    ax.set(title=f"{titulo}\nn = {len(s)}; med. {_pt(med, casas)} ({_pt(q1, casas)}–{_pt(q3, casas)})",
           xlabel=xlabel, ylabel="repositórios")


def figura_rq01_rq02_rq04(df: pd.DataFrame, destino: Path) -> None:
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(6.4, 2.3))
    _hist_log(a, df["deployment_frequency"], "RQ01: deploy/semana", "releases/semana (log)", 2)
    d = df[["lt_release_median_h", "lt_commit_median_h"]].dropna()
    d = d[(d > 0).all(axis=1)]
    b.scatter(d["lt_commit_median_h"], d["lt_release_median_h"], s=6, alpha=0.5, color=COR, edgecolor="none")
    lim = [d.min().min(), d.max().max()]
    b.plot(lim, lim, color=DEST, lw=1)
    b.set(xscale="log", yscale="log", xlabel="LT(b) por commit (h)", ylabel="LT(a) por release (h)",
          title=f"RQ02: LT(a) × LT(b) por repositório\nn = {len(d)}; linha: LT(a) = LT(b)")
    _hist_log(c, df["rec_median_h"], "RQ04: recuperação", "horas (log)", 1)
    fig.tight_layout(pad=0.5, w_pad=0.8)
    fig.savefig(destino, dpi=200)
    plt.close(fig)


def figura_rq05(df: pd.DataFrame, saida: Path, destino: Path) -> None:
    r5 = pd.read_csv(saida / "rq05_spearman.csv").set_index("variante")
    fig, axs = plt.subplots(1, 2, figsize=(6.4, 2.6), sharex=True)
    for ax, (v, col, rot) in zip(axs, [("a", "cfr_a", "CFR (a), proxy de CI"), ("b", "cfr_b", "CFR (b), proxy de entrega")]):
        d = df[[X, col]].dropna()
        ax.scatter(d[X], d[col], s=7, alpha=0.4, color=COR, edgecolor="none")
        ax.set_xscale("log")
        m = _mediana_por_faixa(d, col)
        if len(m) >= 2:
            ax.plot(m["x"], m["y"], color=DEST, lw=1.5, marker="o", ms=3)
        x = r5.loc[v]
        ax.set(ylim=(-0.03, 1.03), xlabel="deployment frequency (releases/semana, log)", ylabel=rot + " (proporção)",
               title=f"ρ = {_pt(x['rho'], 3)}  (IC95% {_pt(x['ic95_inf'])}; {_pt(x['ic95_sup'])}), n = {int(x['n'])}")
    fig.tight_layout(pad=0.5, w_pad=0.8)
    fig.savefig(destino, dpi=200)
    plt.close(fig)


def executar(csv: Path, saida: Path) -> None:
    saida.mkdir(parents=True, exist_ok=True)
    df = common.ler_metricas(csv)
    figura_rq01_rq02_rq04(df, saida / "fig_rq01_rq02_rq04.png")
    fonte = saida if (saida / "rq05_spearman.csv").exists() else common.SAIDA_PADRAO  # ρ e IC vêm do RQ05
    figura_rq05(df, fonte, saida / "fig_rq05.png")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=common.CSV_PADRAO)
    ap.add_argument("--saida", type=Path, default=common.SAIDA_PADRAO)
    a = ap.parse_args(argv)
    executar(a.csv, a.saida)
    print("gerado: fig_rq01_rq02_rq04.png e fig_rq05.png em", a.saida)


if __name__ == "__main__":
    main()
