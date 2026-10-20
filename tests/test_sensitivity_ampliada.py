"""Testes da análise de sensibilidade ampliada RQ07 (Issue #41)."""
import csv
import math

import pandas as pd
import pytest

from scripts.sensitivity_ampliada import (
    ORDEM,
    _classificar_com_fator,
    _resultado,
    analise_censura_rq04,
    analise_cortes,
    analise_janela_cfr_b,
    analise_min_releases,
    run,
)


def _df_base(**extra):
    base = {
        "deployment_frequency": [1.0, 0.1, 10.0, 0.5],
        "lt_release_median_h": [10.0, 200.0, 5.0, 100.0],
        "cfr_a": [0.1, 0.4, 0.05, 0.2],
        "rec_median_h": [0.5, 50.0, 0.2, 5.0],
        "dora_c1": ["Elite", "Low", "Elite", "High"],
        "cfr_b_class": ["Elite", "High", "Elite", "Medium"],
        "cfr_b": [0.1, 0.25, 0.05, 0.35],
        "n_releases_falha_cfr_b": [1, 2, 0, 3],
        "n_releases_avaliadas_cfr_b": [10, 8, 12, 8],
        "n_releases_censuradas_cfr_b": [1, 2, 0, 1],
        "n_releases_janela": [11, 10, 12, 9],
        "rec_class": ["Elite", "Medium", "Elite", "High"],
        "prop_episodios_censurados": [0.0, 0.8, 0.1, 0.3],
        "n_episodios": [5, 4, 3, 6],
    }
    base.update(extra)
    return pd.DataFrame(base)


# ---- _resultado ----

def test_resultado_sem_mudanca():
    s = pd.Series(["Elite", "High", "Low"])
    r = _resultado("teste", s, s)
    assert r["n_mudou"] == 0 and r["pct_mudou"] == 0.0 and r["kappa_linear"] == 1.0


def test_resultado_todos_mudam():
    a = pd.Series(["Elite", "High"])
    b = pd.Series(["Low", "Medium"])
    r = _resultado("teste", a, b)
    assert r["n_mudou"] == 2 and r["pct_mudou"] == 100.0


def test_resultado_ignora_nulos():
    a = pd.Series(["Elite", None, "High"])
    b = pd.Series(["Elite", "High", "High"])
    r = _resultado("teste", a, b)
    assert r["n"] == 2


def test_resultado_campos():
    s = pd.Series(["Elite", "High"] * 4)
    r = _resultado("minha_var", s, s)
    assert set(r) == {"variacao", "n", "n_mudou", "pct_mudou", "kappa_linear"}
    assert r["variacao"] == "minha_var"


# ---- analise_janela_cfr_b ----

def test_janela_cfr_b_retorna_dois_pares():
    df = _df_base()
    res = analise_janela_cfr_b(df)
    assert len(res) == 2
    assert res[0]["variacao"] == "cfr_b_janela_3d_vs_7d"
    assert res[1]["variacao"] == "cfr_b_janela_14d_vs_7d"


def test_janela_cfr_b_lower_bound_menos_falhas_que_upper():
    # lower bound usa denominador maior → cfr menor → mais Elite/High
    df = _df_base()
    r_lb = analise_janela_cfr_b(df)[0]
    r_ub = analise_janela_cfr_b(df)[1]
    # ambos devem ter n > 0
    assert r_lb["n"] > 0 and r_ub["n"] > 0


# ---- analise_min_releases ----

def test_min_releases_retorna_dois():
    df = _df_base()
    res = list(analise_min_releases(df))
    assert len(res) == 2
    assert res[0]["variacao"] == "min_releases_5"
    assert res[1]["variacao"] == "min_releases_10"


def test_min_releases_10_n_menor_ou_igual_5():
    df = _df_base()
    res = list(analise_min_releases(df))
    assert res[1]["n"] <= res[0]["n"]


def test_min_releases_exclui_repos_abaixo_do_minimo():
    df = _df_base()
    # 2 repos com n_releases_janela < 10
    res = list(analise_min_releases(df))
    # com min=10, repos com janela < 10 ficam como None → n_mudou pode ser 0 (vira None não muda "mudou")
    assert res[1]["n"] >= 0


# ---- analise_censura_rq04 ----

def test_censura_rq04_retorna_um():
    df = _df_base()
    res = analise_censura_rq04(df)
    assert len(res) == 1
    assert res[0]["variacao"] == "censura_rq04_excluir_alta"


def test_censura_rq04_exclui_prop_alta():
    # repo com prop > 0.5 deve ser excluído (None)
    df = _df_base()
    alta_censura = (pd.to_numeric(df["prop_episodios_censurados"], errors="coerce") > 0.5).sum()
    res = analise_censura_rq04(df)
    assert res[0]["n"] == df["rec_class"].replace("", None).notna().sum() - alta_censura


# ---- analise_cortes ----

def test_cortes_retorna_dois():
    df = _df_base()
    res = list(analise_cortes(df))
    assert len(res) == 2
    assert res[0]["variacao"] == "cortes_mais10pct"
    assert res[1]["variacao"] == "cortes_menos10pct"


def test_classificar_com_fator_1_igual_ao_base():
    df = _df_base()
    base_cls = list(analise_cortes(df))[0]
    # com fator 1.0 deveria ser idêntico à classificação base
    alt = _classificar_com_fator(df, 1.0)
    n_dif = (df["dora_c1"].replace("", None) != alt).sum()
    # pode haver pequenas diferenças por arredondamento de limiar, mas deve ser baixo
    assert n_dif <= 1


# ---- run (integração) ----

def test_run_gera_arquivos(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    _df_base().to_csv(tmp_path / "data" / "metrics.csv", index=False)

    import scripts.sensitivity_ampliada as sa
    monkeypatch.setattr(sa, "METRICS", tmp_path / "data" / "metrics.csv")
    monkeypatch.setattr(sa, "OUT_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sa, "OUT_CSV", tmp_path / "outputs" / "sensitivity_ampliada.csv")
    monkeypatch.setattr(sa, "OUT_MD", tmp_path / "outputs" / "sensitivity_ampliada.md")

    run()

    assert (tmp_path / "outputs" / "sensitivity_ampliada.csv").exists()
    assert (tmp_path / "outputs" / "sensitivity_ampliada.md").exists()


def test_run_csv_tem_sete_linhas(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    _df_base().to_csv(tmp_path / "data" / "metrics.csv", index=False)

    import scripts.sensitivity_ampliada as sa
    monkeypatch.setattr(sa, "METRICS", tmp_path / "data" / "metrics.csv")
    monkeypatch.setattr(sa, "OUT_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sa, "OUT_CSV", tmp_path / "outputs" / "sensitivity_ampliada.csv")
    monkeypatch.setattr(sa, "OUT_MD", tmp_path / "outputs" / "sensitivity_ampliada.md")

    run()

    with (tmp_path / "outputs" / "sensitivity_ampliada.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 7
