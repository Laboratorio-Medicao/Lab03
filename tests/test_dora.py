"""Testes de metricas.dora — valores derivados de fonte_vdd.md §5.1, §5.5 e §12.2."""
import math
from datetime import datetime, timedelta, timezone

import pytest

from metricas.dora import (
    DF_UM_POR_MES, ELITE, HIGH, LOW, MEDIUM, classify_cfr, classify_df,
    classify_lt, classify_overall, classify_recovery, deployment_frequency, score,
)

UTC = timezone.utc
INI = datetime(2025, 1, 1, tzinfo=UTC)
FIM = INI + timedelta(days=365)
EPS = 1e-9


def rel(dias, draft=False, prerelease=False):
    return {"draft": draft, "prerelease": prerelease, "published_at": INI + timedelta(days=dias)}


# ---------------- deployment_frequency ----------------

def test_df_52_releases_em_365_dias():
    releases = [rel(i * 7) for i in range(52)]
    assert deployment_frequency(releases, (INI, FIM)) == pytest.approx(52 / (365 / 7))
    assert deployment_frequency(releases, (INI, FIM)) == pytest.approx(0.997, abs=1e-3)


@pytest.mark.parametrize("n, dias, esperado", [(1, 7, 1.0), (4, 7, 4.0), (14, 14, 7.0), (3, 21, 1.0)])
def test_df_janelas_curtas(n, dias, esperado):
    releases = [rel(1) for _ in range(n)]
    assert deployment_frequency(releases, (INI, INI + timedelta(days=dias))) == pytest.approx(esperado)


def test_df_zero_releases():
    assert deployment_frequency([], (INI, FIM)) == 0.0


def test_df_ignora_draft_prerelease_e_fora_da_janela():
    releases = [rel(10), rel(11, draft=True), rel(12, prerelease=True), rel(-1), rel(366),
                {"draft": False, "prerelease": False, "published_at": None}]
    assert deployment_frequency(releases, (INI, FIM)) == pytest.approx(1 / (365 / 7))


def test_df_fronteiras_da_janela_inclusivas():
    releases = [rel(0), rel(365)]
    assert deployment_frequency(releases, (INI, FIM)) == pytest.approx(2 / (365 / 7))
    assert deployment_frequency([{"draft": False, "prerelease": False,
                                  "published_at": FIM + timedelta(seconds=1)}], (INI, FIM)) == 0.0


def test_df_aceita_iso_8601():
    r = [{"draft": False, "prerelease": False, "published_at": "2025-01-02T00:00:00Z"}]
    assert deployment_frequency(r, ("2025-01-01T00:00:00Z", "2025-01-08T00:00:00Z")) == pytest.approx(1.0)


@pytest.mark.parametrize("janela", [(FIM, INI), (INI, INI)])
def test_df_janela_invalida(janela):
    with pytest.raises(ValueError):
        deployment_frequency([], janela)


# ---------------- classify_df ----------------

@pytest.mark.parametrize("v, esperado", [
    (10, ELITE), (7.0 + EPS, ELITE), (7.0, ELITE), (6.99, HIGH), (7.0 - EPS, HIGH),
    (3, HIGH), (1.0 + EPS, HIGH), (1.0, HIGH), (1.0 - EPS, MEDIUM), (0.99, MEDIUM),
    (0.5, MEDIUM), (DF_UM_POR_MES + EPS, MEDIUM), (DF_UM_POR_MES, MEDIUM),
    (DF_UM_POR_MES - EPS, LOW), (0.1, LOW), (0, LOW), (0.0, LOW),
])
def test_classify_df(v, esperado):
    assert classify_df(v) == esperado


def test_df_um_por_mes_vale_0_230():
    assert DF_UM_POR_MES == pytest.approx(0.230, abs=1e-3)


# ---------------- classify_lt (horas) ----------------

@pytest.mark.parametrize("h, esperado", [
    (0, ELITE), (6, ELITE), (23.99, ELITE), (24 - EPS, ELITE),
    (24, HIGH), (24 + EPS, HIGH), (72, HIGH), (167.99, HIGH),
    (168 - EPS, HIGH), (168, MEDIUM), (168 + EPS, MEDIUM), (500, MEDIUM), (719.99, MEDIUM),
    (720 - EPS, MEDIUM), (720, LOW), (720 + EPS, LOW), (5000, LOW),
])
def test_classify_lt(h, esperado):
    assert classify_lt(h) == esperado


# ---------------- classify_cfr (proporção) ----------------

