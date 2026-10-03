"""Testes do pipeline.cache (Issue #12) — cache em disco, escrita atômica e retomada."""

import json

import pytest

from pipeline.cache import CachedHttpClient, _chave


class Resp:
    def __init__(self, dados=None, headers=None, status=200):
        self.status_code = status
        self.headers = headers or {}
        self._dados = dados if dados is not None else {}

    def json(self):
        return self._dados


class FakeClient:
    def __init__(self, respostas):
        self._respostas = iter(respostas)
        self.chamadas: list[tuple[str, object]] = []

    def get(self, path, params=None):
        self.chamadas.append((path, params))
        return next(self._respostas)


# ---- cache miss/hit ----

def test_cache_miss_busca_no_cliente(tmp_path):
    client = FakeClient([Resp({"a": 1})])
    cc = CachedHttpClient(client, tmp_path)
    resp = cc.get("/repos/o/r")
    assert resp.status_code == 200
    assert resp.json() == {"a": 1}
    assert len(client.chamadas) == 1


def test_cache_hit_nao_chama_o_cliente(tmp_path):
    client = FakeClient([Resp({"a": 1})])
    cc = CachedHttpClient(client, tmp_path)
    cc.get("/repos/o/r")          # miss → salva
    resp2 = cc.get("/repos/o/r")  # hit → não chama client
    assert len(client.chamadas) == 1
    assert resp2.json() == {"a": 1}


def test_cache_preserva_status_code_e_headers(tmp_path):
    client = FakeClient([Resp({"x": 2}, headers={"Link": "next"}, status=200)])
    cc = CachedHttpClient(client, tmp_path)
    cc.get("/path")
    resp = cc.get("/path")  # hit
    assert resp.status_code == 200
    assert resp.headers["Link"] == "next"
    assert resp.json() == {"x": 2}


def test_params_diferentes_geram_entradas_distintas(tmp_path):
    client = FakeClient([Resp({"p": 1}), Resp({"p": 2})])
    cc = CachedHttpClient(client, tmp_path)
    cc.get("/path", {"page": "1"})
    cc.get("/path", {"page": "2"})
    assert len(client.chamadas) == 2


def test_params_iguais_em_ordem_diferente_mesmo_cache(tmp_path):
    client = FakeClient([Resp({"ok": True})])
    cc = CachedHttpClient(client, tmp_path)
    cc.get("/path", {"b": "2", "a": "1"})
    cc.get("/path", {"a": "1", "b": "2"})  # deve ser cache hit
    assert len(client.chamadas) == 1


# ---- escrita atômica ----

def test_arquivo_tmp_nao_fica_no_disco_apos_escrita(tmp_path):
    client = FakeClient([Resp({})])
    CachedHttpClient(client, tmp_path).get("/path")
    tmps = list(tmp_path.glob("*.tmp"))
    assert tmps == []


def test_arquivo_json_criado_no_cache_dir(tmp_path):
    client = FakeClient([Resp({"y": 3})])
    CachedHttpClient(client, tmp_path).get("/path")
    jsons = list(tmp_path.glob("*.json"))
    assert len(jsons) == 1
    dados = json.loads(jsons[0].read_text())
    assert dados["body"] == {"y": 3} and dados["status_code"] == 200


# ---- interrupção e retomada ----

def test_interrupcao_retomada(tmp_path):
    """Simula pipeline interrompido: segunda execução só busca o que falta."""
    # Fase 1: duas chamadas feitas, uma terceira nunca chegou (interrupção)
    client1 = FakeClient([Resp({"r": 1}), Resp({"r": 2})])
    cc1 = CachedHttpClient(client1, tmp_path)
    cc1.get("/repos/A")
    cc1.get("/repos/B")
    assert len(client1.chamadas) == 2

    # Fase 2: novo cliente com mesmo cache_dir; /A e /B já em cache; /C precisa buscar
    client2 = FakeClient([Resp({"r": 3})])
    cc2 = CachedHttpClient(client2, tmp_path)
    cc2.get("/repos/A")   # cache hit
    cc2.get("/repos/B")   # cache hit
    cc2.get("/repos/C")   # cache miss → busca

    assert len(client2.chamadas) == 1
    assert client2.chamadas[0][0] == "/repos/C"


def test_retomada_devolve_mesmo_conteudo(tmp_path):
    client1 = FakeClient([Resp({"dado": "original"})])
    CachedHttpClient(client1, tmp_path).get("/ep")

    client2 = FakeClient([])
    resp = CachedHttpClient(client2, tmp_path).get("/ep")
    assert resp.json() == {"dado": "original"}


# ---- paginação cacheada ----

def test_paginar_cacheia_cada_pagina(tmp_path):
    link = '<https://api.github.com/res?page=2>; rel="next"'
    client = FakeClient([
        Resp([1, 2], headers={"Link": link}),
        Resp([3, 4]),
    ])
    cc = CachedHttpClient(client, tmp_path)
    paginas = list(cc.paginar("/res"))
    assert [p.json() for p in paginas] == [[1, 2], [3, 4]]

    # segunda execução: zero chamadas ao client
    client2 = FakeClient([])
    cc2 = CachedHttpClient(client2, tmp_path)
    paginas2 = list(cc2.paginar("/res"))
    assert [p.json() for p in paginas2] == [[1, 2], [3, 4]]


# ---- chave determinística ----

def test_chave_e_deterministica():
    assert _chave("/path", {"a": "1"}) == _chave("/path", {"a": "1"})


def test_chave_depende_do_path():
    assert _chave("/a", {}) != _chave("/b", {})


def test_chave_depende_dos_params():
    assert _chave("/p", {"x": "1"}) != _chave("/p", {"x": "2"})


def test_chave_sem_params_e_estavel():
    assert _chave("/path", None) == _chave("/path", {})
