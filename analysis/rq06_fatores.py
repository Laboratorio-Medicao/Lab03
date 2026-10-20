"""RQ06: fatores dos repositórios × métricas DORA, com Kruskal-Wallis/Mann-Whitney, Holm e efeito (Issue #38).

Reexecutável a partir dos CSVs, sem estado oculto:

    python -m analysis.rq06_fatores [--csv data/metrics.csv]
        [--consenso data/amostra_ouro/consenso.csv] [--saida outputs/analise]

Fatores (E§5 RQ06): linguagem, popularidade (quartis de estrelas), contribuidores (quartis), idade (quartis)
e tipo do projeto (consenso da amostra-ouro, E§6). Métricas: as seis das RQ01–RQ04. Para cada fator ×
métrica: Kruskal-Wallis (k ≥ 3 grupos, ε² = H/(n−1)) ou Mann-Whitney (k = 2, δ de Cliff); Holm sobre todos
os testes executados. Saídas em `--saida`: `rq06_testes.csv` (tabela única), `rq06_grupos.csv` (mediana/IQR
por grupo), `rq06_fatores.csv` (grupo de cada repositório) e `rq06_efeitos.png`.
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
from statsmodels.stats.multitest import multipletests  # noqa: E402

from analysis import common  # noqa: E402
from analysis.rq01_rq04 import METRICAS  # noqa: E402

CONSENSO_PADRAO = common.RAIZ / "data" / "amostra_ouro" / "consenso.csv"
ALFA = 0.05
MIN_GRUPO = 5  # grupo com menos repositórios que isso (naquele teste) fica fora do teste
MIN_REPOS_LINGUAGEM = 15  # 5% da amostra de 300; corte arbitrário, abaixo dele a linguagem vai para "Outras"
OUTRAS = "Outras"
QUARTIS = ["Q1", "Q2", "Q3", "Q4"]
TIPOS = ["biblioteca_framework", "aplicacao_servico", "ferramenta_cli"]  # "outro" fica fora (E§5 RQ06)
MAIOR_E_MELHOR = {"deployment_frequency"}  # nas demais métricas (LT, CFR, recuperação) menor é melhor

# fator -> coluna de origem (tipo_projeto vem do consenso). Ordem = ordem das linhas da tabela.
FATORES = {
    "linguagem": "language",
    "popularidade": "stars",
    "contribuidores": "contributors",
    "idade": "age_days",
    "tipo": "tipo_projeto",
}
# Contraste direcional descritivo (δ de Cliff, sem p-valor, fora do Holm): (grupo x, grupo y).
CONTRASTES = {
    "popularidade": ("Q4", "Q1"),
    "contribuidores": ("Q4", "Q1"),
    "idade": ("Q4", "Q1"),
    "tipo": ("aplicacao_servico", "biblioteca_framework"),
}
# Limiares de magnitude: (limite superior exclusivo, rótulo); acima do último = "grande".
LIMIARES_CLIFF = [(0.147, "desprezível"), (0.33, "pequeno"), (0.474, "médio")]  # Romano et al. (2006)
LIMIARES_EPSILON2 = [(0.01, "desprezível"), (0.08, "pequeno"), (0.26, "médio")]  # Mangiafico (rcompanion)
NIVEL_MAGNITUDE = {"desprezível": 0, "pequeno": 1, "médio": 2, "grande": 3}


# ---------- tamanho de efeito ----------

def epsilon2(h: float, n: int) -> float:
    """ε² = H / (n − 1) (enunciado, E§5 RQ06); n = repositórios no teste."""
    return h / (n - 1)


def epsilon2_h0(k: int, n: int) -> float:
    """Valor esperado de ε² sem efeito nenhum: E[H] ≈ k − 1 ⇒ (k − 1)/(n − 1)."""
    return (k - 1) / (n - 1)


def eta2_h(h: float, k: int, n: int) -> float:
    """η²_H = (H − k + 1)/(n − k): ε² descontado do valor esperado sob H0 (pode ser < 0)."""
    return (h - k + 1) / (n - k)


def cliff_delta(u1: float, n1: int, n2: int) -> float:
    """δ = 2·U₁/(n₁·n₂) − 1, com U₁ de `mannwhitneyu(x, y)`; δ > 0 ⇒ x tende a valores maiores."""
    return 2 * u1 / (n1 * n2) - 1


def _magnitude(valor: float, limiares) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return ""
    for limite, rotulo in limiares:
        if abs(valor) < limite:
            return rotulo
    return "grande"


def magnitude_cliff(delta: float) -> str:
    return _magnitude(delta, LIMIARES_CLIFF)


def magnitude_epsilon2(e2: float) -> str:
    return _magnitude(e2, LIMIARES_EPSILON2)


def delta_entre(x, y) -> float:
    """δ de Cliff entre duas amostras (via U₁ de `mannwhitneyu`)."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    u1 = stats.mannwhitneyu(x, y, alternative="two-sided").statistic
    return cliff_delta(float(u1), len(x), len(y))


