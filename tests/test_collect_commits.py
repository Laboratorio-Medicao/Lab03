"""Testes de pipeline.collect_commits (Issue #9) — compare paginado, 404 contado e cache por repo."""

import json
import logging
from datetime import date
from urllib.parse import unquote

import pytest

from pipeline.collect_commits import collect_commits, comparar
from pipeline.collect_releases import pares_com_anterior
from pipeline.selection import ApiError


class Resp:
    def __init__(self, corpo=None, headers=None, status=200):
        self._corpo = {} if corpo is None else corpo
        self.headers = headers or {}
        self.status_code = status

    def json(self):
        return self._corpo


class FakeClient:
    def __init__(self, fn):
        self._fn = fn
        self.chamadas: list[tuple[str, dict]] = []

    def get(self, path, params=None):
        params = dict(params or {})
        self.chamadas.append((path, params))
        return self._fn(path, params)


def commit(i, author_date="2025-03-01T00:00:00Z", committer_date=None, parents=1, message=None):
    """Item de `commits` do compare: o `author` de topo é o usuário do GitHub, sem data."""
    return {
        "sha": f"s{i}",
        "commit": {
            "author": {"name": "a", "date": author_date},
            "committer": {"name": "c", "date": committer_date or author_date},
            "message": message or f"msg {i}",
        },
        "author": {"login": "fulano", "id": 1},
        "committer": {"login": "beltrano", "id": 2},
        "parents": [{"sha": f"p{k}"} for k in range(parents)],
    }


def commits(n):
    return [commit(i) for i in range(n)]


def servidor(comparacoes, status=None, total=None, estado=None):
    """`comparacoes`: "base...head" -> commits; `status`: chave -> HTTP de erro; `total`: força total_commits;
    `estado`: chave -> `status` do compare (padrão "ahead")."""
    status = status or {}
    estado = estado or {}

    def fn(path, params):
        assert "/compare/" in path, f"path inesperado: {path}"
        chave = unquote(path.split("/compare/", 1)[1])
        if chave in status:
            return Resp({"message": "erro"}, status=status[chave])
        todos = comparacoes[chave]
        n, pp = int(params["page"]), int(params["per_page"])
        return Resp({
            "status": estado.get(chave, "ahead"),
            "total_commits": len(todos) if total is None else total,
            "commits": todos[(n - 1) * pp:n * pp],
            "files": [],
        })
    return FakeClient(fn)


def rel(tag, published_at="2025-03-01T00:00:00Z"):
    return {"tag_name": tag, "published_at": published_at, "draft": False, "prerelease": False, "id": 1, "created_at": published_at}


def paginas(client):
    return [p["page"] for _, p in client.chamadas]


# ---- comparar: paginação ----

def test_pagina_compare_com_mais_de_250_commits():
    c = servidor({"v1...v2": commits(320)})
    resultado = comparar(c, "org/repo", "v1", "v2")
    assert resultado["total_commits"] == 320
    assert len(resultado["commits"]) == 320
    assert [x["sha"] for x in resultado["commits"]] == [f"s{i}" for i in range(320)]
    assert resultado["truncado"] is False
    assert paginas(c) == [1, 2, 3, 4]
    assert all(p["per_page"] == 100 for _, p in c.chamadas)
    assert all(path == "/repos/org/repo/compare/v1...v2" for path, _ in c.chamadas)


def test_para_ao_atingir_total_sem_pedir_pagina_extra():
    c = servidor({"v1...v2": commits(200)})
    assert len(comparar(c, "org/repo", "v1", "v2")["commits"]) == 200
    assert paginas(c) == [1, 2]


def test_para_em_pagina_vazia_e_marca_truncado(caplog):
    c = servidor({"v1...v2": commits(150)}, total=500)
    with caplog.at_level(logging.WARNING, logger="pipeline.collect_commits"):
        resultado = comparar(c, "org/repo", "v1", "v2")
    assert len(resultado["commits"]) == 150
    assert resultado["truncado"] is True
    assert paginas(c) == [1, 2, 3]
    assert "truncada" in caplog.text


def test_release_sem_commits_novos_tem_lista_vazia():
    c = servidor({"v1...v2": []})
    resultado = comparar(c, "org/repo", "v1", "v2")
    assert resultado["status"] == "ok"
    assert resultado["total_commits"] == 0
    assert resultado["commits"] == []
    assert paginas(c) == [1]


