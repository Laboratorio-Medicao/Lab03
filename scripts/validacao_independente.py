"""Validação independente da heurística v12 do CFR (b) — sorteio, rotulagem cega e avaliação única.

Fluxo (nada aqui altera a heurística, os rótulos antigos ou `data/amostra_ouro/`):

    python -m scripts.validacao_independente sortear    # 1. repositórios fora da amostra-ouro, com semente
    python -m scripts.validacao_independente pacote     # 2. releases, planilhas CEGAS e dados congelados
    ... três avaliadores rotulam sozinhos e commitam labels_<nome>.csv ...
    python -m scripts.validacao_independente avaliar    # 3. v12 congelada x consenso, F1 e IC por repositório

Garantias de projeto:
- `sortear` e `pacote` NUNCA executam a heurística; as planilhas não têm previsão, versão nem sinais.
- `pacote` grava `congelamento.json` (sha256 de `metricas/heuristica.py`, dos dados e da lista) e
  `avaliar` recusa rodar se a heurística mudou depois disso.
- `avaliar` é de uso único: recusa sobrescrever um resultado existente sem `--refazer`, e só aceita a
  versão congelada. Não há opção de escolher outra versão a partir do resultado do teste.
- Sem rótulos completos e sem consenso (nenhum `pendente`), `avaliar` pára antes de calcular qualquer F1.
- Sem rede por padrão: dados fora do cache HTTP exigem `--permitir-api` (e `GITHUB_TOKEN`).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import random
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from metricas.heuristica import VERSOES, avaliar as aplicar_heuristica
from scripts.sample_gold import (
    COLUNAS_AMOSTRA, COLUNAS_PLANILHA, TIPOS_PROJETO, _escrever_csv, _linha_release, linhas_planilha,
    sortear_releases,
)

log = logging.getLogger("scripts.validacao_independente")

VERSAO_CONGELADA = "v12"
SEED_REPOS = 7342        # semente do sorteio de repositórios (registrada no manifesto)
SEED_RELEASES = 7342     # semente do sorteio de releases (derivada com o full_name, como em sample_gold)
SEED_BOOTSTRAP = 20261015
N_REPOS = 40             # ver docs/validacao-independente.md (IC95% ≈ ±0,10 com 200 releases)
N_RELEASES = 5
PASTA = Path("data/validacao_independente")
ARQ_HEURISTICA = Path("metricas/heuristica.py")


class ValidacaoError(Exception):
    pass


def _sha256(arquivo: Path) -> str:
    return hashlib.sha256(Path(arquivo).read_bytes()).hexdigest()


def _ler_csv(arquivo: Path) -> list[dict]:
    with Path(arquivo).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _dono(full_name: str) -> str:
    return full_name.split("/")[0].lower()


# ----------------------------------------------------------------------------------------- 1. sorteio

def elegiveis(candidatos: list[str], usados: list[str], mesmo_dono: bool = True) -> tuple[list[str], dict]:
    """Candidatos independentes dos repositórios já usados no desenvolvimento.

    Critérios (registrados no manifesto): (1) fora da lista `usados` (sem diferenciar caixa);
    (2) se `mesmo_dono`, fora dos donos (organizações/usuários) que já têm repositório usado: releases do
    mesmo dono costumam compartilhar convenção de notas e mantenedores.
    """
    usados_n = {u.lower() for u in usados}
    donos = {_dono(u) for u in usados}
    unicos: dict[str, str] = {}
    for c in candidatos:
        unicos.setdefault(c.lower(), c)
    saida, por_uso, por_dono = [], 0, 0
    for chave in sorted(unicos):
        nome = unicos[chave]
        if chave in usados_n:
            por_uso += 1
        elif mesmo_dono and _dono(nome) in donos:
            por_dono += 1
        else:
            saida.append(nome)
    return saida, {
        "candidatos_unicos": len(unicos),
        "excluidos_ja_usados": por_uso,
        "excluidos_mesmo_dono": por_dono,
        "elegiveis": len(saida),
    }


def sortear_repos(quadro: list[str], n: int, seed: int) -> list[str]:
    base = sorted(set(quadro))
    if len(base) < n:
        raise ValidacaoError(f"quadro amostral com {len(base)} repositórios; o sorteio pede {n}")
    return sorted(random.Random(seed).sample(base, n))


def cmd_sortear(repos_csv: Path, usados_csv: Path, saida: Path, n: int, seed: int, mesmo_dono: bool,
                forcar: bool = False) -> dict:
    manifesto = saida / "sorteio_repos.json"
    if manifesto.exists() and not forcar:
        raise ValidacaoError(f"{manifesto} já existe: o sorteio é único (use --forcar só se for refazê-lo de propósito)")
    candidatos = [r["full_name"].strip() for r in _ler_csv(repos_csv) if r.get("full_name", "").strip()]
    usados = sorted({r["full_name"].strip() for r in _ler_csv(usados_csv)})
    quadro, contagem = elegiveis(candidatos, usados, mesmo_dono)
    sorteados = sortear_repos(quadro, n, seed)
    assert not ({s.lower() for s in sorteados} & {u.lower() for u in usados})
    saida.mkdir(parents=True, exist_ok=True)
    _escrever_csv(saida / "repos_sorteados.csv", ("full_name",), [{"full_name": s} for s in sorteados])
    info = {
        "seed": seed, "n_repos": n, "mesmo_dono_excluido": mesmo_dono,
        "lista_entrada": str(repos_csv), "lista_entrada_sha256": _sha256(repos_csv),
        "lista_usados": str(usados_csv), "lista_usados_sha256": _sha256(usados_csv), "n_usados": len(usados),
        **contagem, "sorteados": sorteados,
        "criado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifesto.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return info


# -------------------------------------------------------------------------------------------- 2. pacote

class _SemRede:
    """Cliente que só funciona se a resposta já está no cache HTTP (padrão: sem rede)."""

    def get(self, path, params=None):
        raise ValidacaoError(f"resposta fora do cache e sem --permitir-api: {path} {params or ''}")


class ClienteEmCamadas:
    """Lê de caches existentes (**somente leitura**), depois do cache novo desta validação, depois da API.

    Respostas novas só são gravadas em `cache_novo`; os caches de leitura (produção, desenvolvimento)
    nunca são escritos. Conta de onde veio cada resposta para o registro de proveniência.
    """

    def __init__(self, cache_novo: Path, caches_leitura: list[Path], api=None):
        from pipeline.cache import CachedHttpClient, _chave
        self._chave = _chave
        self._leitura = [Path(c) for c in caches_leitura]
        self._novo = CachedHttpClient(api or _SemRede(), cache_novo)
        self._cache_novo = Path(cache_novo)
        self._api = api
        self.contagem = {"leitura": 0, "cache_novo": 0, "api": 0}
        self.por_repo: dict[str, dict] = {}

    def _conta(self, path: str, origem: str) -> None:
        partes = path.split("/")
        repo = "/".join(partes[2:4]).lower() if path.startswith("/repos/") and len(partes) > 4 else "?"
        self.contagem[origem] += 1
        self.por_repo.setdefault(repo, {"leitura": 0, "cache_novo": 0, "api": 0})[origem] += 1

    def get(self, path: str, params=None):
        from pipeline.cache import _cacheavel, _ler
        nome = f"{self._chave(path, params)}.json"
        if not (self._cache_novo / nome).exists():
            for base in self._leitura:
                arq = base / nome
                if arq.exists():
                    resp = _ler(arq)
                    if _cacheavel(resp):
                        self._conta(path, "leitura")
                        return resp
        antes = self._novo.estatisticas()["cache_misses"]
        resp = self._novo.get(path, params)
        self._conta(path, "api" if self._novo.estatisticas()["cache_misses"] > antes else "cache_novo")
        return resp


def _cliente(cache_novo: Path, caches_leitura: list[Path], permitir_api: bool) -> ClienteEmCamadas:
    api = None
    if permitir_api:
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise ValidacaoError("--permitir-api exige GITHUB_TOKEN no ambiente (nunca na linha de comando)")
        from pipeline.http_client import HttpClient
        api = HttpClient(token)
    return ClienteEmCamadas(cache_novo, caches_leitura, api)


def montar_pacote(sorteados: list[str], client, inicio: date, fim: date, seed: int = SEED_RELEASES,
                  n_releases: int = N_RELEASES, falhas: list | None = None) -> tuple[list[dict], dict, list[str]]:
    """(linhas da amostra, dados congelados por `release_id`, avisos). Não executa a heurística.

    Repositório que falha (HTTP, dado fora do cache sem API…) é **registrado em `falhas`** e fica de fora;
    nunca é trocado por outro sorteado. Sem a lista `falhas`, a primeira falha propaga.
    """
    from pipeline.collect_commits import collect_commits
    from pipeline.collect_releases import collect_releases, pares_com_anterior
    from pipeline.selection import ApiError

    linhas: list[dict] = []
    congelado: dict[str, dict] = {}
    avisos: list[str] = []
    for full_name in sorteados:
        try:
            parcial = _repo_pacote(full_name, client, inicio, fim, seed, n_releases)
        except (ApiError, ValidacaoError) as exc:
            if falhas is None:
                raise
            falhas.append({"full_name": full_name, "motivo": f"{type(exc).__name__}: {exc}"})
            continue
        linhas += parcial[0]
        congelado.update(parcial[1])
        avisos += parcial[2]
    return linhas, congelado, avisos


def _repo_pacote(full_name: str, client, inicio: date, fim: date, seed: int, n_releases: int):
    from pipeline.collect_commits import collect_commits
    from pipeline.collect_releases import collect_releases, pares_com_anterior

    linhas: list[dict] = []
    congelado: dict[str, dict] = {}
    avisos: list[str] = []
    releases = collect_releases(client, full_name, None)
    # só releases com anterior (a 1ª da história nunca é corretiva e não tem compare): pré-registrado
    com_anterior = [(a, r) for a, r in pares_com_anterior(releases, inicio, fim) if a is not None]
    if len(com_anterior) < n_releases:
        avisos.append(f"{full_name}: só {len(com_anterior)} releases elegíveis (pedidas {n_releases})")
    escolhidas = _sortear_pares(com_anterior, full_name, n_releases, seed)
    commits = collect_commits(client, full_name, escolhidas, None)["releases"]
    corpo = {r["tag_name"]: r.get("body") for r in releases}
    for (anterior, r), c in zip(escolhidas, commits):
        item = _linha_release(full_name, anterior, r)
        linhas.append(item)
        congelado[str(r["id"])] = {
            "full_name": full_name, "tag_name": r["tag_name"], "base": anterior["tag_name"],
            "published_at": r["published_at"], "status": c["status"], "truncado": c["truncado"],
            "body": corpo.get(r["tag_name"]),
            "commits": [{"sha": x["sha"], "message": x["message"], "n_parents": x["n_parents"],
                         "author_date": x["author_date"]} for x in c["commits"]],
        }
    return linhas, congelado, avisos


def _sortear_pares(pares: list, full_name: str, n: int, seed: int) -> list:
    if len(pares) <= n:
        return pares
    idx = random.Random(f"{seed}/{full_name.lower()}").sample(range(len(pares)), n)
    return [pares[i] for i in sorted(idx)]


PROTOCOLO = """# Protocolo de rotulagem cega — validação independente da heurística de release corretiva

