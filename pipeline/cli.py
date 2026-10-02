"""Ponto de entrada do comando único: python -m pipeline --config config.yaml."""

import argparse
import logging
import sys

from pipeline.config import ConfigError, get_token, load_config

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


def run(config, token: str) -> None:
    """Orquestra as etapas do pipeline.

    As etapas (seleção, coleta, métricas) entram em Issues próprias e serão
    encadeadas aqui na integração (#6). Por ora só valida o ambiente.
    """
    if config.janela_definida:
        log.info("janela: %s a %s", config.janela_inicio, config.janela_fim)
    else:
        log.warning("janela de observação não definida no config (lacuna L01); defina antes de coletar")
    log.info("cache: %s | saídas: %s", config.cache_dir, config.saidas_dir)
    log.info("ambiente OK (token lido de %s). Nenhuma etapa de coleta implementada ainda.", config.token_env)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        token = get_token(config)
    except ConfigError as exc:
        log.error("%s", exc)
        return 1
    run(config, token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