# ---------- fatores ----------

def grupo_linguagem(serie: pd.Series, minimo: int = MIN_REPOS_LINGUAGEM) -> pd.Series:
    """Linguagem com ≥ `minimo` repositórios vira grupo próprio; as demais, "Outras"; vazio fica NaN."""
    contagem = serie.value_counts()
    frequentes = set(contagem[contagem >= minimo].index)
    return serie.map(lambda v: v if v in frequentes else (OUTRAS if pd.notna(v) else np.nan))


def grupo_quartis(serie: pd.Series) -> pd.Series:
    """Quartis da amostra (Q1 = menores valores); intervalos (a, b], bordas por interpolação linear."""
    return pd.qcut(serie, 4, labels=QUARTIS).astype(object)


def tipos_do_consenso(consenso: pd.DataFrame) -> pd.Series:
    """`full_name` -> tipo do projeto (rótulo de consenso da amostra-ouro, E§6)."""
    t = consenso[consenso["dimensao"] == "tipo_projeto"]
    return t.set_index("item_id")["rotulo_consenso"]


def grupo_tipo(full_names: pd.Series, tipos: pd.Series) -> pd.Series:
    """Tipo de consenso; "outro", pendente e repositórios fora da amostra-ouro ficam NaN."""
    t = full_names.map(tipos)
    return t.where(t.isin(TIPOS))


def montar_fatores(df: pd.DataFrame, tipos: pd.Series) -> pd.DataFrame:
    """Grupo de cada repositório em cada fator (NaN = fora do fator)."""
    return pd.DataFrame({
        "full_name": df["full_name"],
        "linguagem": grupo_linguagem(df["language"]),
        "popularidade": grupo_quartis(df["stars"]),
        "contribuidores": grupo_quartis(df["contributors"]),
        "idade": grupo_quartis(df["age_days"]),
        "tipo": grupo_tipo(df["full_name"], tipos),
    }, index=df.index)


def ordem_grupos(fator: str, grupos: pd.Series) -> list[str]:
    """Ordem fixa dos grupos: Q1..Q4, tipos na ordem de TIPOS, linguagens por tamanho (Outras por último)."""
    presentes = set(grupos.dropna())
    if fator in ("popularidade", "contribuidores", "idade"):
        return [g for g in QUARTIS if g in presentes]
    if fator == "tipo":
        return [g for g in TIPOS if g in presentes]
    cont = grupos.value_counts()
    return sorted((g for g in presentes if g != OUTRAS), key=lambda g: (-cont[g], g)) + \
        ([OUTRAS] if OUTRAS in presentes else [])


def criterio(fator: str, grupo: str, df: pd.DataFrame, fatores: pd.DataFrame) -> str:
    col = FATORES[fator]
    membros = fatores[fator] == grupo
    if fator in ("popularidade", "contribuidores", "idade"):
        # bordas = quantis da amostra (as mesmas do qcut); Q1 inclui o mínimo real, os demais são (a, b]
        bordas = df[col].quantile([0, 0.25, 0.5, 0.75, 1]).to_list()
        i = QUARTIS.index(grupo)
        abre = "[" if i == 0 else "("
        return f"{col} em {abre}{bordas[i]:.6g}, {bordas[i + 1]:.6g}]"
    if fator == "linguagem" and grupo == OUTRAS:
        langs = df.loc[membros, col].value_counts()
        return f"{OUTRAS}: " + ", ".join(f"{l} ({n})" for l, n in langs.items())
    return f"{col} = {grupo}"


