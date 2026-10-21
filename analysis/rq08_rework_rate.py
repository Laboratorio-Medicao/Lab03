"""RQ08 (bônus): rework rate e comparação com o CFR (b) (Issue #39).

Rework rate do repositório = releases de deploy **corretivas** da janela ÷ releases de deploy da janela
(E§5 RQ08; corretiva = heurística v12 da RQ03 b). Unidade e janela iguais às do DF (C1) e do CFR (b);
sem censura, porque a corretividade de S é conhecida quando S é publicada.

Reexecutável só a partir de CSVs, sem cache nem token:

    python -m analysis.rq08_rework_rate [--csv data/metrics.csv] [--releases outputs/analise/rq08_releases.csv]
                                        [--saida outputs/analise]

`rq08_releases.csv` (rótulo por release) vem de `python -m scripts.rq08_rotular_releases` (precisa do cache).
Antes das estatísticas, os contadores do CFR (b) recontados dos rótulos são conferidos com
`data/metrics.csv`; repositório divergente sai da RQ08 (NaN) e, se passar de 5% da base, a análise para.

Saídas em `--saida`: `rq08_rework_rate.csv` (por repositório), `rq08_descritiva.csv` (mediana/IQR),
`rq08_comparacao.csv` (Spearman, Wilcoxon pareado, taxas agregadas, calibração), `rq08_*.png` e
`rq08_rework_rate.md` (resultados + discussão rework × CFR (b)).
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from analysis import common, rq01_rq04  # noqa: E402

RELEASES_PADRAO = common.SAIDA_PADRAO / "rq08_releases.csv"
PREDICOES_PADRAO = common.RAIZ / "data" / "validacao_independente" / "predicoes_v12.csv"
LIMITE_DIVERGENCIA = 0.05  # fração máxima da base que pode divergir do metrics.csv
SEMENTE_BOOTSTRAP = 20261015  # a mesma da validação independente da v12
N_BOOTSTRAP = 10_000
CATEGORIAS = ["com_antecedente", "antecedente_censurado", "antecedente_fora_janela", "sem_anterior_7d"]
# contador recontado dos rótulos -> coluna de referência em metrics.csv
CONFERIDOS = {
    "n_releases_janela": "n_releases_janela",
    "n_releases_avaliadas_cfr_b": "n_releases_avaliadas_cfr_b",
    "n_releases_censuradas_cfr_b": "n_releases_censuradas_cfr_b",
    "n_releases_falha_cfr_b": "n_releases_falha_cfr_b",
    "cfr_b_recontado": "cfr_b",
    "n_releases_mensagens_incompletas": "n_releases_mensagens_incompletas_cfr_b",
    "n_compare_divergentes": "n_compare_divergentes",
    "n_compare_truncados": "n_compare_truncados",
}
COLUNAS = [
    "full_name", "n_releases_janela", "n_releases_corretivas", "rework_rate",
    "n_releases_avaliadas_cfr_b", "n_releases_corretivas_avaliaveis", "rework_rate_avaliaveis",
    "n_releases_falha_cfr_b", "cfr_b", "diferenca_rework_cfr_b",
    *[f"n_corretivas_{c}" for c in CATEGORIAS],
    "n_releases_censuradas_cfr_b", "n_releases_mensagens_incompletas", "n_compare_divergentes",
    "n_compare_truncados", "deployment_frequency", "confere_metrics", "campos_divergentes",
    "motivo_exclusao",
]


_DESCRICOES = {
    "repos_base": "Repositórios com referência no metrics.csv (base do limite de 5%)",
    "repos_divergentes": "Repositórios da base excluídos (rótulos ausentes ou contadores diferentes do metrics.csv)",
    "repos_rework_definido": "Repositórios com rework rate definido",
    "n_pareado": "Repositórios com rework rate e CFR (b) definidos",
    "wilcoxon_estatistica": "Wilcoxon pareado (rework − CFR b), zeros descartados: estatística W",
    "wilcoxon_p": "Wilcoxon pareado: p-valor bilateral",
    "wilcoxon_n_zeros": "Pares com diferença zero (descartados do Wilcoxon e do rank-biserial)",
    "rank_biserial_pareado": "Correlação rank-biserial pareada (W+ − W−)/(W+ + W−); positivo = rework maior",
    "n_rework_maior": "Pares com rework > CFR (b)",
    "n_iguais": "Pares com rework = CFR (b)",
    "n_rework_menor": "Pares com rework < CFR (b)",
    "rework_agregado": "Σ corretivas ÷ Σ releases da janela (repositórios com rework definido)",
    "cfr_b_agregado": "Σ falhas ÷ Σ avaliadas (subconjunto pareado)",
    "falhas_por_corretiva_com_antecedente": "Σ falhas ÷ Σ corretivas com antecedente (pareado); > 1 = multiplicidade",
    "corretivas_total": "Releases corretivas (repositórios com rework definido)",
    "releases_total": "Releases de deploy da janela (repositórios com rework definido)",
    "calibracao_n_releases": "Releases da validação independente (predicoes_v12.csv)",
    "calibracao_n_repos": "Repositórios da validação independente",
    "calibracao_prev_consenso": "Proporção de corretivas pelo consenso humano na validação independente",
    "calibracao_prev_v12": "Proporção de corretivas pela v12 na validação independente",
    "calibracao_razao": "Preditas ÷ consenso (= recall ÷ precisão): viés de nível agregado da v12",
    "calibracao_razao_ic95_inf": "IC95% da razão (bootstrap por repositório, 10.000, semente 20261015): limite inferior",
    "calibracao_razao_ic95_sup": "IC95% da razão: limite superior",
}
for _n, _t in {"rework_cfr_b": "rework × CFR (b)", "df_cfr_b": "DF × CFR (b)", "df_rework": "DF × rework"}.items():
    _DESCRICOES.update({f"spearman_{_n}_rho": f"Spearman ρ {_t} (repositórios com rework definido)",
                        f"spearman_{_n}_p": f"Spearman {_t}: p-valor", f"spearman_{_n}_n": f"Spearman {_t}: n"})
for _c in CATEGORIAS:
    _DESCRICOES[f"corretivas_{_c}"] = f"Corretivas na categoria {_c}"


def descricao_indicadores() -> dict:
    """Descrição de cada indicador de `rq08_comparacao.csv` (coluna `descricao`)."""
    return dict(_DESCRICOES)


class DivergenciaExcessiva(SystemExit):
    """Mais de `LIMITE_DIVERGENCIA` da base diverge do metrics.csv: o usuário decide antes de seguir."""


# --- agregação e conferência -------------------------------------------------------------------------

def _bool(s: pd.Series) -> pd.Series:
    return s.map(lambda v: v if isinstance(v, (bool, np.bool_)) else str(v).strip().lower() == "true").astype(bool)


def agregar(rel: pd.DataFrame) -> pd.DataFrame:
    """Contadores por repositório a partir de `rq08_releases.csv` (índice = full_name)."""
    r = rel.copy()
    for c in ["corretiva", "avaliada_cfr_b", "falhou_cfr_b", "mensagens_incompletas", "truncado"]:
        r[c] = _bool(r[c])
    r["categoria_corretiva"] = r["categoria_corretiva"].fillna("")
    r["divergente"] = r["status_compare"].fillna("") == "diverged"
    r["corretiva_avaliavel"] = r["corretiva"] & r["avaliada_cfr_b"]
    for c in CATEGORIAS:
        r[f"n_corretivas_{c}"] = r["categoria_corretiva"] == c
    g = r.groupby("full_name")
    out = pd.DataFrame({
        "n_releases_janela": g.size(),
        "n_releases_corretivas": g["corretiva"].sum(),
        "n_releases_avaliadas_cfr_b": g["avaliada_cfr_b"].sum(),
        "n_releases_corretivas_avaliaveis": g["corretiva_avaliavel"].sum(),
        "n_releases_falha_cfr_b": g["falhou_cfr_b"].sum(),
        **{f"n_corretivas_{c}": g[f"n_corretivas_{c}"].sum() for c in CATEGORIAS},
        "n_releases_mensagens_incompletas": g["mensagens_incompletas"].sum(),
        "n_compare_divergentes": g["divergente"].sum(),
        "n_compare_truncados": g["truncado"].sum(),
    }).astype(int)
    out["n_releases_censuradas_cfr_b"] = out["n_releases_janela"] - out["n_releases_avaliadas_cfr_b"]
    definido = (out["n_releases_janela"] >= 2) & (out["n_releases_avaliadas_cfr_b"] > 0)
    out["cfr_b_recontado"] = (out["n_releases_falha_cfr_b"] / out["n_releases_avaliadas_cfr_b"]).where(definido)
    return out


def _iguais(a, b) -> bool:
    """Igualdade com NaN == NaN e tolerância 1e-9 (floats do CSV)."""
    na, nb = pd.isna(a), pd.isna(b)
    if na or nb:
        return bool(na and nb)
    return math.isclose(float(a), float(b), rel_tol=0, abs_tol=1e-9)


def montar(metricas: pd.DataFrame, rel: pd.DataFrame) -> pd.DataFrame:
    """Tabela por repositório (todos os de `metricas`) com conferência e rework rate."""
    ag = agregar(rel) if len(rel) else agregar(pd.DataFrame(columns=[
        "full_name", "corretiva", "avaliada_cfr_b", "falhou_cfr_b", "mensagens_incompletas", "truncado",
        "categoria_corretiva", "status_compare"]))
    m = metricas.set_index("full_name")
    linhas = []
    for nome, ref in m.iterrows():
        tem_ref = not pd.isna(ref.get("n_releases_janela"))
        tem_rot = nome in ag.index
        a = ag.loc[nome] if tem_rot else None
        if not tem_ref:
            confere, campos, motivo = False, "", "sem referência no metrics.csv"
        elif not tem_rot and int(ref["n_releases_janela"]) > 0:
            confere, campos, motivo = False, "", "sem rótulos (erro ou ausência na extração)"
        else:
            dif = [] if a is None else [k for k, col in CONFERIDOS.items() if not _iguais(a[k], ref.get(col))]
            confere, campos = not dif, ";".join(dif)
            motivo = "" if confere else "diverge do metrics.csv"
        linha = {"full_name": nome, "cfr_b": ref.get("cfr_b"),
                 "deployment_frequency": ref.get("deployment_frequency"),
                 "confere_metrics": confere, "campos_divergentes": campos, "motivo_exclusao": motivo}
        if a is not None:
            linha.update({k: a[k] for k in ag.columns if k != "cfr_b_recontado"})
        linhas.append(linha)
    t = pd.DataFrame(linhas)
    for c in COLUNAS:
        if c not in t:
            t[c] = np.nan
    n = t["n_releases_janela"]
    ok = t["confere_metrics"] & (n >= 1)
    t["rework_rate"] = (t["n_releases_corretivas"] / n).where(ok)
    av = t["n_releases_avaliadas_cfr_b"]
    t["rework_rate_avaliaveis"] = (t["n_releases_corretivas_avaliaveis"] / av).where(ok & (av > 0))
    # arredonda para não transformar ruído de ponto flutuante (1/11 − 1/11 ≈ 1e-17) em diferença
    t["diferenca_rework_cfr_b"] = (t["rework_rate"] - t["cfr_b"].where(t["confere_metrics"])).round(12)
    contadores = [c for c in COLUNAS if c.startswith("n_")]
    t[contadores] = t[contadores].astype("Int64")
    return t[COLUNAS]


def checar_divergencia(t: pd.DataFrame, limite: float = LIMITE_DIVERGENCIA) -> dict:
    """Base = repositórios com referência no metrics.csv; levanta `DivergenciaExcessiva` acima do limite."""
    base = t[t["motivo_exclusao"] != "sem referência no metrics.csv"]
    excl = base[~base["confere_metrics"]]
    frac = len(excl) / len(base) if len(base) else 0.0
    if frac > limite:
        raise DivergenciaExcessiva(
            f"{len(excl)} de {len(base)} repositórios ({frac:.1%}) divergem do metrics.csv (limite "
            f"{limite:.0%}); veja rq08_rework_rate.csv (campos_divergentes): "
            + ", ".join(excl["full_name"].head(20)))
    return {"base": len(base), "divergentes": len(excl), "fracao": frac}


# --- estatísticas -------------------------------------------------------------------------------------

def rank_biserial_pareado(d: pd.Series) -> float:
    """r = (W+ − W−) / (W+ + W−), postos de |d| sem os zeros (mesmo tratamento do `zero_method="wilcox"`)."""
    d = d.dropna()
    d = d[d != 0]
    if d.empty:
        return float("nan")
    postos = stats.rankdata(d.abs())
    w_mais, w_menos = postos[d.values > 0].sum(), postos[d.values < 0].sum()
    return float((w_mais - w_menos) / (w_mais + w_menos))


def spearman(x: pd.Series, y: pd.Series) -> dict:
    par = pd.concat([x, y], axis=1).dropna()
    if len(par) < 3 or par.iloc[:, 0].nunique() < 2 or par.iloc[:, 1].nunique() < 2:  # ρ indefinido
        return {"rho": float("nan"), "p": float("nan"), "n": len(par)}
    r = stats.spearmanr(par.iloc[:, 0], par.iloc[:, 1])
    return {"rho": float(r.statistic), "p": float(r.pvalue), "n": len(par)}


def calibracao(predicoes: Path | None, semente: int = SEMENTE_BOOTSTRAP, b: int = N_BOOTSTRAP) -> dict:
    """Prevalência de corretivas: consenso humano × v12 na amostra independente (5 releases × 40 repos).

    Razão = preditas ÷ consenso (= recall ÷ precisão); IC95% por bootstrap de repositórios.
    """
    vazio = {k: float("nan") for k in ["n_releases", "n_repos", "prev_consenso", "prev_v12", "razao",
                                         "razao_ic95_inf", "razao_ic95_sup"]}
    if predicoes is None or not Path(predicoes).exists():
        return vazio
    p = pd.read_csv(predicoes, encoding="utf-8-sig")
    p["c"] = p["consenso"].str.strip().str.lower() == "sim"
    p["v"] = p["pred_v12"].str.strip().str.lower() == "sim"
    g = p.groupby("full_name")[["c", "v"]].sum()
    c, v = g["c"].to_numpy(), g["v"].to_numpy()
    rng = np.random.default_rng(semente)
    idx = rng.integers(0, len(g), size=(b, len(g)))
    cs, vs = c[idx].sum(axis=1), v[idx].sum(axis=1)
    razoes = vs[cs > 0] / cs[cs > 0]
    return {
        "n_releases": len(p), "n_repos": len(g),
        "prev_consenso": c.sum() / len(p), "prev_v12": v.sum() / len(p),
        "razao": v.sum() / c.sum() if c.sum() else float("nan"),
        "razao_ic95_inf": float(np.percentile(razoes, 2.5)),
        "razao_ic95_sup": float(np.percentile(razoes, 97.5)),
    }


def tabela_descritiva(t: pd.DataFrame) -> pd.DataFrame:
    par = t.dropna(subset=["rework_rate", "cfr_b"])
    series = [
        ("Rework rate", "rework_rate", t["rework_rate"]),
        ("Rework rate (só releases avaliáveis do CFR b)", "rework_rate_avaliaveis", t["rework_rate_avaliaveis"]),
        ("Rework rate (subconjunto pareado)", "rework_rate", par["rework_rate"]),
        ("CFR (b) (subconjunto pareado)", "cfr_b", par["cfr_b"]),
        ("Diferença rework − CFR (b) (pareado)", "diferenca_rework_cfr_b", par["diferenca_rework_cfr_b"]),
    ]
    return pd.DataFrame([{"rq": "RQ08", "metrica": nome, "coluna": col, "unidade": "proporção",
                          **common.resumo(s)} for nome, col, s in series])


def comparacao(t: pd.DataFrame, cal: dict, div: dict) -> dict:
    par = t.dropna(subset=["rework_rate", "cfr_b"])
    d = par["diferenca_rework_cfr_b"]
    nz = d[d != 0]
    w = stats.wilcoxon(nz) if len(nz) >= 1 else None
    ok = t[t["rework_rate"].notna()]
    out = {
        "repos_base": div["base"],
        "repos_divergentes": div["divergentes"],
        "repos_rework_definido": int(t["rework_rate"].notna().sum()),
        "n_pareado": len(par),
    }
    for nome, (x, y) in {
        "rework_cfr_b": (t["rework_rate"], t["cfr_b"].where(t["rework_rate"].notna())),
        "df_cfr_b": (t["deployment_frequency"].where(t["rework_rate"].notna()), t["cfr_b"].where(t["rework_rate"].notna())),
        "df_rework": (t["deployment_frequency"], t["rework_rate"]),
    }.items():
        s = spearman(x, y)
        out.update({f"spearman_{nome}_rho": s["rho"], f"spearman_{nome}_p": s["p"], f"spearman_{nome}_n": s["n"]})
    out.update({
        "wilcoxon_estatistica": float(w.statistic) if w else float("nan"),
        "wilcoxon_p": float(w.pvalue) if w else float("nan"),
        "wilcoxon_n_zeros": int((d == 0).sum()),
        "rank_biserial_pareado": rank_biserial_pareado(d),
        "n_rework_maior": int((d > 0).sum()),
        "n_iguais": int((d == 0).sum()),
        "n_rework_menor": int((d < 0).sum()),
        "rework_agregado": ok["n_releases_corretivas"].sum() / ok["n_releases_janela"].sum() if len(ok) else float("nan"),
        "cfr_b_agregado": par["n_releases_falha_cfr_b"].sum() / par["n_releases_avaliadas_cfr_b"].sum() if len(par) else float("nan"),
        "falhas_por_corretiva_com_antecedente": (
            par["n_releases_falha_cfr_b"].sum() / par["n_corretivas_com_antecedente"].sum()
            if len(par) and par["n_corretivas_com_antecedente"].sum() else float("nan")),
        **{f"corretivas_{c}": int(ok[f"n_corretivas_{c}"].sum()) for c in CATEGORIAS},
        "corretivas_total": int(ok["n_releases_corretivas"].sum()),
        "releases_total": int(ok["n_releases_janela"].sum()),
        **{f"calibracao_{k}": v for k, v in cal.items()},
    })
    return out


# --- gráficos e relatório -----------------------------------------------------------------------------

def _dispersao(t: pd.DataFrame, comp: dict, destino: Path) -> None:
    par = t.dropna(subset=["rework_rate", "cfr_b"])
    fig, ax = plt.subplots(figsize=(5.2, 5))
    ax.scatter(par["cfr_b"], par["rework_rate"], s=14, alpha=0.6, color="#4c78a8", edgecolor="none")
    ax.plot([0, 1], [0, 1], color="#e45756", lw=1, ls="--", label="y = x")
    ax.set(xlim=(-0.02, 1.02), ylim=(-0.02, 1.02), xlabel="CFR (b) (proporção de releases que falharam)",
           ylabel="rework rate (proporção de releases corretivas)",
           title=f"RQ08 — rework × CFR (b) (n={len(par)}, ρ={comp['spearman_rework_cfr_b_rho']:.2f})")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


def _f(v, casas: int = 3) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    return f"{v:.{casas}f}".replace(".", ",")


def _p(v) -> str:
    """p-valor já com o sinal: "< 0,001" ou "= 0,123"."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return "< 0,001" if v < 0.001 else "= " + _f(v)


