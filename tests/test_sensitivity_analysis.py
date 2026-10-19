"""Testes da análise de sensibilidade RQ07 (Issue #40)."""
import csv
from pathlib import Path

import pandas as pd
import pytest

from scripts.sensitivity_analysis import ORDEM, analisar_par, matriz_transicao, run


def _df_simples(c1, c2, c3):
    """DataFrame mínimo com as três colunas de classificação DORA."""
    return pd.DataFrame({"dora_c1": c1, "dora_c2": c2, "dora_c3": c3})


# ---- analisar_par ----

def test_par_sem_mudanca_kappa_1():
    # usa todas as categorias para que o kappa seja definido
    cats = ORDEM * 3
    df = _df_simples(cats, cats, cats)
    r = analisar_par(df, "C1", "C2")
    assert r["n_mudou"] == 0 and r["pct_mudou"] == 0.0 and r["kappa_linear"] == 1.0


def test_par_todos_mudam_pct_100():
    c1 = ["Elite", "High", "Medium", "Low"]
    c2 = ["Low", "Medium", "High", "Elite"]
    df = _df_simples(c1, c2, c1)
    r = analisar_par(df, "C1", "C2")
    assert r["n_mudou"] == 4 and r["pct_mudou"] == 100.0


def test_par_n_exclui_nulos():
    df = _df_simples(["Elite", None, "High"], ["Elite", "High", "High"], ["Elite", "Elite", "High"])
    r = analisar_par(df, "C1", "C2")
    assert r["n"] == 2


def test_par_kappa_entre_menos1_e_1():
    df = _df_simples(ORDEM * 3, (ORDEM * 3)[::-1], ORDEM * 3)
    r = analisar_par(df, "C1", "C2")
    assert -1.0 <= r["kappa_linear"] <= 1.0


def test_par_campos_retornados():
    df = _df_simples(["Elite"], ["High"], ["Elite"])
    r = analisar_par(df, "C1", "C3")
    assert set(r) == {"par", "n", "n_mudou", "pct_mudou", "kappa_linear"}
    assert r["par"] == "C1×C3"


# ---- matriz_transicao ----

def test_matriz_dimensoes_e_ordem():
    df = _df_simples(["Elite", "High", "Medium", "Low"],
                     ["High", "High", "Low", "Low"],
                     ["Elite"] * 4)
    mat = matriz_transicao(df, "C1", "C2")
    assert list(mat.index) == ORDEM
    assert list(mat.columns) == ORDEM


def test_matriz_diagonal_sem_mudanca():
    df = _df_simples(ORDEM, ORDEM, ORDEM)
    mat = matriz_transicao(df, "C1", "C2")
    for cat in ORDEM:
        assert mat.loc[cat, cat] == 1


def test_matriz_soma_igual_a_n():
    c1 = ["Elite", "High", "Medium", "Low", "Elite", "High"]
    c2 = ["High", "High", "Low", "Low", "Elite", "Medium"]
    df = _df_simples(c1, c2, c1)
    mat = matriz_transicao(df, "C1", "C2")
    assert mat.values.sum() == len(c1)


# ---- run (integração) ----

def test_run_gera_arquivos(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()

    df = pd.DataFrame({
        "dora_c1": ORDEM * 5,
        "dora_c2": (ORDEM * 5)[::-1],
        "dora_c3": ORDEM * 5,
    })
    df.to_csv(tmp_path / "data" / "metrics.csv", index=False)

    import scripts.sensitivity_analysis as sa
    monkeypatch.setattr(sa, "METRICS", tmp_path / "data" / "metrics.csv")
    monkeypatch.setattr(sa, "OUT_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sa, "OUT_CSV", tmp_path / "outputs" / "sensitivity_dora.csv")
    monkeypatch.setattr(sa, "OUT_MD", tmp_path / "outputs" / "sensitivity_dora.md")

    run()

    assert (tmp_path / "outputs" / "sensitivity_dora.csv").exists()
    assert (tmp_path / "outputs" / "sensitivity_dora.md").exists()


def test_run_csv_tem_tres_pares(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()

    df = pd.DataFrame({"dora_c1": ORDEM * 2, "dora_c2": ORDEM * 2, "dora_c3": ORDEM * 2})
    df.to_csv(tmp_path / "data" / "metrics.csv", index=False)

    import scripts.sensitivity_analysis as sa
    monkeypatch.setattr(sa, "METRICS", tmp_path / "data" / "metrics.csv")
    monkeypatch.setattr(sa, "OUT_DIR", tmp_path / "outputs")
    monkeypatch.setattr(sa, "OUT_CSV", tmp_path / "outputs" / "sensitivity_dora.csv")
    monkeypatch.setattr(sa, "OUT_MD", tmp_path / "outputs" / "sensitivity_dora.md")

    run()

    with (tmp_path / "outputs" / "sensitivity_dora.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert {r["par"] for r in rows} == {"C1×C2", "C1×C3", "C2×C3"}