Este protocolo vale **somente** para `data/validacao_independente/`. Os rótulos de `data/amostra_ouro/`
não são lidos, alterados nem reutilizados.

## Regras de independência
1. Cada avaliador preenche **só o seu** `labels_<nome>.csv`, **sem conversar** com os outros e sem ver
   rótulos alheios, a saída da heurística ou qualquer `sugestao`. Não use scripts que sugiram rótulos.
2. Quem implementou ou alterou alguma versão da heurística **declara** isso em `observacoes` da 1ª linha; a
   avaliação reporta o resultado com e sem esse avaliador (sensibilidade).
3. Cada avaliador commita o próprio arquivo, com `#N` da sua Issue, antes de qualquer reunião.
4. Os arquivos individuais nunca são alterados depois do commit; o consenso fica em arquivo próprio.

## Definição operacional de release corretiva
Uma release é **corretiva (`sim`)** quando o **objetivo principal** dela é corrigir um defeito (bug,
regressão, falha de segurança) de uma versão já publicada, de acordo com as *release notes* e a lista de
commits. É **`nao`** quando o conteúdo é majoritariamente funcionalidade, melhoria, refatoração,
dependências, documentação ou manutenção, mesmo que contenha uma correção pontual.

Decisões de limite (valem para os três avaliadores):
- **Mista** (correções + funcionalidades): `sim` somente se as correções são o motivo declarado da
  release (notas dizem "patch/security/bugfix release" ou a maioria dos itens substantivos são correções).
