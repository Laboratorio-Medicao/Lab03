"""Coleta dos commits entre releases (Issue #9) — base do lead time da RQ02.

Para cada release R da janela, os commits incluídos nela vêm de
`GET /repos/{owner}/{repo}/compare/{anterior}...{R}` (E§5 RQ02), com a release anterior dada por
`collect_releases.pares_com_anterior` (pode estar fora da janela). Sem paginação o `compare`
devolve no máximo 250 commits (E§4); aqui ele é sempre paginado com `per_page`/`page` até reunir
`total_commits` (lido da 1ª página) ou até vir uma página vazia. Se a API parar antes do total,
a comparação é marcada `truncado` e avisada no log.

De cada commit guarda `sha`, `author_date` (`commit.author.date`, a regra de E§3; o `author` de
topo da resposta é o usuário do GitHub, não a data), `committer_date`, `message` (heurística de
release corretiva da CFR (b), S02) e `n_parents` (commits de merge, lacuna L07).

Status de cada release:
- `ok`: comparação feita (pode ter 0 commits: release sem commits novos, L07 — decisão na #10);
- `404`: o `compare` deu 404 (tag apagada/reescrita). Registrada no log, ignorada no lead time e
  contada em `n_releases_ignored_404` (E§11);
- `sem_anterior`: R é a primeira release da história; fica fora do lead time (RQ02) sem chamar a API.
Outros erros HTTP sobem como `ApiError` e nada é gravado.

Cache em JSON por repositório em `<cache>/commits/<owner>__<repo>.json`, com um mapa
`"base...head" -> comparação` (404 incluído). Só os pares ausentes do mapa vão à API, então mudar
a janela reaproveita as comparações já feitas.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from pipeline.collect_releases import _salvar, arquivo_cache
from pipeline.selection import POR_PAGINA, ApiError, _get

log = logging.getLogger("pipeline.collect_commits")

SUBPASTA_CACHE = "commits"
STATUS_OK = "ok"
STATUS_404 = "404"
STATUS_SEM_ANTERIOR = "sem_anterior"


def caminho_compare(full_name: str, base: str, head: str) -> str:
    """Path do `compare`; nomes de tag são codificados (`+`, `#`, espaço…), mantendo `/`."""
    return f"/repos/{full_name}/compare/{quote(base, safe='/')}...{quote(head, safe='/')}"


def comparar(client, full_name: str, base: str, head: str) -> dict | None:
    """Commits de `base...head` com paginação por `page`; `None` se o `compare` der 404.

    Devolve `{"base", "head", "status", "total_commits", "truncado", "commits"}`.
    """
    caminho = caminho_compare(full_name, base, head)
    commits: list[dict] = []
    total = None
    pagina = 1
    try:
        while True:
            corpo = _get(client, caminho, {"per_page": POR_PAGINA, "page": pagina}).json()
            if total is None:
                total = int(corpo.get("total_commits") or 0)
            lote = corpo.get("commits") or []
            commits.extend(_normalizar(c) for c in lote)
            if not lote or len(commits) >= total:
                break
            pagina += 1
    except ApiError as exc:
        if exc.status != 404:
            raise
        log.warning("%s: compare %s...%s deu 404; release ignorada no lead time", full_name, base, head)
        return None

    truncado = len(commits) < total
    if truncado:
        log.warning(
            "%s: compare %s...%s trouxe %d de %d commits; comparação truncada",
            full_name, base, head, len(commits), total,
        )
    return {
        "base": base,
        "head": head,
        "status": STATUS_OK,
        "total_commits": total,
        "truncado": truncado,
        "commits": commits,
    }


def _normalizar(c: dict) -> dict:
    info = c.get("commit") or {}
    return {
        "sha": c.get("sha"),
        "author_date": (info.get("author") or {}).get("date"),
        "committer_date": (info.get("committer") or {}).get("date"),
        "message": info.get("message"),
        "n_parents": len(c.get("parents") or []),
    }


def collect_commits(
    client,
    full_name: str,
    pares: list[tuple[dict | None, dict]],
    cache_dir: Path | None = None,
) -> dict:
    """Commits de cada release R a partir dos pares `(anterior, R)` de `pares_com_anterior`.

    Devolve `{"full_name", "releases", "n_releases_ignored_404", "n_sem_anterior", "n_truncadas"}`;
    cada item de `releases` tem `tag_name`, `published_at`, `base`, `status`, `total_commits`,
    `truncado` e `commits`, na ordem de `pares`.
    """
    arquivo = arquivo_cache(cache_dir, full_name, subpasta=SUBPASTA_CACHE) if cache_dir is not None else None
    comparacoes: dict[str, dict] = {}
    if arquivo is not None and arquivo.exists():
        comparacoes = json.loads(arquivo.read_text(encoding="utf-8"))["comparacoes"]

    novas = 0
    releases = []
    for anterior, r in pares:
        entrada = {
            "tag_name": r["tag_name"],
            "published_at": r.get("published_at"),
            "base": anterior["tag_name"] if anterior is not None else None,
        }
        if anterior is None:
            releases.append({**entrada, "status": STATUS_SEM_ANTERIOR, "total_commits": None, "truncado": False, "commits": []})
            continue
        chave = f"{anterior['tag_name']}...{r['tag_name']}"
        if chave not in comparacoes:
            comparacoes[chave] = comparar(client, full_name, anterior["tag_name"], r["tag_name"]) or {
                "base": anterior["tag_name"],
                "head": r["tag_name"],
                "status": STATUS_404,
                "total_commits": None,
                "truncado": False,
                "commits": [],
            }
            novas += 1
        c = comparacoes[chave]
        releases.append({
            **entrada,
            "status": c["status"],
            "total_commits": c["total_commits"],
            "truncado": c["truncado"],
            "commits": c["commits"],
        })

    n_404 = sum(1 for r in releases if r["status"] == STATUS_404)
    n_sem_anterior = sum(1 for r in releases if r["status"] == STATUS_SEM_ANTERIOR)
    n_truncadas = sum(1 for r in releases if r["truncado"])
    n_commits = sum(len(r["commits"]) for r in releases)
    log.info(
        "%s: %d releases, %d commits (%d comparações novas), %d ignoradas por 404, %d sem anterior",
        full_name, len(releases), n_commits, novas, n_404, n_sem_anterior,
    )
    if n_404:
        log.warning("%s: %d releases ignoradas no lead time por 404 no compare", full_name, n_404)

    if arquivo is not None and (novas or not arquivo.exists()):
        _salvar(arquivo, {
            "full_name": full_name,
            "atualizado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "comparacoes": comparacoes,
        })
    return {
        "full_name": full_name,
        "releases": releases,
        "n_releases_ignored_404": n_404,
        "n_sem_anterior": n_sem_anterior,
        "n_truncadas": n_truncadas,
    }
