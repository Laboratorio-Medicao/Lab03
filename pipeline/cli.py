"""Ponto de entrada do comando único: python -m pipeline --config config.yaml."""

import argparse
import logging
import sys

from pipeline.config import ConfigError, get_token, load_config
from pipeline.funil import escrever_funil
from pipeline.selection import selecionar

log = logging.getLogger("pipeline")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline",
        description="Pipeline de mineração de métricas DORA.",
    )
    parser.add_argument(
        "--config", default="config.yaml", help="caminho do config.yaml (padrão: config.yaml)"
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


def run(config, token: str, client=None) -> None:
    """Orquestra as etapas do pipeline.

    Seleção + funil (#4) já encadeados; coleta e métricas entram em outras Issues (#6).
    """
    if config.janela_definida:
        log.info("janela: %s a %s", config.janela_inicio, config.janela_fim)
    else:
        log.warning("janela de observação não definida no config (lacuna L01); defina antes de coletar")
    log.info("cache: %s | saídas: %s", config.cache_dir, config.saidas_dir)
    log.info("ambiente OK (token lido de %s).", config.token_env)

    if not config.janela_definida:
        log.warning("seleção não executada: a janela de observação é necessária (releases e runs)")
        return
    if client is None:
        log.warning("seleção não executada: pipeline.http_client (Issue #11) ainda não disponível")
        return
    resultado = selecionar(client, config.selecao, config.janela_inicio, config.janela_fim)
    csv_path, md_path = escrever_funil(resultado, config.saidas_dir)
    log.info("funil gerado: %s e %s", csv_path, md_path)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        token = get_token(config)
    except ConfigError as exc:
        log.error("%s", exc)
        return 1
    run(config, token, criar_cliente(token, config.cache_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