# ---------- testes ----------

def testar(valores: pd.Series, grupos: pd.Series, ordem: list[str]) -> dict:
    """Kruskal-Wallis (k ≥ 3) ou Mann-Whitney (k = 2) de `valores` entre `grupos`.

    Remove NaN (contados em `n_excluidos_nan`) e grupos com menos de MIN_GRUPO repositórios. Sem dois
    grupos, com todos os valores idênticos ou com p não finito, devolve `teste = nao_executado`.
    """
    no_fator = grupos.notna()
    ok = no_fator & valores.notna()
    v, g = valores[ok].astype(float), grupos[ok]
    amostras = {gr: v[g == gr].to_numpy() for gr in ordem if (g == gr).any()}
    excluidos = [gr for gr in ordem if 0 < len(amostras.get(gr, [])) < MIN_GRUPO]
    amostras = {gr: a for gr, a in amostras.items() if len(a) >= MIN_GRUPO}
    n = int(sum(len(a) for a in amostras.values()))
    out = {
        "teste": "nao_executado", "n": n, "n_excluidos_nan": int((no_fator & valores.isna()).sum()),
        "k_grupos": len(amostras), "n_por_grupo": "; ".join(f"{gr}={len(a)}" for gr, a in amostras.items()),
        "grupos_excluidos": "; ".join(f"{gr}={len(v[g == gr])}" for gr in excluidos),
        "estatistica": np.nan, "p_bruto": np.nan, "efeito_nome": "", "efeito": np.nan, "magnitude": "",
        "efeito_grupos": "", "epsilon2_h0": np.nan, "eta2_h": np.nan, "observacao": "",
        "grupos_testados": list(amostras),
    }
    if len(amostras) < 2:
        out["observacao"] = f"menos de 2 grupos com n ≥ {MIN_GRUPO}"
        return out
    todos = np.concatenate(list(amostras.values()))
    if np.all(todos == todos[0]):
        out["observacao"] = "todos os valores idênticos"
        return out
    nomes, listas = list(amostras), list(amostras.values())
    if len(amostras) == 2:
        r = stats.mannwhitneyu(listas[0], listas[1], alternative="two-sided")
        u1, p = float(r.statistic), float(r.pvalue)
        efeito = cliff_delta(u1, len(listas[0]), len(listas[1]))
        out.update(teste="mannwhitney", estatistica=u1, efeito_nome="cliff_delta", efeito=efeito,
                   magnitude=magnitude_cliff(efeito), efeito_grupos=f"{nomes[0]} × {nomes[1]}")
    else:
        r = stats.kruskal(*listas)
        h, p, k = float(r.statistic), float(r.pvalue), len(listas)
        efeito = epsilon2(h, n)
        out.update(teste="kruskal", estatistica=h, efeito_nome="epsilon2", efeito=efeito,
                   magnitude=magnitude_epsilon2(efeito), epsilon2_h0=epsilon2_h0(k, n),
                   eta2_h=eta2_h(h, k, n))
    if not math.isfinite(p):
        out.update(teste="nao_executado", estatistica=np.nan, efeito_nome="", efeito=np.nan,
                   magnitude="", efeito_grupos="", epsilon2_h0=np.nan, eta2_h=np.nan,
                   observacao="p-valor não finito")
        return out
    out["p_bruto"] = p
    return out


def contraste(fator: str, valores: pd.Series, grupos: pd.Series, testados: list[str]) -> dict:
    """δ de Cliff descritivo do contraste fixo do fator (sem p-valor, fora do Holm).

    Só é calculado se os dois grupos do contraste entraram no teste (n ≥ MIN_GRUPO com valor); senão as
    colunas ficam vazias e o motivo vai em `motivo_contraste` (levado para `observacao`).
    """
    vazio = {"contraste": "", "delta_contraste": np.nan, "magnitude_contraste": "", "motivo_contraste": ""}
    if fator not in CONTRASTES:
        return vazio
    gx, gy = CONTRASTES[fator]
    fora = [g for g in (gx, gy) if g not in testados]
    if fora:
        return {**vazio, "motivo_contraste": f"contraste {gx} × {gy} não calculado: "
                f"{', '.join(fora)} fora do teste (n < {MIN_GRUPO} ou sem valor)"}
    ok = valores.notna()
    d = delta_entre(valores[ok & (grupos == gx)], valores[ok & (grupos == gy)])
    return {"contraste": f"{gx} × {gy}", "delta_contraste": d, "magnitude_contraste": magnitude_cliff(d),
            "motivo_contraste": ""}


