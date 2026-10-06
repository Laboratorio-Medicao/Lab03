"""Testes de metricas.lead_time (Issue #10) — exemplos e bordas da E§5/E§7."""

import logging
from datetime import datetime, timedelta, timezone

import pytest

from metricas.lead_time import (
    lead_time_commit,
    lead_time_por_release,
    lead_time_release,
    lead_times_por_commit,
    resumo_lead_time,
)

DIA = 24.0


def commit(author_date, committer_date=None):
    return {"sha": "x", "author_date": author_date, "committer_date": committer_date or author_date}


def release(published_at, datas, status="ok", tag="v1.1"):
    return {
        "tag_name": tag,
        "published_at": published_at,
        "base": "v1.0",
        "status": status,
        "commits": [commit(d) for d in datas],
    }


def release_dias(lead_times_dias, tag="vX"):
    """Release publicada em 01/06 com commits N dias antes."""
    pub = datetime(2025, 6, 1, tzinfo=timezone.utc)
    datas = [(pub - timedelta(days=d)).isoformat() for d in lead_times_dias]
    return release(pub.isoformat(), datas, tag=tag)


V11 = release(
    "2025-03-15T00:00:00Z",
    ["2025-03-02T00:00:00Z", "2025-03-10T00:00:00Z", "2025-03-14T00:00:00Z"],
)


# ---- exemplo do professor (E§5) ----

def test_v11_variante_a_13_dias():
    assert lead_time_por_release(V11) == pytest.approx(13 * DIA)  # 312 h


def test_v11_variante_b_13_5_1_dias():
    assert sorted(lead_times_por_commit(V11)) == pytest.approx([1 * DIA, 5 * DIA, 13 * DIA])


def test_v11_medianas_do_repo():
    assert lead_time_release([V11]) == pytest.approx(13 * DIA)
    assert lead_time_commit([V11]) == pytest.approx(5 * DIA)


# ---- medianas ----

def test_a_mediana_entre_releases():
    rs = [release_dias([13], "r1"), release_dias([4], "r2"), release_dias([2], "r3")]
    assert lead_time_release(rs) == pytest.approx(4 * DIA)


def test_b_mediana_de_todos_os_commits_nao_de_medianas():
    rs = [release_dias([13, 5, 1], "r1"), release_dias([2, 2], "r2")]
    # Todos {1,2,2,5,13} → 2 d; mediana das medianas seria (5+2)/2 = 3,5 d.
    assert lead_time_commit(rs) == pytest.approx(2 * DIA)


def test_divergencia_a_b_commit_esquecido():
    rs = [release_dias([100, 1, 1, 1, 1])]
    assert lead_time_release(rs) == pytest.approx(100 * DIA)
    assert lead_time_commit(rs) == pytest.approx(1 * DIA)


# ---- bordas ----

def test_release_sem_commits_novos_excluida_e_contada():
    vazia = release("2025-04-01T00:00:00Z", [], tag="v1.2")
    assert lead_time_por_release(vazia) is None
    assert lead_times_por_commit(vazia) == []
    assert lead_time_release([vazia]) is None
    assert lead_time_commit([vazia]) is None

    res = resumo_lead_time([V11, vazia])
    assert res["n_sem_commits_novos"] == 1
    assert res["n_releases_avaliadas"] == 1
    assert res["lt_release_median_h"] == pytest.approx(13 * DIA)


def test_repo_com_uma_release_indefinido():
    unica = release("2025-03-15T00:00:00Z", [], status="sem_anterior", tag="v1.0")
    assert lead_time_release([unica]) is None
    assert lead_time_commit([unica]) is None
    res = resumo_lead_time([unica])
    assert res["n_sem_anterior"] == 1
    assert res["lt_release_median_h"] is None
    assert res["lt_commit_median_h"] is None


