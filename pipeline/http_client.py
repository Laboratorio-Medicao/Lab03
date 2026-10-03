"""Cliente HTTP para a API REST do GitHub (Issue #11).

Responsabilidades:
- rate limit: lê X-RateLimit-Remaining/Reset e aguarda automaticamente;
- 5xx: retry com backoff exponencial (1, 2, 4, 8 … s) até MAX_TENTATIVAS;
- paginação: segue Link rel="next" via método `paginar`;
- token: recebido no construtor (obtido de variável de ambiente por pipeline.config).
"""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import parse_qsl, urlparse

import requests

BASE_URL = "https://api.github.com"
MAX_TENTATIVAS = 5

log = logging.getLogger("pipeline.http_client")

_RE_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


class HttpClient:
    def __init__(self, token: str, *, base_url: str = BASE_URL, _sleep=time.sleep):
        self._base_url = base_url.rstrip("/")
        self._sleep = _sleep
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def get(self, path: str, params=None):
        """GET em `path` (ex.: `/repos/org/repo/releases`) com rate limit e backoff."""
        url = self._base_url + path
        return self._fetch(url, params)

    def paginar(self, path: str, params=None):
        """Gerador que itera todas as páginas de um endpoint seguindo Link rel="next"."""
        resp = self.get(path, params)
        yield resp
        proxima = _link_next(resp.headers)
        while proxima:
            resp = self._fetch(proxima, params=None)
            yield resp
            proxima = _link_next(resp.headers)

    def _fetch(self, url: str, params=None):
        atraso = 1
        resp = None
        for tentativa in range(MAX_TENTATIVAS):
            resp = self._session.get(url, params=params)
            self._checar_rate_limit(resp)
            if not (500 <= resp.status_code < 600):
                return resp
            if tentativa < MAX_TENTATIVAS - 1:
                log.warning(
                    "HTTP %d em %s (tentativa %d/%d), aguardando %ds",
                    resp.status_code, url, tentativa + 1, MAX_TENTATIVAS, atraso,
                )
                self._sleep(atraso)
                atraso *= 2
        return resp

    def _checar_rate_limit(self, resp) -> None:
        remaining = int(resp.headers.get("X-RateLimit-Remaining", 1))
        if remaining == 0:
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            espera = max(reset - time.time(), 1)
            log.warning("rate limit atingido, aguardando %.0fs", espera)
            self._sleep(espera)


def _link_next(headers) -> str | None:
    m = _RE_LINK_NEXT.search(headers.get("Link", ""))
    return m.group(1) if m else None