def melhor_grupo(coluna: str, valores: pd.Series, grupos: pd.Series, testados: list[str]) -> str:
    """Grupo(s) de melhor mediana no sentido DORA entre os grupos testados (sem "Outras"); empates: "A|B"."""
    meds = {g: valores[(grupos == g) & valores.notna()].median() for g in testados if g != OUTRAS}
    if not meds:
        return ""
    alvo = max(meds.values()) if coluna in MAIOR_E_MELHOR else min(meds.values())
    return "|".join(g for g, m in meds.items() if m == alvo)


def aplicar_holm(tabela: pd.DataFrame, alfa: float = ALFA) -> pd.DataFrame:
    """Holm sobre todos os testes executados (p finito); os não executados ficam vazios."""
    t = tabela.copy()
    t["p_holm"] = np.nan
    t["significativo_holm"] = pd.Series([pd.NA] * len(t), index=t.index, dtype="boolean")
    mask = t["p_bruto"].notna()
    if mask.any():
        rejeita, p_adj, _, _ = multipletests(t.loc[mask, "p_bruto"].to_numpy(), alpha=alfa, method="holm")
        t.loc[mask, "p_holm"] = p_adj
        t.loc[mask, "significativo_holm"] = rejeita
    return t


COLUNAS_TESTES = [
    "fator", "metrica", "coluna", "teste", "n", "n_excluidos_nan", "k_grupos", "n_por_grupo",
    "grupos_excluidos", "estatistica", "p_bruto", "p_holm", "significativo_holm", "efeito_nome", "efeito",
    "magnitude", "efeito_grupos", "epsilon2_h0", "eta2_h", "contraste", "delta_contraste",
    "magnitude_contraste", "melhor_grupo", "observacao",
]
OBS_RECUPERACAO = ("sem valor = sem episódio de falha (melhor caso) ou só episódios censurados "
                   "(pior caso); ambos fora do teste")


