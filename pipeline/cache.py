"""Cache em disco para respostas da API do GitHub (Issue #12).

Cada chamada `get(path, params)` é salva em JSON com chave determinística
(SHA-256 de path+params normalizados). Escrita atômica via arquivo temporário
seguida de rename. Reexecutar o pipeline após interrupção retoma de onde parou
sem repetir chamadas já em cache.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

log = logging.getLogger("pipeline.cache")


class CachedResponse:
    """Resposta reconstruída do cache; mesma interface de requests.Response."""

    def __init__(self, status_code: int, headers: dict, body):
        self.status_code = status_code
        self.headers = headers
        self._body = body

    def json(self):
        return self._body


class CachedHttpClient:
    """Wraps qualquer cliente com interface `get(path, params)`, adicionando cache em disco."""

    def __init__(self, client, cache_dir: Path):
        self._client = client
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._hits = 0
        self._misses = 0

    def estatisticas(self) -> dict:
        """Contadores desta instância: `cache_hits` (sem chamada HTTP) e `cache_misses` (chamadas à API)."""
        return {"cache_hits": self._hits, "cache_misses": self._misses}

    def get(self, path: str, params=None):
        arquivo = self._arquivo(path, params)
        if arquivo.exists():
            cacheada = _ler(arquivo)
            if _cacheavel(cacheada):  # ignora erros transitórios gravados por versões antigas
                log.debug("cache hit: %s", path)
                self._hits += 1
                return cacheada
        self._misses += 1
        resp = self._client.get(path, params)
        if _cacheavel(resp):
            _salvar(arquivo, resp)
        else:
            log.warning("resposta HTTP %s de %s não foi cacheada (será refeita na próxima execução)",
                        resp.status_code, path)
        return resp

    def paginar(self, path: str, params=None):
        """Itera todas as páginas cacheando cada uma individualmente."""
        from pipeline.http_client import _link_next

        resp = self.get(path, params)
        yield resp
        proxima = _link_next(resp.headers)
        while proxima:
            p = urlparse(proxima)
            resp = self.get(p.path, dict(parse_qsl(p.query)) or None)
            yield resp
            proxima = _link_next(resp.headers)

    def _arquivo(self, path: str, params) -> Path:
        return self._cache_dir / f"{_chave(path, params)}.json"


def _cacheavel(resp) -> bool:
    """Só 2xx e 404 (resultado estável, ex.: `compare` de tag apagada) vão para o disco.

    403/429 (rate limit), 5xx e demais erros são transitórios: gravá-los faria a retomada repetir o erro.
    """
    return 200 <= resp.status_code < 300 or resp.status_code == 404


def _chave(path: str, params) -> str:
    dados = json.dumps(
        {"path": path, "params": sorted((params or {}).items())},
        sort_keys=True,
    )
    return hashlib.sha256(dados.encode()).hexdigest()


def _salvar(arquivo: Path, resp) -> None:
    try:
        body = resp.json()
    except Exception:
        body = None
    conteudo = json.dumps(
        {"status_code": resp.status_code, "headers": dict(resp.headers), "body": body},
        ensure_ascii=False,
    )
    tmp = arquivo.with_suffix(".tmp")
    tmp.write_text(conteudo, encoding="utf-8")
    tmp.rename(arquivo)
    log.debug("cache salvo: %s", arquivo.name)


def _ler(arquivo: Path) -> CachedResponse:
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    return CachedResponse(
        status_code=dados["status_code"],
        headers=dados["headers"],
        body=dados["body"],
    )
