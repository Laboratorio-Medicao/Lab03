import os
import subprocess
import tempfile

TOKEN_FALSO = "ghp_SEGREDO_NAO_PODE_VAZAR"


def rodar(python, raiz, *args, token=None):
    # Roda fora da raiz para não carregar o .env real do desenvolvedor.
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
    env["PYTHONPATH"] = str(raiz)
    args = [str(raiz / a) if a == "config.yaml" else a for a in args]
    if token is not None:
        env["GITHUB_TOKEN"] = token
    return subprocess.run(
        [python, "-m", "pipeline", *args],
        cwd=tempfile.gettempdir(), env=env, capture_output=True, text=True,
    )


def test_comando_unico_funciona(python, raiz, tmp_path):
    # Config sem janela: valida o comando e o ambiente sem sair para a rede.
    cfg = tmp_path / "config.yaml"
    cfg.write_text("janela:\n  inicio: null\n  fim: null\n", encoding="utf-8")
    r = rodar(python, raiz, "--config", str(cfg), token=TOKEN_FALSO)
    assert r.returncode == 0, r.stderr
    assert "ambiente OK" in r.stderr


def test_token_nunca_aparece_na_saida(python, raiz, tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("janela:\n  inicio: null\n  fim: null\n", encoding="utf-8")
    r = rodar(python, raiz, "--config", str(cfg), token=TOKEN_FALSO)
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
