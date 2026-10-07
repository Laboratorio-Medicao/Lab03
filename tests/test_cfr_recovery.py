"""Testes de metricas.cfr e metricas.recovery (Issue #14)."""

import pytest

from metricas.cfr import cfr, classify_conclusion
from metricas.cfr import so_push
from metricas.recovery import episodios, recovery_times

UTC = "+00:00"


def run(conclusion, started="2025-01-01T10:00:00Z", updated="2025-01-01T10:30:00Z", wid=1):
    return {
        "conclusion": conclusion,
        "run_started_at": started,
        "updated_at": updated,
        "workflow_id": wid,
    }


# ---- classify_conclusion (9 valores) ----

@pytest.mark.parametrize("c, esperado", [
    ("success", "success"),
    ("failure", "failure"),
    ("timed_out", "failure"),
    ("startup_failure", "failure"),
    ("cancelled", "ignored"),
    ("skipped", "ignored"),
    ("neutral", "ignored"),
    ("action_required", "ignored"),
    ("stale", "ignored"),
    (None, "ignored"),
])
def test_classify_conclusion_todos_os_valores(c, esperado):
    assert classify_conclusion(c) == esperado


def test_classify_conclusion_valor_desconhecido_e_ignored():
    assert classify_conclusion("unknown_future_value") == "ignored"


# ---- cfr ----

def test_cfr_sem_falhas():
    runs = [run("success"), run("success")]
    assert cfr(runs) == 0.0


def test_cfr_todas_falhas():
    runs = [run("failure"), run("timed_out")]
    assert cfr(runs) == pytest.approx(1.0)


def test_cfr_metade_falhas():
    runs = [run("success"), run("failure")]
    assert cfr(runs) == pytest.approx(0.5)


def test_cfr_cancelled_ignorado():
    runs = [run("success"), run("failure"), run("cancelled")]
    # 1 falha / 2 válidos = 0.5 (cancelled não conta)
    assert cfr(runs) == pytest.approx(0.5)


def test_cfr_sem_runs_validos_retorna_none():
    runs = [run("cancelled"), run("skipped")]
    assert cfr(runs) is None


def test_cfr_lista_vazia_retorna_none():
    assert cfr([]) is None


def test_cfr_agrega_todos_os_workflows():
    runs = [
        run("success", wid=1), run("failure", wid=1),
        run("success", wid=2), run("success", wid=2),
    ]
    # 1 falha / 4 válidos = 0.25
    assert cfr(runs) == pytest.approx(0.25)


# ---- recovery_times: exemplo 1h20 ----

def test_recovery_exemplo_1h20():
    runs = [
        run("failure", started="2025-01-01T10:00:00Z", updated="2025-01-01T10:00:00Z"),
        run("success", started="2025-01-01T11:00:00Z", updated="2025-01-01T11:20:00Z"),
    ]
    # início: failure.run_started_at = 10:00; fim: success.updated_at = 11:20 → 1h20 = 1.333h
    tempos = recovery_times(runs)
    assert len(tempos) == 1
    assert tempos[0] == pytest.approx(1 + 20 / 60, abs=1e-6)


# ---- recovery_times: falha nunca recuperada (censura) ----

def test_falha_nunca_recuperada_e_censurada():
    runs = [run("failure", started="2025-01-01T10:00:00Z")]
    assert recovery_times(runs) == []


def test_falha_seguida_apenas_de_cancelled_e_censurada():
    runs = [
        run("failure", started="2025-01-01T10:00:00Z"),
        run("cancelled", started="2025-01-01T11:00:00Z"),
    ]
    assert recovery_times(runs) == []


# ---- recovery_times: cancelled ignorado entre falha e sucesso ----

def test_cancelled_entre_falha_e_sucesso_nao_bloqueia_recuperacao():
    runs = [
        run("failure",   started="2025-01-01T10:00:00Z", updated="2025-01-01T10:00:00Z"),
        run("cancelled", started="2025-01-01T10:30:00Z", updated="2025-01-01T10:30:00Z"),
        run("success",   started="2025-01-01T11:00:00Z", updated="2025-01-01T11:20:00Z"),
    ]
    tempos = recovery_times(runs)
    assert len(tempos) == 1
    assert tempos[0] == pytest.approx(1 + 20 / 60, abs=1e-6)


# ---- recovery_times: 2 workflows independentes ----

