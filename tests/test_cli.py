import os
import subprocess

TOKEN_FALSO = "ghp_SEGREDO_NAO_PODE_VAZAR"


def rodar(python, raiz, *args, token=None):
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
    if token is not None:
        env["GITHUB_TOKEN"] = token
    return subprocess.run(
        [python, "-m", "pipeline", *args],
        cwd=raiz, env=env, capture_output=True, text=True,
    )


def test_comando_unico_funciona(python, raiz):
    r = rodar(python, raiz, "--config", "config.yaml", token=TOKEN_FALSO)
    assert r.returncode == 0, r.stderr
    assert "ambiente OK" in r.stderr


def test_token_nunca_aparece_na_saida(python, raiz):
    r = rodar(python, raiz, "--config", "config.yaml", token=TOKEN_FALSO)
    assert TOKEN_FALSO not in r.stdout + r.stderr


def test_sem_token_falha_com_mensagem_clara(python, raiz):
    r = rodar(python, raiz, "--config", "config.yaml")
    assert r.returncode == 1
    assert "GITHUB_TOKEN" in r.stderr
    assert "Traceback" not in r.stderr


def test_config_inexistente_falha_sem_traceback(python, raiz):
    r = rodar(python, raiz, "--config", "nao_existe.yaml", token=TOKEN_FALSO)
    assert r.returncode == 1
    assert "não encontrado" in r.stderr
    assert "Traceback" not in r.stderr
