"""Rotulagem assistida e registrada da validação independente (interface local simples).

Cada integrante roda **a própria instância**, na própria máquina, com o próprio nome:

    python -m scripts.rotulagem_assistida --usuario marcosffp

e abre o endereço mostrado (apenas `127.0.0.1`). A ferramenta:

- mostra, para cada repositório e release, os links e o conteúdo que o protocolo manda ler (release
  notes e mensagens dos commits da comparação). **Nunca** mostra previsão, versão, sinais ou qualquer
  saída da heurística, e esta ferramenta não importa `metricas.heuristica`;
- registra cada decisão em um *log* só de acréscimo (`rotulagem/<usuario>.jsonl`) com horário, fase e
  se a sugestão automática já tinha sido vista;
- trabalha em **duas fases**: (1) decisão inicial, do próprio avaliador, sem sugestão; (2) opcionalmente
  vê a sugestão automática e confirma a decisão final (a sugestão nunca vira decisão por um clique:
  é preciso escolher o valor e confirmar);
- exporta `labels_<usuario>.csv` no formato exigido por `scripts.validacao_independente avaliar`.

Limites honestos: não há autenticação. `--usuario` só **informa** um nome; não prova quem está
digitando. A ferramenta escreve apenas os arquivos do usuário informado.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import logging
import sys
import threading
import uuid
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from scripts.sample_gold import (
    COLUNAS_PLANILHA, CORRETIVA, ENTREGA_REAL, TIPOS_PROJETO, _escrever_csv, linhas_planilha,
)
from scripts.validar_rotulos import validar

log = logging.getLogger("scripts.rotulagem_assistida")

PASTA = Path("data/validacao_independente")
ARQ_SUGESTOES = "sugestoes_ia.csv"
MAX_NOTAS = 6000
MAX_COMMITS = 40
MAX_MSG = 300
DIMENSOES = {
    "tipo_projeto": TIPOS_PROJETO,
    "releases_sao_entregas_reais": ENTREGA_REAL,
    "corretiva": CORRETIVA,
}


class RotulagemError(Exception):
    pass


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def item_repo(full_name: str, dimensao: str) -> str:
    return f"repo|{full_name}|{dimensao}"


def item_release(release_id: str) -> str:
    return f"rel|{release_id}|corretiva"


# ------------------------------------------------------------------------------------------ dados

class Pacote:
    """Dados autorizados para exibição: links, notas e mensagens de commit. Nada da heurística."""

    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)
        cong = json.loads((self.pasta / "congelamento.json").read_text(encoding="utf-8"))
        self.avaliadores: list[str] = cong["avaliadores"]
        with (self.pasta / "amostra_validacao.csv").open(encoding="utf-8-sig", newline="") as f:
            self.amostra = list(csv.DictReader(f))
        self._congelado = json.loads((self.pasta / "dados_congelados.json").read_text(encoding="utf-8"))
        self.sugestoes = self._ler_sugestoes()

    def _ler_sugestoes(self) -> dict[str, dict]:
        arq = self.pasta / ARQ_SUGESTOES
        if not arq.exists():
            return {}
        with arq.open(encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.DictReader(f))
        ids = {str(r["release_id"]) for r in self.amostra}
        saida = {}
        for r in linhas:
            rid = str(r["release_id"]).strip()
            if rid not in ids:
                raise RotulagemError(f"{ARQ_SUGESTOES}: release_id {rid} fora da amostra")
            if r["corretiva"] not in CORRETIVA:
                raise RotulagemError(f"{ARQ_SUGESTOES}: valor inválido para {rid}: {r['corretiva']!r}")
            if not (r.get("fonte") or "").strip():
                raise RotulagemError(f"{ARQ_SUGESTOES}: sugestão sem `fonte` (obrigatória: quem/o que sugeriu)")
            saida[rid] = {"corretiva": r["corretiva"], "motivo": r.get("motivo", ""), "fonte": r["fonte"]}
        return saida

    def repositorios(self) -> list[str]:
        vistos: list[str] = []
        for r in self.amostra:
            if r["full_name"] not in vistos:
                vistos.append(r["full_name"])
        return vistos

    def dossie(self, release_id: str) -> dict:
        d = self._congelado[str(release_id)]
        notas = d.get("body") or ""
        commits = []
        for c in d["commits"][:MAX_COMMITS]:
            m = (c.get("message") or "").strip()
            commits.append(m if len(m) <= MAX_MSG else m[:MAX_MSG] + "…")
        return {
            "notas": notas if len(notas) <= MAX_NOTAS else notas[:MAX_NOTAS] + "\n[… truncado; leia a release no link]",
            "n_commits": len(d["commits"]),
            "commits": commits,
            "compare_inacessivel": d["status"] != "ok",
        }

    def itens(self) -> list[dict]:
        saida = []
        for fn in self.repositorios():
            rels = [r for r in self.amostra if r["full_name"] == fn]
            saida.append({
                "full_name": fn, "repo_url": rels[0]["repo_url"],
                "item_tipo": item_repo(fn, "tipo_projeto"), "item_entrega": item_repo(fn, "releases_sao_entregas_reais"),
                "releases": [{
                    "item": item_release(r["release_id"]), "release_id": r["release_id"], "tag_name": r["tag_name"],
                    "published_at": r["published_at"], "release_url": r["release_url"], "compare_url": r["compare_url"],
                    "tem_sugestao": str(r["release_id"]) in self.sugestoes,
                    **self.dossie(r["release_id"]),
                } for r in rels],
            })
        return saida


# ------------------------------------------------------------------------------------------- log

class Registro:
    """Log só de acréscimo de um usuário; o estado é recomputado a partir dele (último evento vale)."""

    def __init__(self, pasta: Path, usuario: str, sessao: str | None = None):
        self.usuario = usuario
        self.dir = Path(pasta) / "rotulagem"
        self.arq = self.dir / f"{usuario}.jsonl"
        self.sessao = sessao or uuid.uuid4().hex[:8]
        self._lock = threading.Lock()

    def eventos(self) -> list[dict]:
        if not self.arq.exists():
            return []
        return [json.loads(l) for l in self.arq.read_text(encoding="utf-8").splitlines() if l.strip()]

    def _acrescentar(self, ev: dict) -> dict:
        ev = {"ts": agora(), "usuario_informado": self.usuario, "sessao": self.sessao, **ev}
        with self._lock:
            self.dir.mkdir(parents=True, exist_ok=True)
            with self.arq.open("a", encoding="utf-8") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return ev

    def estado(self) -> dict[str, dict]:
        est: dict[str, dict] = {}
        for ev in self.eventos():
            e = est.setdefault(ev["item"], {"inicial": None, "final": None, "obs": "", "sugestao_vista": False})
            if ev["tipo"] == "decisao":
                e[ev["fase"]] = ev["valor"]
                if ev.get("observacao"):
                    e["obs"] = ev["observacao"]
            elif ev["tipo"] == "sugestao_exibida":
                e["sugestao_vista"] = True
            elif ev["tipo"] == "observacao":
                e["obs"] = ev["texto"]
        return est

    def decidir(self, item: str, valor: str, fase: str, observacao: str = "", confirmou: bool = False,
                sugestao_valor: str | None = None) -> dict:
        dim = item.split("|")[-1]
        if dim not in DIMENSOES or valor not in DIMENSOES[dim]:
            raise RotulagemError(f"valor inválido para {dim}: {valor!r}")
        if fase not in ("inicial", "final"):
            raise RotulagemError("fase inválida")
        est = self.estado().get(item, {})
        if fase == "inicial" and est.get("sugestao_vista") and est.get("inicial") not in (None, valor):
            raise RotulagemError("a decisão inicial é imutável depois de ver a sugestão; use a decisão final")
        if fase == "final":
            if not confirmou:
                raise RotulagemError("a decisão final exige confirmação explícita")
            if est.get("inicial") is None:
                raise RotulagemError("registre a decisão inicial (sem sugestão) antes da final")
        return self._acrescentar({
            "tipo": "decisao", "item": item, "dimensao": dim, "valor": valor, "fase": fase,
            "observacao": observacao, "sugestao_vista_antes": bool(est.get("sugestao_vista")),
            "valor_coincide_com_sugestao": (valor == sugestao_valor) if sugestao_valor else None,
            "origem": "humano_via_interface",
        })

    def transcrever(self, item: str, valor: str, origem: str, documento: str, transcrito_por: str,
                    valor_original: str | None = None, substituir: bool = False) -> dict:
        """Registra uma decisão **inicial** que o avaliador tomou fora da interface (p.ex. num MD) e que
        outra pessoa/ferramenta transcreve. A origem NÃO é `humano_via_interface`, para não fingir cliques."""
        dim = item.split("|")[-1]
        if dim not in DIMENSOES or valor not in DIMENSOES[dim]:
            raise RotulagemError(f"valor inválido para {dim}: {valor!r}")
        est = self.estado().get(item, {})
        anterior = est.get("inicial")
        if anterior is not None and not substituir:
            raise RotulagemError(f"{item} já tem decisão inicial; a transcrição não sobrescreve")
        return self._acrescentar({
            "tipo": "decisao", "item": item, "dimensao": dim, "valor": valor, "fase": "inicial",
            "observacao": "", "sugestao_vista_antes": False, "valor_coincide_com_sugestao": None,
            "origem": origem, "documento_de_origem": documento, "transcrito_por": transcrito_por,
            **({"valor_original_texto": valor_original} if valor_original is not None else {}),
            **({"substitui_valor_anterior": anterior} if anterior is not None else {}),
        })

    def anotar(self, item: str, texto: str) -> dict:
        """Observação livre; não altera nenhuma decisão."""
        return self._acrescentar({"tipo": "observacao", "item": item, "texto": texto[:500]})

    def sugestao_exibida(self, item: str, fonte: str) -> dict:
        est = self.estado().get(item, {})
        if est.get("inicial") is None:
            raise RotulagemError("a sugestão só é liberada depois da sua decisão inicial")
        return self._acrescentar({"tipo": "sugestao_exibida", "item": item, "fonte_sugestao": fonte})


# ----------------------------------------------------------------------------------------- export

def _decisao(est: dict) -> str:
    return (est.get("final") or est.get("inicial") or "") if est else ""


def montar_planilha(pacote: Pacote, registro: Registro) -> list[dict]:
    est = registro.estado()
    linhas = linhas_planilha([{**r} for r in pacote.amostra])
    vistos: set[str] = set()
    for l in linhas:
        if l["full_name"] not in vistos:
            vistos.add(l["full_name"])
            l["tipo_projeto"] = _decisao(est.get(item_repo(l["full_name"], "tipo_projeto")))
            l["releases_sao_entregas_reais"] = _decisao(est.get(item_repo(l["full_name"], "releases_sao_entregas_reais")))
        e = est.get(item_release(l["release_id"]))
        l["corretiva"] = _decisao(e)
        l["observacoes"] = (e or {}).get("obs", "") or ""
    return linhas


def exportar(pacote: Pacote, registro: Registro, forcar: bool = False) -> dict:
    """Grava `labels_<usuario>.csv`. Recusa sobrescrever conteúdo que não veio desta ferramenta."""
    if registro.usuario not in pacote.avaliadores:
        raise RotulagemError(f"usuário {registro.usuario!r} não é avaliador do pacote: {pacote.avaliadores}")
    destino = pacote.pasta / f"labels_{registro.usuario}.csv"
    resumo_arq = registro.dir / f"{registro.usuario}_resumo.json"
    if destino.exists() and not forcar:
        with destino.open(encoding="utf-8-sig", newline="") as f:
            preenchido = any((r.get("corretiva") or r.get("tipo_projeto") or "").strip() for r in csv.DictReader(f))
        sha = hashlib.sha256(destino.read_bytes()).hexdigest()
        anterior = json.loads(resumo_arq.read_text(encoding="utf-8")).get("labels_sha256") if resumo_arq.exists() else None
        if preenchido and sha != anterior:
            raise RotulagemError(
                f"{destino.name} tem conteúdo que não foi exportado por esta ferramenta; "
                "use --forcar-exportar se for isso mesmo que quer (o original será preservado em .bak)")
    if destino.exists() and forcar:
        destino.with_suffix(".csv.bak").write_bytes(destino.read_bytes())
    linhas = montar_planilha(pacote, registro)
    _escrever_csv(destino, COLUNAS_PLANILHA, linhas)
    problemas = validar(destino, pacote.pasta / "amostra_validacao.csv")
    ev = registro.eventos()
    decis = [e for e in ev if e["tipo"] == "decisao"]
    fin = [e for e in decis if e["fase"] == "final"]
    resumo = {
        "usuario_informado": registro.usuario, "exportado_em": agora(),
        "labels_sha256": hashlib.sha256(destino.read_bytes()).hexdigest(),
        "completo": not problemas, "pendencias": len(problemas),
        "n_decisoes_registradas": len(decis), "n_decisoes_finais": len(fin),
        "n_finais_apos_ver_sugestao": sum(1 for e in fin if e["sugestao_vista_antes"]),
        "n_finais_iguais_a_sugestao": sum(1 for e in fin if e.get("valor_coincide_com_sugestao")),
        "n_sugestoes_exibidas": sum(1 for e in ev if e["tipo"] == "sugestao_exibida"),
        "decisoes_por_origem": dict(sorted(Counter(e["origem"] for e in decis).items())),
        "autenticacao": "nenhuma: o nome é apenas informado",
        "fonte_sugestoes": sorted({s["fonte"] for s in pacote.sugestoes.values()}),
    }
    resumo_arq.parent.mkdir(parents=True, exist_ok=True)
    resumo_arq.write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return resumo


def progresso(pacote: Pacote, registro: Registro) -> dict:
    est = registro.estado()
    total = len(pacote.amostra) + 2 * len(pacote.repositorios())
    feitos = sum(1 for k, e in est.items() if e.get("inicial") or e.get("final"))
    return {"itens": total, "com_decisao": feitos, "completo": feitos >= total}


# ---------------------------------------------------------------------------- modo comparação (IA)

PASTA_COMPARACAO = "comparacao_ia"
ACOES = ("confirmou", "alterou", "rejeitou")
ORIGEM_LOTE = "preenchimento_em_lote_com_sugestao_ia"
ACAO_LOTE = "preenchido_em_lote_ia"


class Comparacao:
    """Compara a sugestão automática (IA) com a resposta do avaliador, **fora** da validação.

    Não escreve `labels_*.csv` nem o log do modo normal. Tudo vai para `comparacao_ia/`, que o
    `avaliar` não lê. Cada ação é uma decisão humana tomada **vendo** a sugestão (não cega).
    """

    def __init__(self, pacote: Pacote, usuario: str, sessao: str | None = None):
        if usuario not in pacote.avaliadores:
            raise RotulagemError(f"usuário {usuario!r} não é avaliador do pacote: {pacote.avaliadores}")
        if not pacote.sugestoes:
            raise RotulagemError(f"o modo de comparação exige {ARQ_SUGESTOES} (nenhuma sugestão carregada)")
        self.pacote, self.usuario = pacote, usuario
        self.dir = pacote.pasta / PASTA_COMPARACAO
        self.log = self.dir / f"{usuario}.jsonl"
        self.csv = self.dir / f"{usuario}_comparacao.csv"
        self.resumo_arq = self.dir / f"{usuario}_comparacao_resumo.json"
        self.sessao = sessao or uuid.uuid4().hex[:8]
        self._lock = threading.Lock()
        self.releases = {str(r["release_id"]): r for r in pacote.amostra}

    def eventos(self) -> list[dict]:
        if not self.log.exists():
            return []
        return [json.loads(l) for l in self.log.read_text(encoding="utf-8").splitlines() if l.strip()]

    def estado(self) -> dict[str, dict]:
        est: dict[str, dict] = {}
        for ev in self.eventos():
            if ev["tipo"] in ("acao", "acao_lote"):
                est[ev["release_id"]] = ev
            elif ev["tipo"] == "limpar":
                est.pop(ev["release_id"], None)
        return est

    def _acrescentar(self, ev: dict) -> dict:
        ev = {"ts": agora(), "usuario_informado": self.usuario, "sessao": self.sessao, **ev}
        with self._lock:
            self.dir.mkdir(parents=True, exist_ok=True)
            with self.log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return ev

    def agir(self, release_id: str, acao: str, valor: str | None = None, confirmou: bool = False) -> dict:
        rid = str(release_id)
        if rid not in self.releases:
            raise RotulagemError(f"release {rid} fora da amostra")
        if rid not in self.pacote.sugestoes:
            raise RotulagemError(f"release {rid} sem sugestão automática")
        if acao not in ACOES:
            raise RotulagemError(f"ação inválida: {acao!r}")
        if not confirmou:
            raise RotulagemError("a ação exige confirmação explícita")
        sug = self.pacote.sugestoes[rid]
        if acao == "confirmou":
            final = sug["corretiva"]
        elif acao == "alterou":
            if valor not in CORRETIVA:
                raise RotulagemError(f"valor inválido: {valor!r}")
            if valor == sug["corretiva"]:
                raise RotulagemError("o valor é igual ao da sugestão; use 'confirmar'")
            final = valor
        else:
            final = None
        return self._acrescentar({
            "tipo": "acao", "release_id": rid, "acao": acao, "valor_ia": sug["corretiva"],
            "fonte_ia": sug["fonte"], "valor_final_humano": final, "decisao_vendo_sugestao": True,
            "origem": "humano_via_interface_comparacao",
        })

    def limpar(self, release_id: str) -> dict:
        return self._acrescentar({"tipo": "limpar", "release_id": str(release_id)})

    def pendentes(self) -> list[str]:
        est = self.estado()
        return [str(r["release_id"]) for r in self.pacote.amostra
                if str(r["release_id"]) in self.pacote.sugestoes and str(r["release_id"]) not in est]

    def preencher_em_lote(self, confirmou: bool = False) -> dict:
        """Registra, **só para itens pendentes**, o valor exato da sugestão da IA, como ação em lote.

        Não toca nenhuma ação existente (humana ou não) e **não** é uma decisão humana: o evento tem
        `decisao_humana=False` e origem `preenchimento_em_lote_com_sugestao_ia`. Uma ação humana posterior
        no mesmo item a substitui (último evento vale).
        """
        if not confirmou:
            raise RotulagemError("o preenchimento em lote exige confirmação explícita")
        lote = self.pendentes()
        sessao_lote = f"lote-{uuid.uuid4().hex[:8]}"
        for rid in lote:
            sug = self.pacote.sugestoes[rid]
            self._acrescentar({
                "tipo": "acao_lote", "release_id": rid, "acao": ACAO_LOTE, "valor_ia": sug["corretiva"],
                "fonte_ia": sug["fonte"], "valor_final_humano": None, "valor_registrado": sug["corretiva"],
                "decisao_humana": False, "decisao_vendo_sugestao": False, "origem": ORIGEM_LOTE,
                "lote": sessao_lote,
            })
        return {"n_preenchidos": len(lote), "lote": sessao_lote, "ja_resolvidos": len(self.estado()) - len(lote)}

    def progresso(self) -> dict:
        est = self.estado()
        total = len(self.pacote.sugestoes)
        return {"total": total, "resolvidos": len(est), "completo": len(est) >= total}

    def concluir(self, forcar: bool = False) -> dict:
        """Gera o CSV e o resumo da comparação. Nunca toca `labels_*.csv`."""
        if self.csv.parent.name != PASTA_COMPARACAO:  # defesa: nunca escrever fora da pasta própria
            raise RotulagemError("destino inválido")
        if self.csv.exists() and not forcar:
            anterior = None
            if self.resumo_arq.exists():
                anterior = json.loads(self.resumo_arq.read_text(encoding="utf-8")).get("csv_sha256")
            if anterior != hashlib.sha256(self.csv.read_bytes()).hexdigest():
                raise RotulagemError(
                    f"{self.csv.name} foi alterado fora da ferramenta; use --forcar-exportar (cria .bak)")
        if self.csv.exists() and forcar:
            self.csv.with_suffix(".csv.bak").write_bytes(self.csv.read_bytes())
        est = self.estado()
        linhas = []
        for rid, r in ((str(x["release_id"]), x) for x in self.pacote.amostra if str(x["release_id"]) in self.pacote.sugestoes):
            sug = self.pacote.sugestoes[rid]
            e = est.get(rid)
            lote = bool(e and e["tipo"] == "acao_lote")
            linhas.append({
                "release_id": rid, "full_name": r["full_name"], "tag_name": r["tag_name"],
                "release_url": r["release_url"],
                "origem_da_sugestao": "AUTOMÁTICA (IA)", "fonte_da_sugestao": sug["fonte"],
                "sugestao_ia": sug["corretiva"], "motivo_ia": sug["motivo"],
                "acao_do_avaliador": e["acao"] if e else "pendente",
                "resposta_humana": (e["valor_final_humano"] or "") if e else "",
                "decisao_humana": "nao" if (lote or not e) else "sim",
                "origem_do_registro": (e["origem"] if e else ""),
                "valor_registrado": (e.get("valor_registrado") or e.get("valor_final_humano") or "") if e else "",
                "alterou_a_sugestao": "sim" if e and e["acao"] in ("alterou", "rejeitou") else "nao",
                "registrado_em": e["ts"] if e else "", "usuario_informado": self.usuario,
                "decisao_vendo_sugestao": "nao" if lote else "sim",
            })
        self.dir.mkdir(parents=True, exist_ok=True)
        cols = list(linhas[0])
        with self.csv.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(linhas)
        cont = {a: sum(1 for l in linhas if l["acao_do_avaliador"] == a) for a in (*ACOES, ACAO_LOTE, "pendente")}
        com_resposta = [l for l in linhas if l["resposta_humana"]]
        resumo = {
            "usuario_informado": self.usuario, "gerado_em": agora(), "csv_sha256":
                hashlib.sha256(self.csv.read_bytes()).hexdigest(),
            "n_releases": len(linhas), **{f"n_{a}": n for a, n in cont.items()},
            "completo": cont["pendente"] == 0,
            "n_decisoes_humanas": sum(1 for l in linhas if l["decisao_humana"] == "sim"),
            "n_registrados_em_lote_nao_humanos": cont[ACAO_LOTE],
            "n_com_resposta_humana": len(com_resposta),
            "concordancia_com_ia": (sum(1 for l in com_resposta if l["resposta_humana"] == l["sugestao_ia"])
                                    / len(com_resposta)) if com_resposta else None,
            "natureza": "comparação de sugestão automática (IA) com resposta do avaliador; "
                        "NÃO é rotulagem cega e NÃO entra na validação independente da v12",
            "consumido_por_avaliar": False,
            "autenticacao": "nenhuma: o nome é apenas informado",
            "fonte_sugestoes": sorted({s["fonte"] for s in self.pacote.sugestoes.values()}),
        }
        self.resumo_arq.write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return resumo


PAGINA_COMP = """<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><title>Comparação com sugestões da IA</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{font:15px/1.45 system-ui,sans-serif;max-width:980px;margin:1rem auto;padding:0 1rem;color:#1c1c1c}
header{position:sticky;top:0;background:#fff;border-bottom:2px solid #c0392b;padding:.5rem 0;z-index:2}
.aviso{background:#fdecea;border:1px solid #c0392b;padding:.5rem .7rem;border-radius:6px;margin:.5rem 0}
.rel{border:1px solid #ccc;border-radius:8px;margin:.7rem 0;padding:.6rem}
.ia{background:#fff7d6;border:1px solid #e0c060;padding:.4rem .6rem;border-radius:6px;margin:.4rem 0}
.tag{font-weight:600;color:#7a5200}.ok{color:#0a6b2d}.pend{color:#a33}
pre{background:#f6f6f6;padding:.5rem;white-space:pre-wrap;max-height:200px;overflow:auto;font-size:13px}
button{cursor:pointer;margin-right:.3rem}
</style></head><body><header><b>Comparação com sugestões automáticas — avaliador informado: <span id="u"></span></b>
<small>(sem autenticação) · <span id="prog"></span></small>
<button onclick="concluir()">Concluir e gerar arquivo de comparação</button> <small id="msg"></small></header>
<div class="aviso"><b>Todos os rótulos abaixo foram gerados automaticamente por IA</b> a partir de notas e commits. Não são decisões
humanas. Este modo <u>não</u> grava <code>labels_*.csv</code> e <u>não</u> faz parte da validação independente da v12.
Você decide cada item vendo a sugestão (decisão não cega).</div>
<div id="app">carregando…</div><script>
async function api(p,b){const r=await fetch(p,b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{});
 const j=await r.json();if(!r.ok)throw new Error(j.erro||r.status);return j}
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function carregar(){const d=await api('/api/comp/estado');
 document.getElementById('u').textContent=d.usuario;
 document.getElementById('prog').textContent=`${d.progresso.resolvidos}/${d.progresso.total} itens resolvidos`;
 document.getElementById('app').innerHTML=d.itens.map(r=>`<h3><a href="${r.repo_url}" target="_blank" rel="noopener">${r.full_name}</a></h3>`+
  r.releases.map(x=>{const s=d.sugestoes[x.release_id],e=d.estado[x.release_id],outro=s.corretiva==='sim'?'nao':'sim';
  return `<div class="rel"><b>${x.tag_name}</b> <small>${x.published_at}</small> ·
  <a href="${x.release_url}" target="_blank" rel="noopener">release</a> · <a href="${x.compare_url}" target="_blank" rel="noopener">commits</a>
  <details><summary>notas e commits (${x.n_commits})</summary><pre>${esc(x.notas)||'(sem notas)'}</pre><pre>${x.commits.map(esc).join('\\n---\\n')}</pre></details>
  <div class="ia"><span class="tag">SUGESTÃO AUTOMÁTICA (IA) — não é decisão humana:</span> <b>${s.corretiva}</b> — ${esc(s.motivo)}<br><small>fonte: ${esc(s.fonte)}</small></div>
  <div>${e&&e.tipo==='acao_lote'?`<span class="pend">Preenchido em lote com a sugestão da IA (<b>${e.valor_registrado}</b>) — <u>não é decisão humana</u></span> <button onclick="limpar('${x.release_id}')">desfazer</button>`:e?`<span class="ok">Sua ação: <b>${e.acao}</b>${e.valor_final_humano?' → '+e.valor_final_humano:' (sem valor)'}</span> <button onclick="limpar('${x.release_id}')">desfazer</button>`:
  `<span class="pend">pendente</span> `}
  <button onclick="agir('${x.release_id}','confirmou',null,'${s.corretiva}')">Confirmar sugestão (${s.corretiva})</button>
  <button onclick="agir('${x.release_id}','alterou','${outro}','${outro}')">Alterar para ${outro}</button>
  <button onclick="agir('${x.release_id}','rejeitou',null,'')">Rejeitar sugestão</button></div></div>`}).join('')).join('')}
async function agir(id,acao,valor,mostrar){const t={confirmou:`CONFIRMAR a sugestão "${mostrar}" como SUA resposta`,alterou:`ALTERAR para "${mostrar}" como SUA resposta`,rejeitou:'REJEITAR a sugestão (sem resposta)'}[acao];
 if(!confirm('Registrar: '+t+'?'))return;
 try{await api('/api/comp/acao',{release_id:id,acao,valor,confirmou:true});await carregar()}catch(e){msg(e.message)}}
async function limpar(id){try{await api('/api/comp/limpar',{release_id:id});await carregar()}catch(e){msg(e.message)}}
async function concluir(){try{const r=await api('/api/comp/concluir',{});msg(`arquivo gerado (${r.completo?'completo':r.n_pendente+' pendentes'}; concordância com a IA: ${r.concordancia_com_ia===null?'n/d':(r.concordancia_com_ia*100).toFixed(1)+'%'})`)}catch(e){msg(e.message)}}
function msg(m){document.getElementById('msg').textContent=m}
carregar();</script></body></html>"""


def criar_servidor_comparacao(comp: Comparacao, porta: int = 8766, forcar_exportar: bool = False):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj, status=200):
            corpo = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):  # noqa: N802
            if self.path == "/":
                corpo = PAGINA_COMP.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)
            elif self.path == "/api/comp/estado":
                self._json({"usuario": comp.usuario, "itens": comp.pacote.itens(), "estado": comp.estado(),
                            "sugestoes": comp.pacote.sugestoes, "progresso": comp.progresso()})
            else:
                self._json({"erro": "não encontrado"}, 404)

        def do_POST(self):  # noqa: N802
            try:
                n = int(self.headers.get("Content-Length") or 0)
                b = json.loads(self.rfile.read(n) or b"{}")
                if self.path == "/api/comp/acao":
                    ev = comp.agir(b["release_id"], b["acao"], b.get("valor"), bool(b.get("confirmou")))
                    self._json({"ok": True, "ts": ev["ts"]})
                elif self.path == "/api/comp/limpar":
                    comp.limpar(b["release_id"])
                    self._json({"ok": True})
                elif self.path == "/api/comp/concluir":
                    self._json(comp.concluir(forcar_exportar))
                else:
                    self._json({"erro": "não encontrado"}, 404)
            except (RotulagemError, KeyError, ValueError) as exc:
                self._json({"erro": str(exc)}, 400)

    return ThreadingHTTPServer(("127.0.0.1", porta), H)


# -------------------------------------------------------------------------------------------- web

PAGINA = """<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><title>Rotulagem — validação independente</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{font:15px/1.45 system-ui,sans-serif;max-width:980px;margin:1rem auto;padding:0 1rem;color:#1c1c1c}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ccc;padding:.5rem 0;z-index:2}
.repo{border:1px solid #bbb;border-radius:8px;margin:1rem 0;padding:.8rem}.rel{border-top:1px solid #ddd;padding:.7rem 0}
pre{background:#f6f6f6;padding:.5rem;white-space:pre-wrap;max-height:220px;overflow:auto;font-size:13px}
.sug{background:#fff7d6;border:1px solid #e0c060;padding:.4rem .6rem;border-radius:6px;margin:.4rem 0}
.ia{font-weight:600;color:#7a5200}.ok{color:#0a6b2d}.pend{color:#a33}button{cursor:pointer}
select,input[type=text]{font:inherit}small{color:#555}
</style></head><body><header><b>Rotulagem cega — avaliador informado: <span id="u"></span></b>
<small>(sem autenticação: o nome só é informado) · <span id="prog"></span></small>
<button onclick="exportar()">Exportar labels_<span id="u2"></span>.csv</button> <small id="msg"></small></header>
<p><small>Fase 1: decida sozinho(a), sem sugestão. Fase 2 (opcional): veja a <span class="ia">sugestão automática (IA)</span>
e confirme a decisão final — a sugestão <u>não</u> é decisão sua enquanto você não confirmar um valor.</small></p>
<div id="app">carregando…</div><script>
let S={};const T=%TIPOS%,E=%ENTREGA%;
async function api(p,b){const r=await fetch(p,b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{});
 const j=await r.json();if(!r.ok)throw new Error(j.erro||r.status);return j}
function opt(v,sel){return `<option value="${v}" ${v===sel?'selected':''}>${v}</option>`}
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function carregar(){const d=await api('/api/estado');S=d;
 document.getElementById('u').textContent=document.getElementById('u2').textContent=d.usuario;
 document.getElementById('prog').textContent=`${d.progresso.com_decisao}/${d.progresso.itens} itens com decisão`;
 document.getElementById('app').innerHTML=d.itens.map(r=>`<div class="repo"><h3><a href="${r.repo_url}" target="_blank" rel="noopener">${r.full_name}</a></h3>
 ${campo(r.item_tipo,'Tipo do projeto',T,d.estado[r.item_tipo])}${campo(r.item_entrega,'Releases são entregas reais?',E,d.estado[r.item_entrega])}
 ${r.releases.map(x=>rel(x,d.estado[x.item]||{},d.sugestoes[x.item])).join('')}</div>`).join('')}
function campo(item,rot,vals,e){e=e||{};return `<div>${rot}: <select onchange="decidir('${item}',this.value,'inicial',this)">
 <option value="">— escolha —</option>${vals.map(v=>opt(v,e.final||e.inicial)).join('')}</select> <small class="${e.inicial?'ok':'pend'}">${e.inicial?'registrado':'pendente'}</small></div>`}
function rel(x,e,sug){const ini=e.inicial,fin=e.final;
 const sugHtml=x.tem_sugestao?(e.sugestao_vista&&sug?`<div class="sug"><span class="ia">SUGESTÃO AUTOMÁTICA (${esc(sug.fonte)}) — não é decisão humana:</span>
  <b>${sug.corretiva}</b> — ${esc(sug.motivo)}</div>`:(ini?`<button onclick="verSug('${x.item}')">Ver sugestão automática</button>`:'<small>(sugestão disponível após sua decisão inicial)</small>')):'';
 return `<div class="rel"><b>${x.tag_name}</b> <small>${x.published_at}</small> ·
 <a href="${x.release_url}" target="_blank" rel="noopener">release</a> · <a href="${x.compare_url}" target="_blank" rel="noopener">commits</a>
 ${x.compare_inacessivel?'<b class="pend"> [compare inacessível]</b>':''}
 <details><summary>notas e commits (${x.n_commits})</summary><pre>${esc(x.notas)||'(sem notas)'}</pre><pre>${x.commits.map(esc).join('\\n---\\n')}</pre></details>
 <div>É corretiva? <label><input type="radio" name="c${x.release_id}" ${ini==='sim'?'checked':''} onchange="decidir('${x.item}','sim','inicial')">sim</label>
 <label><input type="radio" name="c${x.release_id}" ${ini==='nao'?'checked':''} onchange="decidir('${x.item}','nao','inicial')">nao</label>
 <small class="${ini?'ok':'pend'}">${ini?'decisão inicial: '+ini:'pendente'}</small>
 ${fin&&fin!==ini?`<small class="ok"> · final: <b>${fin}</b></small>`:''}</div>
 ${sugHtml}${e.sugestao_vista&&sug?`<div>Decisão final: <select id="f${x.release_id}"><option value="sim" ${(fin||ini)==='sim'?'selected':''}>sim</option><option value="nao" ${(fin||ini)==='nao'?'selected':''}>nao</option></select>
 <button onclick="final('${x.item}','${x.release_id}','${sug.corretiva}')">Confirmar decisão final</button></div>`:''}
 <div><small>observações: </small><input type="text" size="60" value="${esc(e.obs)}" onchange="obs('${x.item}',this.value)"></div></div>`}
async function decidir(item,valor,fase,el){if(!valor)return;try{await api('/api/decisao',{item,valor,fase});await carregar()}catch(e){msg(e.message)}}
async function verSug(item){try{await api('/api/sugestao',{item});await carregar()}catch(e){msg(e.message)}}
async function final(item,id,sv){const v=document.getElementById('f'+id).value;
 if(!confirm(`Registrar COMO SUA decisão final: "${v}"?`))return;
 try{await api('/api/decisao',{item,valor:v,fase:'final',confirmou:true,sugestao_valor:sv});await carregar()}catch(e){msg(e.message)}}
async function obs(item,t){try{await api('/api/obs',{item,texto:t});await carregar()}catch(e){msg(e.message)}}
async function exportar(){try{const r=await api('/api/exportar',{});msg(`exportado: ${r.completo?'COMPLETO':r.pendencias+' pendências'}`)}catch(e){msg(e.message)}}
function msg(m){document.getElementById('msg').textContent=m}
carregar();</script></body></html>"""


def criar_servidor(pacote: Pacote, registro: Registro, porta: int = 8765, forcar_exportar: bool = False):
    pagina = PAGINA.replace("%TIPOS%", json.dumps(list(TIPOS_PROJETO))).replace("%ENTREGA%", json.dumps(list(ENTREGA_REAL)))

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silencioso
            pass

        def _json(self, obj, status=200):
            corpo = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):  # noqa: N802
            if self.path == "/":
                corpo = pagina.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)
            elif self.path == "/api/estado":
                est = registro.estado()
                # sugestões só são entregues ao navegador para itens cuja sugestão já foi liberada pelo servidor
                liberadas = {k: pacote.sugestoes[k.split("|")[1]] for k, e in est.items()
                             if e["sugestao_vista"] and k.startswith("rel|") and k.split("|")[1] in pacote.sugestoes}
                self._json({"usuario": registro.usuario, "itens": pacote.itens(), "estado": est, "sugestoes": liberadas,
                            "progresso": progresso(pacote, registro)})
            else:
                self._json({"erro": "não encontrado"}, 404)

        def do_POST(self):  # noqa: N802
            try:
                n = int(self.headers.get("Content-Length") or 0)
                b = json.loads(self.rfile.read(n) or b"{}")
                if self.path == "/api/decisao":
                    ev = registro.decidir(b["item"], b["valor"], b.get("fase", "inicial"), b.get("observacao", ""),
                                          bool(b.get("confirmou")), b.get("sugestao_valor"))
                    self._json({"ok": True, "ts": ev["ts"]})
                elif self.path == "/api/sugestao":
                    rid = b["item"].split("|")[1]
                    if rid not in pacote.sugestoes:
                        raise RotulagemError("não há sugestão para este item")
                    registro.sugestao_exibida(b["item"], pacote.sugestoes[rid]["fonte"])
                    self._json({"ok": True})
                elif self.path == "/api/obs":
                    registro.anotar(b["item"], str(b.get("texto", "")))
                    self._json({"ok": True})
                elif self.path == "/api/exportar":
                    self._json(exportar(pacote, registro, forcar_exportar))
                else:
                    self._json({"erro": "não encontrado"}, 404)
            except (RotulagemError, KeyError, ValueError) as exc:
                self._json({"erro": str(exc)}, 400)

    return ThreadingHTTPServer(("127.0.0.1", porta), H)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(prog="python -m scripts.rotulagem_assistida", description=__doc__.split("\n\n")[0])
    p.add_argument("--usuario", required=True, help="seu nome de avaliador (um de congelamento.json)")
    p.add_argument("--pasta", default=str(PASTA))
    p.add_argument("--porta", type=int, default=8765)
    p.add_argument("--nao-abrir", action="store_true")
    p.add_argument("--exportar", action="store_true", help="só exporta labels_<usuario>.csv e sai")
    p.add_argument("--preencher-em-lote", action="store_true",
                   help="(com --comparacao) registra a sugestão da IA nos itens PENDENTES, como ação em lote não humana")
    p.add_argument("--confirmar-lote", action="store_true", help="confirma explicitamente o preenchimento em lote")
    p.add_argument("--comparacao", action="store_true",
                   help="modo de comparação com as sugestões da IA (NÃO grava labels_*.csv; saída em comparacao_ia/)")
    p.add_argument("--forcar-exportar", action="store_true")
    a = p.parse_args(argv)
    try:
        pacote = Pacote(Path(a.pasta))
        if a.usuario not in pacote.avaliadores:
            raise RotulagemError(f"--usuario deve ser um de {pacote.avaliadores}")
        if a.comparacao:
            comp = Comparacao(pacote, a.usuario)
            if a.preencher_em_lote:
                if not a.confirmar_lote:
                    print(f"{len(comp.pendentes())} itens pendentes seriam preenchidos com a sugestão da IA "
                          f"(origem '{ORIGEM_LOTE}', não humana). Repita com --confirmar-lote para executar.")
                    return 2
                r = comp.preencher_em_lote(confirmou=True)
                print(json.dumps({**r, "resumo": comp.concluir(a.forcar_exportar)}, ensure_ascii=False, indent=2))
                return 0
            if a.exportar:
                print(json.dumps(comp.concluir(a.forcar_exportar), ensure_ascii=False, indent=2))
                return 0
            porta = a.porta if a.porta != 8765 else 8766
            srv = criar_servidor_comparacao(comp, porta, a.forcar_exportar)
            url = f"http://127.0.0.1:{porta}/"
            log.info("COMPARAÇÃO com sugestões da IA (não é validação) — %s em %s (Ctrl+C encerra)", a.usuario, url)
            if not a.nao_abrir:
                webbrowser.open(url)
            try:
                srv.serve_forever()
            except KeyboardInterrupt:
                pass
            return 0
        reg = Registro(Path(a.pasta), a.usuario)
        if a.exportar:
            r = exportar(pacote, reg, a.forcar_exportar)
            print(json.dumps(r, ensure_ascii=False, indent=2))
            return 0
        srv = criar_servidor(pacote, reg, a.porta, a.forcar_exportar)
    except (RotulagemError, OSError, KeyError) as exc:
        log.error("%s", exc)
        return 1
    url = f"http://127.0.0.1:{a.porta}/"
    log.info("Rotulagem de %s em %s (Ctrl+C encerra). Sugestões: %s", a.usuario, url,
             f"{len(pacote.sugestoes)} (fonte: {', '.join(sorted({s['fonte'] for s in pacote.sugestoes.values()}))})"
             if pacote.sugestoes else "nenhuma")
    if not a.nao_abrir:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