def test_usa_commit_author_date_e_nao_o_author_de_topo():
    item = commit(7, "2025-03-02T10:00:00Z", "2025-03-05T08:00:00Z", parents=2, message="fix: crash\n\ncorpo")
    c = servidor({"v1...v2": [item]})
    assert comparar(c, "org/repo", "v1", "v2")["commits"] == [{
        "sha": "s7",
        "author_date": "2025-03-02T10:00:00Z",
        "committer_date": "2025-03-05T08:00:00Z",
        "message": "fix: crash\n\ncorpo",
        "n_parents": 2,
    }]


def test_codifica_caracteres_especiais_da_tag_no_path():
    c = servidor({"v1.0+build...release/v1.1 rc#1": commits(1)})
    comparar(c, "org/repo", "v1.0+build", "release/v1.1 rc#1")
    assert c.chamadas[0][0] == "/repos/org/repo/compare/v1.0%2Bbuild...release/v1.1%20rc%231"


# ---- comparar: erros ----

def test_404_devolve_none_e_loga(caplog):
    c = servidor({}, status={"v1...v2": 404})
    with caplog.at_level(logging.WARNING, logger="pipeline.collect_commits"):
        assert comparar(c, "org/repo", "v1", "v2") is None
    assert "v1...v2" in caplog.text and "404" in caplog.text


def test_outro_erro_sobe_como_api_error():
    c = servidor({}, status={"v1...v2": 500})
    with pytest.raises(ApiError) as exc:
        comparar(c, "org/repo", "v1", "v2")
    assert exc.value.status == 500


# ---- collect_commits ----

def test_404_ignora_a_release_conta_e_segue_com_as_demais(caplog):
    c = servidor({"v1...v2": commits(3), "v3...v4": commits(2)}, status={"v2...v3": 404})
    pares = [(rel("v1"), rel("v2")), (rel("v2"), rel("v3")), (rel("v3"), rel("v4"))]
    with caplog.at_level(logging.WARNING, logger="pipeline.collect_commits"):
        resultado = collect_commits(c, "org/repo", pares)
    assert [r["status"] for r in resultado["releases"]] == ["ok", "404", "ok"]
    assert resultado["releases"][1]["commits"] == []
    assert resultado["releases"][1]["total_commits"] is None
    assert [len(r["commits"]) for r in resultado["releases"]] == [3, 0, 2]
    assert resultado["n_releases_ignored_404"] == 1
    assert "v2...v3" in caplog.text


def test_conta_varios_404():
    c = servidor({"v3...v4": commits(1)}, status={"v1...v2": 404, "v2...v3": 404})
    pares = [(rel("v1"), rel("v2")), (rel("v2"), rel("v3")), (rel("v3"), rel("v4"))]
    assert collect_commits(c, "org/repo", pares)["n_releases_ignored_404"] == 2


def test_sem_anterior_nao_chama_a_api():
    c = servidor({"v1...v2": commits(1)})
    resultado = collect_commits(c, "org/repo", [(None, rel("v1")), (rel("v1"), rel("v2"))])
    assert [r["status"] for r in resultado["releases"]] == ["sem_anterior", "ok"]
    assert resultado["releases"][0]["base"] is None
    assert resultado["n_sem_anterior"] == 1
    assert resultado["n_releases_ignored_404"] == 0
    assert {path for path, _ in c.chamadas} == {"/repos/org/repo/compare/v1...v2"}


def test_campos_de_cada_release():
    c = servidor({"v1...v2": commits(2)})
    r = collect_commits(c, "org/repo", [(rel("v1"), rel("v2", "2025-04-10T12:00:00Z"))])["releases"][0]
    assert {k: v for k, v in r.items() if k != "commits"} == {
        "tag_name": "v2",
        "published_at": "2025-04-10T12:00:00Z",
        "base": "v1",
        "status": "ok",
        "status_compare": "ahead",
        "total_commits": 2,
        "truncado": False,
    }


def test_conta_releases_truncadas():
    c = servidor({"v1...v2": commits(10)}, total=50)
    assert collect_commits(c, "org/repo", [(rel("v1"), rel("v2"))])["n_truncadas"] == 1


def test_outro_erro_sobe_e_nao_grava_cache(tmp_path):
    c = servidor({"v1...v2": commits(1)}, status={"v2...v3": 403})
    pares = [(rel("v1"), rel("v2")), (rel("v2"), rel("v3"))]
    with pytest.raises(ApiError):
        collect_commits(c, "org/repo", pares, cache_dir=tmp_path)
    assert not (tmp_path / "commits").exists()