def relatorio(t: pd.DataFrame, desc: pd.DataFrame, c: dict, metricas: pd.DataFrame | None = None) -> str:
    def lin(i):
        r = desc.iloc[i]
        return f"| {r['metrica']} | {r['n']} | {_f(r['mediana'])} | {_f(r['q1'])} | {_f(r['q3'])} | {_f(r['iqr'])} |"

    excl = t[(~t["confere_metrics"]) & (t["motivo_exclusao"] != "sem referência no metrics.csv")]
    sem_ref = t[t["motivo_exclusao"] == "sem referência no metrics.csv"]["full_name"].tolist()
    incl = t[t["rework_rate"].notna()]
    dm = abs(desc.iloc[1]["mediana"] - desc.iloc[0]["mediana"])
    txt_censura = ("A diferença é pequena (< 0,02), então a censura não explica a diferença entre as métricas."
                   if dm < 0.02 else "A diferença não é desprezível: parte da distância entre as métricas vem da censura.")
    r_cfr, r_rw = abs(c["spearman_df_cfr_b_rho"]), abs(c["spearman_df_rework_rho"])
    txt_cadencia = ("O rework, que não tem janela de correspondência, é menos associado à cadência."
                    if r_rw < r_cfr else "O rework não ficou menos associado à cadência do que o CFR (b); "
                    "a associação com a DF não se explica só pela janela de 7 dias.")
    lo, hi = c.get("calibracao_razao_ic95_inf", float("nan")), c.get("calibracao_razao_ic95_sup", float("nan"))
    if not (lo <= 1 <= hi) and hi < 1:
        txt_calibracao = "Ou seja, a v12 tende a **subestimar** o rework agregado (o IC fica abaixo de 1)."
    elif not (lo <= 1 <= hi) and lo > 1:
        txt_calibracao = "Ou seja, a v12 tende a **superestimar** o rework agregado (o IC fica acima de 1)."
    else:
        txt_calibracao = ("A estimativa pontual sugere que a v12 **subestima** o rework agregado, mas o IC inclui 1: "
                          "não há evidência firme de viés de nível." if c.get("calibracao_razao", 1) < 1 else
                          "O IC inclui 1: não há evidência firme de viés de nível.")
    soma_cat = sum(c[f"corretivas_{k}"] for k in CATEGORIAS)
    pct = (lambda k: c[f"corretivas_{k}"] / soma_cat * 100 if soma_cat else float("nan"))
    if len(excl):
        n_ref = (metricas.set_index("full_name")["n_releases_janela"] if metricas is not None
                 else t.set_index("full_name")["n_releases_janela"])
        txt_excl = (f"{len(excl)} repositório(s) da base saíram da RQ08 ("
                    + "; ".join(f"{r.full_name}: {r.motivo_exclusao}" for r in excl.itertuples())
                    + f"). Mediana de DF dos excluídos: {_f(excl['deployment_frequency'].median())} releases/semana "
                    f"(incluídos: {_f(incl['deployment_frequency'].median())}); mediana de releases na janela "
                    f"segundo o `metrics.csv`: {_f(n_ref.reindex(excl['full_name']).median(), 0)} "
                    f"(incluídos: {_f(n_ref.reindex(incl['full_name']).median(), 0)}).")
    else:
        txt_excl = "Todos os repositórios com referência reproduzem exatamente os contadores do CFR (b) do `metrics.csv`."
    n_div = int((~t["confere_metrics"] & t["campos_divergentes"].fillna("").astype(bool)).sum())
    txt_excl += (f" Entre os repositórios com rótulos, {n_div} têm contador diferente do `metrics.csv`."
                 if n_div else " Todos os repositórios com rótulos reproduzem exatamente os contadores do `metrics.csv`.")
    med_rw, med_cfr = desc.iloc[2]["mediana"], desc.iloc[3]["mediana"]
    if (med_rw - med_cfr) * (c["rework_agregado"] - c["cfr_b_agregado"]) < 0:
        txt_agregado = (f" Nesta amostra o sinal da comparação depende do peso: por repositório, a mediana do rework "
                        f"({_f(med_rw)}) {'supera' if med_rw > med_cfr else 'fica abaixo de'} a do CFR (b) ({_f(med_cfr)}), "
                        f"mas na taxa agregada o CFR (b) ({_f(c['cfr_b_agregado'])}) "
                        f"{'supera o' if c['cfr_b_agregado'] > c['rework_agregado'] else 'fica abaixo do'} rework "
                        f"({_f(c['rework_agregado'])}). Os repositórios de alta cadência pesam mais no agregado e "
                        "concentram as rajadas.")
    else:
        txt_agregado = ""
    return f"""# RQ08 (bônus) — Rework rate e diferença para o CFR (b)

Gerado por `python -m analysis.rq08_rework_rate` (Issue #39) a partir de `data/metrics.csv` e
`outputs/analise/rq08_releases.csv` (rótulos por release de `python -m scripts.rq08_rotular_releases`).
Não editar à mão.

## Definição operacional

- **Rework rate** do repositório = nº de releases de deploy **corretivas** na janela ÷ nº de releases de
  deploy na janela (E§5 RQ08; DORA 2024: proporção de deploys não planejados, feitos para corrigir um problema).
- **Release de deploy:** `draft=false`, `prerelease=false`, `published_at` em 2025-10-02 a 2026-10-02 (UTC,
  dia final inclusivo, 366 dias); é a mesma unidade do DF (C1) e do CFR (b).
- **Corretiva:** heurística **v12**, a mesma do CFR (b) (`heuristic_version`), sobre os mesmos itens
  (commits do `compare` + release notes). Release sem anterior nunca é corretiva e fica no denominador.
- **Sem censura:** a corretividade de S é conhecida quando S é publicada, então as releases dos últimos 7 dias
  entram. Por isso o rework é definido com ≥ 1 release, e o CFR (b) só com ≥ 2 releases e ≥ 1 avaliada.
- **Conferência:** os contadores do CFR (b) recontados dos rótulos (janela, avaliadas, censuradas, falhas,
  CFR (b), mensagens incompletas, compares divergentes/truncados) precisam bater com o `metrics.csv`. Base:
  {c['repos_base']} repositórios com referência; divergentes: {c['repos_divergentes']} (limite: 5%).
  {txt_excl} Sem referência no CSV (CFR (b) não calculado na S02): {', '.join(sem_ref) or 'nenhum'}.

## Resultados

| Métrica | n | Mediana | Q1 | Q3 | IQR |
|---|---:|---:|---:|---:|---:|
{chr(10).join(lin(i) for i in range(len(desc)))}

- Pareado (n = {c['n_pareado']}): rework > CFR (b) em {c['n_rework_maior']} repositórios, iguais em
  {c['n_iguais']} e rework < CFR (b) em {c['n_rework_menor']}. Wilcoxon pareado (zeros descartados):
  W = {_f(c['wilcoxon_estatistica'], 1)}, p {_p(c['wilcoxon_p'])}; rank-biserial pareado
  r = {_f(c['rank_biserial_pareado'])} (positivo = rework maior).
- Spearman: ρ(rework, CFR (b)) = {_f(c['spearman_rework_cfr_b_rho'])} (p {_p(c['spearman_rework_cfr_b_p'])}, n = {c['spearman_rework_cfr_b_n']});
  ρ(DF, CFR (b)) = {_f(c['spearman_df_cfr_b_rho'])} (p {_p(c['spearman_df_cfr_b_p'])}, n = {c['spearman_df_cfr_b_n']});
  ρ(DF, rework) = {_f(c['spearman_df_rework_rho'])} (p {_p(c['spearman_df_rework_p'])}, n = {c['spearman_df_rework_n']}).
- Taxas agregadas (todas as releases juntas, dominadas pelos repositórios de alta cadência): rework
  {_f(c['rework_agregado'])} ({c['corretivas_total']} de {c['releases_total']} releases); CFR (b) {_f(c['cfr_b_agregado'])}.
- Corretivas por categoria ({soma_cat}): com antecedente avaliada em até 7 d {c['corretivas_com_antecedente']}
  ({_f(pct('com_antecedente'), 1)}%); antecedente só censurado {c['corretivas_antecedente_censurado']}
  ({_f(pct('antecedente_censurado'), 1)}%); antecedente antes do início da janela {c['corretivas_antecedente_fora_janela']}
  ({_f(pct('antecedente_fora_janela'), 1)}%); nenhuma release nos 7 d anteriores {c['corretivas_sem_anterior_7d']}
  ({_f(pct('sem_anterior_7d'), 1)}%). A razão entre releases que falharam e corretivas com antecedente é
  {_f(c['falhas_por_corretiva_com_antecedente'], 2)}; acima de 1, cada correção marca em média mais de uma
  release como falha no CFR (b).

## Em que o rework rate difere do CFR (b)

1. **Pergunta medida.** O CFR (b) pergunta se a release R *precisou* de correção. O rework pergunta se a
   release S *é* uma correção (deploy não planejado). O CFR (b) conta o **antecedente** (R que falhou); o
   rework conta o **consequente** (S corretiva).
2. **Prazo.** O CFR (b) só conta R se houver uma S corretiva em (R, R + 7 d]. O rework não exige uma release
   antecedente em até 7 dias. A v12 não mede a idade do defeito (o enunciado define corretiva como a que corrige
   defeito recente, e as duas métricas usam a mesma marcação), então uma S com a release anterior a mais de 7 d
   conta só no rework ({c['corretivas_sem_anterior_7d']} corretivas nesta amostra).
3. **Censura.** O CFR (b) tira do denominador as releases dos últimos 7 dias da janela. O rework usa todas. A
   variante "só releases avaliáveis" isola esse efeito: mediana {_f(desc.iloc[1]['mediana'])} contra
   {_f(desc.iloc[0]['mediana'])} com todas as releases. {txt_censura}
4. **Multiplicidade.** Uma S corretiva marca como falha **todas** as R avaliadas dos 7 dias anteriores. Em
   repositórios com rajadas de releases (alta DF), uma correção vira várias falhas, e o CFR (b) passa do
   rework. Uma S isolada conta só no rework. Uma corretiva pode, ao mesmo tempo, ser uma R que falhou (cadeia
   de *hotfixes*).{txt_agregado}
5. **Dependência da cadência.** Como a janela de 7 dias do CFR (b) captura mais releases quando a DF é alta, o
   CFR (b) depende mecanicamente da DF. Nesta amostra, ρ(DF, CFR (b)) = {_f(c['spearman_df_cfr_b_rho'])} e
   ρ(DF, rework) = {_f(c['spearman_df_rework_rho'])}. {txt_cadencia}
6. **Correlação em parte mecânica.** ρ(rework, CFR (b)) = {_f(c['spearman_rework_cfr_b_rho'])} é positivo em parte porque as duas saem dos **mesmos
   rótulos** de corretiva. Isso não mostra que medem a mesma coisa. O Wilcoxon descreve a diferença de nível
   entre dois estimandos distintos; ele não testa se as duas são "a mesma métrica".
7. **Erro de classificação.** As duas herdam o erro da v12 (validação independente: precisão 0,729, recall
   0,654, F1 0,689, IC95% 0,563–0,790). A heurística **não está validada** (meta F1 ≥ 0,70 não atingida), e o
   rework, como o CFR (b), é **exploratório**. No rework o erro entra uma vez, como viés de nível. Na amostra
   independente ({_f(c['calibracao_n_releases'], 0)} releases de {_f(c['calibracao_n_repos'], 0)} repositórios, 5 por
   repositório e só releases com anterior), a prevalência de corretivas é {_f(c['calibracao_prev_consenso'])}
   pelo consenso e {_f(c['calibracao_prev_v12'])} pela v12. A razão é {_f(c['calibracao_razao'])} (= recall ÷ precisão;
   IC95% bootstrap por repositório {_f(c['calibracao_razao_ic95_inf'])}–{_f(c['calibracao_razao_ic95_sup'])}).
   {txt_calibracao} Isso supõe que precisão e recall se transportem para a
   população. Esse fator **não** se aplica à mediana por repositório, e a amostra balanceada não é comparável
   às taxas agregadas. No CFR (b), um falso positivo ou negativo em S se propaga para várias R, e o efeito
   depende da cadência.

## Limitações

- Repositórios com publicação em lote (ex.: todas as releases nos últimos 7 dias da janela) entram no rework,
  mas não têm CFR (b) definido.
- Não há classificação DORA do rework: a tabela fixa da disciplina não tem faixa para essa métrica.
- A conferência com o `metrics.csv` é por contadores. Uma troca de rótulo que não altere nenhum contador do
  CFR (b) não seria detectada.
- Release com `compare` 404 ou truncado é classificada com os dados disponíveis (mesmo tratamento do CFR (b)).
"""


