"""Sorteio da amostra-ouro e geração das planilhas de rotulagem (E§6, Sprint S02).

Uso (a partir da raiz do repositório):

    python -m scripts.sample_gold --config config.yaml

O que faz, sem chamar a API (lê só o cache de releases já coletado pelo pipeline):

1. Sorteia `N_REPOS` (60) repositórios da lista final, com semente fixa `SEED` (42).
2. Para cada repositório, sorteia `N_RELEASES` (5) releases de deploy da janela. O sorteio é
   um só: os três avaliadores recebem **as mesmas releases** (condição para o kappa de Fleiss).
3. Grava em `--saida` (padrão `data/amostra_ouro/`):
   - `amostra_ouro.csv`: sorteio completo (uma linha por release sorteada);
   - `sorteio.json`: semente, tamanhos, janela e hash da lista de entrada (reprodutibilidade);
   - `labels_<avaliador>.csv`: uma planilha por avaliador, com os links da release e as colunas
     (i) tipo do projeto, (ii) releases = entregas reais, (iii) corretiva sim/não;
   - `LEIAME.md`: instruções e valores válidos.

As planilhas não contêm nenhuma saída da heurística nem métricas DORA (E§6: rotular "sem ver a
saída da heurística").

Quando o professor informar a janela oficial: edite só `janela.inicio`/`janela.fim` no
`config.yaml`, refaça seleção e coleta (`python -m pipeline`, limpando o cache se a janela
mudou) e rode este script de novo. Se as planilhas já tiverem rótulos, ele aborta; `--forcar`
sobrescreve.

Reprodutibilidade: a lista de entrada é ordenada e deduplicada antes do sorteio, e as releases de
cada repositório são sorteadas com uma semente derivada de `SEED` e do `full_name`. Assim o
resultado não depende da ordem das linhas do CSV nem dos demais repositórios sorteados. Congele a
lista final (S02-019) antes de rodar: com outra lista, o sorteio muda.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import random
import sys
from datetime import date
from pathlib import Path

from pipeline.collect_releases import arquivo_cache, pares_com_anterior
from pipeline.config import ConfigError, load_config

log = logging.getLogger("scripts.sample_gold")

SEED = 42  # semente fixa e documentada (E§6)
N_REPOS = 60
N_RELEASES = 5
AVALIADORES_PADRAO = ("A", "B", "C")

TIPOS_PROJETO = ("biblioteca_framework", "aplicacao_servico", "ferramenta_cli", "outro")
ENTREGA_REAL = ("sim", "nao", "incerto")
CORRETIVA = ("sim", "nao")

COLUNAS_AMOSTRA = (
    "full_name", "repo_url", "release_id", "tag_name", "published_at", "release_url", "compare_url",
)
COLUNAS_PLANILHA = (
    "full_name", "repo_url", "tipo_projeto", "releases_sao_entregas_reais",
    "release_id", "tag_name", "published_at", "release_url", "compare_url", "corretiva", "observacoes",
)


def ler_repos(arquivo: Path) -> list[str]:
    """`full_name` únicos e ordenados. Se houver coluna `status`, só as linhas `concluido`."""
    with Path(arquivo).open(encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        if not leitor.fieldnames or "full_name" not in leitor.fieldnames:
            raise ValueError(f"{arquivo}: coluna 'full_name' ausente")
        filtrar = "status" in leitor.fieldnames
        nomes = {
            linha["full_name"].strip()
            for linha in leitor
            if linha["full_name"].strip() and (not filtrar or linha["status"].strip() == "concluido")
        }
    return sorted(nomes)


def sortear_repos(repos: list[str], n: int = N_REPOS, seed: int = SEED) -> list[str]:
    """`n` repositórios, determinístico para a mesma lista e semente (ordem de entrada irrelevante)."""
    base = sorted(set(repos))
    if len(base) < n:
        raise ValueError(f"lista final com {len(base)} repositórios; o sorteio pede {n}")
    return sorted(random.Random(seed).sample(base, n))


def sortear_releases(
    releases: list[dict],
    inicio: date,
    fim: date,
    full_name: str,
    n: int = N_RELEASES,
    seed: int = SEED,
) -> list[tuple[dict | None, dict]]:
    """`n` pares (anterior, release) de deploy publicados na janela, em ordem cronológica.

    A semente depende do `full_name`, então o resultado de um repositório é independente dos
    demais. Com menos de `n` releases elegíveis, devolve todas (e o chamador avisa).
    """
    pares = pares_com_anterior(releases, inicio, fim)
    if len(pares) <= n:
        return pares
    escolhidos = random.Random(f"{seed}/{full_name.lower()}").sample(range(len(pares)), n)
    return [pares[i] for i in sorted(escolhidos)]


def _linha_release(full_name: str, anterior: dict | None, release: dict) -> dict:
    repo_url = f"https://github.com/{full_name}"
    tag = release["tag_name"]
    return {
        "full_name": full_name,
        "repo_url": repo_url,
        "release_id": release["id"],
        "tag_name": tag,
        "published_at": release["published_at"],
        "release_url": release.get("html_url") or f"{repo_url}/releases/tag/{tag}",
        # lista de commits da release: comparação com a release anterior (vazia para a 1ª da história)
        "compare_url": f"{repo_url}/compare/{anterior['tag_name']}...{tag}" if anterior else "",
    }


def montar_amostra(
    repos: list[str],
    cache_dir: Path,
    inicio: date,
    fim: date,
    n_releases: int = N_RELEASES,
    seed: int = SEED,
) -> list[dict]:
    """Uma linha por release sorteada, repositórios em ordem alfabética, releases cronológicas."""
    linhas: list[dict] = []
    for full_name in repos:
        arquivo = arquivo_cache(cache_dir, full_name)
        if not arquivo.exists():
            raise FileNotFoundError(
                f"{full_name}: sem cache de releases em {arquivo}. "
                "Rode o pipeline (python -m pipeline) antes de sortear."
            )
        releases = json.loads(arquivo.read_text(encoding="utf-8"))["releases"]
        pares = sortear_releases(releases, inicio, fim, full_name, n_releases, seed)
        if len(pares) < n_releases:
            log.warning("%s: só %d releases elegíveis na janela (pedidas %d)", full_name, len(pares), n_releases)
        linhas.extend(_linha_release(full_name, anterior, r) for anterior, r in pares)
    return linhas


def linhas_planilha(amostra: list[dict]) -> list[dict]:
    """Planilha de um avaliador, em branco. (i) e (ii) são do repositório: preenchidas na 1ª linha dele."""
    linhas: list[dict] = []
    for item in amostra:
        linhas.append({
            "full_name": item["full_name"],
            "repo_url": item["repo_url"],
            "tipo_projeto": "",
            "releases_sao_entregas_reais": "",
            "release_id": item["release_id"],
            "tag_name": item["tag_name"],
            "published_at": item["published_at"],
            "release_url": item["release_url"],
            "compare_url": item["compare_url"],
            "corretiva": "",
            "observacoes": "",
        })
    return linhas


CAMPOS_ROTULO = ("tipo_projeto", "releases_sao_entregas_reais", "corretiva", "observacoes")


def planilhas_preenchidas(saida: Path) -> list[Path]:
    """Planilhas `labels_*.csv` já existentes com algum rótulo preenchido (regerar as apagaria)."""
    achadas = []
    for arquivo in sorted(Path(saida).glob("labels_*.csv")):
        with arquivo.open(encoding="utf-8-sig", newline="") as f:
            if any((linha.get(c) or "").strip() for linha in csv.DictReader(f) for c in CAMPOS_ROTULO):
                achadas.append(arquivo)
    return achadas


def _escrever_csv(arquivo: Path, colunas: tuple[str, ...], linhas: list[dict]) -> None:
    # utf-8-sig: o Excel abre com acentos corretos; o leitor Python tolera o BOM.
    with arquivo.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore", lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def _sha256(arquivo: Path) -> str:
    return hashlib.sha256(Path(arquivo).read_bytes()).hexdigest()


def _leiame(avaliadores: tuple[str, ...]) -> str:
    return f"""# Rotulagem da amostra-ouro

