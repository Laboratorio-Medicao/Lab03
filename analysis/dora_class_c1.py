"""Classificação DORA de referência (C1) por repositório e sua distribuição (Issue #35).

C1 = release (DF) | lead time (a) | CFR (a) | recuperação. Recalculada a partir dos valores brutos
de `data/metrics.csv` com a tabela fixa da disciplina (`metricas.dora`), sem reaproveitar as colunas
de classe do CSV; `conferir_com_csv` compara o resultado com `dora_c1` do dataset.

    python -m analysis.dora_class_c1 [--csv data/metrics.csv] [--saida outputs/analise]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from analysis import common

COLUNAS = ["full_name", "deployment_frequency", "lt_release_median_h", "cfr_a", "rec_median_h",
           "df_class", "lt_class", "cfr_class", "rec_class", "n_metricas", "dora_c1"]


def classificar(df: pd.DataFrame) -> pd.DataFrame:
    cls = pd.DataFrame([common.classificar_c1(l) for _, l in df.iterrows()], index=df.index)
    return pd.concat([df[["full_name", "deployment_frequency", "lt_release_median_h", "cfr_a",
                          "rec_median_h"]], cls], axis=1)[COLUNAS]


def distribuicao(classes: pd.DataFrame, coluna: str = "dora_c1") -> pd.DataFrame:
    n = classes[coluna].value_counts().reindex(common.CATEGORIAS, fill_value=0)
    total = int(n.sum())
    return pd.DataFrame({"categoria": n.index, "n": n.values,
                         "pct": (n.values / total * 100) if total else 0.0})


def conferir_com_csv(classes: pd.DataFrame, df: pd.DataFrame) -> int:
    """Nº de repositórios cuja C1 recalculada difere de `dora_c1` do CSV (esperado: 0)."""
    if "dora_c1" not in df:
        return 0
    esperado = df["dora_c1"].fillna("")
    mask = esperado != ""
    return int((classes.loc[mask, "dora_c1"] != esperado[mask]).sum())


def executar(csv: Path, saida: Path) -> pd.DataFrame:
    saida.mkdir(parents=True, exist_ok=True)
    df = common.ler_metricas(csv)
    classes = classificar(df)
    classes.to_csv(saida / "dora_class.csv", index=False)
    dist = distribuicao(classes)
    dist.to_csv(saida / "dora_class_distribuicao.csv", index=False)
    # distribuição por métrica, para a tabela do artigo
    por_metrica = pd.DataFrame({c: classes[c].value_counts().reindex(common.CATEGORIAS, fill_value=0)
                                for c in ["df_class", "lt_class", "cfr_class", "rec_class", "dora_c1"]})
    por_metrica.index.name = "categoria"
    por_metrica.to_csv(saida / "dora_class_por_metrica.csv")
    dif = conferir_com_csv(classes, df)
    if dif:
        raise SystemExit(f"C1 recalculada difere de dora_c1 em {dif} repositórios")
    return dist


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=common.CSV_PADRAO)
    ap.add_argument("--saida", type=Path, default=common.SAIDA_PADRAO)
    a = ap.parse_args(argv)
    print(executar(a.csv, a.saida).to_string(index=False))


if __name__ == "__main__":
    main()