def test_integra_com_pares_de_collect_releases():
    releases = [
        rel("v1", "2024-11-01T00:00:00Z"),
        rel("v2", "2025-02-01T00:00:00Z"),
        rel("v3", "2025-06-01T00:00:00Z"),
    ]
    pares = pares_com_anterior(releases, date(2025, 1, 1), date(2025, 12, 31))
    c = servidor({"v1...v2": commits(2), "v2...v3": commits(4)})
    resultado = collect_commits(c, "org/repo", pares)
    assert [(r["base"], r["tag_name"], len(r["commits"])) for r in resultado["releases"]] == [("v1", "v2", 2), ("v2", "v3", 4)]


# ---- cache por repositório ----

def test_grava_json_por_repositorio_com_404(tmp_path):
    c = servidor({"v1...v2": commits(2)}, status={"v2...v3": 404})
    collect_commits(c, "Org/Repo", [(rel("v1"), rel("v2")), (rel("v2"), rel("v3"))], cache_dir=tmp_path)
    dados = json.loads((tmp_path / "commits" / "org__repo.json").read_text(encoding="utf-8"))
    assert dados["full_name"] == "Org/Repo"
    assert set(dados["comparacoes"]) == {"v1...v2", "v2...v3"}
    assert dados["comparacoes"]["v2...v3"]["status"] == "404"
    assert len(dados["comparacoes"]["v1...v2"]["commits"]) == 2
    assert "atualizado_em" in dados


def test_segunda_chamada_usa_cache_sem_chamar_api(tmp_path):
    c = servidor({"v1...v2": commits(2)}, status={"v2...v3": 404})
    pares = [(None, rel("v1")), (rel("v1"), rel("v2")), (rel("v2"), rel("v3"))]
    primeira = collect_commits(c, "org/repo", pares, cache_dir=tmp_path)
    n = len(c.chamadas)
    segunda = collect_commits(c, "org/repo", pares, cache_dir=tmp_path)
    assert segunda == primeira
    assert len(c.chamadas) == n


def test_par_novo_busca_so_o_que_falta(tmp_path):
    c = servidor({"v1...v2": commits(2), "v2...v3": commits(3)})
    collect_commits(c, "org/repo", [(rel("v1"), rel("v2"))], cache_dir=tmp_path)
    c.chamadas.clear()
    resultado = collect_commits(c, "org/repo", [(rel("v1"), rel("v2")), (rel("v2"), rel("v3"))], cache_dir=tmp_path)
    assert {path for path, _ in c.chamadas} == {"/repos/org/repo/compare/v2...v3"}
    assert [len(r["commits"]) for r in resultado["releases"]] == [2, 3]
    dados = json.loads((tmp_path / "commits" / "org__repo.json").read_text(encoding="utf-8"))
    assert set(dados["comparacoes"]) == {"v1...v2", "v2...v3"}


def test_sem_cache_dir_nao_grava_nada(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    collect_commits(servidor({"v1...v2": commits(1)}), "org/repo", [(rel("v1"), rel("v2"))])
    assert list(tmp_path.iterdir()) == []


def test_full_name_invalido(tmp_path):
    with pytest.raises(ValueError):
        collect_commits(servidor({}), "sem-barra", [], cache_dir=tmp_path)


# ---- status do compare (diverged, L06) ----

def test_compare_divergente_e_registrado_contado_e_mantido(caplog):
    c = servidor({"v1.9...v2.1": commits(3), "v2.1...v2.2": commits(1)}, estado={"v1.9...v2.1": "diverged"})
    pares = [(rel("v1.9"), rel("v2.1")), (rel("v2.1"), rel("v2.2"))]
    with caplog.at_level(logging.WARNING, logger="pipeline.collect_commits"):
        res = collect_commits(c, "org/repo", pares)
    assert [r["status_compare"] for r in res["releases"]] == ["diverged", "ahead"]
    assert res["n_divergentes"] == 1
    assert len(res["releases"][0]["commits"]) == 3  # continua no cálculo
    assert "divergente" in caplog.text


def test_status_compare_nulo_em_404_sem_anterior_e_cache_antigo(tmp_path):
    from pipeline.collect_releases import arquivo_cache
    arquivo = arquivo_cache(tmp_path, "org/repo", subpasta="commits")
    arquivo.parent.mkdir(parents=True)
    antigo = {"base": "v1", "head": "v2", "status": "ok", "total_commits": 0, "truncado": False, "commits": []}
    arquivo.write_text(json.dumps({"comparacoes": {"v1...v2": antigo}}), encoding="utf-8")
    c = servidor({}, status={"v2...v3": 404})
    res = collect_commits(c, "org/repo", [(None, rel("v1")), (rel("v1"), rel("v2")), (rel("v2"), rel("v3"))], tmp_path)
    assert [r["status_compare"] for r in res["releases"]] == [None, None, None]
    assert res["n_divergentes"] == 0
