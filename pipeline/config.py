"""Leitura e validação do config.yaml; o token vem sempre de variável de ambiente."""

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

DEFAULT_TOKEN_ENV = "GITHUB_TOKEN"


class ConfigError(Exception):
    """Configuração inválida ou ausente (mensagem pensada para o usuário final)."""


@dataclass(frozen=True)
class Config:
    token_env: str
    janela_inicio: date | None
    janela_fim: date | None
    cache_dir: Path
    saidas_dir: Path

    @property
    def janela_definida(self) -> bool:
        return self.janela_inicio is not None and self.janela_fim is not None


def _parse_data(valor, campo: str) -> date | None:
    if valor is None:
        return None
    if isinstance(valor, date):  # o YAML já converte AAAA-MM-DD em date
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        raise ConfigError(f"{campo}: data inválida {valor!r} (use AAAA-MM-DD)") from None


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"arquivo de configuração não encontrado: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: YAML inválido ({exc})") from None
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: o conteúdo deve ser um mapa chave/valor")

    github = raw.get("github") or {}
    janela = raw.get("janela") or {}
    caminhos = raw.get("caminhos") or {}

    inicio = _parse_data(janela.get("inicio"), "janela.inicio")
    fim = _parse_data(janela.get("fim"), "janela.fim")
    if (inicio is None) != (fim is None):
        raise ConfigError("janela: defina inicio e fim juntos (ou deixe ambos como null)")
    if inicio is not None and fim is not None and fim <= inicio:
        raise ConfigError("janela: 'fim' deve ser posterior a 'inicio'")

    return Config(
        token_env=str(github.get("token_env") or DEFAULT_TOKEN_ENV),
        janela_inicio=inicio,
        janela_fim=fim,
        cache_dir=Path(caminhos.get("cache") or "cache"),
        saidas_dir=Path(caminhos.get("saidas") or "outputs"),
    )


def get_token(config: Config, environ=None) -> str:
    """Lê o token da variável de ambiente; erro claro se ausente (sem expor valores)."""
    environ = os.environ if environ is None else environ
    token = (environ.get(config.token_env) or "").strip()
    if not token:
        raise ConfigError(
            f"variável de ambiente {config.token_env} não definida. "
            f'Defina com: export {config.token_env}="seu_token"'
        )
    return token
