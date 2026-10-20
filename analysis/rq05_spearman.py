"""RQ05: correlação de Spearman entre deployment frequency e CFR (a) e (b) (Issue #37).

Reexecutável a partir do CSV, sem estado oculto:

    python -m analysis.rq05_spearman [--csv data/metrics.csv] [--saida outputs/analise]

Saídas em `--saida`: `rq05_spearman.csv` (ρ, p-valor, n e IC95% por variante), `rq05_sensibilidade_cfr_b.csv`
(diagnóstico de (b) por nº mínimo de releases avaliadas), `rq05_spearman.md` (tabelas e notas de método) e
`rq05_df_cfr_a.png`/`rq05_df_cfr_b.png` (dispersão com DF em escala log).

Decisões: pares completos por variante (repositório sem CFR fica fora só daquela variante, sem imputação; zeros de
CFR são mantidos); `scipy.stats.spearmanr` com ranks médios em empates e p-valor bilateral pela aproximação t; IC95%
de ρ pela transformação z de Fisher com erro-padrão de Bonett e Wright (2000). O CFR (b) é exploratório (heurística
não validada, F1 independente 0,689; ver artigo/metodologia.tex).
"""
from __future__ import annotations

import argparse
import math
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import scipy  # noqa: E402
from scipy import stats  # noqa: E402

from analysis import common  # noqa: E402

X = "deployment_frequency"
VARIANTES = {"a": ("cfr_a", "CFR (a) proxy de CI"), "b": ("cfr_b", "CFR (b) proxy de entrega")}
ALFA = 0.05
IC_METODO = "Fisher z, SE de Bonett e Wright (2000)"
COL_AVALIADAS = "n_releases_avaliadas_cfr_b"
# Cortes pré-declarados da sensibilidade de (b); diagnóstico do efeito de denominador pequeno, não análise principal.
CORTES_AVALIADAS = (5, 10, 20)
CORTE_ZEROS = 10
FAIXAS_DF = 10

COLUNAS = ["variante", "rotulo", "coluna_x", "coluna_y", "n", "n_excluidos", "excluidos", "n_cfr_zero", "rho",
           "p_valor", "alfa", "ic95_inf", "ic95_sup", "ic_metodo", "forca", "direcao"]


def ic_spearman(rho: float, n: int, nivel: float = 0.95) -> tuple[float, float]:
    """IC de ρ: z de Fisher com SE = sqrt((1 + ρ²/2) / (n − 3)) (Bonett e Wright, 2000).

    Indefinido (NaN) com n < 4 ou ρ NaN; com |ρ| = 1 o intervalo degenera em (ρ, ρ).
    """
    if n < 4 or rho is None or math.isnan(rho):
        return float("nan"), float("nan")
    if abs(rho) >= 1:
        return float(rho), float(rho)
    z = math.atanh(rho)
    se = math.sqrt((1 + rho ** 2 / 2) / (n - 3))
    zc = stats.norm.ppf(0.5 + nivel / 2)
    return math.tanh(z - zc * se), math.tanh(z + zc * se)


def forca(rho: float) -> str:
    """Rótulo descritivo de |ρ| (Cohen, 1988); a decisão estatística usa o p-valor e o IC."""
    if math.isnan(rho):
        return ""
    r = abs(rho)
    return "desprezível" if r < 0.1 else "fraca" if r < 0.3 else "moderada" if r < 0.5 else "forte"


def direcao(ic_inf: float, ic_sup: float) -> str:
    """Direção pelo IC95%: só é positiva/negativa quando o intervalo exclui o zero."""
    if math.isnan(ic_inf) or math.isnan(ic_sup):
        return ""
    if ic_inf > 0:
        return "positiva"
    if ic_sup < 0:
        return "negativa"
    return "inconclusiva (IC contém 0)"


