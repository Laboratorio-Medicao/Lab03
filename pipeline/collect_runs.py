"""Coleta de workflow runs para repositórios selecionados (Issue #13).

`collect_runs` busca todos os runs de um repositório fatiando a janela por mês
(branch=default_branch, event=push, created=<mês>). Loga a contagem mensal e
alerta quando o teto de 1.000 resultados/consulta é atingido.

Diferente de `contar_runs` em selection.py (que conta para o funil de seleção),
esta função retorna os objetos de run completos para o cálculo de métricas
(CFR, tempo de recuperação, lead time).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from pipeline.selection import TETO_RESULTADOS, POR_PAGINA, meses_da_janela, _get, _link, _destino

log = logging.getLogger("pipeline.collect_runs")


def collect_runs(
    client,
    full_name: str,
    branch: str,
    inicio: date,
    fim: date,
) -> list[dict]:
    """Retorna todos os workflow runs de `full_name` na janela [inicio, fim].

    Fatia a janela por mês; subdivide o intervalo se total_count >= 1.000.
    Loga a contagem de runs por mês e avisa quando o teto é atingido.
    """
    todos: list[dict] = []
    for ini_mes, fim_mes in meses_da_janela(inicio, fim):
        antes = len(todos)
        _coletar_intervalo(client, full_name, branch, ini_mes, fim_mes, todos)
        n_mes = len(todos) - antes
        log.info("%s %s/%s: %d runs coletados", full_name, ini_mes.year, ini_mes.month, n_mes)
    return todos


def _coletar_intervalo(
    client,
    full_name: str,
    branch: str,
    ini: date,
    fim: date,
    acumulador: list[dict],
) -> None:
    params = {
        "branch": branch,
        "event": "push",
        "created": f"{ini.isoformat()}..{fim.isoformat()}",
        "per_page": POR_PAGINA,
    }
    resp = _get(client, f"/repos/{full_name}/actions/runs", params)
    total = int(resp.json().get("total_count", 0))

    if total >= TETO_RESULTADOS:
        if ini < fim:
            meio = ini + (fim - ini) // 2
            log.warning(
                "%s runs %s..%s: total_count=%d atingiu o teto; subdividindo",
                full_name, ini, fim, total,
            )
            _coletar_intervalo(client, full_name, branch, ini, meio, acumulador)
            _coletar_intervalo(client, full_name, branch, meio + timedelta(days=1), fim, acumulador)
            return
        log.warning(
            "%s runs em %s atingiram o teto de %d e não podem ser subdivididos; dados incompletos",
            full_name, ini, TETO_RESULTADOS,
        )

    runs = list(resp.json().get("workflow_runs", []))
    proxima = _link(resp.headers, "next")
    while proxima:
        caminho, parametros = _destino(proxima)
        resp = _get(client, caminho, parametros)
        runs.extend(resp.json().get("workflow_runs", []))
        proxima = _link(resp.headers, "next")

    acumulador.extend(runs)
