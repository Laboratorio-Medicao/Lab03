"""Orquestração da execução completa (Issue #6): seleção -> coleta -> métricas -> resultados -> funil -> log.

Este módulo só **encadeia** etapas; não coleta, não calcula e não faz cache:

- seleção + funil: `pipeline.selection.selecionar` e `pipeline.funil.escrever_funil` (Issue #4);
- coleta por repositório e cálculo das métricas: injetados em `Etapas` (Issues #7-#10, #13, #14);
- cache e rate limit: responsabilidade do `client` (Issues #11 e #12). Se o cliente expõe
  `estatisticas()` (dict de contadores inteiros, ex.: cache_hits/cache_misses), o log registra o
  consumo da execução (diferença antes/depois). O nome dos contadores NÃO É DEFINIDO NA FONTE DA
  VERDADE; o log reproduz as chaves devolvidas, sem interpretá-las.

Contrato das etapas injetadas (assinaturas NÃO DEFINIDAS na Fonte da Verdade — definidas aqui):

    coletar(client, repo: RepoRecord, inicio: date, fim: date) -> dados   # levanta exceção em falha
    calcular(repo: RepoRecord, dados, inicio: date, fim: date) -> dict    # colunas de métricas

Política de erro (NÃO DEFINIDA na Fonte da Verdade; escolha registrada no log): a falha em um
repositório é registrada (`status=erro`, `erro=<tipo>: <msg>`) e a execução segue com os demais.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

from pipeline.config import Config
from pipeline.funil import escrever_funil, resumo
from pipeline.selection import RepoRecord, ResultadoSelecao, selecionar

log = logging.getLogger("pipeline.execucao")

ARQUIVO_RESULTADOS = "resultados.csv"
ARQUIVO_LOG = "execucao.log"


@dataclass(frozen=True)
class Etapas:
    coletar: Callable | None
    calcular: Callable | None
    selecionar: Callable = selecionar


@dataclass
class ResultadoRepo:
    full_name: str
    status: str  # "concluido" | "erro"
    erro: str = ""
    metricas: dict = field(default_factory=dict)


@dataclass
class ResumoExecucao:
    candidatos: int = 0
    selecionados: int = 0  # aprovados pelos filtros do funil
    duplicados: int = 0
    fora_da_amostra: int = 0  # aprovados, mas além de `amostra_alvo`
    processados: int = 0
    concluidos: int = 0
    erros: int = 0
    descartes: dict = field(default_factory=dict)  # motivo -> quantidade (funil)
    consumo_cache: dict = field(default_factory=dict)
    resultados: list[ResultadoRepo] = field(default_factory=list)


def validar_amostra(registros: list[RepoRecord], alvo: int | None) -> tuple[list[RepoRecord], int, int]:
    """Amostra final = selecionados sem duplicatas (por `full_name`, sem diferenciar caixa).

    Devolve (amostra, duplicados_removidos, fora_da_amostra). Se `alvo` está definido e há mais
    aprovados que o alvo, mantém os `alvo` primeiros na ordem recebida: o critério de corte NÃO É
    DEFINIDO NA FONTE DA VERDADE (L17 só diz que os 100 devem passar nos filtros). Se há menos,
    não completa nem relaxa filtros: o chamador registra a diferença.
    """
    vistos: set[str] = set()
    amostra: list[RepoRecord] = []
    duplicados = 0
    for r in registros:
        if r.status != "selecionado":
            continue
        chave = r.full_name.strip().lower()
        if "/" not in chave:
            raise ValueError(f"full_name inválido: {r.full_name!r} (esperado owner/repo)")
        if chave in vistos:
            duplicados += 1
            continue
        vistos.add(chave)
        amostra.append(r)
    fora = 0
    if alvo is not None and len(amostra) > alvo:
        fora = len(amostra) - alvo
        amostra = amostra[:alvo]
    return amostra, duplicados, fora


def _contadores(client) -> dict:
    fn = getattr(client, "estatisticas", None)
    if not callable(fn):
        return {}
    return {k: v for k, v in fn().items() if isinstance(v, int) and not isinstance(v, bool)}


def _processar(client, etapas: Etapas, repo: RepoRecord, inicio: date, fim: date) -> ResultadoRepo:
    try:
        dados = etapas.coletar(client, repo, inicio, fim)
        metricas = etapas.calcular(repo, dados, inicio, fim)
    except Exception as exc:  # noqa: BLE001 — qualquer falha de um repo é registrada, nunca escondida
        log.error("%s: falha (%s: %s)", repo.full_name, type(exc).__name__, exc)
        return ResultadoRepo(repo.full_name, "erro", f"{type(exc).__name__}: {exc}")
    return ResultadoRepo(repo.full_name, "concluido", metricas=dict(metricas))


def escrever_resultados(resultados: list[ResultadoRepo], saidas_dir: Path) -> Path:
    saidas_dir.mkdir(parents=True, exist_ok=True)
    caminho = saidas_dir / ARQUIVO_RESULTADOS
    colunas: list[str] = []
    for r in resultados:
        colunas += [k for k in r.metricas if k not in colunas and k not in ("full_name", "status", "erro")]
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["full_name", "status", "erro", *colunas])
        w.writeheader()
        for r in sorted(resultados, key=lambda r: r.full_name.lower()):
            linha = {"full_name": r.full_name, "status": r.status, "erro": r.erro}
            linha.update({k: ("" if v is None else v) for k, v in r.metricas.items()})
            w.writerow(linha)
    return caminho


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def executar(config: Config, client, etapas: Etapas, amostra_alvo: int | None = None) -> ResumoExecucao:
    """Executa o fluxo completo na ordem: seleção -> validação -> coleta -> métricas -> resultados -> funil."""
    inicio, fim = config.janela_inicio, config.janela_fim
    sel = config.selecao
    log.info("execução iniciada em %s", _agora())
    log.info("janela: %s a %s | cache: %s | saídas: %s", inicio, fim, config.cache_dir, config.saidas_dir)
    log.info(
        "seleção: stars_min=%s faixas=%s linguagens=%s min_releases=%s min_runs_validos=%s amostra_alvo=%s",
        sel.stars_min, list(sel.faixas_estrelas), list(sel.linguagens) or "-",
        sel.min_releases, sel.min_runs_validos, amostra_alvo,
    )
    antes = _contadores(client)
    resumo_exec = ResumoExecucao()

    selecao: ResultadoSelecao = etapas.selecionar(client, sel, inicio, fim)
    funil = resumo(selecao.registros)
    resumo_exec.candidatos, resumo_exec.descartes = funil["candidatos"], funil["motivos"]
    log.info("candidatos: %d | descartados: %s", funil["candidatos"], funil["motivos"] or "nenhum")

    amostra, dup, fora = validar_amostra(selecao.registros, amostra_alvo)
    resumo_exec.selecionados, resumo_exec.duplicados, resumo_exec.fora_da_amostra = funil["selecionados"], dup, fora
    log.info("selecionados (aprovados nos filtros): %d | duplicados removidos: %d", funil["selecionados"], dup)
    if fora:
        log.warning("%d aprovados ficaram fora da amostra de %s (critério de corte não definido; ordem da seleção)", fora, amostra_alvo)
    if amostra_alvo is not None and len(amostra) < amostra_alvo:
        log.warning("amostra com %d repositórios, abaixo do alvo %d: filtros mantidos, nada foi completado", len(amostra), amostra_alvo)

    if etapas.coletar is None or etapas.calcular is None:
        amostra_a_processar: list[RepoRecord] = []
        log.warning("coleta/métricas não configuradas: %d repositórios selecionados não foram processados", len(amostra))
    else:
        amostra_a_processar = amostra
    for i, repo in enumerate(amostra_a_processar, 1):
        res = _processar(client, etapas, repo, inicio, fim)
        resumo_exec.resultados.append(res)
        log.info("[%d/%d] %s -> %s", i, len(amostra_a_processar), repo.full_name, res.status)
    resumo_exec.processados = len(resumo_exec.resultados)
    resumo_exec.concluidos = sum(1 for r in resumo_exec.resultados if r.status == "concluido")
    resumo_exec.erros = resumo_exec.processados - resumo_exec.concluidos

    csv_res = escrever_resultados(resumo_exec.resultados, config.saidas_dir)
    csv_funil, _ = escrever_funil(selecao, config.saidas_dir)
    log.info("resultados: %s | funil: %s", csv_res, csv_funil)

    depois = _contadores(client)
    resumo_exec.consumo_cache = {k: depois[k] - antes.get(k, 0) for k in depois}
    if resumo_exec.consumo_cache:
        log.info("cliente/cache nesta execução: %s", resumo_exec.consumo_cache)
    else:
        log.info("cliente/cache: contadores não disponíveis (client.estatisticas ausente)")
    log.info(
        "processados: %d | concluídos: %d | erros: %d | execução encerrada em %s",
        resumo_exec.processados, resumo_exec.concluidos, resumo_exec.erros, _agora(),
    )
    return resumo_exec


def anexar_log_em_arquivo(saidas_dir: Path) -> logging.Handler:
    """Duplica o log do pipeline em `<saidas>/execucao.log` (append; cada execução tem início/fim datados)."""
    saidas_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(saidas_dir / ARQUIVO_LOG, mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger = logging.getLogger("pipeline")
    logger.addHandler(handler)
    if logger.getEffectiveLevel() > logging.INFO:
        logger.setLevel(logging.INFO)
    return handler
