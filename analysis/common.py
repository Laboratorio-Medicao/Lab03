"""Helpers compartilhados das análises da S03 (leitura do CSV, mediana/IQR, classificação C1).

Fontes: E§5 (mediana e IQR, nunca média/DP) e E§5 RQ07 (tabela fixa de classificação DORA).
Tudo é recalculado a partir de `data/metrics.csv`; os cortes vêm de `metricas.dora`.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from metricas import dora

RAIZ = Path(__file__).resolve().parent.parent
CSV_PADRAO = RAIZ / "data" / "metrics.csv"
SAIDA_PADRAO = RAIZ / "outputs" / "analise"
CATEGORIAS = [dora.ELITE, dora.HIGH, dora.MEDIUM, dora.LOW]

# Janela oficial (config.yaml): 2025-10-02 a 2026-10-02, dia final inclusivo (366 dias).
SEMANAS_JANELA = 366 / 7


def ler_metricas(caminho: Path | str = CSV_PADRAO) -> pd.DataFrame:
    return pd.read_csv(caminho)


def quartis(serie: pd.Series) -> tuple[float, float, float]:
    """(Q1, mediana, Q3) ignorando NaN; interpolação linear (padrão do pandas/numpy)."""
    s = serie.dropna()
    if s.empty:
        return (float("nan"),) * 3
    q1, med, q3 = s.quantile([0.25, 0.5, 0.75])
    return float(q1), float(med), float(q3)


def resumo(serie: pd.Series) -> dict:
    """n, mediana, Q1, Q3 e IQR (= Q3 − Q1) de uma série."""
    q1, med, q3 = quartis(serie)
    return {"n": int(serie.notna().sum()), "mediana": med, "q1": q1, "q3": q3, "iqr": q3 - q1}


def classificar_c1(linha: pd.Series, semanas: float = SEMANAS_JANELA) -> dict:
    """Classificação DORA de referência (C1): DF, LT(a), CFR(a) e recuperação.

    Métrica indefinida (ex.: repositório sem episódios de falha) não exclui o repositório: a geral é
    a mediana das notas disponíveis, com `n_metricas` < 4 sinalizando classificação parcial
    (L10, decisão do grupo, ver `metricas.dora.classify_overall_parcial`).
    """
    regras = {
        "df_class": (linha.get("deployment_frequency"), lambda v: dora.classify_df(v, semanas)),
        "lt_class": (linha.get("lt_release_median_h"), dora.classify_lt),
        "cfr_class": (linha.get("cfr_a"), dora.classify_cfr),
        "rec_class": (linha.get("rec_median_h"), dora.classify_recovery),
    }
    out, notas = {}, []
    for col, (valor, fn) in regras.items():
        if pd.isna(valor):
            out[col] = ""
            continue
        out[col] = fn(float(valor))
        notas.append(dora.score(out[col]))
    out["n_metricas"] = len(notas)
    out["dora_c1"] = dora.classify_overall_parcial(notas) if notas else ""
    return out
