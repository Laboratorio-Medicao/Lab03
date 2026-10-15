"""Etapas por repositório do comando único: coleta (releases, tags, commits, runs) e métricas.

Liga os coletores (`collect_*`) às funções de `metricas` seguindo o contrato de `pipeline.execucao`:

    coletar(client, repo, inicio, fim) -> dados
    calcular(repo, dados, inicio, fim) -> dict   # colunas de `resultados.csv`

Definição de referência (C1 da RQ07): deploy = release publicada; lead time (a) por release;
CFR (a) de CI. As demais variantes (lead time (b), tags) são coletadas/calculadas à parte.
"""

from __future__ import annotations

import logging
import statistics
from datetime import date, datetime, time, timezone
from pathlib import Path

from metricas import dora
from metricas.cfr import cfr, classify_conclusion, so_push
from metricas.lead_time import resumo_lead_time
from metricas.recovery import episodios
from pipeline.collect_commits import collect_commits
from pipeline.collect_releases import collect_releases, pares_com_anterior
from pipeline.collect_runs import collect_runs
from pipeline.collect_tags import collect_tags
from pipeline.execucao import Etapas
from pipeline.funil import escrever_funil
from pipeline.selection import RepoRecord, selecionar

log = logging.getLogger("pipeline.etapas")


def coletar_repositorio(client, repo: RepoRecord, inicio: date, fim: date, cache_dir: Path, tags: bool = True) -> dict:
    """Coleta tudo de um repositório. Respostas ficam no cache: reexecutar não repete chamadas."""
    releases = collect_releases(client, repo.full_name, cache_dir)
    pares = pares_com_anterior(releases, inicio, fim)
    commits = collect_commits(client, repo.full_name, pares, cache_dir)
    saturados: list[str] = []
    runs = collect_runs(client, repo.full_name, repo.default_branch, inicio, fim, saturados)
    dados = {"releases": releases, "commits": commits, "runs": runs, "runs_dias_saturados": saturados, "tags": None}
    if tags:
        dados["tags"] = collect_tags(client, repo.full_name, cache_dir)
    return dados


def _janela(inicio: date, fim: date) -> tuple[datetime, datetime]:
    """(início 00:00, fim 23:59:59) UTC: o dia final é inclusivo, como na coleta."""
    return (
        datetime.combine(inicio, time.min, tzinfo=timezone.utc),
        datetime.combine(fim, time.max.replace(microsecond=0), tzinfo=timezone.utc),
    )


def _categoria(funcao, valor) -> str:
    return funcao(valor) if valor is not None else ""


def calcular_metricas(repo: RepoRecord, dados: dict, inicio: date, fim: date) -> dict:
    """Metadados + métricas DORA (C1) + contadores de exclusão/censura de um repositório."""
    releases, runs = dados["releases"], dados["runs"]
    janela = _janela(inicio, fim)

    df = dora.deployment_frequency(releases, janela)
    lt = resumo_lead_time(dados["commits"]["releases"])
    runs_push = so_push(runs)
    n_sucessos = sum(1 for r in runs_push if classify_conclusion(r.get("conclusion")) == "success")
    n_falhas = sum(1 for r in runs_push if classify_conclusion(r.get("conclusion")) == "failure")
    taxa_falha = cfr(runs_push)
    rec = episodios(runs_push)
    rec_mediana = statistics.median(rec["tempos_h"]) if rec["tempos_h"] else None

    categorias = {
        "df_class": dora.classify_df(df, dora.semanas_da_janela(janela)),
        "lt_class": _categoria(dora.classify_lt, lt["lt_release_median_h"]),
        "cfr_class": _categoria(dora.classify_cfr, taxa_falha),
        "rec_class": _categoria(dora.classify_recovery, rec_mediana),
    }
    notas = [dora.score(c) for c in categorias.values() if c]
    # L10 (decisão do grupo, validada com o professor): classifica com as métricas definidas e sinaliza
    # a classificação parcial em `n_metricas_dora`.
    geral = dora.classify_overall_parcial(notas) if notas else ""

    n_deploys = sum(
        1 for r in releases
        if not r.get("draft") and not r.get("prerelease") and r.get("published_at")
    )
    tags = dados.get("tags")
    return {
        "stars": repo.stars,
        "language": repo.language,
        "contributors": repo.contributors,
        "age_days": repo.age_days,
        "default_branch": repo.default_branch,
        "n_releases_total": len(releases),
        "n_releases_deploy_total": n_deploys,
        "deployment_frequency": df,
        **lt,
        "n_runs_coletados": len(runs),
        "n_runs_dias_saturados": len(dados.get("runs_dias_saturados") or []),
        "n_runs_fora_de_push": len(runs) - len(runs_push),
        "n_runs_sucesso": n_sucessos,
        "n_runs_falha": n_falhas,
        "cfr_a": taxa_falha,
        "rec_median_h": rec_mediana,
        "n_episodios": rec["n_episodios"],
        "n_episodios_censurados": rec["n_censurados"],
        "prop_episodios_censurados": rec["n_censurados"] / rec["n_episodios"] if rec["n_episodios"] else None,
        "n_tags": len(tags) if tags is not None else None,
        **categorias,
        "dora_geral": geral,
        "n_metricas_dora": len(notas),
    }


def criar_etapas(config, *, tags: bool = True) -> Etapas:
    """Etapas de coleta e cálculo + seleção que grava o funil de forma incremental e para na amostra."""
    cache_dir, saidas = Path(config.cache_dir), Path(config.saidas_dir)

    def selecao(client, sel, inicio, fim):
        return selecionar(
            client, sel, inicio, fim,
            ao_avaliar=lambda parcial: escrever_funil(parcial, saidas),
            parar_em=sel.amostra_alvo,
        )

    return Etapas(
        coletar=lambda client, repo, inicio, fim: coletar_repositorio(client, repo, inicio, fim, cache_dir, tags),
        calcular=calcular_metricas,
        selecionar=selecao,
    )