def test_404_ignorada_e_contada():
    r404 = release("2025-04-01T00:00:00Z", [], status="404", tag="v1.2")
    # Mesmo se viesse com commits, 404 não entra no cálculo.
    r404_com_commits = release("2025-04-01T00:00:00Z", ["2024-01-01T00:00:00Z"], status="404", tag="v1.3")
    assert lead_time_por_release(r404_com_commits) is None

    res = resumo_lead_time([V11, r404, r404_com_commits])
    assert res["n_releases_ignored_404"] == 2
    assert res["n_releases_avaliadas"] == 1
    assert res["lt_release_median_h"] == pytest.approx(13 * DIA)
    assert res["lt_commit_median_h"] == pytest.approx(5 * DIA)


def test_usa_author_date_e_nao_committer_date():
    r = {
        "tag_name": "v2.0",
        "published_at": "2025-03-15T00:00:00Z",
        "status": "ok",
        "commits": [commit("2025-03-05T00:00:00Z", committer_date="2025-03-14T00:00:00Z")],
    }
    assert lead_time_por_release(r) == pytest.approx(10 * DIA)


def test_primeira_release_da_janela_com_anterior_fora_entra():
    # O status "ok" vem do compare com a release anterior (fora da janela); entra no cálculo.
    r = release("2025-01-02T00:00:00Z", ["2024-12-30T00:00:00Z"], tag="v3.0")
    r["base"] = "v2.9"
    assert lead_time_release([r]) == pytest.approx(3 * DIA)


def test_commit_posterior_a_release_excluido_e_contado(caplog):
    r = release(
        "2025-03-15T00:00:00Z",
        ["2025-03-10T00:00:00Z", "2025-03-16T00:00:00Z"],
    )
    with caplog.at_level(logging.WARNING, logger="metricas.lead_time"):
        assert lead_time_por_release(r) == pytest.approx(5 * DIA)
    assert "posterior à release" in caplog.text
    assert lead_times_por_commit(r) == pytest.approx([5 * DIA])
    assert resumo_lead_time([r])["n_commits_negativos"] == 1


def test_release_so_com_commits_negativos_nao_avaliavel():
    r = release("2025-03-15T00:00:00Z", ["2025-03-16T00:00:00Z"])
    res = resumo_lead_time([r])
    assert res["n_releases_avaliadas"] == 0
    assert res["n_commits_negativos"] == 1
    assert res["lt_release_median_h"] is None


def test_dados_incompletos_ignorados():
    sem_pub = release(None, ["2025-03-10T00:00:00Z"])
    assert lead_time_por_release(sem_pub) is None
    sem_data = release("2025-03-15T00:00:00Z", [None, "2025-03-14T00:00:00Z"])
    assert lead_times_por_commit(sem_data) == pytest.approx([1 * DIA])


def test_datas_com_offset():
    # 15/03 00:00 UTC − 14/03 21:00-03:00 (= 15/03 00:00 UTC) → 0 h, não negativo.
    r = release("2025-03-15T00:00:00Z", ["2025-03-14T21:00:00-03:00", "2025-03-14T00:00:00+00:00"])
    assert sorted(lead_times_por_commit(r)) == pytest.approx([0.0, 1 * DIA])


def test_resumo_conjunto():
    rs = [
        release_dias([13, 5, 1], "r1"),
        release_dias([2, 2], "r2"),
        release("2025-06-01T00:00:00Z", [], status="sem_anterior", tag="r0"),
        release("2025-06-01T00:00:00Z", [], status="404", tag="r3"),
        release("2025-06-01T00:00:00Z", [], tag="r4"),
    ]
    assert resumo_lead_time(rs) == {
        "lt_release_median_h": pytest.approx(7.5 * DIA),
        "lt_commit_median_h": pytest.approx(2 * DIA),
        "n_releases_avaliadas": 2,
        "n_releases_ignored_404": 1,
        "n_sem_anterior": 1,
        "n_sem_commits_novos": 1,
        "n_commits_negativos": 0,
    }
