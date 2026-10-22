"""Testes de replicacao/compara.py (Issue #47/#82)."""
import math
from pathlib import Path

import pandas as pd
import pytest

from replicacao.compara import comparar, gerar_csv, gerar_md, run


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ---- comparar ----------------------------------------------------------------

def test_comparar_sem_diferenca():
    df = _df([
        {"full_name": "a/b", "deployment_frequency": 1.0, "dora_geral": "Elite"},
        {"full_name": "c/d", "deployment_frequency": 2.0, "dora_geral": "High"},
    ])
    r = comparar(df, df, ["deployment_frequency"], ["dora_geral"])
    assert r["n_comparados"] == 2
    assert r["diferencas_relativas"]["deployment_frequency"] == 0.0
    assert r["concordancia_classe"]["dora_geral"] == 100.0


def test_comparar_diferenca_relativa():
    orig = _df([{"full_name": "a/b", "deployment_frequency": 2.0}])
    rep = _df([{"full_name": "a/b", "deployment_frequency": 3.0}])
    r = comparar(orig, rep, ["deployment_frequency"], [])
    assert abs(r["diferencas_relativas"]["deployment_frequency"] - 0.5) < 1e-9


def test_comparar_orig_zero_eh_indefinido():
    orig = _df([{"full_name": "a/b", "deployment_frequency": 0.0}])
    rep = _df([{"full_name": "a/b", "deployment_frequency": 1.0}])
    r = comparar(orig, rep, ["deployment_frequency"], [])
    assert r["indefinidos"]["deployment_frequency"] == 1
    assert r["diferencas_relativas"]["deployment_frequency"] is None


def test_comparar_nan_eh_indefinido():
    orig = _df([{"full_name": "a/b", "deployment_frequency": float("nan")}])
    rep = _df([{"full_name": "a/b", "deployment_frequency": 1.0}])
    r = comparar(orig, rep, ["deployment_frequency"], [])
    assert r["indefinidos"]["deployment_frequency"] == 1


def test_comparar_ausentes():
    orig = _df([{"full_name": "a/b"}, {"full_name": "c/d"}])
    rep = _df([{"full_name": "a/b"}, {"full_name": "e/f"}])
    r = comparar(orig, rep, [], [])
    assert r["n_comparados"] == 1
    assert "c/d" in r["ausentes_replicado"]
    assert "e/f" in r["ausentes_original"]


def test_comparar_classe_igual_diferente():
    orig = _df([
        {"full_name": "a/b", "dora_geral": "Elite"},
        {"full_name": "c/d", "dora_geral": "High"},
    ])
    rep = _df([
        {"full_name": "a/b", "dora_geral": "Elite"},
        {"full_name": "c/d", "dora_geral": "Low"},
    ])
    r = comparar(orig, rep, [], ["dora_geral"])
    assert r["concordancia_classe"]["dora_geral"] == 50.0


def test_comparar_repo_faltando_nao_afeta_n_comparados():
    orig = _df([{"full_name": "a/b"}, {"full_name": "c/d"}])
    rep = _df([{"full_name": "a/b"}])
    r = comparar(orig, rep, [], [])
    assert r["n_comparados"] == 1
    assert len(r["ausentes_replicado"]) == 1


# ---- gerar_csv / gerar_md ----------------------------------------------------

def test_gerar_csv_cria_arquivo(tmp_path):
    r = {
        "diferencas_relativas": {"deployment_frequency": 0.05},
        "indefinidos": {"deployment_frequency": 2},
        "concordancia_classe": {"dora_geral": 90.0},
    }
    gerar_csv(r, tmp_path / "comp.csv")
    import csv
    rows = list(csv.DictReader((tmp_path / "comp.csv").open(encoding="utf-8-sig")))
    assert any(row["metrica"] == "deployment_frequency" for row in rows)
    assert any(row["metrica"] == "dora_geral" for row in rows)


def test_gerar_md_cria_arquivo(tmp_path):
    r = {
        "n_comparados": 28,
        "ausentes_original": [],
        "ausentes_replicado": ["x/y"],
        "diferencas_relativas": {"deployment_frequency": 0.1},
        "indefinidos": {"deployment_frequency": 0},
        "concordancia_classe": {"dora_geral": 85.0},
    }
    gerar_md(r, 30, tmp_path / "comp.md")
    texto = (tmp_path / "comp.md").read_text()
    assert "28/30" in texto
    assert "deployment_frequency" in texto


# ---- run (integração) --------------------------------------------------------

def test_run_gera_arquivos(tmp_path):
    df = _df([
        {"full_name": "a/b", "deployment_frequency": 1.0, "dora_geral": "Elite"},
        {"full_name": "c/d", "deployment_frequency": 2.0, "dora_geral": "High"},
    ])
    orig = tmp_path / "orig.csv"
    rep = tmp_path / "rep.csv"
    df.to_csv(orig, index=False)
    df.to_csv(rep, index=False)

    run(orig, rep, tmp_path)
    assert (tmp_path / "comparacao.csv").exists()
    assert (tmp_path / "comparacao.md").exists()
