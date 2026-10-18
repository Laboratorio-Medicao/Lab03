"""`--repos-file` (Issue #36): lista de repositórios no lugar da Search API."""

import csv
import logging
import os
import subprocess
import tempfile

import pytest

from pipeline.cache import CachedHttpClient
from pipeline.config import ConfigError
from pipeline.etapas import criar_etapas
from pipeline.execucao import executar
from pipeline.repos_file import ler_lista, selecionar_lista
from test_etapas import INICIO, FIM, GitHubFalso, Resp, config
from test_selection import FakeClient, item


class GitHubFalsoComLista(GitHubFalso):
    """Como `GitHubFalso`, mais `GET /repos/org/app`; qualquer outro repositório não existe."""

    def get(self, path, params=None):
        if path == "/repos/org/app":
            self.chamadas.append(path)
            return Resp({"full_name": "org/app", "stargazers_count": 5000, "language": "Python",
                         "default_branch": "trunk", "created_at": "2020-01-01T00:00:00Z"})
        if path.startswith("/repos/") and path.count("/") == 3:
            self.chamadas.append(path)
            return Resp({"message": "Not Found"}, status=404)
        assert path != "/search/repositories", "a lista substitui a busca"
        return super().get(path, params)


def escrever(tmp_path, texto, nome="repos.txt"):
    caminho = tmp_path / nome
    caminho.write_text(texto, encoding="utf-8")
    return caminho


# --------------------------------------------------------------------------- leitura


def test_texto_aceita_comentarios_url_e_remove_duplicatas(tmp_path):
    arq = escrever(tmp_path, "# réplica\n\norg/app  # inline\nhttps://github.com/Org/App\n"
                             "https://github.com/a/b.git\n  c/d/  \n")
    assert ler_lista(arq) == ["org/app", "a/b", "c/d"]


def test_csv_usa_coluna_full_name(tmp_path):
    arq = escrever(tmp_path, "full_name,stars\no/r,10\nx/y,20\n\n", "metrics.csv")
    assert ler_lista(arq) == ["o/r", "x/y"]


def test_csv_com_bom_do_excel(tmp_path):
    arq = tmp_path / "r.csv"
    arq.write_bytes("﻿full_name\no/r\n".encode("utf-8"))
    assert ler_lista(arq) == ["o/r"]


def test_csv_sem_coluna_full_name_falha(tmp_path):
    with pytest.raises(ConfigError, match="full_name"):
        ler_lista(escrever(tmp_path, "repo\no/r\n", "r.csv"))


@pytest.mark.parametrize("ruim", ["so-o-nome", "a/b/c", "a b/c", "/r"])
def test_formato_invalido_aponta_a_linha(tmp_path, ruim):
    with pytest.raises(ConfigError, match="linha 2"):
        ler_lista(escrever(tmp_path, f"o/r\n{ruim}\n"))


def test_arquivo_inexistente_e_vazio_falham(tmp_path):
    with pytest.raises(ConfigError, match="não encontrado"):
        ler_lista(tmp_path / "nao_existe.txt")
    with pytest.raises(ConfigError, match="nenhum repositório"):
        ler_lista(escrever(tmp_path, "# só comentário\n\n"))


# --------------------------------------------------------------------------- seleção


def test_repo_inexistente_vira_descarte_e_nao_derruba_a_lista():
    client = FakeClient({"/repos/o/sumiu": lambda p: Resp({}, status=404),
                         "/repos/o/privado": lambda p: Resp({}, status=403)})
    res = selecionar_lista(client, ["o/sumiu", "o/privado"], config_sel(), INICIO, FIM)
    assert [(r.full_name, r.status, r.motivo) for r in res.registros] == [
        ("o/sumiu", "descartado", "repo_not_found"), ("o/privado", "descartado", "api_error_403")]
    assert res.candidatos_total == 2 and res.fatias == []


def config_sel():
    from pipeline.config import SelecaoConfig
    return SelecaoConfig()


def test_lista_mantem_a_ordem_e_aplica_os_filtros(tmp_path):
    cfg = config(tmp_path)
    api = GitHubFalsoComLista()
    res = selecionar_lista(api, ["z/ausente", "org/app"], cfg.selecao, INICIO, FIM)
    assert [r.full_name for r in res.registros] == ["z/ausente", "org/app"]
    assert [r.status for r in res.registros] == ["descartado", "selecionado"]
    app = res.registros[1]
    assert app.default_branch == "trunk" and app.n_runs_valid_window >= 50 and app.contributors == 42


# --------------------------------------------------------------------------- integração


def test_execucao_com_lista_nao_busca_e_processa_todos_sem_corte(tmp_path):
    cfg = config(tmp_path)  # amostra_alvo = 1: a lista não pode ser cortada por ele
    api = GitHubFalsoComLista()
    r = executar(cfg, CachedHttpClient(api, cfg.cache_dir), criar_etapas(cfg, repos=["org/app", "o/fora"]), None)
    assert "/search/repositories" not in api.chamadas
    assert (r.candidatos, r.selecionados, r.concluidos, r.fora_da_amostra) == (2, 1, 1, 0)
    assert r.descartes == {"repo_not_found": 1}
    with open(cfg.saidas_dir / "resultados.csv", encoding="utf-8") as f:
        assert [l["full_name"] for l in csv.DictReader(f)] == ["org/app"]
    funil = (cfg.saidas_dir / "funil.md").read_text(encoding="utf-8")
    assert "--repos-file" in funil and "repo_not_found" in funil


def test_segunda_execucao_com_lista_nao_repete_chamadas_da_coleta(tmp_path):
    cfg = config(tmp_path)
    executar(cfg, CachedHttpClient(GitHubFalsoComLista(), cfg.cache_dir), criar_etapas(cfg, repos=["org/app"]), None)
    api2 = GitHubFalsoComLista()
    cliente = CachedHttpClient(api2, cfg.cache_dir)
    executar(cfg, cliente, criar_etapas(cfg, repos=["org/app"]), None)
    assert api2.chamadas == [] and cliente.estatisticas()["cache_misses"] == 0


# --------------------------------------------------------------------------- CLI


def rodar_cli(python, raiz, *args):
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
    env.update(PYTHONPATH=str(raiz), GITHUB_TOKEN="ghp_falso")
    return subprocess.run([python, "-m", "pipeline", *args], cwd=tempfile.gettempdir(),
                          env=env, capture_output=True, text=True)


def test_cli_lista_invalida_falha_sem_traceback(python, raiz, tmp_path):
    ruim = escrever(tmp_path, "isso-nao-e-repo\n")
    r = rodar_cli(python, raiz, "--config", str(raiz / "config.yaml"), "--repos-file", str(ruim))
    assert r.returncode == 1 and "owner/repo" in r.stderr and "Traceback" not in r.stderr


def test_cli_lista_inexistente_falha_sem_traceback(python, raiz, tmp_path):
    r = rodar_cli(python, raiz, "--config", str(raiz / "config.yaml"), "--repos-file", str(tmp_path / "x.txt"))
    assert r.returncode == 1 and "não encontrado" in r.stderr and "Traceback" not in r.stderr


def test_cli_com_lista_valida_registra_o_modo(python, raiz, tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("janela:\n  inicio: null\n  fim: null\n", encoding="utf-8")
    lista = escrever(tmp_path, "o/r\n")
    r = rodar_cli(python, raiz, "--config", str(cfg), "--repos-file", str(lista))
    assert r.returncode == 0, r.stderr
    assert "lista de repositórios: 1" in r.stderr
