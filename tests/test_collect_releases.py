"""Testes de pipeline.collect_releases (Issue #7) — releases sem corte de data + cache por repo."""

import json
from datetime import date

import pytest

from pipeline.collect_releases import (
    arquivo_cache,
    collect_releases,
    e_deploy,
    ordenar,
    pares_com_anterior,
)
from pipeline.selection import ApiError

INI = date(2025, 1, 1)
FIM = date(2025, 12, 31)
BASE = "https://api.github.com/repositories/1/releases"


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


def rel(tag, published_at, *, id=None, draft=False, prerelease=False, created_at=None, **extra):
    return {
        "id": id if id is not None else 0,
        "tag_name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "published_at": published_at,
        "created_at": created_at or published_at,
        "target_commitish": "main",
        "html_url": f"https://github.com/org/repo/releases/tag/{tag}",
        **extra,
    }


def link_next(pagina):
    return {"Link": f'<{BASE}?per_page=100&page={pagina}>; rel="next"'}


def cliente_paginas(*paginas):
    """Cada página aponta para a próxima via Link; a última não tem `next`."""
    def fn(path, params):
        n = int(params.get("page", 1))
        headers = link_next(n + 1) if n < len(paginas) else {}
        return Resp(paginas[n - 1], headers)
    return FakeClient(fn)


# ---- coleta ----

def test_extrai_campos_da_issue_mantem_body_e_descarta_o_resto():
    bruta = rel("v1.0", "2025-03-01T10:00:00Z", body="notas longas", author={"login": "x"})
    resultado = collect_releases(cliente_paginas([bruta]), "org/repo")
    assert len(resultado) == 1
    r = resultado[0]
    for campo in ("draft", "prerelease", "published_at", "tag_name"):
        assert campo in r
    # `body` (release notes) é mantido desde o refino pós-auditoria: a heurística v9+ depende dele
    assert r["body"] == "notas longas"
    assert "author" not in r
    assert r["tag_name"] == "v1.0"


def test_pagina_ate_o_fim_seguindo_link():
    p1 = [rel(f"v3.{i}", f"2025-06-{i + 1:02d}T00:00:00Z") for i in range(3)]
    p2 = [rel(f"v2.{i}", f"2025-03-{i + 1:02d}T00:00:00Z") for i in range(3)]
    p3 = [rel(f"v1.{i}", f"2024-01-{i + 1:02d}T00:00:00Z") for i in range(2)]
    client = cliente_paginas(p1, p2, p3)
    resultado = collect_releases(client, "org/repo")
    assert len(resultado) == 8
    assert len(client.chamadas) == 3
    assert client.chamadas[0] == ("/repos/org/repo/releases", {"per_page": 100})
    assert client.chamadas[2] == ("/repositories/1/releases", {"per_page": "100", "page": "3"})


def test_mantem_releases_anteriores_a_janela():
    antigas = [rel("v0.1", "2019-05-01T00:00:00Z"), rel("v0.2", "2024-12-31T23:59:59Z")]
    na_janela = [rel("v1.0", "2025-02-01T00:00:00Z")]
    resultado = collect_releases(cliente_paginas(na_janela + antigas), "org/repo")
    assert [r["tag_name"] for r in resultado] == ["v0.1", "v0.2", "v1.0"]


def test_ordena_por_published_at_independente_da_ordem_da_api():
    api = [
        rel("b", "2025-05-01T00:00:00Z"),
        rel("c", "2025-07-01T00:00:00Z"),
        rel("a", "2025-01-01T00:00:00Z"),
    ]
    resultado = collect_releases(cliente_paginas(api), "org/repo")
    assert [r["tag_name"] for r in resultado] == ["a", "b", "c"]


def test_mantem_draft_e_prerelease_com_flags():
    api = [
        rel("rc", "2025-04-01T00:00:00Z", prerelease=True),
        rel("rascunho", None, draft=True, created_at="2025-05-01T00:00:00Z"),
        rel("v1", "2025-03-01T00:00:00Z"),
    ]
    resultado = collect_releases(cliente_paginas(api), "org/repo")
    por_tag = {r["tag_name"]: r for r in resultado}
    assert por_tag["rc"]["prerelease"] is True
    assert por_tag["rascunho"]["draft"] is True
    assert resultado[-1]["tag_name"] == "rascunho"  # sem published_at vai para o fim


def test_erro_http_sobe_como_api_error(tmp_path):
    client = FakeClient(lambda path, params: Resp(status=404))
    with pytest.raises(ApiError):
        collect_releases(client, "org/sumiu", tmp_path)
    assert not arquivo_cache(tmp_path, "org/sumiu").exists()


def test_pagina_alem_de_1000_releases_sem_teto(tmp_path):
    # /releases não tem o teto de 1.000 da Search API (renovatebot/renovate: 122 páginas).
    paginas = [[rel(f"v{p}.{i}", "2025-01-01T00:00:00Z", id=p * 100 + i) for i in range(100)] for p in range(12)]
    client = cliente_paginas(*paginas)
    resultado = collect_releases(client, "org/grande", tmp_path)
    assert len(resultado) == 1200
    assert len(client.chamadas) == 12
    dados = json.loads(arquivo_cache(tmp_path, "org/grande").read_text(encoding="utf-8"))
    assert dados["total"] == 1200
    assert "truncado" not in dados


def test_cache_truncado_da_versao_antiga_e_recoletado(tmp_path, caplog):
    arquivo = arquivo_cache(tmp_path, "org/repo")
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text(json.dumps({"truncado": True, "releases": [rel("v9", "2025-01-01T00:00:00Z")]}), encoding="utf-8")
    client = cliente_paginas([rel("v1", "2024-01-01T00:00:00Z"), rel("v9", "2025-01-01T00:00:00Z")])
    resultado = collect_releases(client, "org/repo", tmp_path)
    assert [r["tag_name"] for r in resultado] == ["v1", "v9"]
    assert len(client.chamadas) == 1
    assert "truncado" in caplog.text
    assert "truncado" not in json.loads(arquivo.read_text(encoding="utf-8"))


