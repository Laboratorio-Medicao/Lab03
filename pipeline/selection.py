"""Seleção de repositórios (Issue #4): Search API fatiada, filtros baratos primeiro, metadados.

Etapas (Fonte da Verdade §8.4): candidatos -> possui Actions -> releases mínimas ->
runs válidos mínimos -> amostra final. Cada repositório gera um RepoRecord; o funil
(pipeline/funil.py) é derivado apenas desses registros.

O cliente HTTP é injetado: este módulo só exige `client.get(path, params)` devolvendo
algo com `.status_code`, `.json()` e `.headers` (a Issue #11 entrega o http_client real,
com rate limit, backoff e cache). Nenhuma chamada HTTP é feita aqui diretamente.
"""

from __future__ import annotations

import logging
import re
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import parse_qsl, urlparse

from pipeline.config import SelecaoConfig

log = logging.getLogger("pipeline.selection")

LIMITE_ESTRELAS = 10_000_000  # acima de qualquer repositório real: encerra a divisão de faixas abertas
TETO_RESULTADOS = 1000  # Search e actions/runs: no máximo 1.000 resultados por consulta (E§4)
POR_PAGINA = 100
# `conclusion` que entram no cálculo (E§3); as demais (cancelled, skipped, neutral,
# action_required, stale, vazio) são ignoradas. Lacuna L04: "run válido" = default branch,
# event=push, criado na janela e com uma destas conclusões.
CONCLUSOES_VALIDAS = frozenset({"success", "failure", "timed_out", "startup_failure"})


class ApiError(Exception):
    def __init__(self, status: int, path: str):
        super().__init__(f"HTTP {status} em {path}")
        self.status = status
        self.path = path


# --------------------------------------------------------------------------- modelos


@dataclass(frozen=True)
class Fatia:
    """Uma consulta da Search API: linguagem (opcional) + faixa de estrelas [minimo, maximo]."""

    minimo: int
    maximo: int | None  # None = faixa aberta
    linguagem: str | None = None

    def consulta(self, sel: SelecaoConfig) -> str:
        estrelas = f"stars:>={self.minimo}" if self.maximo is None else f"stars:{self.minimo}..{self.maximo}"
        partes = [estrelas]
        if self.linguagem:
            partes.append(f'language:"{self.linguagem}"')
        if sel.excluir_forks:
            partes.append("fork:false")
        if sel.excluir_arquivados:
            partes.append("archived:false")
        return " ".join(partes)


@dataclass
class RegistroFatia:
    consulta: str
    total_count: int
    retornados: int
    saturada: bool = False  # faixa de 1 só valor ainda acima do teto: não dá para fatiar mais


@dataclass
class ResultadoBusca:
    candidatos: list[dict]
    fatias: list[RegistroFatia]
    brutos: int  # ocorrências antes da deduplicação


@dataclass
class RepoRecord:
    full_name: str
    stars: int
    language: str | None
    default_branch: str
    created_at: str
    status: str = "selecionado"  # "selecionado" | "descartado"
    etapa: str = "final"  # etapa onde terminou: actions | releases | runs | final
    motivo: str = ""
    workflows_total_count: int | None = None
    n_releases_window: int | None = None
    runs_consultados: int | None = None
    n_runs_valid_window: int | None = None
    contributors: int | None = None
    age_days: float | None = None


@dataclass
class ResultadoSelecao:
    registros: list[RepoRecord] = field(default_factory=list)
    fatias: list[RegistroFatia] = field(default_factory=list)
    brutos: int = 0
    candidatos_total: int = 0  # candidatos únicos da busca (>= len(registros) se a avaliação parou cedo)
    origem: str = "Search API"  # de onde vieram os candidatos (muda com `--repos-file`)


# --------------------------------------------------------------------------- HTTP helpers


def _get(client, path: str, params: dict | None = None):
    resp = client.get(path, params)
    if not 200 <= resp.status_code < 300:
        raise ApiError(resp.status_code, path)
    return resp


def _link(headers, rel: str) -> str | None:
    cabecalho = headers.get("Link") or headers.get("link") or ""
    for trecho in cabecalho.split(","):
        m = re.match(r'\s*<([^>]+)>\s*;\s*rel="?(\w+)"?', trecho)
        if m and m.group(2) == rel:
            return m.group(1)
    return None


