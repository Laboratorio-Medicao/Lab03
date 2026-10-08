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
TIMEOUT_S = 30  # sem timeout, uma conexão perdida trava a execução para sempre
MAX_TENTATIVAS = 5
MAX_ESPERAS_RATE_LIMIT = 10

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
        """GET com: backoff exponencial em 5xx e erros de rede, e espera automática de rate limit.

        - 5xx / erro de rede: espera 1, 2, 4, 8… s, até MAX_TENTATIVAS;
        - 403/429 por rate limit (`X-RateLimit-Remaining: 0` ou `Retry-After`): espera e repete,
          até MAX_ESPERAS_RATE_LIMIT vezes; um 403 comum (sem esses sinais) é devolvido;
        - resposta que zerou a cota (`remaining=0`): espera o reset antes da próxima chamada.
        """
        atraso = 1
        tentativa = 0
        esperas_rate_limit = 0
        while True:
            try:
                resp = self._session.get(url, params=params, timeout=TIMEOUT_S)
            except (requests.ConnectionError, requests.Timeout) as exc:
                tentativa += 1
                if tentativa >= MAX_TENTATIVAS:
                    raise
                log.warning("erro de rede em %s (%s) (tentativa %d/%d), aguardando %ds",
                            url, type(exc).__name__, tentativa, MAX_TENTATIVAS, atraso)
                self._sleep(atraso)
                atraso *= 2
                continue

            if resp.status_code in (403, 429):
                espera = _espera_rate_limit(resp.headers)
                if espera is not None and esperas_rate_limit < MAX_ESPERAS_RATE_LIMIT:
                    esperas_rate_limit += 1
                    self._aguardar(espera, resp.headers)
                    continue
                return resp

            self._checar_rate_limit(resp)
            if not (500 <= resp.status_code < 600):
                return resp
            tentativa += 1
            if tentativa >= MAX_TENTATIVAS:
                return resp
            log.warning(
                "HTTP %d em %s (tentativa %d/%d), aguardando %ds",
                resp.status_code, url, tentativa, MAX_TENTATIVAS, atraso,
            )
            self._sleep(atraso)
            atraso *= 2

    def _checar_rate_limit(self, resp) -> None:
        """Cota zerada numa resposta de sucesso: espera o reset antes da próxima chamada."""
        if _remaining(resp.headers) == 0:
            self._aguardar(_espera_rate_limit(resp.headers) or 60, resp.headers)

    def _aguardar(self, espera: float, headers) -> None:
        reset = headers.get("X-RateLimit-Reset")
        ate = f"até {reset} (epoch)" if reset else f"por {espera:.0f}s"
        log.warning("rate limit: aguardando %s (%.0fs)", ate, espera)
        self._sleep(espera)


def _remaining(headers) -> int | None:
    valor = headers.get("X-RateLimit-Remaining")
    try:
        return int(valor) if valor is not None else None
    except ValueError:
        return None


def _espera_rate_limit(headers) -> float | None:
    """Segundos a esperar se os cabeçalhos indicam rate limit; None caso contrário."""
    retry_after = headers.get("Retry-After")
    if retry_after is not None:
        try:
            return max(float(retry_after), 1.0)
        except ValueError:
            pass
    if _remaining(headers) == 0:
        try:
            reset = float(headers.get("X-RateLimit-Reset"))
        except (TypeError, ValueError):
            return 60.0
        return max(reset - time.time(), 1.0) + 1  # +1 s de folga: o reset é por segundo inteiro
    return None


def _link_next(headers) -> str | None:
    m = _RE_LINK_NEXT.search(headers.get("Link", ""))
    return m.group(1) if m else None