- **Backport / outra linha de versão** (ex.: `5.0.1` publicada depois de `4.4.3`): avalie o conteúdo da
  release; o número da versão não decide.
- **Release só com bump de versão ou sem notas e sem commits**: `nao`, com `observacoes = sem_informacao`.
- **Dado inacessível** (repositório/release removidos, `compare` 404): marque `nao` e escreva
  `observacoes = inacessivel`; o item é reportado à parte e entra na análise de sensibilidade.
- **Dúvida real**: escolha `sim`/`nao` pelo objetivo principal e anote `observacoes = duvida`. Não existe
  valor intermediário em `corretiva` (a dimensão `releases_sao_entregas_reais` já admite `incerto`).

## Consenso (depois de os três arquivos estarem commitados)
- Concordância (κ de Fleiss) calculada **antes** de qualquer discussão, sobre os arquivos originais.
- Unanimidade e maioria simples (2 a 1) resolvem automaticamente (`scripts.agreement`).
- Como `corretiva` é binária, não há 1-1-1; nenhum item é decidido em reunião.
- Itens com `observacoes = inacessivel` são mantidos no consenso e reportados em sensibilidade.

## Limitações conhecidas (leia antes de interpretar o F1)
- No desenvolvimento, κ de `corretiva` = 0,27 e as taxas de "sim" por avaliador foram 59%, 16% e 29%: o
  critério é ambíguo e os limiares diferem. A definição acima reduz, não elimina, esse ruído.
