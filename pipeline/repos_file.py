"""Entrada por lista de repositórios (`--repos-file`, Issue #36): substitui a Search API.

Serve à replicação cruzada (E§9): o grupo replicador roda o pipeline sobre os 30 repositórios do
dataset original, sem refazer a busca. Os metadados vêm de `GET /repos/{owner}/{repo}` e os
filtros do funil (Actions, releases, runs) são os mesmos da seleção normal, então o funil mostra
o que mudou desde a coleta original. Sem corte por `amostra_alvo`: a lista é a amostra.

Formatos aceitos:
- texto: um `owner/repo` por linha (também `https://github.com/owner/repo`, com ou sem `.git`);
  linhas em branco e `#` (linha inteira ou final de linha) são ignoradas;
- `.csv`: coluna `full_name` (como `data/metrics.csv` e `outputs/repos_final.csv`).
"""

from __future__ import annotations

import csv
import logging
import re
from datetime import date
from pathlib import Path

from pipeline.config import ConfigError, SelecaoConfig
from pipeline.selection import ApiError, RepoRecord, ResultadoSelecao, _descartar, _get, avaliar

log = logging.getLogger("pipeline.repos_file")

COLUNA_CSV = "full_name"
_NOME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_PREFIXO_URL = re.compile(r"^https?://github\.com/", re.IGNORECASE)


def _normalizar(bruto: str) -> str:
    nome = _PREFIXO_URL.sub("", bruto.strip()).rstrip("/")
    return nome.removesuffix(".git")


def _validar(nomes: list[tuple[str, str]], origem: Path) -> list[str]:
    """Valida `(onde, texto)`, remove duplicatas (sem diferenciar caixa) e preserva a ordem."""
    vistos: set[str] = set()
    saida: list[str] = []
    for onde, bruto in nomes:
        nome = _normalizar(bruto)
        if not _NOME.match(nome):
            raise ConfigError(f"{origem}: {onde}: {bruto!r} não é um repositório no formato owner/repo")
        if nome.lower() in vistos:
            continue
        vistos.add(nome.lower())
        saida.append(nome)
    if not saida:
        raise ConfigError(f"{origem}: nenhum repositório na lista")
    return saida


def ler_lista(caminho: str | Path) -> list[str]:
    """Lê a lista de repositórios (`owner/repo`) de um .txt ou .csv; erro claro se inválida."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ConfigError(f"arquivo de repositórios não encontrado: {caminho}")
    try:
        if caminho.suffix.lower() == ".csv":
            with caminho.open(newline="", encoding="utf-8-sig") as f:
                leitor = csv.DictReader(f)
                if COLUNA_CSV not in (leitor.fieldnames or []):
                    raise ConfigError(f"{caminho}: o CSV precisa da coluna {COLUNA_CSV!r}")
                itens = [(f"linha {i}", (linha[COLUNA_CSV] or "")) for i, linha in enumerate(leitor, 2)]
        else:
            itens = []
            for i, linha in enumerate(caminho.read_text(encoding="utf-8-sig").splitlines(), 1):
                texto = linha.split("#", 1)[0].strip()
                if texto:
                    itens.append((f"linha {i}", texto))
    except UnicodeDecodeError:
        raise ConfigError(f"{caminho}: o arquivo precisa estar em UTF-8") from None
    return _validar([i for i in itens if i[1].strip()], caminho)


def selecionar_lista(
    client, nomes: list[str], sel: SelecaoConfig, inicio: date, fim: date, ao_avaliar=None
) -> ResultadoSelecao:
    """Avalia cada repositório da lista com os filtros do funil, na ordem recebida."""
    res = ResultadoSelecao([], [], 0, len(nomes), origem="lista de repositórios (--repos-file)")
    for i, nome in enumerate(nomes, 1):
        try:
            item = _get(client, f"/repos/{nome}", None).json()
            reg = avaliar(client, item, sel, inicio, fim)
        except ApiError as exc:
            log.warning("%s: %s ao ler os metadados", nome, exc)
            motivo = "repo_not_found" if exc.status in (404, 410) else f"api_error_{exc.status}"
            reg = _descartar(RepoRecord(nome, 0, None, "", ""), "actions", motivo)
        log.info("[%d/%d] %s -> %s%s", i, len(nomes), reg.full_name, reg.status, f" ({reg.motivo})" if reg.motivo else "")
        res.registros.append(reg)
        if ao_avaliar is not None and i % 10 == 0:
            ao_avaliar(res)
    if ao_avaliar is not None:
        ao_avaliar(res)
    return res