def tabela_testes(df: pd.DataFrame, fatores: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for fator in FATORES:
        grupos = fatores[fator]
        ordem = ordem_grupos(fator, grupos)
        for nome, (col, _unid, _rq) in METRICAS.items():
            valores = df[col]
            r = testar(valores, grupos, ordem)
            testados = r.pop("grupos_testados")
            c = contraste(fator, valores, grupos, testados)
            obs = [r["observacao"], c.pop("motivo_contraste")]
            if col == "rec_median_h" and r["n_excluidos_nan"]:
                obs.append(OBS_RECUPERACAO)
            r["observacao"] = "; ".join(filter(None, obs))
            linhas.append({"fator": fator, "metrica": nome, "coluna": col, **r, **c,
                           "melhor_grupo": melhor_grupo(col, valores, grupos, testados)})
    return aplicar_holm(pd.DataFrame(linhas))[COLUNAS_TESTES]


def tabela_grupos(df: pd.DataFrame, fatores: pd.DataFrame) -> pd.DataFrame:
    """Mediana/IQR de cada métrica por fator × grupo, com os NaN excluídos de cada métrica."""
    linhas = []
    for fator in FATORES:
        grupos = fatores[fator]
        for grupo in ordem_grupos(fator, grupos):
            membros = grupos == grupo
            crit = criterio(fator, grupo, df, fatores)
            for nome, (col, _unid, _rq) in METRICAS.items():
                s = df.loc[membros, col]
                extra = {"n_sem_episodios": np.nan, "n_so_censurados": np.nan}
                if col == "rec_median_h":
                    sem = s.isna() & (df.loc[membros, "n_episodios"] == 0)
                    extra = {"n_sem_episodios": int(sem.sum()), "n_so_censurados": int((s.isna() & ~sem).sum())}
                linhas.append({"fator": fator, "grupo": grupo, "criterio": crit, "metrica": nome, "coluna": col,
                               **common.resumo(s), "n_excluidos_nan": int(s.isna().sum()), **extra})
    t = pd.DataFrame(linhas)
    for c in ("n_sem_episodios", "n_so_censurados"):
        t[c] = t[c].astype("Int64")
    return t


# ---------- gráfico ----------

ROTULO_CURTO = {
    "Deployment frequency": "DF", "Lead time (a) por release": "LT (a)", "Lead time (b) por commit": "LT (b)",
    "CFR (a) proxy de CI": "CFR (a)", "CFR (b) proxy de entrega": "CFR (b)", "Tempo de recuperação": "Recup.",
}


def _mapa_efeitos(testes: pd.DataFrame, destino: Path) -> None:
    metricas, fatores = list(METRICAS), list(FATORES)
    nivel = np.full((len(fatores), len(metricas)), np.nan)
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    for _, l in testes.iterrows():
        i, j = fatores.index(l["fator"]), metricas.index(l["metrica"])
        if l["magnitude"]:
            nivel[i, j] = NIVEL_MAGNITUDE[l["magnitude"]]
            marca = "*" if bool(pd.notna(l["significativo_holm"]) and l["significativo_holm"]) else ""
            simbolo = "ε²" if l["efeito_nome"] == "epsilon2" else "δ"
            ax.text(j, i, f"{simbolo}={l['efeito']:.3f}{marca}", ha="center", va="center", fontsize=8)
        else:
            ax.text(j, i, "n/e", ha="center", va="center", fontsize=8, color="#888888")
    cmap = matplotlib.colors.ListedColormap(["#f2f2f2", "#c6dbef", "#6baed6", "#2171b5"])
    ax.imshow(nivel, cmap=cmap, vmin=-0.5, vmax=3.5, aspect="auto")
    ax.set_xticks(range(len(metricas)), [ROTULO_CURTO[m] for m in metricas])
    ax.set_yticks(range(len(fatores)), fatores)
    ax.set_title("RQ06 — tamanho de efeito por fator × métrica (* = significativo após Holm)", fontsize=10)
    handles = [matplotlib.patches.Patch(color=cmap(k), label=m) for m, k in NIVEL_MAGNITUDE.items()]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False,
              fontsize=8)
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


# ---------- execução ----------

def executar(csv: Path, consenso: Path, saida: Path) -> dict:
    saida.mkdir(parents=True, exist_ok=True)
    df = common.ler_metricas(csv)
    tipos = tipos_do_consenso(pd.read_csv(consenso, encoding="utf-8-sig"))
    fatores = montar_fatores(df, tipos)
    testes = tabela_testes(df, fatores)
    grupos = tabela_grupos(df, fatores)
    fatores.to_csv(saida / "rq06_fatores.csv", index=False)
    testes.to_csv(saida / "rq06_testes.csv", index=False)
    grupos.to_csv(saida / "rq06_grupos.csv", index=False)
    _mapa_efeitos(testes, saida / "rq06_efeitos.png")
    return {"testes": testes, "grupos": grupos, "fatores": fatores}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=common.CSV_PADRAO)
    ap.add_argument("--consenso", type=Path, default=CONSENSO_PADRAO)
    ap.add_argument("--saida", type=Path, default=common.SAIDA_PADRAO)
    a = ap.parse_args(argv)
    t = executar(a.csv, a.consenso, a.saida)["testes"]
    cols = ["fator", "metrica", "teste", "n", "k_grupos", "p_bruto", "p_holm", "significativo_holm",
            "efeito_nome", "efeito", "magnitude", "eta2_h", "contraste", "delta_contraste", "melhor_grupo"]
    with pd.option_context("display.width", 250, "display.max_columns", None):
        print(t[cols].to_string(index=False, float_format=lambda v: f"{v:.4g}"))
    exec_ = t["p_bruto"].notna()
    print(f"\n{int(exec_.sum())} testes executados (família do Holm); "
          f"{int(t['significativo_holm'].fillna(False).sum())} significativos após Holm (alfa = {ALFA}).")


if __name__ == "__main__":
    main()
