"""Testes do pipeline.http_client (Issue #11) — rate limit, backoff e paginação."""

import time

import pytest

from pipeline.http_client import HttpClient, _link_next


class Resp:
    def __init__(self, dados=None, headers=None, status=200):
        self.status_code = status
        self.headers = headers or {}
        self._dados = dados if dados is not None else {}

    def json(self):
        return self._dados


class FakeSession:
    """Sessão fake: devolve respostas pré-programadas em sequência e registra chamadas."""

    def __init__(self, respostas):
        self._respostas = iter(respostas)
        self.chamadas: list[tuple[str, dict | None]] = []

    def get(self, url, params=None):
        self.chamadas.append((url, params))
        return next(self._respostas)

    def headers(self):
        return {}


def _cliente(respostas, sleeps=None):
    """Cria HttpClient com sessão fake; os atrasos são acumulados em `sleeps`."""
    registros: list[float] = [] if sleeps is None else sleeps
    client = HttpClient("token-falso", _sleep=registros.append)
    client._session = FakeSession(respostas)
    return client, registros


# ---- rate limit ----

def test_rate_limit_restante_zero_aguarda_ate_reset():
    reset = int(time.time() + 30)
    resp = Resp(status=200, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset)})
    client, sleeps = _cliente([resp])
    client.get("/repos/o/r")
    assert len(sleeps) == 1
    assert sleeps[0] >= 1


def test_rate_limit_restante_positivo_nao_aguarda():
    resp = Resp(status=200, headers={"X-RateLimit-Remaining": "100"})
    client, sleeps = _cliente([resp])
    client.get("/repos/o/r")
    assert sleeps == []


def test_rate_limit_sem_cabecalho_nao_aguarda():
    client, sleeps = _cliente([Resp(status=200)])
    client.get("/repos/o/r")
    assert sleeps == []


# ---- backoff exponencial (500, 500, 200) ----

def test_retry_500_500_200_retorna_200():
    respostas = [Resp(status=500), Resp(status=500), Resp(status=200, dados={"ok": True})]
    client, _ = _cliente(respostas)
    resp = client.get("/path")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_retry_500_500_200_aplica_backoff_exponencial():
    respostas = [Resp(status=500), Resp(status=500), Resp(status=200)]
    client, sleeps = _cliente(respostas)
    client.get("/path")
    assert sleeps == [1, 2]


def test_retry_esgota_tentativas_retorna_ultima_resposta():
    respostas = [Resp(status=503)] * 5
    client, sleeps = _cliente(respostas)
    resp = client.get("/path")
    assert resp.status_code == 503
    assert len(sleeps) == MAX_TENTATIVAS - 1


def test_sem_5xx_nao_retenta():
    client, sleeps = _cliente([Resp(status=200)])
    client.get("/path")
    assert sleeps == []


def test_4xx_nao_retenta():
    client, sleeps = _cliente([Resp(status=404)])
    resp = client.get("/path")
    assert resp.status_code == 404
    assert sleeps == []


def test_503_retenta_com_backoff_duplo():
    respostas = [Resp(status=503), Resp(status=503), Resp(status=503), Resp(status=200)]
    client, sleeps = _cliente(respostas)
    resp = client.get("/path")
    assert resp.status_code == 200
    assert sleeps == [1, 2, 4]


# ---- paginação via Link ----

def test_paginar_segue_link_next():
    link = '<https://api.github.com/repos/o/r/releases?page=2>; rel="next"'
    respostas = [
        Resp(dados={"items": [1, 2]}, headers={"Link": link}),
        Resp(dados={"items": [3]}),
    ]
    client, _ = _cliente(respostas)
    paginas = list(client.paginar("/repos/o/r/releases"))
    assert len(paginas) == 2
    assert paginas[0].json()["items"] == [1, 2]
    assert paginas[1].json()["items"] == [3]


def test_paginar_sem_link_next_retorna_uma_pagina():
    client, _ = _cliente([Resp(dados={"items": [1, 2, 3]})])
    paginas = list(client.paginar("/repos/o/r/releases"))
    assert len(paginas) == 1