def executar(csv: Path, releases: Path, saida: Path, predicoes: Path | None = PREDICOES_PADRAO) -> dict:
    saida.mkdir(parents=True, exist_ok=True)
    metricas = common.ler_metricas(csv)
    rel = pd.read_csv(releases, dtype={"tag_name": str}, keep_default_na=False, na_values=[""])
    t = montar(metricas, rel)
    t.to_csv(saida / "rq08_rework_rate.csv", index=False)
    div = checar_divergencia(t)  # para aqui (exit ≠ 0) se a divergência passar do limite

    desc = tabela_descritiva(t)
    desc.to_csv(saida / "rq08_descritiva.csv", index=False)
    comp = comparacao(t, calibracao(predicoes), div)
    pd.DataFrame({"indicador": list(comp), "valor": list(comp.values()),
                  "descricao": [_DESCRICOES.get(k, "") for k in comp]}).to_csv(saida / "rq08_comparacao.csv", index=False)

    rq01_rq04._histograma(t, "rework_rate", "RQ08 — Rework rate", "proporção", saida / "rq08_rework_rate.png")
    _dispersao(t, comp, saida / "rq08_rework_vs_cfr_b.png")
    (saida / "rq08_rework_rate.md").write_text(relatorio(t, desc, comp, metricas), encoding="utf-8")
    return {"por_repo": t, "descritiva": desc, "comparacao": comp}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=common.CSV_PADRAO)
    ap.add_argument("--releases", type=Path, default=RELEASES_PADRAO)
    ap.add_argument("--saida", type=Path, default=common.SAIDA_PADRAO)
    ap.add_argument("--predicoes", type=Path, default=PREDICOES_PADRAO,
                    help="predicoes_v12.csv da validação independente (calibração)")
    a = ap.parse_args(argv)
    r = executar(a.csv, a.releases, a.saida, a.predicoes)
    print(r["descritiva"].to_string(index=False, float_format=lambda v: f"{v:.4g}"))
    print()
    for k, v in r["comparacao"].items():
        print(f"{k}: {round(v, 4) if isinstance(v, float) else v}")


if __name__ == "__main__":
    main()
