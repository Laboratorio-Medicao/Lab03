"""Integração fim a fim (auditoria S01, P1): seleção -> coleta -> métricas com uma 'API do GitHub' falsa.

Cobre o encadeamento que antes não existia (`criar_etapas` devolvia None) e a 2ª execução sem chamadas.
"""

import csv
import logging
from datetime import date

import pytest

from pipeline.cache import CachedHttpClient
from pipeline.config import Config, SelecaoConfig
from pipeline.etapas import calcular_metricas, criar_etapas
from pipeline.execucao import executar
from pipeline.selection import RepoRecord

INICIO, FIM = date(2025, 1, 1), date(2025, 12, 31)


class Resp:
    def __init__(self, dados, status=200, headers=None):
        self.status_code, self._d, self.headers = status, dados, headers or {}

    def json(self):
        return self._d


class GitHubFalso:
    """Um repositório `org/app` com 6 releases (a 1ª fora da janela) e 60 runs push."""

    def __init__(self):
        self.chamadas = []

    def get(self, path, params=None):
        self.chamadas.append(path)
        params = params or {}
        if path == "/search/repositories":
            item = {"full_name": "org/app", "stargazers_count": 5000, "language": "Python",
                    "default_branch": "trunk", "created_at": "2020-01-01T00:00:00Z"}
            return Resp({"total_count": 1, "items": [item]})
        if path.endswith("/actions/workflows"):
            return Resp({"total_count": 2})
        if path.endswith("/releases"):
            rels = [{"id": i, "tag_name": f"v{i}", "draft": False, "prerelease": False,
                     "published_at": f"2024-12-{i + 1:02d}T00:00:00Z" if i == 0 else f"2025-0{i}-15T00:00:00Z",
                     "created_at": "2025-01-01T00:00:00Z", "target_commitish": "trunk", "html_url": "u"}
                    for i in range(6)]
            return Resp(rels)
        if path.endswith("/actions/runs"):
            assert params["branch"] == "trunk" and params["event"] == "push"
            runs = [{"workflow_id": 1, "conclusion": "success" if i % 4 else "failure", "event": "push",
                     "run_started_at": f"2025-02-01T{i // 60:02d}:{i % 60:02d}:00Z",
                     "updated_at": f"2025-02-01T{i // 60:02d}:{i % 60:02d}:30Z"} for i in range(60)]
            return Resp({"total_count": 60, "workflow_runs": runs}) if params["created"].startswith("2025-02-01") \
                else Resp({"total_count": 0, "workflow_runs": []})
        if path.endswith("/contributors"):
            return Resp([{}], headers={"Link": '<https://api.github.com/x?per_page=1&anon=true&page=42>; rel="last"'})
        if "/compare/" in path:
            fim = path.split("...")[1]
            return Resp({"total_commits": 1, "status": "ahead", "commits": [
                {"sha": "s" + fim, "commit": {"author": {"date": "2025-01-10T00:00:00Z"},
                 "committer": {"date": "2025-01-10T00:00:00Z"}, "message": "m"}, "parents": []}]})
        if path.endswith("/tags"):
            return Resp([{"name": "v1", "commit": {"sha": "abc"}}])
        if "/git/commits/" in path:
            return Resp({"author": {"date": "2025-01-10T00:00:00Z"}, "committer": {"date": "2025-01-10T00:00:00Z"}})
        raise AssertionError(f"endpoint inesperado: {path}")


def config(tmp_path):
    sel = SelecaoConfig(faixas_estrelas=(1000,), amostra_alvo=1, min_releases=5, min_runs_validos=50)
    return Config(token_env="GITHUB_TOKEN", janela_inicio=INICIO, janela_fim=FIM,
                  cache_dir=tmp_path / "cache", saidas_dir=tmp_path / "out", selecao=sel)