def _spearman(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    """ρ e p só com n ≥ 3 e variância não nula nas duas séries; caso contrário NaN (sem aviso)."""
    if len(x) < 3 or x.nunique() < 2 or y.nunique() < 2:
        return float("nan"), float("nan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", stats.ConstantInputWarning)
        r = stats.spearmanr(x, y)
    return float(r.statistic), float(r.pvalue)


def correlacao(df: pd.DataFrame, col_y: str, variante: str = "", rotulo: str = "") -> dict:
    """Spearman entre DF e `col_y` nos pares completos (exclusão listwise só desta variante)."""
    completo = df[X].notna() & df[col_y].notna()
    d = df[completo]
    nomes = df.loc[~completo, "full_name"] if "full_name" in df else pd.Series(dtype=str)
    rho, p = _spearman(d[X], d[col_y])
    n = len(d)
    inf, sup = ic_spearman(rho, n)
    return {
        "variante": variante, "rotulo": rotulo, "coluna_x": X, "coluna_y": col_y,
        "n": n, "n_excluidos": int((~completo).sum()), "excluidos": "; ".join(map(str, nomes)),
        "n_cfr_zero": int((d[col_y] == 0).sum()), "rho": rho, "p_valor": p, "alfa": ALFA,
        "ic95_inf": inf, "ic95_sup": sup, "ic_metodo": IC_METODO, "forca": forca(rho), "direcao": direcao(inf, sup),
    }


def tabela(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([correlacao(df, col, v, rot) for v, (col, rot) in VARIANTES.items()], columns=COLUNAS)


def sensibilidade_cfr_b(df: pd.DataFrame, cortes=CORTES_AVALIADAS) -> pd.DataFrame:
    """ρ de DF × CFR (b) só entre repositórios com ≥ corte releases avaliadas.

    Ressalva: DF e nº de releases avaliadas são quase o mesmo ranking, então o corte também restringe a faixa de
    DF, e restrição de faixa por si só reduz |ρ|.
    """
    col, rot = VARIANTES["b"]
    linhas = []
    for c in cortes:
        sub = df[df[COL_AVALIADAS] >= c]
        linhas.append({"min_releases_avaliadas": c, **correlacao(sub, col, "b", rot)})
    return pd.DataFrame(linhas, columns=["min_releases_avaliadas", *COLUNAS])


def zeros_por_avaliadas(df: pd.DataFrame, corte: int = CORTE_ZEROS) -> pd.DataFrame:
    """Proporção de CFR (b) = 0 abaixo e acima de `corte` releases avaliadas (efeito de denominador pequeno)."""
    d = df[df["cfr_b"].notna()]
    linhas = []
    for nome, mask in ((f"< {corte}", d[COL_AVALIADAS] < corte), (f">= {corte}", d[COL_AVALIADAS] >= corte)):
        s = d.loc[mask, "cfr_b"]
        linhas.append({"releases_avaliadas": nome, "n": len(s), "n_cfr_b_zero": int((s == 0).sum()),
                       "prop_zero": (s == 0).mean() if len(s) else float("nan")})
    return pd.DataFrame(linhas)


def fmt_p(p: float) -> str:
    if math.isnan(p):
        return "—"
    return "< 0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")


def _num(v: float, casas: int = 3) -> str:
    return "—" if math.isnan(v) else f"{v:.{casas}f}".replace(".", ",")


def _mediana_por_faixa(d: pd.DataFrame, col_y: str, faixas: int = FAIXAS_DF) -> pd.DataFrame:
    """Mediana de DF e de CFR em faixas de quantil de DF (empates de DF podem fundir faixas)."""
    grupos = pd.qcut(d[X], q=min(faixas, d[X].nunique()), duplicates="drop")
    return d.groupby(grupos, observed=True).agg(x=(X, "median"), y=(col_y, "median"))


def _dispersao(df: pd.DataFrame, linha: dict, destino: Path) -> None:
    col_y = linha["coluna_y"]
    d = df[[X, col_y]].dropna()
    fig, ax = plt.subplots(figsize=(6, 4.4))
    ax.scatter(d[X], d[col_y], s=14, alpha=0.45, color="#4c78a8", edgecolor="none", label="repositório")
    log = d[X].nunique() >= 2 and bool((d[X] > 0).all())
    if log:
        ax.set_xscale("log")
    m = _mediana_por_faixa(d, col_y) if log else pd.DataFrame()
    if len(m) >= 2:
        ax.plot(m["x"], m["y"], color="#e45756", lw=2, marker="o", ms=4,
                label=f"mediana por faixa de DF ({len(m)} faixas de quantil)")
    ax.set_ylim(-0.03, 1.03)
    ax.set(xlabel="deployment frequency, releases/semana" + (" (escala log)" if log else ""),
           ylabel=f"{linha['rotulo']} (proporção)",
           title=f"RQ05 — DF × {linha['rotulo']}\nρ = {_num(linha['rho'])} "
                 f"[IC95% {_num(linha['ic95_inf'])}; {_num(linha['ic95_sup'])}], p {_p_titulo(linha['p_valor'])}, "
                 f"n = {linha['n']}")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


def _p_titulo(p: float) -> str:
    s = fmt_p(p)
    return s if s.startswith("<") or s == "—" else f"= {s}"


def _md_tabela(t: pd.DataFrame) -> list[str]:
    corte = "min_releases_avaliadas" in t
    cab = (["Mín. avaliadas"] if corte else []) + ["Variante", "n", "Excluídos", "CFR = 0", "ρ", "IC95%", "p",
                                                    "Força", "Direção (IC)"]
    linhas = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    for _, r in t.iterrows():
        cel = ([f"≥ {r['min_releases_avaliadas']}"] if corte else []) + [
            r["rotulo"], str(r["n"]), str(r["n_excluidos"]), str(r["n_cfr_zero"]), _num(r["rho"]),
            f"[{_num(r['ic95_inf'])}; {_num(r['ic95_sup'])}]", fmt_p(r["p_valor"]), r["forca"], r["direcao"]]
        linhas.append("| " + " | ".join(cel) + " |")
    return linhas


def relatorio_md(df: pd.DataFrame, principal: pd.DataFrame, sens: pd.DataFrame, zeros: pd.DataFrame) -> str:
    rho_av, _ = _spearman(*[df.loc[df[X].notna() & df[COL_AVALIADAS].notna(), c] for c in (X, COL_AVALIADAS)])
    excl = principal.loc[principal["n_excluidos"] > 0, ["rotulo", "excluidos"]]
    out = [
        "# RQ05 — Spearman entre deployment frequency e CFR (a) e (b)",
        "",
        "Gerado por `python -m analysis.rq05_spearman` a partir de `data/metrics.csv` "
        f"(scipy {scipy.__version__}). Discussão em `docs/rq05_discussao.md`.",
        "",
        "## Resultado principal",
        "",
        *_md_tabela(principal),
        "",
        f"IC95%: {IC_METODO}. α = {_num(ALFA, 2)}. Força: |ρ| < 0,1 desprezível; < 0,3 fraca; < 0,5 moderada; "
        "≥ 0,5 forte (Cohen, 1988; rótulo só descritivo). Direção: positiva/negativa só quando o IC95% exclui o 0.",
        "",
        "Excluídos (pares incompletos, exclusão só da variante):",
        "",
        *([f"- {r['rotulo']}: {r['excluidos']}" for _, r in excl.iterrows()] or ["- nenhum"]),
        "",
        "## Sensibilidade de CFR (b) ao nº mínimo de releases avaliadas (diagnóstico)",
        "",
        "Cortes pré-declarados (5, 10, 20). **Ressalva:** DF e nº de releases avaliadas têm "
        f"ρ = {_num(rho_av)}; o corte restringe a faixa de DF, e restrição de faixa por si só reduz |ρ|. "
        "Serve para dimensionar o efeito de denominador pequeno, não substitui o resultado principal.",
        "",
        *_md_tabela(sens),
        "",
        "CFR (b) = 0 por nº de releases avaliadas:",
        "",
        "| Releases avaliadas | n | CFR (b) = 0 | Proporção |",
        "|---|---|---|---|",
        *[f"| {r['releases_avaliadas']} | {r['n']} | {r['n_cfr_b_zero']} | {_num(r['prop_zero'])} |"
          for _, r in zeros.iterrows()],
        "",
        "## Notas de método",
        "",
        "- Pares completos por variante; zeros de CFR mantidos; nenhuma imputação.",
        f"- Empates recebem ranks médios (DF tem {df[X].nunique()} valores distintos em {df[X].notna().sum()}; "
        f"CFR (b) tem {int((df['cfr_b'] == 0).sum())} zeros). O p-valor bilateral vem da aproximação t do "
        "`spearmanr`, aproximada na cauda: no texto usar \"p < 0,001\"; o valor completo fica no CSV.",
        "- Gráficos: DF em escala log (varia mais de duas ordens de grandeza, sem zeros); CFR em escala linear "
        "[0, 1] (proporção limitada, com zeros). Linha vermelha = mediana de CFR em faixas de quantil de DF.",
        "- CFR (b) é exploratório: heurística v12 não validada (F1 independente 0,689, IC95% 0,563–0,790).",
        "",
    ]
    return "\n".join(out)


def executar(csv: Path, saida: Path) -> dict:
    saida.mkdir(parents=True, exist_ok=True)
    df = common.ler_metricas(csv)
    principal = tabela(df)
    principal.to_csv(saida / "rq05_spearman.csv", index=False)
    sens = sensibilidade_cfr_b(df)
    sens.to_csv(saida / "rq05_sensibilidade_cfr_b.csv", index=False)
    zeros = zeros_por_avaliadas(df)
    (saida / "rq05_spearman.md").write_text(relatorio_md(df, principal, sens, zeros), encoding="utf-8")
    for _, linha in principal.iterrows():
        _dispersao(df, linha.to_dict(), saida / f"rq05_df_cfr_{linha['variante']}.png")
    return {"spearman": principal, "sensibilidade": sens, "zeros": zeros}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=common.CSV_PADRAO)
    ap.add_argument("--saida", type=Path, default=common.SAIDA_PADRAO)
    a = ap.parse_args(argv)
    r = executar(a.csv, a.saida)
    cols = ["variante", "n", "n_excluidos", "rho", "p_valor", "ic95_inf", "ic95_sup", "forca", "direcao"]
    fmt = lambda v: f"{v:.4g}"  # noqa: E731
    print(r["spearman"][cols].to_string(index=False, float_format=fmt))
    print("\nSensibilidade CFR (b):\n", r["sensibilidade"][["min_releases_avaliadas", *cols]]
          .to_string(index=False, float_format=fmt))
    print("\nCFR (b) = 0 por releases avaliadas:\n", r["zeros"].to_string(index=False, float_format=fmt))


if __name__ == "__main__":
    main()
