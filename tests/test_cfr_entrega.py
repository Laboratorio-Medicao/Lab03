"""Testes de metricas.cfr_entrega (Issue #27) — CFR (b), exemplos da E§5 e bordas da fonte_vdd.

Fixtures fictícias, feitas à mão: nenhum repositório ou tag da amostra-ouro.
"""

from datetime import datetime, timedelta, timezone

import pytest

from metricas.cfr_entrega import cfr_entrega, resumo_cfr_entrega
from metricas.heuristica import HEURISTIC_VERSION

JANELA = ("2025-01-01T00:00:00Z", "2025-12-31T23:59:59Z")
FIM = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


def rel(published_at, corretiva=False):
    if isinstance(published_at, datetime):
        published_at = published_at.isoformat()
    return {"published_at": published_at, "heuristic_corrective": corretiva}


def test_exemplo_professor():
    """v2.3.0 (10/05) → v2.3.1 (12/05) corretiva: v2.3.0 falhou; v2.4.0 (01/06) → v2.5.0 (20/06): não."""
    r = cfr_entrega([
        rel("2025-05-10T12:00:00Z"),                   # v2.3.0
        rel("2025-05-12T12:00:00Z", corretiva=True),   # v2.3.1
        rel("2025-06-01T12:00:00Z"),                   # v2.4.0
        rel("2025-06-20T12:00:00Z"),                   # v2.5.0
    ], JANELA)
    assert r["n_releases_falha_cfr_b"] == 1
    assert r["n_releases_avaliadas_cfr_b"] == 4
    assert r["cfr_b"] == pytest.approx(1 / 4)


def test_corretiva_que_nao_e_a_proxima_release_conta():
    """L08: qualquer release em (R, R+7d], não só a próxima."""
    r = cfr_entrega([
        rel("2025-03-01T00:00:00Z"),                   # R
        rel("2025-03-03T00:00:00Z"),                   # X, não corretiva
        rel("2025-03-06T00:00:00Z", corretiva=True),   # S
    ], JANELA)
    # R falha (S em +5d); X falha (S em +3d); S não tem corretiva depois.
    assert r["n_releases_falha_cfr_b"] == 2
    assert r["cfr_b"] == pytest.approx(2 / 3)


def test_exatamente_7_dias_falha_e_7_dias_mais_1s_nao():
    r0 = datetime(2025, 4, 1, 10, tzinfo=timezone.utc)
    no_limite = cfr_entrega([rel(r0), rel(r0 + timedelta(days=7), corretiva=True)], JANELA)
    assert no_limite["n_releases_falha_cfr_b"] == 1
    depois = cfr_entrega([rel(r0), rel(r0 + timedelta(days=7, seconds=1), corretiva=True)], JANELA)
    assert depois["n_releases_falha_cfr_b"] == 0
    assert depois["cfr_b"] == 0.0


def test_mesmo_instante_nao_conta():
    r0 = "2025-04-01T10:00:00Z"
    assert cfr_entrega([rel(r0), rel(r0, corretiva=True)], JANELA)["n_releases_falha_cfr_b"] == 0


def test_corretiva_antes_de_r_nao_conta():
    r = cfr_entrega([rel("2025-04-01T00:00:00Z", corretiva=True), rel("2025-04-03T00:00:00Z")], JANELA)
    assert r["n_releases_falha_cfr_b"] == 0


def test_censura_ultimos_7_dias():
    """R em fim−7d é avaliada; R em fim−7d+1s é censurada e sai do denominador."""
    r = cfr_entrega([
        rel("2025-06-01T00:00:00Z"),
        rel(FIM - timedelta(days=7)),
        rel(FIM - timedelta(days=7) + timedelta(seconds=1), corretiva=True),
    ], JANELA)
    assert r["n_releases_janela"] == 3
    assert r["n_releases_censuradas_cfr_b"] == 1
    assert r["n_releases_avaliadas_cfr_b"] == 2
    # a avaliada em fim−7d é seguida pela corretiva 1 s depois (dentro da janela)
    assert r["n_releases_falha_cfr_b"] == 1
    assert r["cfr_b"] == pytest.approx(1 / 2)


def test_dez_releases_duas_falhas_e_censurada_fora_do_denominador():
    """Tabela da fonte_vdd: CFR = 2 / avaliadas."""
    base = datetime(2025, 2, 1, tzinfo=timezone.utc)
    releases = [rel(base + timedelta(days=20 * i)) for i in range(10)]
    releases += [rel(base + timedelta(days=1), corretiva=True), rel(base + timedelta(days=41), corretiva=True)]
    releases.append(rel(FIM - timedelta(days=1)))  # censurada
    r = cfr_entrega(releases, JANELA)
    assert r["n_releases_censuradas_cfr_b"] == 1
    assert r["n_releases_avaliadas_cfr_b"] == 12
    assert r["n_releases_falha_cfr_b"] == 2
    assert r["cfr_b"] == pytest.approx(2 / 12)


