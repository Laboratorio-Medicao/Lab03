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
class SelecaoConfig:
    """Parâmetros da seleção (lacuna L03: critério de "popular" é decisão do grupo)."""

    stars_min: int = 1000
    # Limites inferiores das faixas de estrelas; a última faixa é aberta (stars:>=último).
    faixas_estrelas: tuple[int, ...] = (1000, 2000, 5000, 10000, 20000, 50000)
    linguagens: tuple[str, ...] = ()  # vazio = sem fatiar por linguagem
    excluir_forks: bool = True
    excluir_arquivados: bool = True
    min_releases: int = 5
    min_runs_validos: int = 50
    idade_referencia: str = "fim"  # "inicio" ou "fim" da janela (lacuna L16)
    amostra_alvo: int = 100  # tamanho da amostra da S01 (E§10); corte acima disso não é definido (L17)


@dataclass(frozen=True)
class Config:
    token_env: str
    janela_inicio: date | None
    janela_fim: date | None
    cache_dir: Path
    saidas_dir: Path
    selecao: SelecaoConfig = SelecaoConfig()

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


def _parse_selecao(raw: dict) -> SelecaoConfig:
    if not isinstance(raw, dict):
        raise ConfigError("selecao: deve ser um mapa chave/valor")
    padrao = SelecaoConfig()
    try:
        faixas = tuple(int(x) for x in raw.get("faixas_estrelas", padrao.faixas_estrelas))
        stars_min = int(raw.get("stars_min", padrao.stars_min))
        min_releases = int(raw.get("min_releases", padrao.min_releases))
        min_runs = int(raw.get("min_runs_validos", padrao.min_runs_validos))
        amostra_alvo = int(raw.get("amostra_alvo", padrao.amostra_alvo))
    except (TypeError, ValueError):
        raise ConfigError("selecao: faixas_estrelas, stars_min, min_releases e min_runs_validos devem ser inteiros") from None
    if not faixas or list(faixas) != sorted(set(faixas)):
        raise ConfigError("selecao.faixas_estrelas: use inteiros estritamente crescentes")
    if amostra_alvo < 1:
        raise ConfigError("selecao.amostra_alvo: deve ser um inteiro >= 1")
    referencia = str(raw.get("idade_referencia", padrao.idade_referencia))
    if referencia not in ("inicio", "fim"):
        raise ConfigError("selecao.idade_referencia: use 'inicio' ou 'fim'")
    return SelecaoConfig(
        stars_min=stars_min,
        faixas_estrelas=faixas,
        linguagens=tuple(str(x) for x in (raw.get("linguagens") or ())),
        excluir_forks=bool(raw.get("excluir_forks", padrao.excluir_forks)),
        excluir_arquivados=bool(raw.get("excluir_arquivados", padrao.excluir_arquivados)),
        min_releases=min_releases,
        min_runs_validos=min_runs,
        idade_referencia=referencia,
        amostra_alvo=amostra_alvo,
    )


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
        selecao=_parse_selecao(raw.get("selecao") or {}),
        token_env=str(github.get("token_env") or DEFAULT_TOKEN_ENV),
        janela_inicio=inicio,
        janela_fim=fim,
        cache_dir=Path(caminhos.get("cache") or "cache"),
        saidas_dir=Path(caminhos.get("saidas") or "outputs"),
    )


def carregar_dotenv(path: str | Path = ".env", environ=None) -> bool:
    """Carrega `CHAVE=valor` de um .env para o ambiente, sem sobrescrever variáveis já definidas.

    Aceita comentários (#), `export CHAVE=...` e aspas simples/duplas. Devolve False se o
    arquivo não existe. Nunca loga valores.
    """
    environ = os.environ if environ is None else environ
    path = Path(path)
    if not path.is_file():
        return False
    for linha in path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.removeprefix("export ").partition("=")
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        environ.setdefault(chave.strip(), valor)
    return True


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