@pytest.mark.parametrize("v, esperado", [
    (0, ELITE), (0.10, ELITE), (0.15 - EPS, ELITE), (0.15, ELITE),
    (0.1501, HIGH), (0.15 + EPS, HIGH), (0.20, HIGH), (0.30 - EPS, HIGH), (0.30, HIGH),
    (0.3001, MEDIUM), (0.30 + EPS, MEDIUM), (0.40, MEDIUM), (0.45 - EPS, MEDIUM), (0.45, MEDIUM),
    (0.4501, LOW), (0.45 + EPS, LOW), (0.8, LOW), (1, LOW), (1.0, LOW),
])
def test_classify_cfr(v, esperado):
    assert classify_cfr(v) == esperado


# ---------------- classify_recovery (horas) ----------------

@pytest.mark.parametrize("h, esperado", [
    (0, ELITE), (0.5, ELITE), (1 - EPS, ELITE),
    (1, HIGH), (1 + EPS, HIGH), (3, HIGH), (24 - EPS, HIGH),
    (24, MEDIUM), (24 + EPS, MEDIUM), (100, MEDIUM), (168 - EPS, MEDIUM),
    (168, LOW), (168 + EPS, LOW), (1000, LOW),
])
def test_classify_recovery(h, esperado):
    assert classify_recovery(h) == esperado


# ---------------- entradas inválidas ----------------

@pytest.mark.parametrize("fn, v", [
    (classify_df, -0.1), (classify_df, math.nan), (classify_df, None),
    (classify_lt, -1), (classify_lt, math.nan),
    (classify_cfr, -0.01), (classify_cfr, 1.01), (classify_cfr, math.nan),
    (classify_recovery, -1), (classify_recovery, math.nan),
])
def test_classify_entrada_invalida(fn, v):
    with pytest.raises(ValueError):
        fn(v)


# ---------------- classify_overall ----------------

def test_overall_exemplo_do_professor_4_3_3_1_high():
    notas = (4, 3, 3, 1)
    assert sorted(notas) == [1, 3, 3, 4]       # ordenado
    assert (3 + 3) / 2 == 3                    # mediana dos dois centrais
    assert classify_overall(notas) == "High"   # floor(3) = 3 -> High


@pytest.mark.parametrize("notas, esperado", [
    ((4, 4, 4, 4), ELITE), ((3, 3, 3, 3), HIGH), ((2, 2, 2, 2), MEDIUM), ((1, 1, 1, 1), LOW),
    ((4, 3, 2, 1), MEDIUM),   # 2,5 -> floor 2
    ((4, 4, 3, 1), HIGH),     # 3,5 -> floor 3
    ((4, 4, 1, 1), MEDIUM),   # 2,5 -> floor 2
    ((4, 4, 4, 1), ELITE),    # 4
    ((4, 1, 1, 1), LOW),      # 1
    ((3, 3, 2, 2), MEDIUM),   # 2,5 -> floor 2
    ((4, 4, 3, 3), HIGH),     # 3,5 -> floor 3
    ((2, 2, 1, 1), LOW),      # 1,5 -> floor 1
    ((3, 2, 2, 1), MEDIUM),   # 2
])
def test_overall_mediana_com_floor(notas, esperado):
    assert classify_overall(notas) == esperado


@pytest.mark.parametrize("notas", [(1, 3, 4, 3), (3, 1, 3, 4), (3, 3, 4, 1), [4, 3, 3, 1]])
def test_overall_independe_da_ordem(notas):
    assert classify_overall(notas) == HIGH


@pytest.mark.parametrize("notas, esperado_media_arred", [((4, 4, 4, 1), HIGH), ((4, 1, 1, 1), MEDIUM)])
def test_overall_usa_mediana_nao_media(notas, esperado_media_arred):
    # média 3,25 -> High / 1,75 -> Medium (arredondada); a mediana dá outra resposta
    assert classify_overall(notas) != esperado_media_arred


@pytest.mark.parametrize("notas", [(4, 3, 3), (4, 3, 3, 1, 1), (), (0, 3, 3, 1), (5, 3, 3, 1),
                                   (4, 3, 3, None), (4, 3, 3, 2.5), (True, 3, 3, 1)])
def test_overall_entrada_invalida(notas):
    with pytest.raises(ValueError):
        classify_overall(notas)


def test_score_mapeamento():
    assert [score(c) for c in (ELITE, HIGH, MEDIUM, LOW)] == [4, 3, 2, 1]


def test_pipeline_das_quatro_metricas():
    notas = [score(classify_df(10)), score(classify_lt(6)), score(classify_cfr(0.10)),
             score(classify_recovery(0.5))]
    assert notas == [4, 4, 4, 4] and classify_overall(notas) == ELITE


def test_df_datas_ingenuas_tratadas_como_utc():
    r = [{"draft": False, "prerelease": False, "published_at": datetime(2025, 1, 2)}]
    assert deployment_frequency(r, (datetime(2025, 1, 1), datetime(2025, 1, 8))) == pytest.approx(1.0)
