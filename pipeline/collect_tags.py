"""Coleta de tags por repositório (Issue #8) — unidade de deploy da combinação C3 da RQ07.

`GET /repos/{owner}/{repo}/tags` devolve só `name` e `commit.sha`: tags **não trazem data**
(E§4). A data da tag é a do commit apontado, lida em `GET /repos/{owner}/{repo}/git/commits/{sha}`
(resposta pequena, só autor/committer; `commits/{sha}` traria também o diff). A data usada é
`author.date`, a mesma regra de "data de um commit" de E§3; `committer.date` é guardada para
desempate e análise de sensibilidade. Cada SHA distinto é consultado uma única vez.

Sem corte de data, como em `collect_releases`: a tag anterior à 1ª tag da janela é a base do
`compare` do lead time (b) da C3. Todas as tags entram, inclusive as que têm release e as que
apontam para commits fora do default branch (as releases também não filtram por branch, L06).

Commit não encontrado (404/422, tag apontando para commit apagado/reescrito): a tag fica com
`data=None`, é contada em `sem_data` e fica fora de `pares_com_anterior` (NÃO DEFINIDO NA FONTE
DA VERDADE). Erro em `/tags` sobe como `ApiError` e nada é gravado.

Como `/releases`, `/tags` não para nos 1.000 primeiros resultados (conferido em
kubernetes/kubernetes: a página 11 com `per_page=100` traz dados), então a paginação vai até o
fim. Custo: 1 chamada por página de tags + 1 por commit distinto (repositórios com milhares de
tags custam milhares de chamadas na 1ª coleta; depois tudo vem do cache).

Cache em JSON por repositório em `<cache>/tags/<owner>__<repo>.json`.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline.collect_releases import _instante, _salvar, arquivo_cache
from pipeline.selection import POR_PAGINA, ApiError, _data, _destino, _get, _link

log = logging.getLogger("pipeline.collect_tags")

SUBPASTA_CACHE = "tags"
STATUS_COMMIT_AUSENTE = frozenset({404, 422})


def collect_tags(client, full_name: str, cache_dir: Path | None = None) -> list[dict]:
    """Todas as tags de `full_name` com a data do commit apontado, ordenadas por data (sem data no fim).

    Cada tag: `{"name", "sha", "data", "author_date", "committer_date"}` (`data` = `author_date`).
    Com `cache_dir`, lê o JSON do repositório se existir (sem chamar a API) ou o grava após a coleta.
    """
    arquivo = arquivo_cache(cache_dir, full_name, subpasta=SUBPASTA_CACHE) if cache_dir is not None else None
    if arquivo is not None and arquivo.exists():
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        log.info("%s: %d tags (cache)", full_name, len(dados["tags"]))
        return dados["tags"]

    brutas = _paginar_tags(client, full_name)
    datas: dict[str, tuple[str | None, str | None]] = {}
    for t in brutas:
        sha = t["commit"]["sha"]
        if sha not in datas:
            datas[sha] = _datas_do_commit(client, full_name, sha)

    tags = []
    for t in brutas:
        autor, committer = datas[t["commit"]["sha"]]
        tags.append({
            "name": t["name"],
            "sha": t["commit"]["sha"],
            "data": autor,
            "author_date": autor,
            "committer_date": committer,
        })
    tags = ordenar(tags)
    sem_data = sum(1 for t in tags if t["data"] is None)
    if sem_data:
        log.warning("%s: %d tags sem data (commit não encontrado); ficam fora dos pares", full_name, sem_data)
    log.info("%s: %d tags coletadas (%d commits consultados, %d sem data)", full_name, len(tags), len(datas), sem_data)

    if arquivo is not None:
        _salvar(arquivo, {
            "full_name": full_name,
            "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "total": len(tags),
            "sem_data": sem_data,
            "tags": tags,
        })
    return tags


def _paginar_tags(client, full_name: str) -> list[dict]:
    """Segue `Link: rel="next"` até o fim."""
    resp = _get(client, f"/repos/{full_name}/tags", {"per_page": POR_PAGINA})
    itens: list[dict] = list(resp.json())
    proxima = _link(resp.headers, "next")
    while proxima:
        caminho, parametros = _destino(proxima)
        resp = _get(client, caminho, parametros)
        itens.extend(resp.json())
        proxima = _link(resp.headers, "next")
    return itens


def _datas_do_commit(client, full_name: str, sha: str) -> tuple[str | None, str | None]:
    """(author.date, committer.date) do commit; (None, None) se o commit não existe mais."""
    try:
        corpo = _get(client, f"/repos/{full_name}/git/commits/{sha}").json()
    except ApiError as exc:
        if exc.status not in STATUS_COMMIT_AUSENTE:
            raise
        log.warning("%s: commit %s da tag não encontrado (HTTP %d)", full_name, sha, exc.status)
        return None, None
    return (corpo.get("author") or {}).get("date"), (corpo.get("committer") or {}).get("date")


def ordenar(tags: list[dict]) -> list[dict]:
    """Por `author_date` crescente; empate por `committer_date` e `name`; sem data no fim."""
    minimo = datetime.min.replace(tzinfo=timezone.utc)

    def chave(t: dict):
        autor = _instante(t.get("author_date"))
        return (
            autor is None,
            autor or minimo,
            _instante(t.get("committer_date")) or minimo,
            t.get("name") or "",
        )

    return sorted(tags, key=chave)


def pares_com_anterior(tags: list[dict], inicio: date, fim: date) -> list[tuple[dict | None, dict]]:
    """(anterior, T) para cada tag T com `data` em [inicio, fim] (limites inclusivos por data).

    A anterior é a tag imediatamente anterior a T por data, mesmo fora da janela; `None` quando T
    é a primeira da história coletada. Tags sem data são ignoradas.
    """
    pares: list[tuple[dict | None, dict]] = []
    anterior = None
    for t in ordenar([t for t in tags if t.get("data")]):
        dia = _data(t["data"])
        if dia > fim:
            break
        if dia >= inicio:
            pares.append((anterior, t))
        anterior = t
    return pares
