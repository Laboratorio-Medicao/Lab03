"""Coleta de releases por repositório (Issue #7).

`collect_releases` busca **todas** as releases de um repositório, sem corte de data: as
anteriores à janela são necessárias como "release anterior" da 1ª release da janela
(E§5 RQ02, compare/{anterior}...{R}). Guarda `draft`, `prerelease`, `published_at` e
`tag_name` (E§4) e alguns campos baratos usados adiante (`id`, `created_at` para desempate,
`target_commitish` para a lacuna L06, `html_url` para a planilha de rotulagem da S02).

Cache em JSON por repositório em `<cache>/releases/<owner>__<repo>.json`. Como não há corte
de data, o arquivo continua válido se a janela mudar. Usa o mesmo path/params da contagem de
releases da seleção (`contar_releases`), então as páginas já estão no cache HTTP (Issue #12).

A paginação vai até o fim: diferente da Search API e de `actions/runs`, `/releases` **não** para
nos 1.000 primeiros resultados (conferido em renovatebot/renovate: 122 páginas com `per_page=100`).
Um cache gravado pela versão antiga, com `"truncado": true`, é descartado e a coleta é refeita.

`pares_com_anterior` devolve, para cada release de deploy publicada na janela, a release de
deploy imediatamente anterior (pode estar fora da janela; `None` se não houver).
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline.selection import POR_PAGINA, _data, _destino, _get, _link

log = logging.getLogger("pipeline.collect_releases")

CAMPOS = ("id", "tag_name", "draft", "prerelease", "published_at", "created_at", "target_commitish", "html_url")
SUBPASTA_CACHE = "releases"


def arquivo_cache(cache_dir: Path, full_name: str, subpasta: str = SUBPASTA_CACHE) -> Path:
    """`<cache>/<subpasta>/<owner>__<repo>.json` (minúsculas: `full_name` não diferencia caixa).

    `subpasta` permite reaproveitar o mesmo layout para outras coletas por repositório (ex.: tags).
    """
    partes = full_name.strip().lower().split("/")
    if len(partes) != 2 or not all(partes):
        raise ValueError(f"full_name inválido: {full_name!r} (esperado owner/repo)")
    return Path(cache_dir) / subpasta / f"{partes[0]}__{partes[1]}.json"


def collect_releases(client, full_name: str, cache_dir: Path | None = None) -> list[dict]:
    """Todas as releases de `full_name`, ordenadas por `published_at` (drafts no fim).

    Com `cache_dir`, lê o JSON do repositório se existir (sem chamar a API) ou o grava após a
    coleta. Erros HTTP sobem como `ApiError` e nada é gravado.
    """
    arquivo = arquivo_cache(cache_dir, full_name) if cache_dir is not None else None
    if arquivo is not None and arquivo.exists():
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        if not dados.get("truncado"):
            log.info("%s: %d releases (cache)", full_name, len(dados["releases"]))
            return dados["releases"]
        log.warning("%s: cache de releases truncado no antigo teto de 1.000; coletando de novo", full_name)

    releases = ordenar([_normalizar(r) for r in _paginar_releases(client, full_name)])
    log.info("%s: %d releases coletadas", full_name, len(releases))

    if arquivo is not None:
        _salvar(arquivo, {
            "full_name": full_name,
            "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "total": len(releases),
            "releases": releases,
        })
    return releases


def _paginar_releases(client, full_name: str) -> list[dict]:
    """Segue `Link: rel="next"` até o fim."""
    resp = _get(client, f"/repos/{full_name}/releases", {"per_page": POR_PAGINA})
    itens: list[dict] = list(resp.json())
    proxima = _link(resp.headers, "next")
    while proxima:
        caminho, parametros = _destino(proxima)
        resp = _get(client, caminho, parametros)
        itens.extend(resp.json())
        proxima = _link(resp.headers, "next")
    return itens


def _normalizar(r: dict) -> dict:
    return {campo: r.get(campo) for campo in CAMPOS}


def _instante(valor: str | None) -> datetime | None:
    if not valor:
        return None
    return datetime.fromisoformat(valor.replace("Z", "+00:00")).astimezone(timezone.utc)


def ordenar(releases: list[dict]) -> list[dict]:
    """Por `published_at` crescente; empate por `created_at` e `id`; sem `published_at` (drafts) no fim."""
    minimo = datetime.min.replace(tzinfo=timezone.utc)

    def chave(r: dict):
        publicada = _instante(r.get("published_at"))
        return (
            publicada is None,
            publicada or minimo,
            _instante(r.get("created_at")) or minimo,
            r.get("id") or 0,
        )

    return sorted(releases, key=chave)


def e_deploy(r: dict, incluir_prerelease: bool = False) -> bool:
    """Deploy = release publicada (`draft=false`, com `published_at`); pré-release só na variante (RQ07)."""
    if r.get("draft") or not r.get("published_at"):
        return False
    return incluir_prerelease or not r.get("prerelease")


def pares_com_anterior(
    releases: list[dict],
    inicio: date,
    fim: date,
    incluir_prerelease: bool = False,
) -> list[tuple[dict | None, dict]]:
    """(anterior, R) para cada release de deploy R com `published_at` em [inicio, fim] (L05).

    A anterior é a release de deploy imediatamente anterior a R, mesmo fora da janela; `None`
    quando R é a primeira da história coletada (RQ02: R fica fora do lead time).
    """
    pares: list[tuple[dict | None, dict]] = []
    anterior = None
    for r in ordenar([r for r in releases if e_deploy(r, incluir_prerelease)]):
        publicada = _data(r["published_at"])
        if publicada > fim:
            break
        if publicada >= inicio:
            pares.append((anterior, r))
        anterior = r
    return pares


def _salvar(arquivo: Path, dados: dict) -> None:
    """Escrita atômica: arquivo temporário seguido de replace."""
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    tmp = arquivo.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(arquivo)
