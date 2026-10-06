"""Testes de pipeline.collect_tags (Issue #8) — tags com a data do commit apontado + cache por repo."""

import json
import logging
from datetime import date

import pytest

from pipeline.collect_tags import collect_tags, ordenar, pares_com_anterior
from pipeline.selection import ApiError

INI = date(2025, 1, 1)
FIM = date(2025, 12, 31)
BASE = "https://api.github.com/repositories/1/tags"


class Resp:
    def __init__(self, corpo=None, headers=None, status=200):
        self._corpo = [] if corpo is None else corpo
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

    def commits_consultados(self):
        return [p for p, _ in self.chamadas if "/git/commits/" in p]


def tag(name, sha, **extra):
    return {
        "name": name,
        "commit": {"sha": sha, "url": f"https://api.github.com/repos/org/repo/commits/{sha}"},
        "zipball_url": "z",
        "tarball_url": "t",
        "node_id": "n",
        **extra,
    }


def commit(author_date, committer_date=None):
    return {
        "sha": "x",
        "author": {"name": "a", "date": author_date},
        "committer": {"name": "c", "date": committer_date or author_date},
        "message": "msg",
    }


def cliente(paginas, commits, status_commit=None):
    """`paginas`: lista de páginas de /tags (encadeadas por Link); `commits`: sha -> corpo de git/commits.

    SHA ausente de `commits` responde `status_commit` (padrão 404).
    """
    def fn(path, params):
        if path.endswith("/tags") or path.startswith("/repositories/"):
            n = int(params.get("page", 1))
            headers = {"Link": f'<{BASE}?per_page=100&page={n + 1}>; rel="next"'} if n < len(paginas) else {}
            return Resp(paginas[n - 1], headers)
        if "/git/commits/" in path:
            sha = path.rsplit("/", 1)[1]
            if sha in commits:
                return Resp(commits[sha])
            return Resp({"message": "Not Found"}, status=status_commit or 404)
        raise AssertionError(f"path inesperado: {path}")
    return FakeClient(fn)


# ---- coleta ----

def test_extrai_nome_sha_e_datas_e_descarta_o_resto():
    c = cliente([[tag("v1.0", "a1")]], {"a1": commit("2025-03-01T10:00:00Z", "2025-03-02T08:00:00Z")})
    resultado = collect_tags(c, "org/repo")
    assert resultado == [{
        "name": "v1.0",
        "sha": "a1",
        "data": "2025-03-01T10:00:00Z",
        "author_date": "2025-03-01T10:00:00Z",
        "committer_date": "2025-03-02T08:00:00Z",
    }]


def test_usa_git_commits_e_nao_commits_com_diff():
    c = cliente([[tag("v1.0", "a1")]], {"a1": commit("2025-03-01T10:00:00Z")})
    collect_tags(c, "org/repo")
    assert c.commits_consultados() == ["/repos/org/repo/git/commits/a1"]


def test_pagina_tags_seguindo_link():
    paginas = [[tag("v3", "c3")], [tag("v2", "c2")], [tag("v1", "c1")]]
    commits = {
        "c1": commit("2025-01-10T00:00:00Z"),
        "c2": commit("2025-02-10T00:00:00Z"),
        "c3": commit("2025-03-10T00:00:00Z"),
    }
    resultado = collect_tags(cliente(paginas, commits), "org/repo")
    assert [t["name"] for t in resultado] == ["v1", "v2", "v3"]


def test_consulta_cada_sha_uma_unica_vez():
    tags = [tag("v1.0", "a1"), tag("latest", "a1"), tag("stable", "a1"), tag("v0.9", "b2")]
    c = cliente([tags], {"a1": commit("2025-03-01T00:00:00Z"), "b2": commit("2025-02-01T00:00:00Z")})
    resultado = collect_tags(c, "org/repo")
    assert len(resultado) == 4
    assert sorted(c.commits_consultados()) == ["/repos/org/repo/git/commits/a1", "/repos/org/repo/git/commits/b2"]


def test_ordena_por_data_e_nao_pela_ordem_da_api():
    # A API ordena por nome; "v10" viria antes de "v9" mesmo sendo posterior.
    tags = [tag("v9", "s9"), tag("v10", "s10"), tag("v1", "s1")]
    commits = {
        "s1": commit("2024-06-01T00:00:00Z"),
        "s9": commit("2025-05-01T00:00:00Z"),
        "s10": commit("2025-07-01T00:00:00Z"),
    }
    resultado = collect_tags(cliente([tags], commits), "org/repo")
    assert [t["name"] for t in resultado] == ["v1", "v9", "v10"]


def test_commit_inexistente_fica_sem_data_e_a_coleta_segue(caplog):
    c = cliente([[tag("v2", "ok"), tag("v1", "sumiu")]], {"ok": commit("2025-04-01T00:00:00Z")})
    with caplog.at_level(logging.WARNING, logger="pipeline.collect_tags"):
        resultado = collect_tags(c, "org/repo")
    assert [t["name"] for t in resultado] == ["v2", "v1"]  # sem data vai para o fim
    assert resultado[1]["data"] is None and resultado[1]["committer_date"] is None
    assert "sumiu" in caplog.text


def test_commit_422_tambem_fica_sem_data():
    c = cliente([[tag("v1", "ruim")]], {}, status_commit=422)
    assert collect_tags(c, "org/repo")[0]["data"] is None