def _destino(url: str) -> tuple[str, dict]:
    p = urlparse(url)
    return p.path, dict(parse_qsl(p.query))


def _paginar(client, path: str, params: dict, chave: str | None = None) -> list:
    """Segue `Link: rel="next"` até o fim e devolve todos os itens (`chave` = lista no corpo)."""
    itens: list = []
    resp = _get(client, path, params)
    while True:
        corpo = resp.json()
        itens.extend(corpo[chave] if chave else corpo)
        proxima = _link(resp.headers, "next")
        if not proxima:
            return itens
        caminho, parametros = _destino(proxima)
        resp = _get(client, caminho, parametros)


# --------------------------------------------------------------------------- busca fatiada


def fatias_iniciais(sel: SelecaoConfig) -> list[Fatia]:
    """Faixas de estrelas (config) x linguagens (config; vazio = sem filtro de linguagem)."""
    limites = sorted({max(x, sel.stars_min) for x in sel.faixas_estrelas} | {sel.stars_min})
    faixas = [(limites[i], limites[i + 1] - 1) for i in range(len(limites) - 1)] + [(limites[-1], None)]
    linguagens: list[str | None] = list(sel.linguagens) or [None]
    return [Fatia(lo, hi, lang) for lang in linguagens for lo, hi in faixas]


def _dividir(fatia: Fatia) -> list[Fatia] | None:
    """Divide a faixa de estrelas ao meio (determinístico); None se for um único valor."""
    if fatia.maximo is None:  # faixa aberta: parte em [lo, 2lo] e (2lo, ∞)
        if fatia.minimo >= LIMITE_ESTRELAS:
            return None
        corte = max(fatia.minimo * 2, fatia.minimo + 1)
        return [Fatia(fatia.minimo, corte, fatia.linguagem), Fatia(corte + 1, None, fatia.linguagem)]
    if fatia.minimo >= fatia.maximo:
        return None
    meio = (fatia.minimo + fatia.maximo) // 2
    return [Fatia(fatia.minimo, meio, fatia.linguagem), Fatia(meio + 1, fatia.maximo, fatia.linguagem)]


def _buscar_fatia(client, fatia: Fatia, sel: SelecaoConfig, itens: list[dict], registros: list[RegistroFatia]):
    consulta = fatia.consulta(sel)
    params = {"q": consulta, "sort": "stars", "order": "desc", "per_page": POR_PAGINA}
    resp = _get(client, "/search/repositories", params)
    corpo = resp.json()
    total = int(corpo.get("total_count", 0))

    if total > TETO_RESULTADOS:
        partes = _dividir(fatia)
        if partes is not None:
            log.info("fatia '%s': %d resultados > %d; subdividindo", consulta, total, TETO_RESULTADOS)
            for parte in partes:
                _buscar_fatia(client, parte, sel, itens, registros)
            return
        log.warning("fatia '%s' saturada (%d > %d, faixa indivisível): só os primeiros %d", consulta, total, TETO_RESULTADOS, TETO_RESULTADOS)

    novos = list(corpo.get("items", []))
    proxima = _link(resp.headers, "next")
    while proxima and len(novos) < TETO_RESULTADOS:
        caminho, parametros = _destino(proxima)
        resp = _get(client, caminho, parametros)
        novos.extend(resp.json().get("items", []))
        proxima = _link(resp.headers, "next")
    novos = novos[:TETO_RESULTADOS]
    itens.extend(novos)
    registros.append(RegistroFatia(consulta, total, len(novos), saturada=total > TETO_RESULTADOS))
    log.info("fatia '%s': total_count=%d, coletados=%d", consulta, total, len(novos))


def search_candidatos(client, sel: SelecaoConfig) -> ResultadoBusca:
    """Consulta todas as fatias e deduplica por full_name (sem diferenciar maiúsculas)."""
    itens: list[dict] = []
    registros: list[RegistroFatia] = []
    for fatia in fatias_iniciais(sel):
        _buscar_fatia(client, fatia, sel, itens, registros)

    unicos: dict[str, dict] = {}
    for item in itens:
        unicos.setdefault(item["full_name"].lower(), item)
    candidatos = [unicos[k] for k in sorted(unicos)]  # ordem determinística
    log.info("candidatos: %d ocorrências, %d únicos", len(itens), len(candidatos))
    return ResultadoBusca(candidatos, registros, len(itens))


