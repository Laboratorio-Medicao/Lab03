"""Compara o CSV original do autor com o CSV gerado pelo grupo replicador.

Calcula diferença relativa por métrica numérica e % de repos com a mesma
classificação DORA. Gera comparacao.csv e comparacao.md.

Uso:
    python replicacao/compara.py --original data/metrics.csv \\
        --replicado outputs_replicacao/repos_final.csv

Com mapeamento de colunas (formato do autor diferente):
    python replicacao/compara.py --original data/metrics.csv \\
        --replicado <csv> --mapeamento replicacao/mapeamento_<grupo>.yaml
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

RAIZ = Path(__file__).parent.parent

METRICAS_NUMERICAS = [
    "deployment_frequency",
    "lt_release_median_h",
    "lt_commit_median_h",
    "cfr_a",
    "cfr_b",
    "rec_median_h",
]

METRICAS_CLASSE = [
    "df_class",
    "lt_class",
    "cfr_class",
    "rec_class",
    "dora_geral",
]


def _carregar_mapeamento(caminho: Path) -> dict[str, str]:
    """Lê YAML ou retorna dict vazio (sem dependência obrigatória de PyYAML)."""
    try:
        import yaml
        with caminho.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        import json
        with caminho.open(encoding="utf-8") as f:
            return json.load(f)


def comparar(
    original: pd.DataFrame,
    replicado: pd.DataFrame,
    metricas_num: list[str] | None = None,
    metricas_cls: list[str] | None = None,
) -> dict[str, Any]:
    """Compara dois DataFrames (por full_name) e devolve métricas de concordância.

    Retorna:
        n_comparados: repos presentes nos dois
        ausentes_original: repos no replicado mas não no original
        ausentes_replicado: repos no original mas não no replicado
        diferencas_relativas: {metrica: mediana(|rep-orig|/|orig|)} para repos com orig≠0
        indefinidos: {metrica: n de pares com orig=0 ou NaN}
        concordancia_classe: {col_classe: pct de repos com mesmo valor}
    """
    if metricas_num is None:
        metricas_num = METRICAS_NUMERICAS
    if metricas_cls is None:
        metricas_cls = METRICAS_CLASSE

    orig = original.set_index("full_name")
    rep = replicado.set_index("full_name")

    comuns = orig.index.intersection(rep.index)
    ausentes_orig = list(rep.index.difference(orig.index))
    ausentes_rep = list(orig.index.difference(rep.index))

    sub_o = orig.loc[comuns]
    sub_r = rep.loc[comuns]

    diferencas: dict[str, float | None] = {}
    indefinidos: dict[str, int] = {}

    for col in metricas_num:
        if col not in sub_o.columns or col not in sub_r.columns:
            continue
        vo = pd.to_numeric(sub_o[col], errors="coerce")
        vr = pd.to_numeric(sub_r[col], errors="coerce")
        mask_indef = (vo == 0) | vo.isna() | vr.isna()
        indefinidos[col] = int(mask_indef.sum())
        mask_ok = ~mask_indef
        if mask_ok.sum() == 0:
            diferencas[col] = None
        else:
            rel = ((vr[mask_ok] - vo[mask_ok]).abs() / vo[mask_ok].abs())
            diferencas[col] = float(rel.median())

    concordancia: dict[str, float] = {}
    for col in metricas_cls:
        if col not in sub_o.columns or col not in sub_r.columns:
            continue
        mask = sub_o[col].notna() & sub_r[col].notna() & (sub_o[col] != "") & (sub_r[col] != "")
        n = int(mask.sum())
        if n == 0:
            concordancia[col] = float("nan")
        else:
            iguais = int((sub_o[col][mask] == sub_r[col][mask]).sum())
            concordancia[col] = round(iguais / n * 100, 1)

    return {
        "n_comparados": len(comuns),
        "ausentes_original": ausentes_orig,
        "ausentes_replicado": ausentes_rep,
        "diferencas_relativas": diferencas,
        "indefinidos": indefinidos,
        "concordancia_classe": concordancia,
    }


def gerar_csv(resultado: dict, caminho: Path) -> None:
    rows = []
    for col, val in resultado["diferencas_relativas"].items():
        rows.append({
            "tipo": "numerica",
            "metrica": col,
            "mediana_dif_relativa": "" if val is None else f"{val:.4f}",
            "n_indefinidos": resultado["indefinidos"].get(col, 0),
            "concordancia_pct": "",
        })
    for col, pct in resultado["concordancia_classe"].items():
        rows.append({
            "tipo": "classe",
            "metrica": col,
            "mediana_dif_relativa": "",
            "n_indefinidos": "",
            "concordancia_pct": "" if math.isnan(pct) else f"{pct:.1f}",
        })
    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tipo", "metrica", "mediana_dif_relativa",
                                          "n_indefinidos", "concordancia_pct"],
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def gerar_md(resultado: dict, n_alvo: int, caminho: Path) -> None:
    r = resultado
    linhas = [
        "# Comparação: CSV original × replicado\n",
        f"**Comparados:** {r['n_comparados']}/{n_alvo}",
    ]
    if r["ausentes_replicado"]:
        linhas.append(f"**Ausentes no replicado ({len(r['ausentes_replicado'])}):** "
                      + ", ".join(r["ausentes_replicado"][:10])
                      + (" …" if len(r["ausentes_replicado"]) > 10 else ""))
    if r["ausentes_original"]:
        linhas.append(f"**Extras no replicado ({len(r['ausentes_original'])}):** "
                      + ", ".join(r["ausentes_original"][:10]))
    linhas += [
        "",
        "## Diferença relativa nas métricas numéricas\n",
        "| Métrica | Mediana |dif rel| | Indefinidos (orig=0 ou NaN) |",
        "|---|---:|---:|",
    ]
    for col, val in r["diferencas_relativas"].items():
        val_s = "—" if val is None else f"{val:.4f}"
        linhas.append(f"| {col} | {val_s} | {r['indefinidos'].get(col, 0)} |")
    linhas += [
        "",
        "## Concordância nas classificações DORA\n",
        "| Métrica | % mesma classe |",
        "|---|---:|",
    ]
    for col, pct in r["concordancia_classe"].items():
        pct_s = "—" if math.isnan(pct) else f"{pct:.1f}%"
        linhas.append(f"| {col} | {pct_s} |")
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def run(
    original: Path,
    replicado: Path,
    saida_dir: Path,
    mapeamento: Path | None = None,
    n_alvo: int = 30,
) -> dict:
    df_orig = pd.read_csv(original)
    df_rep = pd.read_csv(replicado)

    if mapeamento is not None:
        renomear = _carregar_mapeamento(mapeamento)
        df_rep = df_rep.rename(columns=renomear)

    resultado = comparar(df_orig, df_rep)
    saida_dir.mkdir(parents=True, exist_ok=True)
    gerar_csv(resultado, saida_dir / "comparacao.csv")
    gerar_md(resultado, n_alvo, saida_dir / "comparacao.md")
    return resultado


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--original", default=str(RAIZ / "data" / "metrics.csv"))
    parser.add_argument("--replicado", required=True)
    parser.add_argument("--saida", default=str(RAIZ / "replicacao"))
    parser.add_argument("--mapeamento", default=None)
    parser.add_argument("--n-alvo", type=int, default=30)
    args = parser.parse_args(argv)

    resultado = run(
        Path(args.original),
        Path(args.replicado),
        Path(args.saida),
        Path(args.mapeamento) if args.mapeamento else None,
        args.n_alvo,
    )
    r = resultado
    print(f"Comparados: {r['n_comparados']}/{args.n_alvo}")
    if r["ausentes_replicado"]:
        print(f"Ausentes no replicado: {len(r['ausentes_replicado'])}")
    print("\nDiferença relativa (mediana):")
    for col, val in r["diferencas_relativas"].items():
        print(f"  {col}: {val:.4f}" if val is not None else f"  {col}: —")
    print("\nConcordância de classe:")
    for col, pct in r["concordancia_classe"].items():
        print(f"  {col}: {pct:.1f}%" if not math.isnan(pct) else f"  {col}: —")
    print(f"\nGravados: {Path(args.saida) / 'comparacao.csv'}, comparacao.md")


if __name__ == "__main__":
    main()
