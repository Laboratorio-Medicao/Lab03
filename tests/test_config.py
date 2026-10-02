from datetime import date

import pytest

from pipeline.config import ConfigError, get_token, load_config


def escrever(tmp_path, conteudo: str):
    caminho = tmp_path / "config.yaml"
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def test_config_do_repositorio_e_valido(raiz):
    config = load_config(raiz / "config.yaml")
    assert config.token_env == "GITHUB_TOKEN"
    assert not config.janela_definida  # datas ainda não definidas pelo professor


def test_config_do_repositorio_nao_contem_token(raiz):
    texto = (raiz / "config.yaml").read_text(encoding="utf-8")
    assert "ghp_" not in texto and "github_pat_" not in texto


def test_janela_valida(tmp_path):
    caminho = escrever(tmp_path, "janela:\n  inicio: 2025-01-01\n  fim: 2026-01-01\n")
    config = load_config(caminho)
    assert config.janela_inicio == date(2025, 1, 1)
    assert config.janela_fim == date(2026, 1, 1)
    assert config.janela_definida


def test_valores_padrao_quando_vazio(tmp_path):
    config = load_config(escrever(tmp_path, ""))
    assert config.token_env == "GITHUB_TOKEN"
    assert str(config.cache_dir) == "cache"


@pytest.mark.parametrize(
    "conteudo",
    [
        "janela:\n  inicio: 2025-01-01\n",  # só um dos lados
        "janela:\n  inicio: 2026-01-01\n  fim: 2025-01-01\n",  # fim antes do início
        "janela:\n  inicio: ontem\n  fim: hoje\n",  # data inválida
        "- isso\n- e uma lista\n",  # não é mapa
        "janela: [\n",  # YAML quebrado
    ],
)
def test_config_invalida(tmp_path, conteudo):
    with pytest.raises(ConfigError):
        load_config(escrever(tmp_path, conteudo))


def test_arquivo_inexistente(tmp_path):
    with pytest.raises(ConfigError, match="não encontrado"):
        load_config(tmp_path / "nao_existe.yaml")


def test_token_vem_da_variavel_de_ambiente(raiz):
    config = load_config(raiz / "config.yaml")
    assert get_token(config, {"GITHUB_TOKEN": " abc123 "}) == "abc123"


@pytest.mark.parametrize("ambiente", [{}, {"GITHUB_TOKEN": ""}, {"GITHUB_TOKEN": "   "}])
def test_token_ausente_gera_erro_claro(raiz, ambiente):
    config = load_config(raiz / "config.yaml")
    with pytest.raises(ConfigError, match="GITHUB_TOKEN"):
        get_token(config, ambiente)


def test_nome_da_variavel_e_configuravel(tmp_path):
    config = load_config(escrever(tmp_path, "github:\n  token_env: MEU_TOKEN\n"))
    assert get_token(config, {"MEU_TOKEN": "x"}) == "x"