# --------------------------------------------------------------------------- filtros


def total_workflows(client, full_name: str) -> int:
    resp = _get(client, f"/repos/{full_name}/actions/workflows", {"per_page": 1})
    return int(resp.json().get("total_count", 0))


def _data(valor: str | None) -> date | None:
    if not valor:
        return None
    return datetime.fromisoformat(valor.replace("Z", "+00:00")).astimezone(timezone.utc).date()


def contar_releases(client, full_name: str, inicio: date, fim: date) -> int:
    """Releases de deploy na janela (L05): draft=false, prerelease=false, published_at em [inicio, fim]."""
    releases = _paginar(client, f"/repos/{full_name}/releases", {"per_page": POR_PAGINA})
    total = 0
    for r in releases:
        publicada = _data(r.get("published_at"))
        if r.get("draft") or r.get("prerelease") or publicada is None:
            continue
        if inicio <= publicada <= fim:
            total += 1
    return total


def meses_da_janela(inicio: date, fim: date) -> list[tuple[date, date]]:
    """Divide a janela em meses de calendário (limites inclusivos)."""
    partes = []
    atual = inicio
    while atual <= fim:
        ultimo = date(atual.year, atual.month, monthrange(atual.year, atual.month)[1])
        partes.append((atual, min(ultimo, fim)))
        atual = ultimo + timedelta(days=1)
    return partes


def _runs_do_intervalo(client, full_name: str, branch: str, ini: date, fim: date, contagem: dict) -> None:
    minimo = contagem.get("minimo")
    if minimo is not None and contagem["validos"] >= minimo:
        return  # já basta para o filtro: não gasta mais chamadas
    params = {"branch": branch, "event": "push", "created": f"{ini.isoformat()}..{fim.isoformat()}", "per_page": POR_PAGINA}
    resp = _get(client, f"/repos/{full_name}/actions/runs", params)
    total = int(resp.json().get("total_count", 0))

    runs = list(resp.json().get("workflow_runs", []))
    validos_pagina = sum(1 for r in runs if r.get("conclusion") in CONCLUSOES_VALIDAS)
    if minimo is not None and contagem["validos"] + validos_pagina >= minimo:
        contagem["consultados"] += len(runs)
        contagem["validos"] += validos_pagina
        return

    if total >= TETO_RESULTADOS:  # teto atingido: subdividir o intervalo (E§4)
        if ini < fim:
            meio = ini + (fim - ini) // 2
            log.info("%s runs %s..%s: total_count=%d no teto; subdividindo", full_name, ini, fim, total)
            _runs_do_intervalo(client, full_name, branch, ini, meio, contagem)
            _runs_do_intervalo(client, full_name, branch, meio + timedelta(days=1), fim, contagem)
            return
        log.warning("%s runs em %s atingiram o teto de %d e não podem ser subdivididos", full_name, ini, TETO_RESULTADOS)
        contagem["saturado"] = True

    proxima = _link(resp.headers, "next")
    while proxima:
        if minimo is not None and contagem["validos"] + validos_pagina >= minimo:
            break
        caminho, parametros = _destino(proxima)
        resp = _get(client, caminho, parametros)
        pagina = resp.json().get("workflow_runs", [])
        runs.extend(pagina)
        validos_pagina += sum(1 for r in pagina if r.get("conclusion") in CONCLUSOES_VALIDAS)
        proxima = _link(resp.headers, "next")
    contagem["consultados"] += len(runs)
    contagem["validos"] += validos_pagina


def contar_runs(client, full_name: str, branch: str, inicio: date, fim: date, minimo: int | None = None) -> tuple[int, int]:
    """(runs consultados, runs válidos) no default branch, event=push, fatiado por mês.

    Com `minimo`, a contagem **para ao atingir** esse número de runs válidos (o filtro do funil só
    precisa saber se o mínimo foi alcançado): então `válidos` é exato abaixo do mínimo e um piso
    (>= minimo) acima dele. A contagem completa vem da coleta (`collect_runs`).
    """
    contagem = {"consultados": 0, "validos": 0, "minimo": minimo}
    for ini, fim_mes in meses_da_janela(inicio, fim):
        _runs_do_intervalo(client, full_name, branch, ini, fim_mes, contagem)
    return contagem["consultados"], contagem["validos"]


# --------------------------------------------------------------------------- metadados