# ---- cache por repositório ----

def test_grava_json_por_repositorio(tmp_path):
    collect_releases(cliente_paginas([rel("v1", "2025-01-01T00:00:00Z")]), "Org/Repo", tmp_path)
    arquivo = tmp_path / "releases" / "org__repo.json"
    assert arquivo.exists()
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert dados["full_name"] == "Org/Repo"
    assert dados["total"] == 1
    assert dados["releases"][0]["tag_name"] == "v1"
    assert not list(arquivo.parent.glob("*.tmp"))


def test_segunda_chamada_usa_cache_sem_chamar_api(tmp_path):
    primeira = collect_releases(cliente_paginas([rel("v1", "2025-01-01T00:00:00Z")]), "org/repo", tmp_path)
    client = FakeClient(lambda path, params: pytest.fail("não deveria chamar a API"))
    segunda = collect_releases(client, "ORG/repo", tmp_path)
    assert segunda == primeira
    assert client.chamadas == []


def test_sem_cache_dir_nao_grava_nada(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    collect_releases(cliente_paginas([rel("v1", "2025-01-01T00:00:00Z")]), "org/repo")
    assert list(tmp_path.iterdir()) == []


def test_arquivo_cache_com_outra_subpasta(tmp_path):
    assert arquivo_cache(tmp_path, "Org/Repo", "tags") == tmp_path / "tags" / "org__repo.json"


def test_full_name_invalido(tmp_path):
    with pytest.raises(ValueError):
        arquivo_cache(tmp_path, "sem-barra")


# ---- release anterior ----

def test_primeira_release_da_janela_tem_anterior_fora_da_janela():
    releases = [
        rel("v0.9", "2024-11-20T00:00:00Z"),
        rel("v1.0", "2025-02-01T00:00:00Z"),
        rel("v1.1", "2025-03-15T00:00:00Z"),
    ]
    pares = pares_com_anterior(releases, INI, FIM)
    assert [(a and a["tag_name"], r["tag_name"]) for a, r in pares] == [("v0.9", "v1.0"), ("v1.0", "v1.1")]
    assert pares[0][0]["published_at"] < "2025-01-01"


def test_repo_com_uma_release_nao_tem_anterior():
    pares = pares_com_anterior([rel("v1.0", "2025-02-01T00:00:00Z")], INI, FIM)
    assert len(pares) == 1
    assert pares[0][0] is None


def test_prerelease_e_draft_nao_sao_anterior_na_definicao_principal():
    releases = [
        rel("v1.0", "2025-01-10T00:00:00Z"),
        rel("v1.1-rc1", "2025-01-20T00:00:00Z", prerelease=True),
        rel("rascunho", None, draft=True),
        rel("v1.1", "2025-02-01T00:00:00Z"),
    ]
    pares = pares_com_anterior(releases, INI, FIM)
    assert [(a and a["tag_name"], r["tag_name"]) for a, r in pares] == [(None, "v1.0"), ("v1.0", "v1.1")]


def test_variante_com_prerelease_usa_pre_release_como_anterior():
    releases = [
        rel("v1.0", "2025-01-10T00:00:00Z"),
        rel("v1.1-rc1", "2025-01-20T00:00:00Z", prerelease=True),
        rel("v1.1", "2025-02-01T00:00:00Z"),
    ]
    pares = pares_com_anterior(releases, INI, FIM, incluir_prerelease=True)
    assert [r["tag_name"] for _, r in pares] == ["v1.0", "v1.1-rc1", "v1.1"]
    assert pares[2][0]["tag_name"] == "v1.1-rc1"


def test_limites_da_janela_sao_inclusivos_por_data():
    releases = [
        rel("antes", "2024-12-31T23:59:59Z"),
        rel("inicio", "2025-01-01T00:00:00Z"),
        rel("fim", "2025-12-31T23:59:59Z"),
        rel("depois", "2026-01-01T00:00:00Z"),
    ]
    pares = pares_com_anterior(releases, INI, FIM)
    assert [r["tag_name"] for _, r in pares] == ["inicio", "fim"]


def test_pares_aceita_lista_fora_de_ordem():
    releases = [rel("v2", "2025-06-01T00:00:00Z"), rel("v1", "2025-03-01T00:00:00Z")]
    pares = pares_com_anterior(releases, INI, FIM)
    assert pares[1][0]["tag_name"] == "v1"


def test_empate_em_published_at_desempata_por_created_at_e_id():
    mesma = "2025-05-01T00:00:00Z"
    releases = [
        rel("c", mesma, id=3, created_at="2025-04-30T00:00:00Z"),
        rel("b", mesma, id=2, created_at="2025-04-29T00:00:00Z"),
        rel("a", mesma, id=1, created_at="2025-04-29T00:00:00Z"),
    ]
    assert [r["tag_name"] for r in ordenar(releases)] == ["a", "b", "c"]


@pytest.mark.parametrize(
    "draft,prerelease,published,incluir,esperado",
    [
        (False, False, "2025-01-01T00:00:00Z", False, True),
        (True, False, None, False, False),
        (False, True, "2025-01-01T00:00:00Z", False, False),
        (False, True, "2025-01-01T00:00:00Z", True, True),
        (False, False, None, False, False),
    ],
)
def test_e_deploy(draft, prerelease, published, incluir, esperado):
    r = rel("x", published, draft=draft, prerelease=prerelease)
    assert e_deploy(r, incluir) is esperado