def linhas(caminho):
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_comando_encadeia_selecao_coleta_e_metricas(tmp_path):
    cfg = config(tmp_path)
    cliente = CachedHttpClient(GitHubFalso(), cfg.cache_dir)
    r = executar(cfg, cliente, criar_etapas(cfg), cfg.selecao.amostra_alvo)
    assert (r.selecionados, r.processados, r.concluidos, r.erros) == (1, 1, 1, 0)
    linha = linhas(cfg.saidas_dir / "resultados.csv")[0]
    assert linha["full_name"] == "org/app" and linha["default_branch"] == "trunk"
    assert linha["contributors"] == "42"
    assert linha["n_releases_deploy_total"] == "6"
    # 5 releases na janela, janela de 364 dias -> 5 / 52 semanas
    assert float(linha["deployment_frequency"]) == pytest.approx(5 / (364.99999 / 7), rel=1e-3)
    # v0 (dez/2024) é só a "anterior" de v1; v1..v5: 5 comparações, 1 commit de 10/01 cada
    assert linha["n_sem_anterior"] == "0" and linha["n_releases_avaliadas"] == "5"
    assert float(linha["lt_commit_median_h"]) > 0
    assert linha["n_runs_coletados"] == "60"
    assert linha["n_tags"] == "1"
    assert linha["df_class"] in {"Elite", "High", "Medium", "Low"}
    assert (cfg.saidas_dir / "funil.csv").exists()


def test_segunda_execucao_nao_chama_a_api(tmp_path, caplog):
    cfg = config(tmp_path)
    api1 = GitHubFalso()
    executar(cfg, CachedHttpClient(api1, cfg.cache_dir), criar_etapas(cfg), 1)
    assert api1.chamadas

    api2 = GitHubFalso()
    cliente2 = CachedHttpClient(api2, cfg.cache_dir)
    with caplog.at_level(logging.INFO):
        r = executar(cfg, cliente2, criar_etapas(cfg), 1)
    assert api2.chamadas == []                      # 0 chamadas na 2ª execução
    assert cliente2.estatisticas()["cache_misses"] == 0
    assert r.consumo_cache["cache_misses"] == 0 and r.consumo_cache["cache_hits"] > 0
    assert "cache_misses" in caplog.text


def test_calcular_metricas_classifica_e_conta_censura():
    repo = RepoRecord("o/r", 10, "Go", "main", "2020-01-01T00:00:00Z", contributors=3, age_days=100.0)

    def run(c, h, wf=1, ev="push"):
        return {"workflow_id": wf, "conclusion": c, "event": ev,
                "run_started_at": f"2025-03-01T{h:02d}:00:00Z", "updated_at": f"2025-03-01T{h:02d}:20:00Z"}

    dados = {
        "releases": [{"draft": False, "prerelease": False, "published_at": "2025-03-15T00:00:00Z"}],
        "commits": {"releases": [{"tag_name": "v1", "published_at": "2025-03-15T00:00:00Z", "status": "ok",
                                  "commits": [{"author_date": "2025-03-14T00:00:00Z"}]}]},
        "runs": [run("success", 9), run("failure", 10), run("failure", 11), run("success", 12),
                 run("failure", 13), run("failure", 14, ev="schedule")],
        "tags": None,
    }
    m = calcular_metricas(repo, dados, INICIO, FIM)
    assert m["lt_release_median_h"] == 24 and m["lt_class"] == "High"
    assert m["n_runs_fora_de_push"] == 1
    assert (m["n_runs_sucesso"], m["n_runs_falha"]) == (2, 3)
    assert m["cfr_a"] == pytest.approx(3 / 5) and m["cfr_class"] == "Low"
    # episódio 1: falha 10:00 -> sucesso updated 12:20 = 2h20; episódio 2: falha 13:00 sem recuperação
    assert m["rec_median_h"] == pytest.approx(2 + 20 / 60)
    assert (m["n_episodios"], m["n_episodios_censurados"]) == (2, 1)
    assert m["prop_episodios_censurados"] == pytest.approx(0.5)
    assert m["n_tags"] is None
    # DF 1/52 semana -> Low (1) ; LT High (3); CFR Low (1); REC High (3) -> mediana 2 -> Medium
    assert (m["df_class"], m["rec_class"], m["dora_geral"]) == ("Low", "High", "Medium")


def test_classificacao_geral_parcial_com_metricas_definidas_e_sinalizada():
    repo = RepoRecord("o/r", 10, None, "main", "2020-01-01T00:00:00Z")
    dados = {"releases": [], "commits": {"releases": []}, "runs": [], "tags": None}
    m = calcular_metricas(repo, dados, INICIO, FIM)
    # só DF é definida (0 releases → Low): classifica com ela e sinaliza 1 métrica
    assert m["lt_class"] == "" and m["cfr_a"] is None
    assert m["dora_geral"] == "Low" and m["n_metricas_dora"] == 1
