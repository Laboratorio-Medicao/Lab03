"""RQ01–RQ04: mediana e IQR de DF, lead time (a)/(b), CFR (a)/(b) e recuperação (Issue #35).

Reexecutável a partir do CSV, sem estado oculto:

    python -m analysis.rq01_rq04 [--csv data/metrics.csv] [--saida outputs/analise]

Saídas em `--saida`: `rq01_rq04_descritiva.csv` (mediana, Q1, Q3, IQR e n por métrica),
`rq04_censura.csv` (censura por repositório + resumo), `rq0X_*.png` e `dora_class.csv`/
`dora_class_distribuicao.csv` (via `analysis.dora_class_c1`).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from analysis import common, dora_class_c1  # noqa: E402

# métrica -> (coluna, unidade, RQ). LT e recuperação em horas; DF em releases/semana; CFR em proporção.
METRICAS = {
    "Deployment frequency": ("deployment_frequency", "releases/semana", "RQ01"),
    "Lead time (a) por release": ("lt_release_median_h", "horas", "RQ02"),
    "Lead time (b) por commit": ("lt_commit_median_h", "horas", "RQ02"),
    "CFR (a) proxy de CI": ("cfr_a", "proporção", "RQ03"),
    "CFR (b) proxy de entrega": ("cfr_b", "proporção", "RQ03"),
    "Tempo de recuperação": ("rec_median_h", "horas", "RQ04"),
}
LOG = {"deployment_frequency", "lt_release_median_h", "lt_commit_median_h", "rec_median_h"}


def tabela_descritiva(df: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for nome, (col, unidade, rq) in METRICAS.items():
        linhas.append({"rq": rq, "metrica": nome, "coluna": col, "unidade": unidade,
                       **common.resumo(df[col])})
    return pd.DataFrame(linhas)


def tabela_censura(df: pd.DataFrame) -> pd.DataFrame:
    """RQ04: proporção de episódios censurados por repositório (só quem teve episódios)."""
    t = df[["full_name", "n_episodios", "n_episodios_censurados", "prop_episodios_censurados"]].copy()
    t["sem_episodios"] = t["n_episodios"] == 0
    return t


def resumo_censura(df: pd.DataFrame) -> dict:
    com = df[df["n_episodios"] > 0]
    total, cens = int(df["n_episodios"].sum()), int(df["n_episodios_censurados"].sum())
    return {
        "repos": len(df),
        "repos_com_episodios": len(com),
        "repos_sem_episodios": len(df) - len(com),
        "repos_com_algum_censurado": int((com["n_episodios_censurados"] > 0).sum()),
        "episodios_total": total,
        "episodios_censurados": cens,
        "prop_global": cens / total if total else float("nan"),
        **{f"prop_repo_{k}": v for k, v in common.resumo(com["prop_episodios_censurados"]).items()},
    }


def _histograma(df: pd.DataFrame, col: str, titulo: str, unidade: str, destino: Path) -> None:
    s = df[col].dropna()
    q1, med, q3 = common.quartis(s)
    fig, ax = plt.subplots(figsize=(6, 3.6))
    log = col in LOG and (s > 0).all()
    if log:
        ax.set_xscale("log")
    ax.hist(s, bins=_bins(s, log), color="#4c78a8", edgecolor="white")
    ax.axvline(med, color="#e45756", lw=2, label=f"mediana = {med:.3g}")
    ax.axvspan(q1, q3, color="#e45756", alpha=0.15, label=f"IQR = {q1:.3g}–{q3:.3g}")
    ax.set(title=f"{titulo} (n={len(s)})", xlabel=unidade + (" (escala log)" if log else ""),
           ylabel="repositórios")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


def _bins(s: pd.Series, log: bool):
    if log:
        return np.logspace(np.log10(s.min()), np.log10(s.max()), 30)
    return 30


def _boxplot_lt(df: pd.DataFrame, destino: Path) -> None:
    """LT(a) × LT(b) lado a lado: mostra a divergência entre as variantes."""
    d = df[["lt_release_median_h", "lt_commit_median_h"]].dropna()
    fig, ax = plt.subplots(figsize=(5, 3.8))
    ax.boxplot([d["lt_release_median_h"], d["lt_commit_median_h"]], whis=(5, 95), showfliers=False)
    ax.set_xticks([1, 2], ["(a) por release", "(b) por commit"])
    ax.set_yscale("log")
    ax.set(ylabel="mediana por repositório (horas, escala log)",
           title=f"RQ02 — Lead time (n={len(d)})")
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


def _barras_censura(df: pd.DataFrame, destino: Path) -> None:
    s = df.loc[df["n_episodios"] > 0, "prop_episodios_censurados"]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.hist(s, bins=20, range=(0, 1), color="#72b7b2", edgecolor="white")
    ax.set(title=f"RQ04 — episódios censurados por repositório (n={len(s)})",
           xlabel="proporção de episódios censurados", ylabel="repositórios")
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


def _barras_classes(dist: pd.DataFrame, destino: Path) -> None:
    cores = {"Elite": "#54a24b", "High": "#4c78a8", "Medium": "#f58518", "Low": "#e45756"}
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    x = range(len(dist))
    ax.bar(x, dist["n"], color=[cores[c] for c in dist["categoria"]])
    for i, (n, p) in enumerate(zip(dist["n"], dist["pct"])):
        ax.text(i, n, f"{n} ({p:.1f}%)", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(list(x), dist["categoria"])
    ax.set(title="Classificação DORA geral — C1", ylabel="repositórios")
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


def executar(csv: Path, saida: Path) -> dict:
    saida.mkdir(parents=True, exist_ok=True)
    df = common.ler_metricas(csv)

    desc = tabela_descritiva(df)
    desc.to_csv(saida / "rq01_rq04_descritiva.csv", index=False)
    tabela_censura(df).to_csv(saida / "rq04_censura.csv", index=False)
    cens = resumo_censura(df)
    pd.Series(cens).to_frame("valor").to_csv(saida / "rq04_censura_resumo.csv", index_label="indicador")

    _histograma(df, "deployment_frequency", "RQ01 — Deployment frequency", "releases/semana",
                saida / "rq01_df.png")
    _boxplot_lt(df, saida / "rq02_lead_time.png")
    _histograma(df, "cfr_a", "RQ03 — CFR (a) proxy de CI", "proporção", saida / "rq03_cfr_a.png")
    _histograma(df, "cfr_b", "RQ03 — CFR (b) proxy de entrega", "proporção", saida / "rq03_cfr_b.png")
    _histograma(df, "rec_median_h", "RQ04 — Tempo de recuperação", "horas", saida / "rq04_recuperacao.png")
    _barras_censura(df, saida / "rq04_censura.png")

    dist = dora_class_c1.executar(csv, saida)
    _barras_classes(dist, saida / "dora_class_c1.png")
    return {"descritiva": desc, "censura": cens, "distribuicao": dist}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=common.CSV_PADRAO)
    ap.add_argument("--saida", type=Path, default=common.SAIDA_PADRAO)
    a = ap.parse_args(argv)
    r = executar(a.csv, a.saida)
    print(r["descritiva"].to_string(index=False, float_format=lambda v: f"{v:.4g}"))
    print("\nCensura RQ04:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r["censura"].items()})
    print("\nClassificação DORA C1:\n", r["distribuicao"].to_string(index=False))


if __name__ == "__main__":
    main()
