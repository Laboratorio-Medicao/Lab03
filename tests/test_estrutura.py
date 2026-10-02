import importlib
import subprocess

import pytest


@pytest.mark.parametrize("pacote", ["pipeline", "metricas"])
def test_pacotes_importaveis(pacote):
    importlib.import_module(pacote)


@pytest.mark.parametrize(
    "caminho",
    [
        "pipeline", "metricas", "tests", ".github/workflows/testes.yml",
        "README.md", "requirements.txt", "config.yaml", ".gitignore",
        "artigo", "data", "outputs",
    ],
)
def test_estrutura_minima_existe(raiz, caminho):
    assert (raiz / caminho).exists()


@pytest.mark.parametrize(
    "ignorado", [".env", "meu.token", "cache/x.json", "__pycache__/x.pyc", ".coverage", "htmlcov/index.html"]
)
def test_gitignore_cobre_arquivos_sensiveis_e_gerados(raiz, ignorado):
    r = subprocess.run(["git", "check-ignore", "-q", ignorado], cwd=raiz)
    assert r.returncode == 0, f"{ignorado} deveria estar no .gitignore"


def test_ci_mede_cobertura_do_modulo_metricas(raiz):
    wf = (raiz / ".github/workflows/testes.yml").read_text(encoding="utf-8")
    assert "--cov=metricas" in wf and "--cov-fail-under=80" in wf
    assert "pip install -r requirements.txt" in wf
    assert "push" in wf
