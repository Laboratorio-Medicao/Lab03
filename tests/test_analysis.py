"""Testes das análises RQ01–RQ04 e da classificação C1 (Issue #35)."""
import math

import pandas as pd
import pytest

from analysis import common, dora_class_c1, rq01_rq04


def _linha(**kw):
    base = {"deployment_frequency": 0.5, "lt_release_median_h": 100.0, "cfr_a": 0.1, "rec_median_h": 0.5}
    return pd.Series({**base, **kw})


def test_resumo_mediana_e_iqr():
    r = common.resumo(pd.Series([1, 2, 3, 4, 5, None]))
    assert (r["n"], r["mediana"], r["q1"], r["q3"], r["iqr"]) == (5, 3, 2, 4, 2)


def test_resumo_vazio_nao_quebra():
    r = common.resumo(pd.Series([None, None], dtype=float))
    assert r["n"] == 0 and math.isnan(r["mediana"])


def test_classificar_c1_exemplo_do_professor():
    # (4, 3, 3, 1) -> mediana 3 -> High
    c = common.classificar_c1(_linha(deployment_frequency=8, lt_release_median_h=30, cfr_a=0.2,
                                     rec_median_h=200))
    assert [c[k] for k in ("df_class", "lt_class", "cfr_class", "rec_class")] == \
        ["Elite", "High", "High", "Low"]
    assert c["dora_c1"] == "High" and c["n_metricas"] == 4


def test_classificar_c1_sem_recuperacao_e_parcial():
    c = common.classificar_c1(_linha(rec_median_h=float("nan")))
    assert c["rec_class"] == "" and c["n_metricas"] == 3 and c["dora_c1"] != ""


def test_classificar_c1_sem_nenhuma_metrica():
    c = common.classificar_c1(pd.Series({"deployment_frequency": None, "lt_release_median_h": None,
                                         "cfr_a": None, "rec_median_h": None}))
    assert c["dora_c1"] == "" and c["n_metricas"] == 0


def test_corte_um_por_mes_usa_a_janela():
    corte = 12 / common.SEMANAS_JANELA
    assert common.classificar_c1(_linha(deployment_frequency=corte))["df_class"] == "Medium"
    assert common.classificar_c1(_linha(deployment_frequency=corte * 0.99))["df_class"] == "Low"


@pytest.fixture
def df():
    return pd.DataFrame({
        "full_name": ["a/a", "b/b", "c/c"],
        "deployment_frequency": [8.0, 0.5, 0.05],
        "lt_release_median_h": [10.0, 100.0, 1000.0],
        "lt_commit_median_h": [12.0, 90.0, 900.0],
        "cfr_a": [0.1, 0.2, 0.5],
        "cfr_b": [0.0, None, 0.9],
        "rec_median_h": [0.5, 10.0, None],
        "n_episodios": [4, 2, 0],
        "n_episodios_censurados": [1, 0, 0],
        "prop_episodios_censurados": [0.25, 0.0, None],
        "dora_c1": ["Elite", "High", "Low"],
    })


def test_distribuicao_inclui_categorias_vazias(df):
    d = dora_class_c1.distribuicao(dora_class_c1.classificar(df))
    assert list(d["categoria"]) == ["Elite", "High", "Medium", "Low"]
    assert d["n"].sum() == 3 and d["pct"].sum() == pytest.approx(100)


def test_conferir_com_csv_detecta_divergencia(df):
    cl = dora_class_c1.classificar(df)
    assert dora_class_c1.conferir_com_csv(cl, df.assign(dora_c1=cl["dora_c1"])) == 0
    errado = df.assign(dora_c1=["Low", "Low", "Low"])
    assert dora_class_c1.conferir_com_csv(cl, errado) >= 1


def test_censura_nao_descarta_episodios(df):
    r = rq01_rq04.resumo_censura(df)
    assert (r["episodios_total"], r["episodios_censurados"]) == (6, 1)
    assert (r["repos_com_episodios"], r["repos_sem_episodios"]) == (2, 1)
    assert r["prop_global"] == pytest.approx(1 / 6)


def test_executar_gera_todas_as_saidas(df, tmp_path):
    csv = tmp_path / "m.csv"
    df.to_csv(csv, index=False)
    saida = tmp_path / "out"
    rq01_rq04.executar(csv, saida)
    esperados = {"rq01_rq04_descritiva.csv", "rq04_censura.csv", "rq04_censura_resumo.csv",
                 "dora_class.csv", "dora_class_distribuicao.csv", "dora_class_por_metrica.csv",
                 "rq01_df.png", "rq02_lead_time.png", "rq03_cfr_a.png", "rq03_cfr_b.png",
                 "rq04_recuperacao.png", "rq04_censura.png", "dora_class_c1.png"}
    assert esperados <= {p.name for p in saida.iterdir()}
    d = pd.read_csv(saida / "rq01_rq04_descritiva.csv")
    assert set(d["rq"]) == {"RQ01", "RQ02", "RQ03", "RQ04"}