def test_dois_workflows_independentes():
    runs = [
        run("failure", started="2025-01-01T10:00:00Z", updated="2025-01-01T10:00:00Z", wid=1),
        run("success", started="2025-01-01T11:00:00Z", updated="2025-01-01T11:30:00Z", wid=1),
        run("failure", started="2025-01-01T10:00:00Z", updated="2025-01-01T10:00:00Z", wid=2),
        run("success", started="2025-01-01T12:00:00Z", updated="2025-01-01T12:00:00Z", wid=2),
    ]
    tempos = recovery_times(runs)
    assert len(tempos) == 2
    assert pytest.approx(1.5) in tempos  # wf 1: 1h30
    assert pytest.approx(2.0) in tempos  # wf 2: 2h


def test_sucesso_de_workflow_1_nao_recupera_falha_de_workflow_2():
    runs = [
        run("failure", started="2025-01-01T10:00:00Z", wid=1),
        run("success", started="2025-01-01T11:00:00Z", updated="2025-01-01T11:00:00Z", wid=2),
    ]
    # falha em wf=1 não tem sucesso em wf=1 → censurada
    assert recovery_times(runs) == []


# ---- recovery_times: falhas consecutivas ----

def test_falhas_consecutivas_formam_um_unico_episodio():
    runs = [
        run("failure", started="2025-01-01T09:00:00Z", updated="2025-01-01T09:00:00Z"),
        run("failure", started="2025-01-01T10:00:00Z", updated="2025-01-01T10:00:00Z"),
        run("success", started="2025-01-01T11:00:00Z", updated="2025-01-01T11:00:00Z"),
    ]
    # episódio começa na PRIMEIRA falha (09:00) e termina no sucesso (11:00): 2h
    assert recovery_times(runs) == [pytest.approx(2.0)]


def test_exemplo_do_enunciado_um_episodio_de_1h20():
    """E§5 RQ04: success 09:00 · failure 10:00 · failure 10:30 · success 11:15 (terminou 11:20)."""
    runs = [
        run("success", started="2025-01-01T09:00:00Z", updated="2025-01-01T09:05:00Z"),
        run("failure", started="2025-01-01T10:00:00Z", updated="2025-01-01T10:05:00Z"),
        run("failure", started="2025-01-01T10:30:00Z", updated="2025-01-01T10:35:00Z"),
        run("success", started="2025-01-01T11:15:00Z", updated="2025-01-01T11:20:00Z"),
    ]
    r = episodios(runs)
    assert r["tempos_h"] == [pytest.approx(80 / 60)]
    assert (r["n_episodios"], r["n_censurados"]) == (1, 0)


def test_dois_episodios_separados_por_sucesso():
    runs = [
        run("failure", started="2025-01-01T08:00:00Z", updated="2025-01-01T08:00:00Z"),
        run("success", started="2025-01-01T09:00:00Z", updated="2025-01-01T09:00:00Z"),
        run("failure", started="2025-01-01T10:00:00Z", updated="2025-01-01T10:00:00Z"),
        run("success", started="2025-01-01T10:30:00Z", updated="2025-01-01T10:30:00Z"),
    ]
    assert recovery_times(runs) == [pytest.approx(1.0), pytest.approx(0.5)]


def test_censura_e_contada_nao_removida():
    runs = [
        run("failure", started="2025-01-01T08:00:00Z", updated="2025-01-01T08:00:00Z", wid=1),
        run("success", started="2025-01-01T09:00:00Z", updated="2025-01-01T09:00:00Z", wid=1),
        run("failure", started="2025-01-01T10:00:00Z", wid=1),   # nunca recuperada
        run("failure", started="2025-01-01T10:00:00Z", wid=2),   # outro workflow, nunca recuperada
    ]
    r = episodios(runs)
    assert r["tempos_h"] == [pytest.approx(1.0)]
    assert (r["n_episodios"], r["n_censurados"]) == (3, 2)


def test_so_push_ignora_schedule_e_dispatch():
    runs = [
        {**run("failure"), "event": "schedule"},
        {**run("failure"), "event": "workflow_dispatch"},
        {**run("success"), "event": "push"},
        run("failure"),  # sem campo event: mantido
    ]
    assert len(so_push(runs)) == 2
    assert cfr(runs) == pytest.approx(0.5)
    assert episodios([{**run("failure"), "event": "schedule"}])["n_episodios"] == 0


def test_recovery_sem_runs_retorna_lista_vazia():
    assert recovery_times([]) == []
