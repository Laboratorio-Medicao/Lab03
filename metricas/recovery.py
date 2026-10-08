"""Tempo de recuperação de falhas por workflow (RQ04, Issue #14).

Dentro de um mesmo workflow, em ordem cronológica de `run_started_at`, um **episódio de falha**
começa na primeira falha após um sucesso e termina no próximo sucesso. Falhas seguidas pertencem
ao mesmo episódio. O tempo é `updated_at` do sucesso − `run_started_at` da primeira falha.

Execuções ignoradas (`cancelled`, `skipped`, `neutral`, `action_required`, `stale`, em andamento)
não abrem nem fecham episódios. Um episódio sem sucesso posterior na janela é **censurado**: não
entra nos tempos, mas é contado (`n_censurados`), como exige a Fonte da Verdade (TRV-009).

Decisão do grupo (o enunciado não define): uma falha que aparece antes de qualquer sucesso do
workflow na janela também abre um episódio.
"""

from __future__ import annotations

from datetime import datetime, timezone

from metricas.cfr import classify_conclusion, so_push


def _dt(valor) -> datetime:
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor


def _inicio(run: dict) -> datetime:
    return _dt(run.get("run_started_at") or run["created_at"])


def episodios(runs: list[dict]) -> dict:
    """`{"tempos_h": [...], "n_episodios": int, "n_censurados": int}` agregando todos os workflows."""
    por_workflow: dict = {}
    for r in so_push(runs):
        por_workflow.setdefault(r.get("workflow_id"), []).append(r)

    tempos: list[float] = []
    censurados = 0
    for wf_runs in por_workflow.values():
        inicio_falha: datetime | None = None
        for run in sorted(wf_runs, key=_inicio):
            classe = classify_conclusion(run.get("conclusion"))
            if classe == "failure":
                if inicio_falha is None:
                    inicio_falha = _inicio(run)
            elif classe == "success" and inicio_falha is not None:
                tempos.append((_dt(run["updated_at"]) - inicio_falha).total_seconds() / 3600)
                inicio_falha = None
        if inicio_falha is not None:
            censurados += 1
    return {
        "tempos_h": tempos,
        "n_episodios": len(tempos) + censurados,
        "n_censurados": censurados,
    }


def recovery_times(runs: list[dict]) -> list[float]:
    """Horas de recuperação de cada episódio não censurado (ver `episodios` para a contagem)."""
    return episodios(runs)["tempos_h"]