- O consenso por maioria de 3 avaliadores é a referência; F1 alto contra ele mede concordância com a
  maioria, não "verdade" independente.
- Amostra pequena: o intervalo de confiança do F1 é largo (≈ ±0,10 com 40 repositórios).
"""


def cmd_pacote(sorteio_json: Path, saida: Path, cache_novo: Path, inicio: date, fim: date,
               avaliadores: list[str], permitir_api: bool, forcar: bool = False,
               caches_leitura: list[Path] | None = None) -> dict:
    manifesto_sorteio = json.loads(Path(sorteio_json).read_text(encoding="utf-8"))
    sorteados = manifesto_sorteio["sorteados"]
    alvo = saida / "amostra_validacao.csv"
    if alvo.exists() and not forcar:
        raise ValidacaoError(f"{alvo} já existe; regerar apagaria o pacote em uso (use --forcar)")
    for arq in saida.glob("labels_*.csv"):
        if any((r.get("corretiva") or "").strip() for r in _ler_csv(arq)) and not forcar:
            raise ValidacaoError(f"{arq.name} já tem rótulos; não regerar")
    caches_leitura = [Path(c) for c in (caches_leitura or [])]
    for c in caches_leitura:
        if c.resolve() == Path(cache_novo).resolve():
            raise ValidacaoError("o cache novo não pode ser também um cache de leitura")
    client = _cliente(cache_novo, caches_leitura, permitir_api)
    falhas: list[dict] = []
    linhas, congelado, avisos = montar_pacote(sorteados, client, inicio, fim, falhas=falhas)
    saida.mkdir(parents=True, exist_ok=True)
    _escrever_csv(alvo, COLUNAS_AMOSTRA, linhas)
    for nome in avaliadores:
        _escrever_csv(saida / f"labels_{nome}.csv", COLUNAS_PLANILHA, linhas_planilha(linhas))
    dados = saida / "dados_congelados.json"
    dados.write_text(json.dumps(congelado, ensure_ascii=False, indent=1), encoding="utf-8")
    (saida / "PROTOCOLO_ROTULAGEM_CEGA.md").write_text(PROTOCOLO, encoding="utf-8")
    cong = {
        "versao_heuristica": VERSAO_CONGELADA,
        "descricao": VERSOES[VERSAO_CONGELADA].descricao,
        "heuristica_sha256": _sha256(ARQ_HEURISTICA),
        "dados_congelados_sha256": _sha256(dados),
        "amostra_sha256": _sha256(alvo),
        "sorteio_repos_sha256": _sha256(sorteio_json),
        "seed_releases": SEED_RELEASES, "n_releases_por_repo": N_RELEASES,
        "janela": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "avaliadores": avaliadores,
        "n_repos": len(sorteados), "n_releases": len(linhas),
        "heuristica_executada_no_pacote": False,
        "proveniencia": {
            "caches_leitura_somente_leitura": [str(c) for c in caches_leitura],
            "cache_novo": str(cache_novo), "permitir_api": permitir_api,
            "respostas_por_origem": client.contagem,
            "por_repositorio": {k: v for k, v in sorted(client.por_repo.items())},
        },
        "repositorios_com_falha": falhas,
        "n_status_compare_404": sum(1 for d in congelado.values() if d["status"] == "404"),
        "n_compare_truncado": sum(1 for d in congelado.values() if d["truncado"]),
        "n_sem_corpo": sum(1 for d in congelado.values() if not d.get("body")),
        "avisos": avisos,
        "criado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (saida / "congelamento.json").write_text(json.dumps(cong, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return cong


# ------------------------------------------------------------------------------------------ 3. avaliação

def prf(y: list[bool], p: list[bool]) -> dict:
    tp = sum(1 for a, b in zip(y, p) if a and b)
    fp = sum(1 for a, b in zip(y, p) if not a and b)
    fn = sum(1 for a, b in zip(y, p) if a and not b)
    tn = len(y) - tp - fp - fn
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"n": len(y), "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precisao": prec, "recall": rec, "f1": f1}


def bootstrap_por_repositorio(y: list[bool], p: list[bool], repos: list[str], b: int = 10000,
                              seed: int = SEED_BOOTSTRAP) -> dict:
    """IC95% percentil de P/R/F1 reamostrando **repositórios** (releases do mesmo repositório são dependentes)."""
    import numpy as np
    rng = np.random.RandomState(seed)
    nomes = sorted(set(repos))
    idx = {n: [i for i, r in enumerate(repos) if r == n] for n in nomes}
    f, pr, rc = [], [], []
    for _ in range(b):
        sel = [i for n in rng.choice(nomes, len(nomes)) for i in idx[n]]
        m = prf([y[i] for i in sel], [p[i] for i in sel])
        f.append(m["f1"]); pr.append(m["precisao"]); rc.append(m["recall"])
    q = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]  # noqa: E731
    return {"b": b, "seed": seed, "n_repositorios": len(nomes), "f1_ic95": q(f), "precisao_ic95": q(pr), "recall_ic95": q(rc),
            "p_f1_maior_igual_070": float(np.mean(np.array(f) >= 0.70))}


def _prever(congelado: dict) -> dict[str, bool]:
    saida = {}
    for rid, d in congelado.items():
        msgs = [c["message"] for c in d["commits"]] if d["status"] == "ok" else []
        saida[rid] = bool(aplicar_heuristica(d["base"], d["tag_name"], msgs, VERSAO_CONGELADA,
                                             notas=d.get("body") or "")["heuristic_corrective"])
    return saida


def cmd_avaliar(saida: Path, refazer: bool = False, aceitar_mudanca: bool = False, b: int = 10000) -> dict:
    from scripts.agreement import analisar, ler_planilha
    from scripts.validar_rotulos import validar

    cong_arq = saida / "congelamento.json"
    if not cong_arq.exists():
        raise ValidacaoError("sem congelamento.json: rode `pacote` antes")
    cong = json.loads(cong_arq.read_text(encoding="utf-8"))
    resultado = saida / "resultado_validacao.json"
    if resultado.exists() and not refazer:
        raise ValidacaoError(f"{resultado.name} já existe: o teste é de uso único (use --refazer só para reproduzir)")
    if cong["versao_heuristica"] != VERSAO_CONGELADA:
        raise ValidacaoError("versão congelada diferente da suportada")
    if _sha256(ARQ_HEURISTICA) != cong["heuristica_sha256"] and not aceitar_mudanca:
        raise ValidacaoError("metricas/heuristica.py mudou depois do congelamento: a avaliação não seria independente")
    for chave, arq in (("dados_congelados_sha256", "dados_congelados.json"), ("amostra_sha256", "amostra_validacao.csv")):
        if _sha256(saida / arq) != cong[chave]:
            raise ValidacaoError(f"{arq} foi alterado depois do congelamento")

    planilhas, problemas = {}, []
    for nome in cong["avaliadores"]:
        arq = saida / f"labels_{nome}.csv"
        if not arq.exists():
            problemas.append(f"{arq.name}: ausente")
            continue
        problemas += [f"{arq.name}: {p}" for p in validar(arq, saida / "amostra_validacao.csv")[:5]]
        planilhas[nome] = ler_planilha(arq)
    if problemas or len(planilhas) != len(cong["avaliadores"]):
        raise ValidacaoError("rotulagem incompleta — nenhum F1 foi calculado:\n  " + "\n  ".join(problemas[:20]))

    concordancia, consenso = analisar(planilhas)
    pend = [c for c in consenso if c["dimensao"] == "corretiva" and not c["rotulo_consenso"]]
    if pend:
        raise ValidacaoError(f"{len(pend)} itens sem consenso — nenhum F1 foi calculado")
    ref = {str(c["item_id"]): c["rotulo_consenso"] == "sim" for c in consenso if c["dimensao"] == "corretiva"}
    congelado = json.loads((saida / "dados_congelados.json").read_text(encoding="utf-8"))
    if set(ref) != set(congelado):
        raise ValidacaoError("release_id dos rótulos e dos dados congelados diferem")
    pred = _prever(congelado)
    ids = sorted(ref)
    y = [ref[i] for i in ids]; p = [pred[i] for i in ids]; repos = [congelado[i]["full_name"] for i in ids]
    metricas = prf(y, p)
    ic = bootstrap_por_repositorio(y, p, repos, b)
    inacess = [i for i in ids if congelado[i]["status"] != "ok"]
    sens = prf([ref[i] for i in ids if i not in inacess], [pred[i] for i in ids if i not in inacess]) if inacess else None
    res = {
        "versao_heuristica": VERSAO_CONGELADA, "heuristica_sha256": cong["heuristica_sha256"],
        "avaliacao_independente": True,
        "condicao": "independente apenas se os rótulos foram feitos conforme PROTOCOLO_ROTULAGEM_CEGA.md",
        "n_releases": len(ids), "n_repositorios": len(set(repos)), "n_positivas_consenso": sum(y),
        **metricas, "intervalo_confianca": ic,
        "sem_itens_inacessiveis": sens, "n_inacessiveis": len(inacess),
        "concordancia": concordancia,
        "meta_f1_070_atingida_no_ponto": metricas["f1"] >= 0.70,
        "calculado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    resultado.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _escrever_csv(saida / "predicoes_v12.csv", ("release_id", "full_name", "tag_name", "consenso", "pred_v12"),
                  [{"release_id": i, "full_name": congelado[i]["full_name"], "tag_name": congelado[i]["tag_name"],
                    "consenso": "sim" if ref[i] else "nao", "pred_v12": "sim" if pred[i] else "nao"} for i in ids])
    return res


# -------------------------------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="python -m scripts.validacao_independente", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sortear")
    s.add_argument("--repos", default="outputs/repos_final.csv")
    s.add_argument("--usados", default="data/amostra_ouro/amostra_ouro.csv", help="repositórios já usados no desenvolvimento")
    s.add_argument("--saida", default=str(PASTA))
    s.add_argument("--n", type=int, default=N_REPOS)
    s.add_argument("--seed", type=int, default=SEED_REPOS)
    s.add_argument("--permitir-mesmo-dono", action="store_true", help="não excluir donos que já têm repositório usado")
    s.add_argument("--forcar", action="store_true")
    k = sub.add_parser("pacote")
    k.add_argument("--config", default="config.yaml")
    k.add_argument("--saida", default=str(PASTA))
    k.add_argument("--cache", help="cache NOVO e isolado desta validação (padrão: <caminhos.cache>/validacao_independente)")
    k.add_argument("--cache-leitura", action="append", default=[],
                   help="cache existente, usado SOMENTE para leitura (repetível); nunca é escrito")
    k.add_argument("--avaliadores", nargs="+", help="padrão: avaliadores de data/amostra_ouro/sorteio.json")
    k.add_argument("--permitir-api", action="store_true", help="busca na API o que faltar no cache (exige GITHUB_TOKEN)")
    k.add_argument("--forcar", action="store_true")
    a = sub.add_parser("avaliar")
    a.add_argument("--saida", default=str(PASTA))
    a.add_argument("--refazer", action="store_true")
    a.add_argument("--aceitar-mudanca", action="store_true")
    args = p.parse_args(argv)
    saida = Path(args.saida)
    try:
        if args.cmd == "sortear":
            info = cmd_sortear(Path(args.repos), Path(args.usados), saida, args.n, args.seed,
                               not args.permitir_mesmo_dono, args.forcar)
            print(json.dumps({k: v for k, v in info.items() if k != "sorteados"}, ensure_ascii=False, indent=2))
        elif args.cmd == "pacote":
            from pipeline.config import load_config
            cfg = load_config(args.config)
            av = args.avaliadores or json.loads(Path("data/amostra_ouro/sorteio.json").read_text())["avaliadores"]
            novo = Path(args.cache) if args.cache else Path(cfg.cache_dir) / "validacao_independente"
            cong = cmd_pacote(saida / "sorteio_repos.json", saida, novo, cfg.janela_inicio, cfg.janela_fim, av,
                              args.permitir_api, args.forcar, [Path(c) for c in args.cache_leitura])
            print(f"pacote gerado: {cong['n_repos']} repositórios, {cong['n_releases']} releases; "
                  f"falhas: {len(cong['repositorios_com_falha'])}; avisos: {len(cong['avisos'])}; "
                  f"respostas: {cong['proveniencia']['respostas_por_origem']}")
        else:
            res = cmd_avaliar(saida, args.refazer, args.aceitar_mudanca)
            ic = res["intervalo_confianca"]
            print(f"n={res['n_releases']} repos={res['n_repositorios']} P={res['precisao']:.3f} R={res['recall']:.3f} "
                  f"F1={res['f1']:.4f} IC95%={ic['f1_ic95'][0]:.3f}–{ic['f1_ic95'][1]:.3f}; meta no ponto: "
                  f"{res['meta_f1_070_atingida_no_ponto']}")
    except (ValidacaoError, OSError, KeyError, ValueError) as exc:
        log.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
