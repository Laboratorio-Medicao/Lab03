"""Testes de scripts/ensaio_replicacao.py (Issue #82)."""
from pathlib import Path

import pandas as pd
import pytest

from scripts.ensaio_replicacao import run, sha256_arquivo, sortear_repos, salvar_repos_file

RAIZ = Path(__file__).parent.parent


def _csv_fake(tmp_path: Path, n: int = 50) -> Path:
    df = pd.DataFrame({
        "full_name": [f"owner{i}/repo{i}" for i in range(n)],
        "deployment_frequency": [float(i) for i in range(n)],
        "dora_geral": ["Elite"] * n,
    })
    p = tmp_path / "metrics.csv"
    df.to_csv(p, index=False)
    return p


# ---- sortear_repos -----------------------------------------------------------

def test_sortear_repos_retorna_30(tmp_path):
    csv = _csv_fake(tmp_path, n=100)
    repos = sortear_repos(csv, n=30, semente=42)
    assert len(repos) == 30
    assert "full_name" in repos.columns


def test_sortear_repos_reprodutivel(tmp_path):
    csv = _csv_fake(tmp_path, n=100)
    r1 = sortear_repos(csv, n=30, semente=42)
    r2 = sortear_repos(csv, n=30, semente=42)
    assert list(r1["full_name"]) == list(r2["full_name"])


def test_sortear_repos_semente_diferente_muda(tmp_path):
    csv = _csv_fake(tmp_path, n=100)
    r1 = sortear_repos(csv, n=30, semente=42)
    r2 = sortear_repos(csv, n=30, semente=99)
    assert list(r1["full_name"]) != list(r2["full_name"])


# ---- sha256_arquivo ----------------------------------------------------------

def test_sha256_arquivo_deterministico(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("conteúdo", encoding="utf-8")
    h1 = sha256_arquivo(p)
    h2 = sha256_arquivo(p)
    assert h1 == h2
    assert len(h1) == 64


def test_sha256_arquivo_muda_com_conteudo(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("a", encoding="utf-8")
    h1 = sha256_arquivo(p)
    p.write_text("b", encoding="utf-8")
    h2 = sha256_arquivo(p)
    assert h1 != h2


# ---- salvar_repos_file -------------------------------------------------------

def test_salvar_repos_file_cria_arquivo(tmp_path):
    repos = pd.DataFrame({"full_name": ["a/b", "c/d"]})
    destino = tmp_path / "repos_30.txt"
    salvar_repos_file(repos, destino, sha_origem="abc123")
    conteudo = destino.read_text(encoding="utf-8")
    assert "a/b" in conteudo
    assert "c/d" in conteudo
    assert "abc123" in conteudo


def test_salvar_repos_file_formato_valido(tmp_path):
    repos = pd.DataFrame({"full_name": ["owner/repo"]})
    destino = tmp_path / "repos.txt"
    salvar_repos_file(repos, destino, sha_origem="x")
    linhas = [l for l in destino.read_text().splitlines() if not l.startswith("#")]
    assert linhas == ["owner/repo"]


# ---- run (integração, sem pipeline) -----------------------------------------

def test_run_sem_pipeline_gera_repos_file(tmp_path):
    csv = _csv_fake(tmp_path, n=50)
    repos_file = tmp_path / "repos_30.txt"
    resultado = run(
        csv=csv,
        saida_dir=tmp_path / "saida",
        config=RAIZ / "config.yaml",
        repos_file=repos_file,
        sem_pipeline=True,
    )
    assert repos_file.exists()
    assert resultado["n_repos"] == 30
    assert len(resultado["sha_metricas"]) == 64


def test_run_sem_pipeline_gera_log(tmp_path):
    csv = _csv_fake(tmp_path, n=50)
    saida = tmp_path / "saida"
    run(
        csv=csv,
        saida_dir=saida,
        config=RAIZ / "config.yaml",
        repos_file=tmp_path / "repos.txt",
        sem_pipeline=True,
    )
    assert (saida / "ensaio.log").exists()
    log_texto = (saida / "ensaio.log").read_text()
    assert "SO:" in log_texto
    assert "Python:" in log_texto


def test_run_compara_quando_csv_replicado_existe(tmp_path):
    csv = _csv_fake(tmp_path, n=50)
    saida = tmp_path / "saida"
    saida.mkdir()
    # cria CSV "replicado" igual ao original (30 repos sorteados)
    repos = sortear_repos(csv, n=30, semente=42)
    orig = pd.read_csv(csv)
    replicado = orig[orig["full_name"].isin(repos["full_name"])]
    replicado.to_csv(saida / "repos_final.csv", index=False)

    resultado = run(
        csv=csv,
        saida_dir=saida,
        config=RAIZ / "config.yaml",
        repos_file=tmp_path / "repos.txt",
        sem_pipeline=True,
    )
    assert resultado["resultado_compara"] is not None
    assert resultado["resultado_compara"]["n_comparados"] == 30
