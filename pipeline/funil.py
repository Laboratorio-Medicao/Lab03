"""Funil de seleção: funil.csv (1 linha por repositório) e funil.md (resumo), do mesmo dado."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import asdict, fields
from pathlib import Path

from pipeline.selection import RepoRecord, ResultadoSelecao

ETAPAS = (
    ("actions", "1. Possui Actions"),
    ("releases", "2. Releases mínimas"),
    ("runs", "3. Runs válidos mínimos"),
)
COLUNAS = [f.name for f in fields(RepoRecord)]


def resumo(registros: list[RepoRecord]) -> dict:
    """Entram/saem/restam por etapa e contagem de motivos, calculados só a partir dos registros."""
    entram = len(registros)
    etapas = []
    motivos: Counter = Counter()
    for chave, nome in ETAPAS:
        descartados = [r for r in registros if r.status == "descartado" and r.etapa == chave]
        motivos.update(r.motivo for r in descartados)
        etapas.append({"etapa": nome, "entram": entram, "saem": len(descartados), "restam": entram - len(descartados)})
        entram -= len(descartados)
    return {
        "candidatos": len(registros),
        "etapas": etapas,
        "motivos": dict(sorted(motivos.items())),
        "selecionados": sum(1 for r in registros if r.status == "selecionado"),
    }


def escrever_csv(registros: list[RepoRecord], caminho: Path) -> None:
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        for r in sorted(registros, key=lambda r: r.full_name.lower()):
            w.writerow({k: ("" if v is None else v) for k, v in asdict(r).items()})


def renderizar_md(res: ResultadoSelecao) -> str:
    s = resumo(res.registros)
    linhas = [
        "# Funil de Seleção",
        "",
        f"Resultados brutos da busca: {res.brutos} · candidatos após deduplicação: {res.candidatos_total or s['candidatos']}",
        "",
        "| Etapa | Entram | Saem | Restam |",
        "|---|---:|---:|---:|",
        f"| 0. Candidatos avaliados ({res.origem}, sem duplicatas) | {s['candidatos']} | — | {s['candidatos']} |",
    ]
    linhas += [f"| {e['etapa']} | {e['entram']} | {e['saem']} | {e['restam']} |" for e in s["etapas"]]
    linhas += [f"| Amostra final | {s['selecionados']} | — | {s['selecionados']} |", ""]
    if res.candidatos_total > s["candidatos"]:
        nao = res.candidatos_total - s["candidatos"]
        linhas += [
            f"A avaliação parou ao atingir a amostra: **{s['candidatos']}** candidatos avaliados "
            f"e **{nao}** não avaliados (ordem determinística por `full_name`; lacuna L17).",
            "",
        ]
    linhas += ["## Motivos de descarte", ""]
    if s["motivos"]:
        linhas += ["| Motivo | Quantidade |", "|---|---:|"] + [f"| {m} | {n} |" for m, n in s["motivos"].items()]
    else:
        linhas.append("Nenhum descarte.")
    linhas += ["", "## Fatias consultadas na Search API", ""]
    if res.origem != "Search API":
        linhas.append("Sem busca: os candidatos vieram da lista informada.")
    elif res.fatias:
        linhas += ["| Consulta | total_count | Coletados | Saturada |", "|---|---:|---:|---|"]
        linhas += [f"| `{f.consulta}` | {f.total_count} | {f.retornados} | {'sim' if f.saturada else 'não'} |" for f in res.fatias]
    else:
        linhas.append("Nenhuma fatia registrada.")
    return "\n".join(linhas) + "\n"


def escrever_funil(res: ResultadoSelecao, saidas_dir: Path) -> tuple[Path, Path]:
    saidas_dir.mkdir(parents=True, exist_ok=True)
    csv_path, md_path = saidas_dir / "funil.csv", saidas_dir / "funil.md"
    escrever_csv(res.registros, csv_path)
    md_path.write_text(renderizar_md(res), encoding="utf-8")
    return csv_path, md_path