def contar_contribuidores(client, full_name: str) -> int:
    """`contributors?per_page=1&anon=true`: o nº da última página (Link rel=last) é o total."""
    resp = _get(client, f"/repos/{full_name}/contributors", {"per_page": 1, "anon": "true"})
    ultima = _link(resp.headers, "last")
    if ultima:
        return int(_destino(ultima)[1]["page"])
    corpo = resp.json()
    return len(corpo) if isinstance(corpo, list) else 0


def idade_dias(created_at: str, referencia: date) -> float:
    """Dias entre `created_at` e a referência (início ou fim da janela, 00:00 UTC) — lacuna L16."""
    criado = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(timezone.utc)
    ref = datetime.combine(referencia, time.min, tzinfo=timezone.utc)
    return (ref - criado).total_seconds() / 86400


# --------------------------------------------------------------------------- orquestração


def _registro(item: dict) -> RepoRecord:
    return RepoRecord(
        full_name=item["full_name"],
        stars=item["stargazers_count"],
        language=item.get("language"),
        default_branch=item["default_branch"],
        created_at=item["created_at"],
    )


def _descartar(reg: RepoRecord, etapa: str, motivo: str) -> RepoRecord:
    reg.status, reg.etapa, reg.motivo = "descartado", etapa, motivo
    return reg


def avaliar(client, item: dict, sel: SelecaoConfig, inicio: date, fim: date) -> RepoRecord:
    """Aplica os filtros em ordem barata -> cara; descarta no primeiro que falhar."""
    reg = _registro(item)
    etapa = "actions"
    try:
        reg.workflows_total_count = total_workflows(client, reg.full_name)
        if reg.workflows_total_count == 0:
            return _descartar(reg, "actions", "no_actions")

        etapa = "releases"
        reg.n_releases_window = contar_releases(client, reg.full_name, inicio, fim)
        if reg.n_releases_window < sel.min_releases:
            return _descartar(reg, "releases", f"lt_{sel.min_releases}_releases")

        etapa = "runs"
        reg.runs_consultados, reg.n_runs_valid_window = contar_runs(
            client, reg.full_name, reg.default_branch, inicio, fim, sel.min_runs_validos
        )
        if reg.n_runs_valid_window < sel.min_runs_validos:
            return _descartar(reg, "runs", f"lt_{sel.min_runs_validos}_runs")

        etapa = "final"
        reg.contributors = contar_contribuidores(client, reg.full_name)
        referencia = inicio if sel.idade_referencia == "inicio" else fim
        reg.age_days = idade_dias(reg.created_at, referencia)
    except ApiError as exc:
        log.warning("%s: %s (etapa %s)", reg.full_name, exc, etapa)
        return _descartar(reg, etapa, f"api_error_{exc.status}")
    return reg


def selecionar(
    client, sel: SelecaoConfig, inicio: date, fim: date, ao_avaliar=None, parar_em: int | None = None
) -> ResultadoSelecao:
    """Busca fatiada + filtros. Candidatos são avaliados na ordem determinística de `full_name`.

    - `parar_em`: encerra a avaliação quando esse número de repositórios for selecionado (amostra
      da S01). Os candidatos não avaliados ficam fora de `registros`, mas contam em
      `candidatos_total` (o funil mostra a diferença). Critério de corte: lacuna L17.
    - `ao_avaliar(resultado_parcial)`: chamado a cada 10 repositórios e ao final, para gravar o
      funil de forma incremental (uma interrupção não perde o progresso).
    """
    busca = search_candidatos(client, sel)
    res = ResultadoSelecao([], busca.fatias, busca.brutos, len(busca.candidatos))
    selecionados = 0
    for i, item in enumerate(busca.candidatos, 1):
        reg = avaliar(client, item, sel, inicio, fim)
        log.info("[%d/%d] %s -> %s%s", i, len(busca.candidatos), reg.full_name, reg.status, f" ({reg.motivo})" if reg.motivo else "")
        res.registros.append(reg)
        selecionados += reg.status == "selecionado"
        if ao_avaliar is not None and i % 10 == 0:
            ao_avaliar(res)
        if parar_em is not None and selecionados >= parar_em:
            log.info("amostra de %d selecionados atingida após avaliar %d de %d candidatos", parar_em, i, len(busca.candidatos))
            break
    if ao_avaliar is not None:
        ao_avaliar(res)
    return res