Cada avaliador ({", ".join(avaliadores)}) preenche **somente o seu arquivo** `labels_<avaliador>.csv`,
sem consultar os demais e sem ver a saída da heurística de release corretiva. As releases são as
mesmas nos três arquivos.

## Colunas a preencher

| Coluna | Onde preencher | Valores válidos |
|---|---|---|
| `tipo_projeto` | primeira linha de cada repositório | {" · ".join(f"`{v}`" for v in TIPOS_PROJETO)} |
| `releases_sao_entregas_reais` | primeira linha de cada repositório | {" · ".join(f"`{v}`" for v in ENTREGA_REAL)} |
| `corretiva` | todas as linhas (uma por release) | {" · ".join(f"`{v}`" for v in CORRETIVA)} |
| `observacoes` | opcional | texto livre |

- `release_url`: página da release (leia as *release notes*).
- `compare_url`: lista de commits entre a release anterior e esta (vazia na primeira release da história).
- Não altere nem reordene as demais colunas: a consolidação do kappa casa as linhas por `release_id`.
- Commite o arquivo preenchido com `#N` da sua Issue de rotulagem.

Sorteio: semente `{SEED}`, {N_REPOS} repositórios, {N_RELEASES} releases por repositório
(ver `sorteio.json`). Gerado por `python -m scripts.sample_gold`.
"""


def gerar(
    repos_csv: Path,
    cache_dir: Path,
    inicio: date,
    fim: date,
    saida: Path,
    avaliadores: tuple[str, ...] = AVALIADORES_PADRAO,
    n_repos: int = N_REPOS,
    n_releases: int = N_RELEASES,
    seed: int = SEED,
    forcar: bool = False,
) -> list[dict]:
    """Executa o sorteio completo e grava os arquivos em `saida`. Devolve a amostra (uma linha por release).

    Recusa-se a sobrescrever planilhas já preenchidas, a menos que `forcar=True`.
    """
    if len(set(avaliadores)) != len(avaliadores) or not avaliadores:
        raise ValueError("avaliadores: informe nomes distintos")
    preenchidas = planilhas_preenchidas(saida)
    if preenchidas and not forcar:
        nomes = ", ".join(p.name for p in preenchidas)
        raise ValueError(
            f"já há rótulos preenchidos em {nomes}; regerar apagaria o trabalho dos avaliadores. "
            "Use --forcar se for isso mesmo que quer."
        )
    repos = sortear_repos(ler_repos(repos_csv), n_repos, seed)
    amostra = montar_amostra(repos, cache_dir, inicio, fim, n_releases, seed)

    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    _escrever_csv(saida / "amostra_ouro.csv", COLUNAS_AMOSTRA, amostra)
    for nome in avaliadores:
        _escrever_csv(saida / f"labels_{nome}.csv", COLUNAS_PLANILHA, linhas_planilha(amostra))
    (saida / "sorteio.json").write_text(
        json.dumps({
            "seed": seed,
            "n_repos": n_repos,
            "n_releases_por_repo": n_releases,
            "n_linhas": len(amostra),
            "janela": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
            "lista_entrada": Path(repos_csv).name,
            "lista_entrada_sha256": _sha256(repos_csv),
            "avaliadores": list(avaliadores),
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (saida / "LEIAME.md").write_text(_leiame(avaliadores), encoding="utf-8")
    log.info("amostra-ouro: %d repositórios, %d releases -> %s", len(repos), len(amostra), saida)
    return amostra


LISTA_FINAL = Path("data/repos_final.csv")


def _lista_padrao(saidas_dir: Path) -> Path:
    """Lista final congelada (S02) se existir; senão o resultado da última execução do pipeline."""
    return LISTA_FINAL if LISTA_FINAL.is_file() else Path(saidas_dir) / "resultados.csv"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m scripts.sample_gold",
        description="Sorteia a amostra-ouro (semente fixa) e gera as planilhas de rotulagem.",
    )
    p.add_argument("--config", default="config.yaml", help="config.yaml (cache e janela)")
    p.add_argument(
        "--repos",
        help="CSV com coluna full_name (padrão: data/repos_final.csv se existir; senão <saidas>/resultados.csv)",
    )
    p.add_argument("--forcar", action="store_true", help="sobrescreve planilhas já preenchidas pelos avaliadores")
    p.add_argument("--saida", default="data/amostra_ouro", help="diretório de saída")
    p.add_argument("--avaliadores", nargs="+", default=list(AVALIADORES_PADRAO), help="nomes dos avaliadores")
    return p


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if not config.janela_definida:
            raise ConfigError("janela de observação não definida no config")
        repos_csv = Path(args.repos) if args.repos else _lista_padrao(config.saidas_dir)
        log.info("janela: %s a %s | lista: %s", config.janela_inicio, config.janela_fim, repos_csv)
        gerar(
            repos_csv, config.cache_dir, config.janela_inicio, config.janela_fim,
            Path(args.saida), tuple(args.avaliadores), forcar=args.forcar,
        )
    except (ConfigError, ValueError, FileNotFoundError, OSError) as exc:
        log.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