def test_uma_release_e_indefinido_com_contadores():
    r = cfr_entrega([rel("2025-03-01T00:00:00Z")], JANELA)
    assert r == {
        "cfr_b": None,
        "n_releases_avaliadas_cfr_b": 1,
        "n_releases_censuradas_cfr_b": 0,
        "n_releases_janela": 1,
        "n_releases_falha_cfr_b": 0,
    }


def test_todas_censuradas_e_indefinido():
    r = cfr_entrega([rel(FIM - timedelta(days=3)), rel(FIM - timedelta(days=1))], JANELA)
    assert r["cfr_b"] is None
    assert r["n_releases_censuradas_cfr_b"] == 2 and r["n_releases_avaliadas_cfr_b"] == 0


def test_sem_releases():
    r = cfr_entrega([], JANELA)
    assert r["cfr_b"] is None and r["n_releases_janela"] == 0


def test_fora_da_janela_e_sem_data_ignoradas():
    r = cfr_entrega([
        rel("2024-12-31T23:59:59Z", corretiva=True),
        rel("2026-01-01T00:00:00Z", corretiva=True),
        {"published_at": None, "heuristic_corrective": True},
        rel("2025-03-01T00:00:00Z"),
        rel("2025-05-01T00:00:00Z"),
    ], JANELA)
    assert r["n_releases_janela"] == 2
    assert r["n_releases_falha_cfr_b"] == 0


def test_ordem_de_entrada_nao_importa():
    a = [rel("2025-03-06T00:00:00Z", corretiva=True), rel("2025-03-01T00:00:00Z")]
    assert cfr_entrega(a, JANELA) == cfr_entrega(list(reversed(a)), JANELA)


def test_janela_com_datetime():
    janela = (datetime(2025, 1, 1, tzinfo=timezone.utc), FIM)
    assert cfr_entrega([rel("2025-03-01T00:00:00Z")] * 2, janela)["n_releases_janela"] == 2


@pytest.mark.parametrize("releases", [
    [rel("2025-03-01T00:00:00Z"), rel("2025-03-02T00:00:00Z", corretiva=True), rel(FIM - timedelta(hours=1))],
    [rel(FIM - timedelta(days=d), corretiva=d % 2 == 0) for d in range(0, 30, 3)],
])
def test_invariante_avaliadas_mais_censuradas_igual_janela(releases):
    r = cfr_entrega(releases, JANELA)
    assert r["n_releases_avaliadas_cfr_b"] + r["n_releases_censuradas_cfr_b"] == r["n_releases_janela"]
    assert r["cfr_b"] is None or 0 <= r["cfr_b"] <= 1


# ---- resumo_cfr_entrega (formato de collect_commits) ----


def item(tag, base, published_at, status="ok", mensagens=(), truncado=False):
    return {
        "tag_name": tag,
        "published_at": published_at,
        "base": base,
        "status": status,
        "status_compare": "ahead" if status == "ok" else None,
        "total_commits": len(mensagens) if status == "ok" else None,
        "truncado": truncado,
        "commits": [{"sha": "x", "author_date": published_at, "message": m} for m in mensagens],
    }


def test_resumo_ponta_a_ponta():
    r = resumo_cfr_entrega([
        item("v2.3.0", "v2.2.0", "2025-05-10T12:00:00Z", mensagens=["feat: x"]),
        item("v2.3.1", "v2.3.0", "2025-05-12T12:00:00Z", mensagens=["fix: crash ao abrir arquivo"]),
        item("v2.4.0", "v2.3.1", "2025-06-01T12:00:00Z", status="404"),
        item("v2.5.0", "v2.4.0", "2025-06-20T12:00:00Z", mensagens=["fix: y"], truncado=True),
        item("v2.5.1", "v2.5.0", "2024-01-01T00:00:00Z", status="404"),  # fora da janela: não conta
    ], JANELA)
    assert r["cfr_b"] == pytest.approx(1 / 4)
    assert r["n_releases_falha_cfr_b"] == 1
    assert r["n_releases_janela"] == 4
    assert r["n_releases_mensagens_incompletas_cfr_b"] == 2
    assert r["heuristic_version"] == HEURISTIC_VERSION
