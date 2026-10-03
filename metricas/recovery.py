"""Tempo de recuperação de falhas por workflow (Issue #14).

Para cada run com falha, o episódio começa em `run_started_at` e termina em
`updated_at` do próximo sucesso no mesmo workflow. Falhas sem recuperação
posterior são censuradas (excluídas da lista retornada).
"""

from __future__ import annotations

from datetime import datetime, timezone

from metricas.cfr import classify_conclusion


def _dt(valor) -> datetime:
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor


def recovery_times(runs: list[dict]) -> list[float]:
    """Horas de recuperação para cada episódio de falha não censurado.

    Agrupa por `workflow_id`. Para cada falha, busca o próximo sucesso
    (por `run_started_at`) no mesmo workflow. Falhas sem sucesso posterior
    são censuradas e não entram na lista.
    """
    por_workflow: dict = {}
    for r in runs:
        wid = r.get("workflow_id")
        por_workflow.setdefault(wid, []).append(r)

    tempos: list[float] = []
    for wf_runs in por_workflow.values():
        ordenados = sorted(
            wf_runs,
            key=lambda r: _dt(r["run_started_at"]),
        )
        for i, run in enumerate(ordenados):
            if classify_conclusion(run.get("conclusion")) != "failure":
                continue
            # Procura o próximo sucesso após esta falha
            for proximo in ordenados[i + 1:]:
                if classify_conclusion(proximo.get("conclusion")) == "success":
                    inicio = _dt(run["run_started_at"])
                    fim = _dt(proximo["updated_at"])
                    tempos.append((fim - inicio).total_seconds() / 3600)
                    break

    return tempos
