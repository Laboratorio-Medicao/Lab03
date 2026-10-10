"""Concordância entre avaliadores (kappa de Fleiss) e rótulo de consenso (E§6, Issue #26).

Uso (a partir da raiz do repositório):

    python -m scripts.agreement data/amostra_ouro/labels_marcos.csv \
        data/amostra_ouro/labels_arthur.csv data/amostra_ouro/labels_guilherme.csv

Lê as três planilhas preenchidas (uma por avaliador, mesmas linhas) e, para cada dimensão:

- (i) `tipo_projeto` e (ii) `releases_sao_entregas_reais`: um item por repositório;
- (iii) `corretiva`: um item por release sorteada.

Calcula o kappa de Fleiss com `aggregate_raters` + `fleiss_kappa` (statsmodels), a
interpretação de Landis & Koch (1977) e a concordância simples, e grava em `--saida`
(padrão: a pasta das planilhas):

- `concordancia.csv`: uma linha por dimensão (kappa, interpretação, % de concordância);
- `consenso.csv`: uma linha por item e dimensão, com os 3 rótulos e o rótulo de consenso.

Protocolo de desempate (ver `PROTOCOLO_CONSENSO.md`): unanimidade e maioria simples (2 a 1) são
resolvidas automaticamente; 1-1-1 fica `pendente` e é decidido na reunião, registrado em
`desempate.csv` (colunas `dimensao,item_id,rotulo,justificativa`) e aplicado na próxima execução.
Casos pendentes fazem o comando sair com código 2 (o consenso ainda não está completo).
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa

from scripts.validar_rotulos import validar

DIMENSOES = (
    # (nome, coluna, nível do item)
    ("tipo_projeto", "tipo_projeto", "repo"),
    ("entrega_real", "releases_sao_entregas_reais", "repo"),
    ("corretiva", "corretiva", "release"),
)

COLUNAS_CONCORDANCIA = ("dimensao", "n_itens", "n_avaliadores", "kappa_fleiss", "interpretacao", "concordancia_simples")
COLUNAS_DESEMPATE = ("dimensao", "item_id", "rotulo", "justificativa")


def interpretar(kappa: float) -> str:
    """Landis & Koch (1977); `indefinido` quando não há variação nos rótulos (kappa = 0/0)."""
    if kappa is None or math.isnan(kappa):
        return "indefinido"
    if kappa < 0:
        return "pobre"
    if kappa <= 0.20:
        return "leve"
    if kappa <= 0.40:
        return "razoável"
    if kappa <= 0.60:
        return "moderada"
    if kappa <= 0.80:
        return "substancial"
    return "quase perfeita"


def kappa_fleiss(avaliacoes: list[list[str]]) -> float:
    """Kappa de Fleiss de `avaliacoes[item] = [rótulo de cada avaliador]` (mesmo nº de avaliadores).

    `nan` se todos deram o mesmo rótulo em todos os itens (concordância esperada = 1).
    """
    if not avaliacoes:
        raise ValueError("sem itens para calcular o kappa")
    if len({r for item in avaliacoes for r in item}) < 2:
        return float("nan")
    codigos = {r: i for i, r in enumerate(sorted({r for item in avaliacoes for r in item}))}
    matriz = np.array([[codigos[r] for r in item] for item in avaliacoes])
    tabela, _ = aggregate_raters(matriz)
    return float(fleiss_kappa(tabela, method="fleiss"))


def concordancia_simples(avaliacoes: list[list[str]]) -> float:
    """Fração de itens em que todos os avaliadores deram o mesmo rótulo (só informativa)."""
    return sum(len(set(item)) == 1 for item in avaliacoes) / len(avaliacoes)


def resolver(rotulos: list[str]) -> tuple[str, str]:
    """(rótulo, método) pelo protocolo: unanimidade, maioria (2 a 1) ou pendente (sem maioria)."""
    (rotulo, votos), = Counter(rotulos).most_common(1)
    if votos == len(rotulos):
        return rotulo, "unanimidade"
    if votos > len(rotulos) / 2:
        return rotulo, "maioria"
    return "", "pendente"


def ler_planilha(arquivo: Path) -> list[dict]:
    with Path(arquivo).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def itens_da_planilha(linhas: list[dict], coluna: str, nivel: str) -> dict[str, tuple[str, str]]:
    """`item_id -> (rótulo, descrição)`. Repo: 1ª linha de cada `full_name`; release: `release_id`."""
    itens: dict[str, tuple[str, str]] = {}
    for linha in linhas:
        if nivel == "repo":
            chave, descricao = linha["full_name"], linha["full_name"]
            if chave in itens:
                continue
        else:
            chave, descricao = str(linha["release_id"]), f"{linha['full_name']} {linha['tag_name']}"
        itens[chave] = (linha[coluna].strip(), descricao)
    return itens


def ler_desempate(arquivo: Path | None) -> dict[tuple[str, str], tuple[str, str]]:
    """`(dimensao, item_id) -> (rótulo, justificativa)` das decisões da reunião (arquivo opcional)."""
    if arquivo is None or not Path(arquivo).is_file():
        return {}
    with Path(arquivo).open(encoding="utf-8-sig", newline="") as f:
        return {
            (r["dimensao"].strip(), r["item_id"].strip()): (r["rotulo"].strip(), r.get("justificativa", "").strip())
            for r in csv.DictReader(f)
            if r.get("rotulo", "").strip()
        }


def analisar(
    planilhas: dict[str, list[dict]],
    desempate: dict[tuple[str, str], tuple[str, str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    """(linhas de concordancia.csv, linhas de consenso.csv) para as planilhas dos avaliadores."""
    desempate = desempate or {}
    avaliadores = list(planilhas)
    if len(avaliadores) < 2:
        raise ValueError("são necessários ao menos 2 avaliadores")
    concordancia: list[dict] = []
    consenso: list[dict] = []
    for dimensao, coluna, nivel in DIMENSOES:
        por_avaliador = {a: itens_da_planilha(planilhas[a], coluna, nivel) for a in avaliadores}
        ids = list(por_avaliador[avaliadores[0]])
        for a in avaliadores[1:]:
            if list(por_avaliador[a]) != ids:
                raise ValueError(f"{a}: itens da dimensão {dimensao} diferem dos de {avaliadores[0]}")
        avaliacoes = [[por_avaliador[a][i][0] for a in avaliadores] for i in ids]
        kappa = kappa_fleiss(avaliacoes)
        concordancia.append({
            "dimensao": dimensao,
            "n_itens": len(ids),
            "n_avaliadores": len(avaliadores),
            "kappa_fleiss": "" if math.isnan(kappa) else f"{kappa:.4f}",
            "interpretacao": interpretar(kappa),
            "concordancia_simples": f"{concordancia_simples(avaliacoes):.4f}",
        })
        for item_id, rotulos in zip(ids, avaliacoes):
            rotulo, metodo = resolver(rotulos)
            justificativa = ""
            if metodo == "pendente" and (dimensao, item_id) in desempate:
                rotulo, justificativa = desempate[(dimensao, item_id)]
                metodo = "reuniao"
            consenso.append({
                "dimensao": dimensao,
                "item_id": item_id,
                "descricao": por_avaliador[avaliadores[0]][item_id][1],
                **dict(zip(avaliadores, rotulos)),
                "rotulo_consenso": rotulo,
                "metodo": metodo,
                "justificativa": justificativa,
            })
    return concordancia, consenso


def _escrever(arquivo: Path, colunas: list[str] | tuple[str, ...], linhas: list[dict]) -> None:
    with Path(arquivo).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(colunas), lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def nome_avaliador(arquivo: Path) -> str:
    """`labels_marcos.csv` -> `marcos`."""
    return Path(arquivo).stem.removeprefix("labels_")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m scripts.agreement", description="Kappa de Fleiss e consenso.")
    p.add_argument("planilhas", nargs="+", help="labels_<nome>.csv preenchidos (um por avaliador)")
    p.add_argument("--saida", help="diretório de saída (padrão: pasta da primeira planilha)")
    p.add_argument("--desempate", help="CSV com as decisões da reunião (padrão: <saida>/desempate.csv)")
    args = p.parse_args(argv)

    arquivos = [Path(a) for a in args.planilhas]
    saida = Path(args.saida) if args.saida else arquivos[0].parent
    try:
        for arq in arquivos:
            problemas = validar(arq, saida / "amostra_ouro.csv" if (saida / "amostra_ouro.csv").is_file() else None)
            if problemas:
                print(f"{arq.name}: planilha incompleta ou inválida ({len(problemas)} pendências, "
                      f"rode scripts.validar_rotulos). Ex.: {problemas[0]}", file=sys.stderr)
                return 1
        nomes = [nome_avaliador(a) for a in arquivos]
        if len(set(nomes)) != len(nomes):
            print("avaliadores com o mesmo nome de arquivo", file=sys.stderr)
            return 1
        planilhas = {n: ler_planilha(a) for n, a in zip(nomes, arquivos)}
        desempate = ler_desempate(Path(args.desempate) if args.desempate else saida / "desempate.csv")
        concordancia, consenso = analisar(planilhas, desempate)
        _escrever(saida / "concordancia.csv", COLUNAS_CONCORDANCIA, concordancia)
        _escrever(saida / "consenso.csv",
                  ["dimensao", "item_id", "descricao", *nomes, "rotulo_consenso", "metodo", "justificativa"], consenso)
    except (OSError, ValueError, KeyError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1

    for c in concordancia:
        kappa = c["kappa_fleiss"] or "indefinido"
        print(f"{c['dimensao']:<13} n={c['n_itens']:<4} kappa={kappa:<8} ({c['interpretacao']}); "
              f"concordância simples {float(c['concordancia_simples']):.1%}")
    metodos = Counter(r["metodo"] for r in consenso)
    print("consenso:", ", ".join(f"{m}={n}" for m, n in sorted(metodos.items())))
    if metodos.get("pendente"):
        print(f"{metodos['pendente']} caso(s) 1-1-1 pendente(s): decida na reunião e registre em desempate.csv",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
