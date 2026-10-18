"""Ponto de entrada do comando único: python -m pipeline --config config.yaml."""

import argparse
import logging
import sys

from pipeline.config import ConfigError, carregar_dotenv, get_token, load_config
from pipeline.selection import ApiError
from pipeline.execucao import Etapas, anexar_log_em_arquivo, executar
from pipeline.repos_file import ler_lista

log = logging.getLogger("pipeline")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline",
        description="Pipeline de mineração de métricas DORA.",
    )
    parser.add_argument(
        "--config", default="config.yaml", help="caminho do config.yaml (padrão: config.yaml)"
    )
    parser.add_argument(
        "--repos-file",
        metavar="ARQUIVO",
        help="lista de repositórios (owner/repo por linha, ou CSV com coluna full_name) no lugar da busca; "
        "usada na replicação cruzada",
    )
    return parser


def criar_cliente(token: str, cache_dir=None):
    """Cliente HTTP com cache em disco (Issues #11 e #12). None enquanto não existir."""
    try:
        from pipeline.cache import CachedHttpClient
        from pipeline.http_client import HttpClient
    except ImportError:
        return None
    client = HttpClient(token)
    if cache_dir is not None:
        return CachedHttpClient(client, cache_dir)
    return client


def criar_etapas(config, repos: list[str] | None = None) -> Etapas:
    """Seleção incremental + coleta (releases, tags, commits, runs) + métricas de cada repositório."""
    from pipeline.etapas import criar_etapas as montar

    return montar(config, tags=config.coletar_tags, repos=repos)


def run(config, token: str, client=None, etapas: Etapas | None = None, repos: list[str] | None = None) -> None:
    """Orquestra o fluxo completo (Issue #6): seleção -> coleta -> métricas -> resultados -> funil -> log."""
    if config.janela_definida:
        log.info("janela: %s a %s", config.janela_inicio, config.janela_fim)
    else:
        log.warning("janela de observação não definida no config (lacuna L01); defina antes de coletar")
    log.info("cache: %s | saídas: %s", config.cache_dir, config.saidas_dir)
    log.info("ambiente OK (token lido de %s).", config.token_env)
    if repos is not None:
        log.info("lista de repositórios: %d (busca na Search API desativada)", len(repos))

    if not config.janela_definida:
        log.warning("seleção não executada: a janela de observação é necessária (releases e runs)")
        return
    if client is None:
        log.warning("seleção não executada: pipeline.http_client (Issue #11) ainda não disponível")
        return
    if etapas is None:
        log.warning("sem etapas de coleta/métricas: só seleção e funil")
        etapas = Etapas(coletar=None, calcular=None)
    handler = anexar_log_em_arquivo(config.saidas_dir)  # outputs/execucao.log
    try:
        # Com lista, ela própria é a amostra: sem corte por `amostra_alvo`.
        resumo = executar(config, client, etapas, None if repos is not None else config.selecao.amostra_alvo)
        log.info("execução concluída: %d concluídos, %d erros", resumo.concluidos, resumo.erros)
    finally:
        logging.getLogger("pipeline").removeHandler(handler)
        handler.close()


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    try:
        carregar_dotenv(".env")  # opcional; variável de ambiente já definida tem prioridade
        config = load_config(args.config)
        token = get_token(config)
        repos = ler_lista(args.repos_file) if args.repos_file else None
    except ConfigError as exc:
        log.error("%s", exc)
        return 1
    try:
        run(config, token, criar_cliente(token, config.cache_dir), criar_etapas(config, repos), repos)
    except ApiError as exc:
        log.error("execução interrompida: %s (confira o token e a cota da API)", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
