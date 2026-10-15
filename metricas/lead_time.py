"""Lead time for changes (RQ02) — variantes (a) por release e (b) por commit (Issue #10).

Entrada: a lista `releases` devolvida por `pipeline.collect_commits.collect_commits`, em que cada
item tem `published_at`, `status` (`ok`, `404` ou `sem_anterior`) e `commits` com `author_date`.

- (a) Por release: `published_at(R) − author_date(commit mais antigo de R)`; o valor do
  repositório é a mediana entre as releases.
- (b) Por commit: `published_at(R) − author_date(c)` para cada commit c de R; o valor do
  repositório é a mediana de **todos** os commits de **todas** as releases (não é mediana de
  medianas).

Data do commit = `commit.author.date` (E§3), nunca `committer.date`. Unidade: horas.

Casos fora do cálculo (contados em `resumo_lead_time`):
- `404` no `compare` (E§11) e `sem_anterior` (1ª release da história, E§5);
- release sem commits novos (L07, decisão do grupo: excluída e contada);
- commit com data posterior à release (L07, decisão do grupo: excluído, contado e avisado no log);
- commit sem `author_date` ou release sem `published_at` (dado incompleto da API).
"""

from __future__ import annotations

import logging
import statistics
from typing import Iterable, Mapping

from metricas.dora import _dt

log = logging.getLogger("metricas.lead_time")

# Mesmos valores de pipeline.collect_commits; repetidos aqui para `metricas` não depender do pipeline.
STATUS_OK = "ok"
STATUS_404 = "404"
STATUS_SEM_ANTERIOR = "sem_anterior"


def _duracoes(release: Mapping) -> tuple[list[float], int]:
    """Lead times válidos (horas) dos commits de R e quantos commits deram negativo."""
    if release.get("status") != STATUS_OK or not release.get("published_at"):
        return [], 0
    publicada = _dt(release["published_at"])
    horas: list[float] = []
    negativos = 0
    for c in release.get("commits") or []:
        if not c.get("author_date"):
            continue
        h = (publicada - _dt(c["author_date"])).total_seconds() / 3600
        if h < 0:
            negativos += 1
            continue
        horas.append(h)
    if negativos:
        log.warning(
            "%s: %d commit(s) com author_date posterior à release; excluídos do lead time",
            release.get("tag_name"), negativos,
        )
    return horas, negativos


def lead_time_por_release(release: Mapping) -> float | None:
    """Variante (a) de uma release, em horas; `None` se R não é avaliável."""
    horas, _ = _duracoes(release)
    return max(horas) if horas else None


def lead_times_por_commit(release: Mapping) -> list[float]:
    """Variante (b) de uma release: um lead time (horas) por commit; `[]` se R não é avaliável."""
    horas, _ = _duracoes(release)
    return horas


def lead_time_release(releases: Iterable[Mapping]) -> float | None:
    """Mediana de (a) entre as releases avaliáveis; `None` se nenhuma (ex.: repo com 1 release)."""
    valores = [v for v in (lead_time_por_release(r) for r in releases) if v is not None]
    return statistics.median(valores) if valores else None


def lead_time_commit(releases: Iterable[Mapping]) -> float | None:
    """Mediana de (b) sobre todos os commits de todas as releases; `None` se não houver nenhum."""
    valores = [h for r in releases for h in lead_times_por_commit(r)]
    return statistics.median(valores) if valores else None


def resumo_lead_time(releases: Iterable[Mapping]) -> dict:
    """Medianas (a) e (b) do repositório e as contagens de releases/commits fora do cálculo."""
    releases = list(releases)
    por_release: list[float] = []
    por_commit: list[float] = []
    n_negativos = 0
    for r in releases:
        horas, negativos = _duracoes(r)
        n_negativos += negativos
        if horas:
            por_release.append(max(horas))
            por_commit.extend(horas)
    return {
        "lt_release_median_h": statistics.median(por_release) if por_release else None,
        "lt_commit_median_h": statistics.median(por_commit) if por_commit else None,
        "n_releases_avaliadas": len(por_release),
        "n_releases_ignored_404": sum(1 for r in releases if r.get("status") == STATUS_404),
        "n_sem_anterior": sum(1 for r in releases if r.get("status") == STATUS_SEM_ANTERIOR),
        # sem commit utilizável: sem commits novos OU só com commits posteriores à release (excluídos)
        "n_sem_commits_novos": sum(
            1 for r in releases if r.get("status") == STATUS_OK and not _duracoes(r)[0]
        ),
        "n_commits_negativos": n_negativos,
    }
