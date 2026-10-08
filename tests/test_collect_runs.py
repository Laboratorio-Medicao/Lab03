"""Testes de pipeline.collect_runs (Issue #13) — coleta fatiada por mês."""

from datetime import date

import pytest

from pipeline.collect_runs import collect_runs

INI = date(2025, 1, 1)
FIM = date(2025, 12, 31)


class Resp:
    def __init__(self, runs=None, total=None, headers=None, status=200):
        self._runs = runs or []
        self._total = len(self._runs) if total is None else total
        self.headers = headers or {}
        self.status_code = status

    def json(self):
        return {"total_count": self._total, "workflow_runs": self._runs}


def run(conclusion="success", branch="main"):
    return {"conclusion": conclusion, "head_branch": branch, "event": "push"}


class FakeClient:
    def __init__(self, fn):
        self._fn = fn
        self.chamadas: list[tuple[str, dict]] = []

    def get(self, path, params=None):
        params = dict(params or {})
        self.chamadas.append((path, params))
        return self._fn(path, params)


def cliente_fixo(n_por_mes=5, total=None):
    """Devolve `n_por_mes` runs para qualquer consulta com `created`."""
    def fn(path, params):
        if "actions/runs" in path:
            runs = [run() for _ in range(n_por_mes)]
            return Resp(runs=runs, total=total or n_por_mes)
        return Resp()
    return FakeClient(fn)


# ---- coleta básica ----

def test_collect_runs_retorna_lista_de_dicts(tmp_path):
    client = cliente_fixo(n_por_mes=3)
    resultado = collect_runs(client, "org/repo", "main", INI, FIM)
    assert isinstance(resultado, list)
    assert all(isinstance(r, dict) for r in resultado)


def test_collect_runs_acumula_todos_os_meses():
    client = cliente_fixo(n_por_mes=4)
    resultado = collect_runs(client, "org/repo", "main", INI, FIM)
    assert len(resultado) == 4 * 12  # 4 runs × 12 meses


def test_collect_runs_janela_de_um_mes():
    client = cliente_fixo(n_por_mes=7)
    resultado = collect_runs(client, "org/repo", "main", date(2025, 3, 1), date(2025, 3, 31))
    assert len(resultado) == 7


# ---- parâmetros enviados à API ----

def test_parametros_branch_event_e_created_enviados():
    client = cliente_fixo()
    collect_runs(client, "org/repo", "trunk", date(2025, 1, 1), date(2025, 1, 31))
    _, params = client.chamadas[0]
    assert params["branch"] == "trunk"
    assert params["event"] == "push"
    assert params["created"] == "2025-01-01..2025-01-31"


def test_um_mes_gera_uma_chamada_por_mes():
    client = cliente_fixo()
    collect_runs(client, "org/repo", "main", INI, FIM)
    created_params = [p["created"] for _, p in client.chamadas]
    assert len(created_params) == 12
    assert created_params[0] == "2025-01-01..2025-01-31"
    assert created_params[-1] == "2025-12-01..2025-12-31"


# ---- teto de 1.000: subdivisão ----

def test_teto_subdivide_o_intervalo():
    """Mês com total_count=1000 deve ser dividido em dois sub-intervalos."""
    def fn(path, params):
        ini, fim = params["created"].split("..")
        dias = (date.fromisoformat(fim) - date.fromisoformat(ini)).days
        total = 1000 if dias > 7 else 10
        runs = [run() for _ in range(min(total, 100))]
        return Resp(runs=runs, total=total)

    client = FakeClient(fn)
    collect_runs(client, "org/repo", "main", date(2025, 1, 1), date(2025, 1, 31))
    intervals = [p["created"] for _, p in client.chamadas]
    assert len(intervals) > 1
    assert intervals[0] == "2025-01-01..2025-01-31"
    assert any("2025-01-01..2025-01-16" in iv for iv in intervals)


def test_teto_em_dia_unico_nao_subdivide_e_continua(caplog):
    """Intervalo de 1 dia com teto: emite warning e continua sem travar."""
    import logging
    def fn(path, params):
        return Resp(runs=[run()], total=1000)

    client = FakeClient(fn)
    with caplog.at_level(logging.WARNING, logger="pipeline.collect_runs"):
        resultado = collect_runs(client, "org/repo", "main", date(2025, 6, 1), date(2025, 6, 1))
    assert any("teto" in m.lower() or "incompletos" in m.lower() for m in caplog.messages)
    assert isinstance(resultado, list)


# ---- paginação ----

def test_paginacao_link_next_acumula_todas_as_paginas():
    link = "<https://api.github.com/repos/org/repo/actions/runs?page=2>; rel=\"next\""
    paginas = {
        "1": Resp(runs=[run() for _ in range(100)], total=150, headers={"Link": link}),
        "2": Resp(runs=[run() for _ in range(50)], total=150),
    }

    def fn(path, params):
        page = params.get("page", "1")
        return paginas.get(str(page), Resp())

    client = FakeClient(fn)
    resultado = collect_runs(client, "org/repo", "main", date(2025, 1, 1), date(2025, 1, 31))
    assert len(resultado) == 150


# ---- log mensal ----

def test_log_mensal_emitido(caplog):
    import logging
    client = cliente_fixo(n_por_mes=3)
    with caplog.at_level(logging.INFO, logger="pipeline.collect_runs"):
        collect_runs(client, "org/repo", "main", date(2025, 1, 1), date(2025, 2, 28))
    assert any("2025/1" in m or "2025/2" in m for m in caplog.messages)


def test_dia_saturado_e_registrado_na_lista(caplog):
    """Auditoria S01: o teto em dia único (dado incompleto) deixa marca nos dados, não só no log."""
    from datetime import date
    from pipeline.collect_runs import collect_runs

    class Api:
        def get(self, path, params=None):
            class R:
                status_code = 200
                headers = {}

                def json(self_):
                    return {"total_count": 1000, "workflow_runs": []}
            return R()

    saturados = []
    collect_runs(Api(), "o/r", "main", date(2025, 3, 5), date(2025, 3, 5), saturados)
    assert saturados == ["2025-03-05"]
