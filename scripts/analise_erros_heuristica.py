"""Análise de erros da heurística de release corretiva (Issue #30, bônus).

Uso (a partir da raiz do repositório, depois da rodada de `scripts.evaluate_heuristic`, #28):

    python -m scripts.analise_erros_heuristica [--versao vN]

Lê `heuristica_amostra.csv` e `avaliacao_heuristica.csv` (#28), o consenso da dimensão `corretiva` e os
links de `amostra_ouro.csv`. A versão analisada é `--versao` ou a `escolhida` na avaliação. Gera em
`data/amostra_ouro/`:

- `erros_heuristica.csv`: um falso positivo (FP) ou falso negativo (FN) por linha, com a causa automática e
  a coluna `causa_manual` para o grupo anotar lendo os commits (ex.: "fix em docs"). As anotações são
  preservadas por `release_id` quando o arquivo é regravado;
- `erros_heuristica.md`: matriz de confusão, contagem por causa, comparação entre versões, lista de FP/FN e
  um resumo para Ameaças à validade (construto).

**Taxonomia automática** (só a partir dos sinais; uma causa por erro, pela ordem abaixo). A "palavra" é o
sinal que a própria versão usa (`PALAVRA_DA_VERSAO`).

- FP: `palavra_sem_semver` > `patch_e_palavra_sem_correcao` > `patch_sem_palavra` > `palavra_sem_patch`.
- FN: `sem_release_anterior` > `commits_indisponiveis` > `palavra_ampla_nao_estrita` > `palavra_sem_patch`
  > `patch_sem_palavra` > `nao_semver_sem_palavra` > `sem_sinal`. As duas causas "de palavra" são
  contrafactuais com a regra da versão: `commits_indisponiveis` só se as mensagens faltantes poderiam mudar
  a predição; `palavra_ampla_nao_estrita` (versões estritas) só se trocar a palavra estrita pela ampla
  corrigiria o erro.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from metricas.heuristica import VERSOES
from scripts.evaluate_heuristic import ARQ_AVALIACAO, ARQ_HEURISTICA, AvaliacaoError, consenso_corretiva

ARQ_ERROS = "erros_heuristica.csv"
ARQ_RELATORIO = "erros_heuristica.md"
ARQ_CONSENSO = "consenso.csv"
PALAVRA_DA_VERSAO = {
    "v1": "palavra_chave", "v2": "palavra_chave", "v3": "palavra_chave", "v4": "palavra_chave",
    "v5": "palavra_chave_ampla", "v6": "palavra_chave_ampla", "v7": "palavra_chave_ampla",
}
VERSOES_DE_CONTEUDO = ("v8", "v9")  # decidem por commits/notas; causa automática genérica (anotar `causa_manual`)
COLUNAS_ERROS = (
    "versao", "release_id", "full_name", "tag_name", "base", "tipo_erro", "causa_automatica",
    "semver_patch", "palavra_chave", "palavra_chave_ampla", "mensagens_incompletas",
    "release_url", "compare_url", "causa_manual",
)
_BOOL = {"sim": True, "nao": False, "": None}


def _ler_csv(arquivo: Path) -> list[dict]:
    with Path(arquivo).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sinais(linha: dict) -> dict:
    """Sinais de uma linha de `heuristica_amostra.csv` como booleanos (`semver_patch` vazio → None)."""
    return {
        "semver_patch": _BOOL[linha["semver_patch"]],
        "palavra_chave": linha["palavra_chave"] == "sim",
        "palavra_chave_ampla": linha["palavra_chave_ampla"] == "sim",
    }


def causa(linha: dict, versao: str, tipo_erro: str) -> str:
    """Causa automática de um FP ou FN da `versao` (ver precedência no docstring do módulo)."""
    if versao in VERSOES_DE_CONTEUDO:
        return "conteudo_corretivo_sem_consenso" if tipo_erro == "FP" else "conteudo_sem_sinal_corretivo"
    if versao not in PALAVRA_DA_VERSAO:
        raise AvaliacaoError(f"versão {versao} sem sinal de palavra em PALAVRA_DA_VERSAO: atualize o mapa")
    s = sinais(linha)
    campo = PALAVRA_DA_VERSAO[versao]
    patch, palavra = s["semver_patch"], s[campo]
    if tipo_erro == "FP":
        if patch is None:
            return "palavra_sem_semver"
        if patch and palavra:
            return "patch_e_palavra_sem_correcao"
        if patch:
            return "patch_sem_palavra"
        return "palavra_sem_patch"
    regra = VERSOES[versao].regra
    if linha["status"] == "sem_anterior":
        return "sem_release_anterior"
    if linha["mensagens_incompletas"] == "sim" and regra({**s, campo: True}):
        return "commits_indisponiveis"
    if campo == "palavra_chave" and regra({**s, "palavra_chave": s["palavra_chave_ampla"]}):
        return "palavra_ampla_nao_estrita"
    if patch is False and (s["palavra_chave"] or s["palavra_chave_ampla"]):
        return "palavra_sem_patch"
    if patch:
        return "patch_sem_palavra"
    if patch is None:
        return "nao_semver_sem_palavra"
    return "sem_sinal"


def _acertou(linha: dict, versao: str, consenso: dict[str, int]) -> bool:
    return (linha[versao] == "sim") == bool(consenso[linha["release_id"]])


def matriz(linhas: list[dict], consenso: dict[str, int], versao: str) -> dict[str, int]:
    contagem = Counter()
    for l in linhas:
        previsto, real = l[versao] == "sim", bool(consenso[l["release_id"]])
        contagem[("t" if previsto == real else "f") + ("p" if previsto else "n")] += 1
    return {k: contagem[k] for k in ("tp", "fp", "fn", "tn")}


def listar_erros(linhas: list[dict], consenso: dict[str, int], versao: str, links: dict[str, dict]) -> list[dict]:
    erros = []
    for l in linhas:
        if _acertou(l, versao, consenso):
            continue
        tipo = "FP" if l[versao] == "sim" else "FN"
        link = links.get(l["release_id"], {})
        erros.append({
            "versao": versao, "release_id": l["release_id"], "full_name": l["full_name"], "tag_name": l["tag_name"],
            "base": l["base"], "tipo_erro": tipo, "causa_automatica": causa(l, versao, tipo),
            "semver_patch": l["semver_patch"], "palavra_chave": l["palavra_chave"],
            "palavra_chave_ampla": l["palavra_chave_ampla"], "mensagens_incompletas": l["mensagens_incompletas"],
            "release_url": link.get("release_url", ""), "compare_url": link.get("compare_url", ""), "causa_manual": "",
        })
    return erros


def preservar_anotacoes(erros: list[dict], anteriores: list[dict]) -> tuple[list[dict], int]:
    """Copia `causa_manual` das linhas anteriores por `release_id`; devolve quantas anotações saíram do CSV."""
    anotacoes = {a["release_id"]: a["causa_manual"] for a in anteriores if (a.get("causa_manual") or "").strip()}
    atuais = {e["release_id"] for e in erros}
    for e in erros:
        e["causa_manual"] = anotacoes.get(e["release_id"], "")
    return erros, sum(1 for rid in anotacoes if rid not in atuais)


def comparar_versoes(linhas: list[dict], consenso: dict[str, int], versao: str, avaliacao: list[dict]) -> list[dict]:
    """Métricas de cada versão (de `avaliacao_heuristica.csv`) + quantas releases ela corrige/piora frente à `versao`."""
    tabela = []
    for a in avaliacao:
        outra = a["versao"]
        corrige = sum(1 for l in linhas if not _acertou(l, versao, consenso) and _acertou(l, outra, consenso))
        piora = sum(1 for l in linhas if _acertou(l, versao, consenso) and not _acertou(l, outra, consenso))
        tabela.append({**a, "corrige": corrige, "piora": piora})
    return tabela


def _pct(parte: int, todo: int) -> str:
    return f"{parte / todo:.0%}" if todo else "—"


def relatorio_md(versao: str, m: dict, erros: list[dict], comparacao: list[dict]) -> str:
    por_tipo = {t: Counter(e["causa_automatica"] for e in erros if e["tipo_erro"] == t) for t in ("FP", "FN")}
    marcadas, reais = m["tp"] + m["fp"], m["tp"] + m["fn"]
    partes = [
        f"# Análise de erros da heurística — versão {versao}",
        "",
        "Gerado por `python -m scripts.analise_erros_heuristica` (Issue #30) a partir da rodada da #28.",
        "",
        "## Matriz de confusão",
        "",
        "| | Consenso: corretiva | Consenso: não |",
        "|---|---:|---:|",
        f"| **Heurística: corretiva** | {m['tp']} (TP) | {m['fp']} (FP) |",
        f"| **Heurística: não** | {m['fn']} (FN) | {m['tn']} (TN) |",
        "",
        "## Causas (triagem automática)",
        "",
        "| Tipo | Causa | Releases |",
        "|---|---|---:|",
    ]
    for tipo in ("FP", "FN"):
        partes += [f"| {tipo} | `{c}` | {n} |" for c, n in por_tipo[tipo].most_common()]
    partes += [
        "",
        f"## Comparação entre versões (frente à {versao})",
        "",
        "\"Corrige\": releases que a versão acerta e a analisada erra; \"piora\": o contrário.",
        "",
        "| Versão | Regra | Precisão | Recall | F1 | TP | FP | FN | TN | Corrige | Piora |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    partes += [
        f"| {c['versao']} | {c['descricao']} | {float(c['precisao']):.2f} | {float(c['recall']):.2f} "
        f"| {float(c['f1']):.2f} | {c['tp']} | {c['fp']} | {c['fn']} | {c['tn']} | {c['corrige']} | {c['piora']} |"
        for c in comparacao
    ]
    partes += ["", "## Falsos positivos e falsos negativos", "",
               "| Tipo | Release | Base | Causa automática | Causa manual |", "|---|---|---|---|---|"]
    partes += [
        f"| {e['tipo_erro']} | [{e['full_name']} {e['tag_name']}]({e['release_url']}) | {e['base'] or '—'} "
        f"| `{e['causa_automatica']}` | {e['causa_manual']} |"
        for e in erros
    ]
    principal = {t: (por_tipo[t].most_common(1)[0] if por_tipo[t] else ("—", 0)) for t in ("FP", "FN")}
    indisponiveis = por_tipo["FN"]["commits_indisponiveis"]
    partes += [
        "",
        "## Resumo para Ameaças à validade (construto)",
        "",
        f"Na versão {versao}, {m['fp']} das {marcadas} releases marcadas como corretivas são falsos positivos "
        f"({_pct(m['fp'], marcadas)}) e {m['fn']} das {reais} corretivas do consenso não foram encontradas "
        f"({_pct(m['fn'], reais)}). Causa mais frequente de FP: `{principal['FP'][0]}` ({principal['FP'][1]}); "
        f"de FN: `{principal['FN'][0]}` ({principal['FN'][1]}). {indisponiveis} FN se devem a commits "
        "indisponíveis (`compare` 404 ou truncado). O CFR (b) herda esses erros: FP inflam e FN reduzem a taxa.",
    ]
    return "\n".join(partes) + "\n"


def _escrever_csv(arquivo: Path, linhas: list[dict]) -> None:
    with Path(arquivo).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(COLUNAS_ERROS), lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def executar(amostra_dir: Path, versao: str | None = None) -> dict:
    """Fluxo completo; devolve `{versao, matriz, erros, descartadas}` e grava os 2 arquivos."""
    amostra_dir = Path(amostra_dir)
    faltando = [n for n in (ARQ_HEURISTICA, ARQ_AVALIACAO, ARQ_CONSENSO) if not (amostra_dir / n).is_file()]
    if faltando:
        raise AvaliacaoError(f"insumos ausentes em {amostra_dir}: {', '.join(faltando)}; rode antes "
                             "`python -m scripts.evaluate_heuristic` (#28)")
    linhas = _ler_csv(amostra_dir / ARQ_HEURISTICA)
    avaliacao = _ler_csv(amostra_dir / ARQ_AVALIACAO)
    consenso = consenso_corretiva(amostra_dir / ARQ_CONSENSO)
    if versao is None:
        versao = next((a["versao"] for a in avaliacao if a["escolhida"] == "sim"), None)
    por_versao = {a["versao"]: a for a in avaliacao}
    if versao not in por_versao or (linhas and versao not in linhas[0]):
        raise AvaliacaoError(f"versão {versao!r} não está em {ARQ_AVALIACAO} e {ARQ_HEURISTICA}")
    if {l["release_id"] for l in linhas} != set(consenso):
        raise AvaliacaoError(f"releases de {ARQ_HEURISTICA} e do consenso diferem: rode a #28 de novo")

    m = matriz(linhas, consenso, versao)
    if any(int(por_versao[versao][k]) != m[k] for k in m):
        raise AvaliacaoError(f"matriz da {versao} difere de {ARQ_AVALIACAO}: insumos de rodadas diferentes")
    links = {}
    if (amostra_dir / "amostra_ouro.csv").is_file():
        links = {r["release_id"]: r for r in _ler_csv(amostra_dir / "amostra_ouro.csv")}
    erros = listar_erros(linhas, consenso, versao, links)
    anteriores = _ler_csv(amostra_dir / ARQ_ERROS) if (amostra_dir / ARQ_ERROS).is_file() else []
    erros, descartadas = preservar_anotacoes(erros, anteriores)
    comparacao = comparar_versoes(linhas, consenso, versao, avaliacao)
    _escrever_csv(amostra_dir / ARQ_ERROS, erros)
    (amostra_dir / ARQ_RELATORIO).write_text(relatorio_md(versao, m, erros, comparacao), encoding="utf-8")
    return {"versao": versao, "matriz": m, "erros": erros, "descartadas": descartadas}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m scripts.analise_erros_heuristica", description=__doc__.splitlines()[0])
    p.add_argument("--amostra-dir", default="data/amostra_ouro", help="pasta da amostra-ouro")
    p.add_argument("--versao", help="versão a analisar (padrão: a escolhida em avaliacao_heuristica.csv)")
    args = p.parse_args(argv)
    try:
        r = executar(Path(args.amostra_dir), args.versao)
    except AvaliacaoError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return exc.codigo
    except (OSError, KeyError, ValueError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    m = r["matriz"]
    print(f"versão {r['versao']}: TP={m['tp']} FP={m['fp']} FN={m['fn']} TN={m['tn']}")
    for (tipo, c), n in sorted(Counter((e["tipo_erro"], e["causa_automatica"]) for e in r["erros"]).items()):
        print(f"  {tipo} {c}: {n}")
    if r["descartadas"]:
        print(f"aviso: {r['descartadas']} anotação(ões) de causa_manual saíram do CSV (releases que deixaram de ser "
              "erro nesta versão); o histórico fica no git")
    print(f"gravados em {args.amostra_dir}: {ARQ_ERROS}, {ARQ_RELATORIO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
