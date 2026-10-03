"""Testes de metricas.cfr e metricas.recovery (Issue #14)."""

import pytest

from metricas.cfr import cfr, classify_conclusion
from metricas.recovery import recovery_times

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

def test_falhas_consecutivas_cada_uma_conta_independentemente():
    runs = [
        run("failure", started="2025-01-01T09:00:00Z", updated="2025-01-01T09:00:00Z"),
        run("failure", started="2025-01-01T10:00:00Z", updated="2025-01-01T10:00:00Z"),
        run("success", started="2025-01-01T11:00:00Z", updated="2025-01-01T11:00:00Z"),
    ]
    tempos = recovery_times(runs)
    # F1 → S: 2h; F2 → S: 1h
    assert len(tempos) == 2
    assert pytest.approx(2.0) in tempos
    assert pytest.approx(1.0) in tempos


def test_recovery_sem_runs_retorna_lista_vazia():
    assert recovery_times([]) == []