def test_outro_erro_no_commit_sobe_como_api_error(tmp_path):
    c = cliente([[tag("v1", "x")]], {}, status_commit=403)
    with pytest.raises(ApiError):
        collect_tags(c, "org/repo", cache_dir=tmp_path)
    assert not (tmp_path / "tags").exists()


def test_erro_http_em_tags_sobe_como_api_error(tmp_path):
    c = FakeClient(lambda path, params: Resp({"message": "Not Found"}, status=404))
    with pytest.raises(ApiError):
        collect_tags(c, "org/repo", cache_dir=tmp_path)
    assert not (tmp_path / "tags").exists()


def test_repo_sem_tags_devolve_lista_vazia():
    c = cliente([[]], {})
    assert collect_tags(c, "org/repo") == []
    assert c.commits_consultados() == []


# ---- cache por repositório ----

def test_grava_json_por_repositorio(tmp_path):
    c = cliente([[tag("v1", "a"), tag("v0", "sumiu")]], {"a": commit("2025-03-01T00:00:00Z")})
    collect_tags(c, "Org/Repo", cache_dir=tmp_path)
    arquivo = tmp_path / "tags" / "org__repo.json"
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert dados["full_name"] == "Org/Repo"
    assert dados["total"] == 2
    assert dados["sem_data"] == 1
    assert [t["name"] for t in dados["tags"]] == ["v1", "v0"]
    assert "coletado_em" in dados


def test_segunda_chamada_usa_cache_sem_chamar_api(tmp_path):
    c = cliente([[tag("v1", "a")]], {"a": commit("2025-03-01T00:00:00Z")})
    primeira = collect_tags(c, "org/repo", cache_dir=tmp_path)
    n = len(c.chamadas)
    segunda = collect_tags(c, "org/repo", cache_dir=tmp_path)
    assert segunda == primeira
    assert len(c.chamadas) == n


def test_sem_cache_dir_nao_grava_nada(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    collect_tags(cliente([[tag("v1", "a")]], {"a": commit("2025-03-01T00:00:00Z")}), "org/repo")
    assert list(tmp_path.iterdir()) == []


def test_full_name_invalido(tmp_path):
    with pytest.raises(ValueError):
        collect_tags(cliente([[]], {}), "sem-barra", cache_dir=tmp_path)


# ---- ordenação ----

def t(name, author, committer=None):
    return {"name": name, "sha": name, "data": author, "author_date": author, "committer_date": committer or author}


def test_empate_de_data_desempata_por_committer_e_nome():
    mesmo = "2025-03-01T00:00:00Z"
    tags = [
        t("b", mesmo, "2025-03-05T00:00:00Z"),
        t("z", mesmo, "2025-03-02T00:00:00Z"),
        t("a", mesmo, "2025-03-05T00:00:00Z"),
    ]
    assert [x["name"] for x in ordenar(tags)] == ["z", "a", "b"]


def test_ordenar_compara_instantes_e_nao_texto():
    # Mesmo instante em fusos diferentes; o texto "+02:00" ordenaria errado.
    tags = [t("depois", "2025-03-01T11:00:00+02:00"), t("antes", "2025-03-01T08:00:00Z")]
    assert [x["name"] for x in ordenar(tags)] == ["antes", "depois"]


# ---- pares (anterior, T) ----

def test_primeira_tag_da_janela_tem_anterior_fora_da_janela():
    tags = [t("v1", "2024-11-01T00:00:00Z"), t("v2", "2025-02-01T00:00:00Z"), t("v3", "2025-06-01T00:00:00Z")]
    pares = pares_com_anterior(tags, INI, FIM)
    assert [(a and a["name"], x["name"]) for a, x in pares] == [("v1", "v2"), ("v2", "v3")]


def test_repo_com_uma_tag_nao_tem_anterior():
    pares = pares_com_anterior([t("v1", "2025-03-01T00:00:00Z")], INI, FIM)
    assert pares == [(None, pares[0][1])]
    assert pares[0][1]["name"] == "v1"


def test_limites_da_janela_sao_inclusivos_por_data():
    tags = [
        t("antes", "2024-12-31T23:59:59Z"),
        t("inicio", "2025-01-01T00:00:00Z"),
        t("fim", "2025-12-31T23:59:59Z"),
        t("depois", "2026-01-01T00:00:00Z"),
    ]
    assert [x["name"] for _, x in pares_com_anterior(tags, INI, FIM)] == ["inicio", "fim"]


def test_tags_sem_data_ficam_fora_dos_pares_e_nao_viram_anterior():
    tags = [t("v1", "2025-02-01T00:00:00Z"), {**t("orfa", None), "data": None}, t("v2", "2025-03-01T00:00:00Z")]
    pares = pares_com_anterior(tags, INI, FIM)
    assert [(a and a["name"], x["name"]) for a, x in pares] == [(None, "v1"), ("v1", "v2")]


def test_pares_aceita_lista_fora_de_ordem():
    tags = [t("v3", "2025-06-01T00:00:00Z"), t("v1", "2025-02-01T00:00:00Z"), t("v2", "2025-04-01T00:00:00Z")]
    assert [x["name"] for _, x in pares_com_anterior(tags, INI, FIM)] == ["v1", "v2", "v3"]
