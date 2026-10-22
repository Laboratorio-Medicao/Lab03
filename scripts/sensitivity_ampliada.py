"""RQ07 (complementar; o bônus oficial é a RQ08) — Sensibilidade ampliada: quatro variações controladas da classificação DORA.

Variações implementadas:
  1. Janela CFR(b) 3/7/14 dias — proxy via lower bound (3d) e upper bound (14d) calculados
     a partir de n_releases_falha_cfr_b / n_releases_janela e (falha+censuradas)/janela.
     Nota: recomputa apenas a classificação CFR(b), não re-executa o pipeline.
  2. Mínimo de releases 5 vs 10 — filtra repos com n_releases_janela >= 5 ou >= 10.
  3. Censura RQ04 — compara rec_class com e sem repos com prop_episodios_censurados > 0,5.
  4. Cortes DORA ±10% — desloca os limiares de DF/LT/CFR/rec ±10% e reclassifica.

Saída: outputs/sensitivity_ampliada.csv, outputs/sensitivity_ampliada.md
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from metricas.dora import (
    ELITE, HIGH, MEDIUM, LOW,
    classify_cfr, classify_df, classify_lt, classify_overall_parcial, classify_recovery, score,
)

RAIZ = Path(__file__).parent.parent
METRICS = RAIZ / "data" / "metrics.csv"
OUT_DIR = RAIZ / "outputs"
OUT_CSV = OUT_DIR / "sensitivity_ampliada.csv"
OUT_MD = OUT_DIR / "sensitivity_ampliada.md"

ORDEM = [ELITE, HIGH, MEDIUM, LOW]
SEMANAS_JANELA = 366 / 7


# ---- helpers ----------------------------------------------------------------

def _kappa(a: pd.Series, b: pd.Series) -> float:
    mask = a.notna() & b.notna()
    if mask.sum() < 2:
        return float("nan")
    return round(cohen_kappa_score(a[mask], b[mask], weights="linear", labels=ORDEM), 3)


def _pct_mudou(a: pd.Series, b: pd.Series) -> tuple[int, float]:
    mask = a.notna() & b.notna()
    sub_a, sub_b = a[mask], b[mask]
    n_mudou = int((sub_a != sub_b).sum())
    return n_mudou, round(n_mudou / mask.sum() * 100, 1) if mask.sum() else float("nan")


def _resultado(variacao: str, base: pd.Series, alternativa: pd.Series) -> dict:
    mask = base.notna() & alternativa.notna()
    n = int(mask.sum())
    n_mudou, pct = _pct_mudou(base, alternativa)
    return {
        "variacao": variacao,
        "n": n,
        "n_mudou": n_mudou,
        "pct_mudou": pct,
        "kappa_linear": _kappa(base, alternativa),
    }


# ---- variação 1: janela CFR(b) ----------------------------------------------

def _cfr_b_classificar(df: pd.DataFrame, col_falha: str, col_total: str) -> pd.Series:
    """Reclassifica CFR(b) a partir de colunas de contagem."""
    def _cls(row):
        falha = row[col_falha]
        total = row[col_total]
        if pd.isna(falha) or pd.isna(total) or total == 0:
            return None
        taxa = falha / total
        try:
            return classify_cfr(min(taxa, 1.0))
        except ValueError:
            return None
    return df.apply(_cls, axis=1)


def analise_janela_cfr_b(df: pd.DataFrame) -> list[dict]:
    """Proxy: lower bound (janela curta ~3d) e upper bound (janela longa ~14d)."""
    # lower bound: só releases avaliadas no numerador e denominador = janela toda
    df2 = df.copy()
    df2["_falha"] = pd.to_numeric(df["n_releases_falha_cfr_b"], errors="coerce")
    df2["_avaliadas"] = pd.to_numeric(df["n_releases_avaliadas_cfr_b"], errors="coerce")
    df2["_janela"] = pd.to_numeric(df["n_releases_janela"], errors="coerce")
    df2["_censuradas"] = pd.to_numeric(df["n_releases_censuradas_cfr_b"], errors="coerce")

    cls_lb = _cfr_b_classificar(df2, "_falha", "_janela")        # janela ~3d (denominador maior)
    cls_ub = _cfr_b_classificar(df2, "_falha", "_avaliadas")     # já é cfr_b atual (7d)
    cls_ub2 = _cfr_b_classificar(                                # janela ~14d (mais censuradas no num)
        df2.assign(_falha_ub=df2["_falha"] + df2["_censuradas"].fillna(0)),
        "_falha_ub", "_janela",
    )

    base = df["cfr_b_class"].replace("", None)
    return [
        _resultado("cfr_b_janela_3d_vs_7d", base, cls_lb),
        _resultado("cfr_b_janela_14d_vs_7d", base, cls_ub2),
    ]


# ---- variação 2: mínimo de releases -----------------------------------------

def _dora_c1_serie(df: pd.DataFrame) -> pd.Series:
    return df["dora_c1"].replace("", None)


def analise_min_releases(df: pd.DataFrame) -> list[dict]:
    full = _dora_c1_serie(df)
    for minimo in (5, 10):
        mask = pd.to_numeric(df["n_releases_janela"], errors="coerce") >= minimo
        sub = full.copy()
        sub[~mask] = None
        yield _resultado(f"min_releases_{minimo}", full, sub)


# ---- variação 3: censura RQ04 -----------------------------------------------

def analise_censura_rq04(df: pd.DataFrame) -> list[dict]:
    prop = pd.to_numeric(df["prop_episodios_censurados"], errors="coerce")
    base = df["rec_class"].replace("", None)
    # alternativa: exclude repos com censura alta (> 50%)
    alta_censura = prop > 0.5
    alt = base.copy()
    alt[alta_censura] = None
    return [_resultado("censura_rq04_excluir_alta", base, alt)]


# ---- variação 4: cortes ±10% ------------------------------------------------

def _classificar_com_fator(df: pd.DataFrame, fator: float) -> pd.Series:
    """Reclassifica dora_c1 deslocando todos os limiares DF/LT/CFR/rec pelo fator."""
    HORAS_DIA = 24.0
    HORAS_SEMANA = 168.0
    HORAS_30_DIAS = 720.0
    DF_CORTE = 12 / SEMANAS_JANELA

    def _df(v):
        if pd.isna(v):
            return None
        if v >= 7 * fator:
            return ELITE
        if v >= 1 * fator:
            return HIGH
        if v >= DF_CORTE * fator:
            return MEDIUM
        return LOW

    def _lt(v):
        if pd.isna(v):
            return None
        if v < HORAS_DIA * fator:
            return ELITE
        if v < HORAS_SEMANA * fator:
            return HIGH
        if v < HORAS_30_DIAS * fator:
            return MEDIUM
        return LOW

    def _cfr(v):
        if pd.isna(v):
            return None
        v = min(float(v), 1.0)
        if v <= 0.15 * fator:
            return ELITE
        if v <= 0.30 * fator:
            return HIGH
        if v <= 0.45 * fator:
            return MEDIUM
        return LOW

    def _rec(v):
        if pd.isna(v):
            return None
        if v < 1 * fator:
            return ELITE
        if v < HORAS_DIA * fator:
            return HIGH
        if v < HORAS_SEMANA * fator:
            return MEDIUM
        return LOW

    def _row(r):
        notas = []
        for fn, col in [(_df, "deployment_frequency"), (_lt, "lt_release_median_h"),
                        (_cfr, "cfr_a"), (_rec, "rec_median_h")]:
            val = pd.to_numeric(r.get(col), errors="coerce")
            cls = fn(val if not (isinstance(val, float) and math.isnan(val)) else None)
            if cls:
                notas.append(score(cls))
        if not notas:
            return None
        return classify_overall_parcial(notas)

    return df.apply(_row, axis=1)


def analise_cortes(df: pd.DataFrame) -> list[dict]:
    base = _dora_c1_serie(df)
    for nome, fator in [("cortes_mais10pct", 1.10), ("cortes_menos10pct", 0.90)]:
        alt = _classificar_com_fator(df, fator)
        yield _resultado(nome, base, alt)


# ---- relatório --------------------------------------------------------------

def _md_tabela_resultados(rows: list[dict]) -> str:
    linhas = [
        "| Variação | n | Mudaram | % mudou | κ linear |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        linhas.append(
            f"| {r['variacao']} | {r['n']} | {r['n_mudou']} | {r['pct_mudou']}% | {r['kappa_linear']} |"
        )
    return "\n".join(linhas)


def run() -> None:
    df = pd.read_csv(METRICS)
    OUT_DIR.mkdir(exist_ok=True)

    resultados: list[dict] = []
    resultados += analise_janela_cfr_b(df)
    resultados += list(analise_min_releases(df))
    resultados += analise_censura_rq04(df)
    resultados += list(analise_cortes(df))

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(resultados[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(resultados)

    md = "\n".join([
        "# RQ07 (complementar) — Sensibilidade ampliada\n",
        "## Resultados por variação\n",
        _md_tabela_resultados(resultados),
        "",
        "## Notas metodológicas\n",
        "- **CFR(b) janela**: lower bound usa `falha/janela_total` (proxy janela ~3 d); upper bound usa",
        "  `(falha+censuradas)/janela_total` (proxy ~14 d). Recomputa apenas a classificação; os",
        "  valores exatos exigem re-execução do pipeline com `PRAZO_CORRECAO` ajustado.",
        "- **Mínimo releases**: repos com `n_releases_janela < mínimo` têm classificação marcada como",
        "  indefinida; κ e % medem a estabilidade em relação ao conjunto completo.",
        "- **Censura RQ04**: repos com `prop_episodios_censurados > 0,5` têm `rec_class` excluída;",
        "  κ mede concordância no subconjunto restante.",
        "- **Cortes ±10%**: todos os limiares DF/LT/CFR/rec deslocados pelo mesmo fator;",
        "  reclassificação de `dora_c1` a partir das métricas brutas.",
        "",
        "## Quais variações são informativas",
        "",
        "- **Informativas:** `cfr_b_janela_*` (proxy aritmético, não re-execução do pipeline) e `cortes_*`.",
        "- **Tautológicas (0% de mudança por construção):** `min_releases_5` (todo repositório da amostra tem ≥ 5",
        "  releases na janela), `min_releases_10` e `censura_rq04_excluir_alta` (comparam o conjunto com um",
        "  subconjunto dele mesmo, sem reclassificar). Não devem ser lidas como evidência de robustez.",
        "",
        "Fonte: `data/metrics.csv` · Script: `scripts/sensitivity_ampliada.py`",
    ])
    OUT_MD.write_text(md, encoding="utf-8")

    print(f"{'Variação':<35} {'n':>5} {'% mudou':>9} {'κ linear':>9}")
    print("-" * 62)
    for r in resultados:
        print(f"{r['variacao']:<35} {r['n']:>5} {r['pct_mudou']:>8.1f}% {r['kappa_linear']:>9.3f}")
    print(f"\nGravados: {OUT_CSV.name}, {OUT_MD.name}")


if __name__ == "__main__":
    run()
