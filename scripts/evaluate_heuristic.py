"""Avaliação da heurística de release corretiva contra o consenso da amostra-ouro (E§6, Issue #28).

Uso (a partir da raiz do repositório, depois do consenso da #26):

    python -m scripts.evaluate_heuristic --config config.yaml

1. **Guarda de independência:** só roda se os 3 `labels_<avaliador>.csv` (avaliadores de `sorteio.json`)
   passarem em `validar_rotulos`. A heurística não é aplicada à amostra-ouro antes disso (E§6: rotular
   "sem ver a saída da heurística").
2. Lê o consenso da dimensão `corretiva` em `consenso.csv` (`item_id` = `release_id`); exige consenso
   completo (sem `pendente`).
3. Obtém os commits de cada release sorteada com `compare/{anterior}...{R}` (a anterior vem do
   `compare_url` de `amostra_ouro.csv`), reaproveitando o cache de commits do pipeline. Comparações fora do
   cache vão à API e precisam de `GITHUB_TOKEN`.
4. Aplica **todas** as versões de `metricas.heuristica.VERSOES` e grava `heuristica_amostra.csv`.
5. Calcula precisão, recall e F1 de cada versão com `precision_recall_fscore_support` e grava
   `avaliacao_heuristica.csv` e `avaliacao_heuristica.md` (tabela versão → F1 para o artigo).

Escolha da versão final: fica a v1 (definida antes de ver os dados) se F1 ≥ 0,70; senão, a de maior F1
(empate → menor número). Escolher entre várias versões na mesma amostra deixa o F1 da escolhida otimista
(sem amostra de validação separada): o relatório traz todas as versões e o número de corretivas do
consenso, e isso entra em Ameaças à validade.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from metricas.heuristica import HEURISTIC_VERSION, VERSOES, corretiva, sinais_conteudo, sinais_da_release
from pipeline.collect_commits import STATUS_404, STATUS_OK, collect_commits
from pipeline.config import ConfigError, carregar_dotenv, get_token, load_config
from scripts.validar_rotulos import validar

F1_MINIMO = 0.70
DIMENSAO = "corretiva"
ROTULO = {"sim": 1, "nao": 0}
ARQ_HEURISTICA = "heuristica_amostra.csv"
ARQ_AVALIACAO = "avaliacao_heuristica.csv"
ARQ_RELATORIO = "avaliacao_heuristica.md"
COLUNAS_SINAIS = ("semver_patch", "palavra_chave", "palavra_chave_ampla")
COLUNAS_CONTEUDO = ("n_correcoes", "n_features", "nota_correcao", "nota_novidade")  # v8/v9
COLUNAS_HEURISTICA = (
    "release_id", "full_name", "tag_name", "base", "status", "mensagens_incompletas", *COLUNAS_SINAIS, *COLUNAS_CONTEUDO, *VERSOES,
)
COLUNAS_AVALIACAO = ("versao", "descricao", "n", "tp", "fp", "fn", "tn", "precisao", "recall", "f1", "escolhida")


class AvaliacaoError(Exception):
    """Pré-condição não atendida (rótulos, consenso ou dados); `codigo` é o exit code."""

    def __init__(self, mensagem: str, codigo: int = 1):
        super().__init__(mensagem)
        self.codigo = codigo


def _ler_csv(arquivo: Path) -> list[dict]:
    with Path(arquivo).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _escrever_csv(arquivo: Path, colunas, linhas: list[dict]) -> None:
    with Path(arquivo).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(colunas), lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def checar_rotulos(amostra_dir: Path) -> list[str]:
    """Uma linha por planilha incompleta (só o nº de pendências, sem expor os rótulos); [] se as 3 estão ok."""
    amostra_dir = Path(amostra_dir)
    sorteio = json.loads((amostra_dir / "sorteio.json").read_text(encoding="utf-8"))
    problemas = []
    for avaliador in sorteio["avaliadores"]:
        planilha = amostra_dir / f"labels_{avaliador}.csv"
        if not planilha.is_file():
            problemas.append(f"{planilha.name}: arquivo ausente")
            continue
        n = len(validar(planilha, amostra_dir / "amostra_ouro.csv"))
        if n:
            problemas.append(f"{planilha.name}: {n} pendência(s)")
    return problemas


def consenso_corretiva(arquivo: Path) -> dict[str, int]:
    """`release_id -> 1 (corretiva) | 0` a partir das linhas `dimensao == corretiva` de `consenso.csv`."""
    arquivo = Path(arquivo)
    if not arquivo.is_file():
        raise AvaliacaoError(f"{arquivo} não existe: rode `python -m scripts.agreement` com os 3 rótulos")
    consenso: dict[str, int] = {}
    pendentes = 0
    for linha in _ler_csv(arquivo):
        if linha["dimensao"] != DIMENSAO:
            continue
        rotulo = (linha.get("rotulo_consenso") or "").strip()
        if linha.get("metodo") == "pendente" or rotulo not in ROTULO:
            pendentes += 1
            continue
        consenso[str(linha["item_id"]).strip()] = ROTULO[rotulo]
    if pendentes:
        raise AvaliacaoError(f"consenso incompleto: {pendentes} release(s) sem rótulo de consenso", codigo=2)
    if not consenso:
        raise AvaliacaoError(f"{arquivo}: nenhuma linha da dimensão {DIMENSAO}")
    return consenso


def base_do_compare(compare_url: str, tag_name: str) -> str | None:
    """Tag da release anterior em `.../compare/{base}...{tag}`; `None` sem compare (1ª da história)."""
    if not compare_url:
        return None
    sufixo = f"...{tag_name}"
    trecho = compare_url.split("/compare/", 1)[-1]
    if not trecho.endswith(sufixo) or len(trecho) == len(sufixo):
        raise AvaliacaoError(f"compare_url inesperado para {tag_name}: {compare_url}")
    return trecho[: -len(sufixo)]


def pares_da_amostra(linhas: list[dict]) -> dict[str, list[tuple[dict | None, dict]]]:
    """`full_name -> [(anterior, R)]` na ordem de `amostra_ouro.csv`, no formato de `collect_commits`."""
    pares: dict[str, list[tuple[dict | None, dict]]] = {}
    for linha in linhas:
        base = base_do_compare(linha.get("compare_url", ""), linha["tag_name"])
        release = {"tag_name": linha["tag_name"], "published_at": linha["published_at"], "id": str(linha["release_id"])}
        pares.setdefault(linha["full_name"], []).append(({"tag_name": base} if base else None, release))
    return pares


class ClienteSemToken:
    """Usado sem `GITHUB_TOKEN`: funciona só se todas as comparações estiverem no cache."""

    def get(self, path, params=None):
        raise AvaliacaoError(
            f"comparação fora do cache e sem token ({path}): defina GITHUB_TOKEN ou copie o cache de commits"
        )


def coletar_commits(pares: dict, client, cache_dir: Path | None) -> dict[str, list[dict]]:
    """`full_name -> releases de collect_commits`, com `id` (release_id) repassado pela posição."""
    saida = {}
    for full_name, pares_repo in pares.items():
        releases = collect_commits(client, full_name, pares_repo, cache_dir)["releases"]
        saida[full_name] = [{**r, "id": par[1]["id"]} for r, par in zip(releases, pares_repo)]
    return saida


def coletar_notas(linhas_amostra: list[dict], client) -> dict[str, str | None]:
    """`release_id -> corpo (release notes)`; `None` se a release não está acessível (ex.: 404).

    Usa `GET /repos/{owner}/{repo}/releases/{id}` pelo cliente do pipeline (com cache em disco quando
    há token). Sem token e fora do cache, o cliente levanta `AvaliacaoError` como na coleta de commits.
    """
    notas: dict[str, str | None] = {}
    for linha in linhas_amostra:
        resp = client.get(f"/repos/{linha['full_name']}/releases/{linha['release_id']}")
        corpo = resp.json() if resp.status_code == 200 else None
        notas[str(linha["release_id"])] = (corpo.get("body") or "") if isinstance(corpo, dict) else None
    return notas


def _conteudo_str(valor) -> str:
    return str(valor) if isinstance(valor, int) and not isinstance(valor, bool) else _sim_nao(valor)


def _sim_nao(valor) -> str:
    if valor is None:
        return ""
    return "sim" if valor else "nao"


def aplicar_versoes(releases_por_repo: dict[str, list[dict]], notas: dict[str, str | None] | None = None) -> list[dict]:
    """Uma linha por release sorteada: sinais da heurística e o resultado de cada versão (`sim`/`nao`).

    Release com anterior e sem notas coletadas (`notas` ausente, sem a release ou `None`) levanta
    `AvaliacaoError` antes de qualquer linha: a v9 não cai na regra da v8. Notas `""` são dado presente.
    """
    sem_notas = [
        f"{fn}@{r['tag_name']} (id {r['id']})"
        for fn, rels in releases_por_repo.items() for r in rels
        if r.get("base") is not None and (notas or {}).get(str(r["id"])) is None
    ]
    if any(VERSOES[v].exige_notas for v in VERSOES) and sem_notas:
        raise AvaliacaoError(
            f"release notes indisponíveis para {len(sem_notas)} release(s) com anterior, exigidas pela v9; "
            "nada foi gravado. Ex.: " + ", ".join(sem_notas[:5])
        )
    linhas = []
    for full_name, releases in releases_por_repo.items():
        for r in releases:
            mensagens = [c.get("message") for c in r.get("commits") or []] if r.get("status") == STATUS_OK else []
            sinais = sinais_da_release(r.get("base"), r["tag_name"], mensagens)
            conteudo = (
                sinais_conteudo(mensagens, (notas or {}).get(str(r["id"])))
                if r.get("base") is not None else {k: None for k in COLUNAS_CONTEUDO}
            )
            todos = {**sinais, **conteudo}
            linhas.append({
                "release_id": r["id"],
                "full_name": full_name,
                "tag_name": r["tag_name"],
                "base": r.get("base") or "",
                "status": r.get("status"),
                "mensagens_incompletas": _sim_nao(r.get("status") == STATUS_404 or bool(r.get("truncado"))),
                **{k: _sim_nao(v) for k, v in sinais.items()},
                **{k: _conteudo_str(v) for k, v in conteudo.items()},
                **{
                    v: _sim_nao(False if r.get("base") is None else corretiva(todos, v))
                    for v in VERSOES
                },
            })
    return linhas


def avaliar_versoes(linhas: list[dict], consenso: dict[str, int]) -> list[dict]:
    """P/R/F1 (positivo = corretiva) e matriz de confusão de cada versão frente ao consenso."""
    ids = [str(l["release_id"]) for l in linhas]
    if sorted(ids) != sorted(consenso):
        faltam = sorted(set(ids) - set(consenso))[:5]
        sobram = sorted(set(consenso) - set(ids))[:5]
        raise AvaliacaoError(f"releases da amostra e do consenso diferem (sem consenso: {faltam}; só no consenso: {sobram})")
    y_true = [consenso[i] for i in ids]
    tabela = []
    for versao, info in VERSOES.items():
        y_pred = [ROTULO[l[versao]] for l in linhas]
        p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", pos_label=1, zero_division=0)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        tabela.append({
            "versao": versao, "descricao": info.descricao, "n": len(ids),
            "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
            "precisao": round(float(p), 4), "recall": round(float(r), 4), "f1": round(float(f1), 4),
        })
    escolhida = escolher_versao(tabela)
    for linha in tabela:
        linha["escolhida"] = "sim" if linha["versao"] == escolhida else "nao"
    return tabela


def _numero(versao: str) -> int:
    return int(versao.lstrip("v"))


def escolher_versao(tabela: list[dict]) -> str:
    """v1 se F1 ≥ 0,70; senão a de maior F1 (empate → menor número de versão)."""
    por_versao = {l["versao"]: l for l in tabela}
    if "v1" in por_versao and por_versao["v1"]["f1"] >= F1_MINIMO:
        return "v1"
    return min(tabela, key=lambda l: (-l["f1"], _numero(l["versao"])))["versao"]


def relatorio_md(tabela: list[dict], linhas: list[dict]) -> str:
    escolhida = next(l for l in tabela if l["escolhida"] == "sim")
    positivas = tabela[0]["tp"] + tabela[0]["fn"]
    incompletas = sum(1 for l in linhas if l["mensagens_incompletas"] == "sim")
    partes = [
        "# Avaliação da heurística de release corretiva",
        "",
        f"Gerado por `python -m scripts.evaluate_heuristic` (Issue #28). Referência: consenso da dimensão "
        f"`corretiva` em `consenso.csv`; {escolhida['n']} releases da amostra-ouro, **{positivas} corretivas** "
        f"no consenso. Métricas com `precision_recall_fscore_support` (positivo = corretiva).",
        "",
        "| Versão | Regra | TP | FP | FN | TN | Precisão | Recall | F1 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for l in tabela:
        marca = " **(escolhida)**" if l["escolhida"] == "sim" else ""
        partes.append(
            f"| {l['versao']}{marca} | {l['descricao']} | {l['tp']} | {l['fp']} | {l['fn']} | {l['tn']} "
            f"| {l['precisao']:.2f} | {l['recall']:.2f} | {l['f1']:.2f} |"
        )
    partes += [
        "",
        f"**Versão escolhida: {escolhida['versao']}** (F1 = {escolhida['f1']:.2f}). Regra de escolha: fica a v1, "
        f"definida antes de ver os dados, se F1 ≥ {F1_MINIMO:.2f}; senão, a de maior F1 (empate → menor número).",
        "",
        f"- Releases com mensagens incompletas (`compare` 404 ou truncado): {incompletas}.",
        "- Viés de seleção: as versões foram comparadas na mesma amostra, sem conjunto de validação separado; "
        "o F1 da versão escolhida tende a ser otimista (registrar em Ameaças à validade).",
    ]
    if escolhida["versao"] != HEURISTIC_VERSION:
        partes.append(
            f"- **Ação:** a versão escolhida difere de `HEURISTIC_VERSION` ({HEURISTIC_VERSION}) em "
            "`metricas/heuristica.py`: atualize a constante e recalcule o CFR (b) (#21)."
        )
    return "\n".join(partes) + "\n"


def criar_cliente(config):
    """Cliente com cache do pipeline se houver token; senão `ClienteSemToken` (só cache)."""
    try:
        token = get_token(config)
    except ConfigError:
        return ClienteSemToken()
    from pipeline.cli import criar_cliente as criar

    return criar(token, config.cache_dir)


def executar(amostra_dir: Path, client, cache_dir: Path | None) -> list[dict]:
    """Fluxo completo; devolve a tabela versão → P/R/F1 e grava os 3 arquivos em `amostra_dir`."""
    amostra_dir = Path(amostra_dir)
    problemas = checar_rotulos(amostra_dir)
    if problemas:
        raise AvaliacaoError(
            "rotulagem incompleta; a heurística não roda na amostra-ouro antes de os 3 rótulos estarem "
            "completos (E§6):\n  " + "\n  ".join(problemas)
        )
    consenso = consenso_corretiva(amostra_dir / "consenso.csv")
    amostra = _ler_csv(amostra_dir / "amostra_ouro.csv")
    pares = pares_da_amostra(amostra)
    linhas = aplicar_versoes(coletar_commits(pares, client, cache_dir), coletar_notas(amostra, client))
    tabela = avaliar_versoes(linhas, consenso)
    _escrever_csv(amostra_dir / ARQ_HEURISTICA, COLUNAS_HEURISTICA, linhas)
    _escrever_csv(amostra_dir / ARQ_AVALIACAO, COLUNAS_AVALIACAO, tabela)
    (amostra_dir / ARQ_RELATORIO).write_text(relatorio_md(tabela, linhas), encoding="utf-8")
    return tabela


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m scripts.evaluate_heuristic", description=__doc__.splitlines()[0])
    p.add_argument("--config", default="config.yaml", help="config.yaml (cache e token)")
    p.add_argument("--amostra-dir", default="data/amostra_ouro", help="pasta da amostra-ouro")
    args = p.parse_args(argv)
    amostra_dir = Path(args.amostra_dir)
    try:
        carregar_dotenv(".env")
        config = load_config(args.config)
        tabela = executar(amostra_dir, criar_cliente(config), Path(config.cache_dir))
    except AvaliacaoError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return exc.codigo
    except (OSError, KeyError, ValueError, ConfigError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    for l in tabela:
        marca = "  <- escolhida" if l["escolhida"] == "sim" else ""
        print(f"{l['versao']}: P={l['precisao']:.2f} R={l['recall']:.2f} F1={l['f1']:.2f} ({l['descricao']}){marca}")
    print(f"gravados em {amostra_dir}: {ARQ_HEURISTICA}, {ARQ_AVALIACAO}, {ARQ_RELATORIO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
