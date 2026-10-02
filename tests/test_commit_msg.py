import subprocess

import pytest

from scripts.check_commit_msg import tem_referencia

ACEITAS = [
    "feat(pipeline): cria estrutura inicial (#3)",
    "test(metricas): adiciona testes de lead time (#3)",
    "fix: corrige coisa\n\ncloses #12",
    "Merge branch 'main' into feature",
]
REJEITADAS = [
    "ajustes",
    "corrige coisas",
    "wip",
    "feat: algo sem numero #",
    "feat: issue #abc",
    "feat: sem ref\n\n# Please enter the commit message\n# #3 no comentario",
]


@pytest.mark.parametrize("mensagem", ACEITAS)
def test_aceita_com_referencia(mensagem):
    assert tem_referencia(mensagem)


@pytest.mark.parametrize("mensagem", REJEITADAS)
def test_rejeita_sem_referencia(mensagem):
    assert not tem_referencia(mensagem)


@pytest.fixture
def repo_com_hook(tmp_path, raiz):
    """Repositório git temporário com o hook do projeto instalado via core.hooksPath."""
    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True
        )
    git("init", "-q")
    git("config", "user.email", "t@t.com")
    git("config", "user.name", "T")
    git("config", "commit.gpgsign", "false")
    # o hook usa `git rev-parse --show-toplevel`; copia scripts/ e .githooks/ para o repo de teste
    (tmp_path / "scripts").mkdir()
    (tmp_path / ".githooks").mkdir()
    for rel in ("scripts/check_commit_msg.py", ".githooks/commit-msg"):
        destino = tmp_path / rel
        destino.write_bytes((raiz / rel).read_bytes())
        destino.chmod(0o755)
    git("config", "core.hooksPath", ".githooks")
    (tmp_path / "a.txt").write_text("x")
    git("add", "a.txt")
    return git


def test_hook_rejeita_commit_sem_numero(repo_com_hook):
    r = repo_com_hook("commit", "-m", "ajustes")
    assert r.returncode != 0
    assert "REJEITADO" in r.stderr
    assert repo_com_hook("log", "--oneline").returncode != 0  # nenhum commit foi criado


def test_hook_aceita_commit_com_numero(repo_com_hook):
    r = repo_com_hook("commit", "-m", "feat(pipeline): cria estrutura inicial (#3)")
    assert r.returncode == 0, r.stderr
    assert "(#3)" in repo_com_hook("log", "--format=%s").stdout