def test_paginar_tres_paginas():
    def link(pagina):
        return {"Link": f'<https://api.github.com/res?page={pagina}>; rel="next"'}

    respostas = [
        Resp(dados=[1], headers=link(2)),
        Resp(dados=[2], headers=link(3)),
        Resp(dados=[3]),
    ]
    client, _ = _cliente(respostas)
    todos = [p.json() for p in client.paginar("/res")]
    assert todos == [[1], [2], [3]]


# ---- helper _link_next ----

def test_link_next_extrai_url_de_cabecalho_composto():
    headers = {"Link": '<https://api.github.com/page=2>; rel="next", <https://api.github.com/page=5>; rel="last"'}
    assert _link_next(headers) == "https://api.github.com/page=2"


def test_link_next_sem_next_retorna_none():
    assert _link_next({"Link": '<https://api.github.com/page=5>; rel="last"'}) is None
    assert _link_next({}) is None


def test_link_next_aceita_aspas_simples():
    headers = {"Link": "<https://api.github.com/page=2>; rel='next'"}
    # o padrão do GitHub usa aspas duplas; aspas simples não devem ser reconhecidas
    assert _link_next(headers) is None


# ---- integração: token passado nos headers ----

def test_token_enviado_no_header_authorization():
    client = HttpClient("meu-token-secreto")
    assert "Authorization" in client._session.headers
    assert "meu-token-secreto" in client._session.headers["Authorization"]


# ---- constante usada nos testes de esgotamento ----

from pipeline.http_client import MAX_TENTATIVAS


# ---- auditoria S01 (P4): rate limit em 403/429, erros de rede, log com epoch ----

def test_403_com_cota_zerada_espera_e_repete():
    reset = int(time.time() + 30)
    respostas = [
        Resp(status=403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset)}),
        Resp(status=200, dados={"ok": True}),
    ]
    client, sleeps = _cliente(respostas)
    resp = client.get("/x")
    assert resp.status_code == 200
    assert len(sleeps) == 1 and 25 <= sleeps[0] <= 35


def test_429_com_retry_after_espera_e_repete():
    client, sleeps = _cliente([Resp(status=429, headers={"Retry-After": "10"}), Resp(status=200)])
    assert client.get("/x").status_code == 200
    assert sleeps == [10.0]


def test_403_comum_sem_sinal_de_rate_limit_e_devolvido(  ):
    client, sleeps = _cliente([Resp(status=403, headers={"X-RateLimit-Remaining": "50"})])
    assert client.get("/x").status_code == 403
    assert sleeps == []


def test_rate_limit_persistente_desiste_no_limite_de_esperas():
    from pipeline.http_client import MAX_ESPERAS_RATE_LIMIT
    resp = lambda: Resp(status=429, headers={"Retry-After": "1"})
    client, sleeps = _cliente([resp() for _ in range(MAX_ESPERAS_RATE_LIMIT + 1)])
    assert client.get("/x").status_code == 429
    assert len(sleeps) == MAX_ESPERAS_RATE_LIMIT


def test_log_informa_epoch_do_reset(caplog):
    import logging
    reset = int(time.time() + 30)
    client, _ = _cliente([Resp(status=200, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset)})])
    with caplog.at_level(logging.WARNING):
        client.get("/x")
    assert f"aguardando até {reset}" in caplog.text


def test_erro_de_rede_usa_backoff_e_recupera():
    import requests

    class Sessao:
        def __init__(self):
            self.n = 0

        def get(self, url, params=None):
            self.n += 1
            if self.n < 3:
                raise requests.ConnectionError("rede")
            return Resp(status=200)

    client, sleeps = _cliente([])
    client._session = Sessao()
    assert client.get("/x").status_code == 200
    assert sleeps == [1, 2]


def test_erro_de_rede_persistente_propaga_apos_limite():
    import requests

    class Sessao:
        def get(self, url, params=None):
            raise requests.Timeout("lento")

    client, sleeps = _cliente([])
    client._session = Sessao()
    with pytest.raises(requests.Timeout):
        client.get("/x")
    assert sleeps == [1, 2, 4, 8]
