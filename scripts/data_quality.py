"""Relatório de qualidade dos dados e invariantes automáticos (Issue #29, bônus).

Uso (a partir da raiz do repositório):

    python -m scripts.data_quality --config config.yaml
    python -m scripts.data_quality --metricas data/metrics.csv --dicionario DICIONARIO_DE_DADOS.csv

Lê o CSV de métricas (padrão `<saidas>/resultados.csv`), o `funil.csv` e, se existirem, o cache
de commits e o dicionário de dados. Grava em `<saidas>/`:

- `data_quality.csv`: uma linha por verificação (`grupo,verificacao,status,valor,detalhe`);
- `data_quality.md`: o mesmo, legível, para a Metodologia/ameaças à validade.

Grupos:
- `invariante`: regras que NÃO podem ser violadas (status `OK` ou `FALHA`; `N/A` se a coluna ou
  o arquivo necessário não existe ainda). Qualquer `FALHA` faz o comando sair com código 1.
- `nulos`, `duplicatas`, `datas`, `censura`, `404`, `cobertura`, `linguagem`: descrição dos dados
  (status `INFO`/`ALERTA`; alertas não derrubam o comando).

Os nomes das colunas do CFR (b) ainda não existem no dataset (Issue #21): ficam nas constantes
`COL_*` abaixo e as invariantes correspondentes aparecem como `N/A` até as colunas existirem.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from pipeline.config import ConfigError, load_config

# Colunas do dataset consultadas pelas invariantes.
COL_REPO = "full_name"
COL_CFR_A, COL_CFR_B = "cfr_a", "cfr_b"
COLS_LEAD_TIME = ("lt_release_median_h", "lt_commit_median_h")
COLS_PARTICAO_LT = ("n_releases_avaliadas", "n_sem_anterior", "n_releases_ignored_404", "n_sem_commits_novos")
COL_RELEASES_JANELA_FUNIL = "n_releases_window"  # funil.csv
COL_CFR_B_AVALIADAS, COL_CFR_B_CENSURADAS, COL_CFR_B_TOTAL = (
    "n_releases_avaliadas_cfr_b", "n_releases_censuradas_cfr_b", "n_releases_janela",
)
COL_PROP_CENSURA = "prop_episodios_censurados"

COLUNAS_SAIDA = ("grupo", "verificacao", "status", "valor", "detalhe")
LIMITE_EXEMPLOS = 5


def _num(valor):
    """float ou None (vazio/ausente/inválido)."""
    try:
        x = float(valor)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def _inst(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None


def ler_csv(arquivo: Path) -> list[dict]:
    with Path(arquivo).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _linha(grupo, verificacao, status, valor="", detalhe="") -> dict:
    return {"grupo": grupo, "verificacao": verificacao, "status": status, "valor": valor, "detalhe": detalhe}


def _exemplos(nomes: list[str]) -> str:
    resto = len(nomes) - LIMITE_EXEMPLOS
    return ", ".join(nomes[:LIMITE_EXEMPLOS]) + (f" (+{resto})" if resto > 0 else "")


def _invariante(nome: str, violacoes: list[str] | None, n_avaliados: int = 0) -> dict:
    """`violacoes=None` = não verificável (coluna/arquivo ausente)."""
    if violacoes is None:
        return _linha("invariante", nome, "N/A", "", "coluna ou arquivo necessário ausente")
    if violacoes:
        return _linha("invariante", nome, "FALHA", len(violacoes), _exemplos(violacoes))
    return _linha("invariante", nome, "OK", 0, f"{n_avaliados} itens verificados")


# --- invariantes ------------------------------------------------------------------------------

def inv_faixa(linhas: list[dict], coluna: str, minimo: float, maximo: float | None, nome: str) -> dict:
    if not linhas or coluna not in linhas[0]:
        return _invariante(nome, None)
    ruins, n = [], 0
    for r in linhas:
        v = _num(r.get(coluna))
        if v is None:
            continue
        n += 1
        if v < minimo or (maximo is not None and v > maximo):
            ruins.append(f"{r[COL_REPO]}={v:g}")
    return _invariante(nome, ruins, n)


def inv_particao_lead_time(linhas: list[dict], funil: dict[str, dict]) -> dict:
    """avaliadas + sem_anterior + 404 + sem_commits_novos == releases de deploy na janela."""
    nome = "releases avaliadas + ignoradas = releases da janela (lead time)"
    if not linhas or not funil or not all(c in linhas[0] for c in COLS_PARTICAO_LT):
        return _invariante(nome, None)
    ruins, n = [], 0
    for r in linhas:
        f = funil.get(r[COL_REPO])
        janela = _num(f.get(COL_RELEASES_JANELA_FUNIL)) if f else None
        if janela is None:
            continue
        n += 1
        soma = sum(_num(r.get(c)) or 0 for c in COLS_PARTICAO_LT)
        if soma != janela:
            ruins.append(f"{r[COL_REPO]}: {soma:g} != {janela:g}")
    return _invariante(nome, ruins, n)


def inv_particao_cfr_b(linhas: list[dict]) -> dict:
    """avaliadas + censuradas == releases da janela (CFR b; E§5 RQ03: últimos 7 dias censurados)."""
    nome = "releases avaliadas + censuradas = releases da janela (CFR b)"
    cols = (COL_CFR_B_AVALIADAS, COL_CFR_B_CENSURADAS, COL_CFR_B_TOTAL)
    if not linhas or not all(c in linhas[0] for c in cols):
        return _invariante(nome, None)
    ruins, n = [], 0
    for r in linhas:
        a, c, t = (_num(r.get(k)) for k in cols)
        if None in (a, c, t):
            continue
        n += 1
        if a + c != t:
            ruins.append(f"{r[COL_REPO]}: {a:g}+{c:g} != {t:g}")
    return _invariante(nome, ruins, n)


def inv_dicionario(linhas: list[dict], dicionario: set[str] | None) -> dict:
    nome = "toda coluna do CSV está no dicionário de dados"
    if not linhas or dicionario is None:
        return _invariante(nome, None)
    return _invariante(nome, [c for c in linhas[0] if c not in dicionario], len(linhas[0]))


def inv_funil(funil: list[dict], metricas: list[dict], tabela_md: list[dict] | None) -> list[dict]:
    """Somas do funil: tabela etapa a etapa, descartes + selecionados e amostra final x dataset."""
    out = []
    nome = "funil: entram − saem = restam em cada etapa"
    if tabela_md is None:
        out.append(_invariante(nome, None))
    else:
        ruins = [f"{e['etapa']}: {e['entram']}-{e['saem']}!={e['restam']}"
                 for e in tabela_md if e["saem"] is not None and e["entram"] - e["saem"] != e["restam"]]
        ruins += [f"{b['etapa']}: restam {a['restam']} != entram {b['entram']}"
                  for a, b in zip(tabela_md, tabela_md[1:]) if b["entram"] is not None and a["restam"] != b["entram"]]
        out.append(_invariante(nome, ruins, len(tabela_md)))

    nome = "funil: selecionados + descartados = candidatos avaliados"
    if not funil:
        out.append(_invariante(nome, None))
        out.append(_invariante("funil: amostra final = repositórios do dataset", None))
        return out
    cont = Counter(r["status"] for r in funil)
    desconhecidos = [f"{s}={n}" for s, n in cont.items() if s not in ("selecionado", "descartado")]
    sem_motivo = [r[COL_REPO] for r in funil if r["status"] == "descartado" and not r.get("motivo")]
    out.append(_invariante(nome, desconhecidos + [f"{n} sem motivo" for n in sem_motivo[:1]], len(funil)))

    nome = "funil: amostra final = repositórios do dataset"
    if not metricas:
        out.append(_invariante(nome, None))
    else:
        finais = {r[COL_REPO] for r in funil if r["status"] == "selecionado"}
        dados = {r[COL_REPO] for r in metricas}
        ruins = [f"só no funil: {x}" for x in sorted(finais - dados)] + [f"só no dataset: {x}" for x in sorted(dados - finais)]
        out.append(_invariante(nome, ruins, len(dados)))
    return out


# --- descrição dos dados ----------------------------------------------------------------------

COLUNAS_VAZIAS_ESPERADAS = ("erro",)  # vazia = sem erro


def rel_nulos(linhas: list[dict]) -> list[dict]:
    out = []
    for coluna in (linhas[0] if linhas else []):
        if coluna in COLUNAS_VAZIAS_ESPERADAS:
            continue
        n = sum(1 for r in linhas if (r.get(coluna) or "").strip() == "")
        if n:
            out.append(_linha("nulos", coluna, "ALERTA", n, f"{n / len(linhas):.1%} das linhas vazias"))
    if not out:
        out.append(_linha("nulos", "(todas as colunas)", "OK", 0, "nenhum valor vazio"))
    return out


def rel_duplicatas(linhas: list[dict]) -> list[dict]:
    cont = Counter(r[COL_REPO].strip().lower() for r in linhas)
    dup = sorted(k for k, n in cont.items() if n > 1)
    if dup:
        return [_linha("duplicatas", "full_name repetido (sem diferenciar caixa)", "FALHA", len(dup), _exemplos(dup))]
    return [_linha("duplicatas", "full_name repetido (sem diferenciar caixa)", "OK", 0, f"{len(linhas)} únicos")]


def rel_censura_e_404(linhas: list[dict]) -> list[dict]:
    out = []
    n = len(linhas)
    if linhas and "n_episodios_censurados" in linhas[0]:
        total = sum(_num(r.get("n_episodios_censurados")) or 0 for r in linhas)
        eps = sum(_num(r.get("n_episodios")) or 0 for r in linhas)
        com = sum(1 for r in linhas if (_num(r.get("n_episodios_censurados")) or 0) > 0)
        out.append(_linha("censura", "episódios de falha censurados (RQ04)", "INFO", int(total),
                          f"{total:g} de {eps:g} episódios; {com} de {n} repositórios com ao menos um"))
    if linhas and COL_CFR_B_CENSURADAS in linhas[0]:
        total = sum(_num(r.get(COL_CFR_B_CENSURADAS)) or 0 for r in linhas)
        out.append(_linha("censura", "releases censuradas no CFR (b) (últimos 7 dias)", "INFO", int(total), ""))
    for coluna, rotulo in (
        ("n_releases_ignored_404", "releases ignoradas por 404 no compare"),
        ("n_sem_anterior", "releases sem anterior (1ª da história)"),
        ("n_sem_commits_novos", "releases sem commits novos"),
        ("n_commits_negativos", "commits com data posterior à release (excluídos)"),
        ("n_runs_dias_saturados", "dias de runs saturados (teto de 1.000 da API)"),
    ):
        if linhas and coluna in linhas[0]:
            total = sum(_num(r.get(coluna)) or 0 for r in linhas)
            com = sum(1 for r in linhas if (_num(r.get(coluna)) or 0) > 0)
            grupo = "404" if coluna == "n_releases_ignored_404" else "datas" if coluna == "n_commits_negativos" else "cobertura"
            status = "ALERTA" if coluna == "n_runs_dias_saturados" and total else "INFO"
            out.append(_linha(grupo, rotulo, status, int(total), f"{com} de {n} repositórios afetados"))
    return out


def rel_linguagem(linhas: list[dict]) -> list[dict]:
    if not linhas or "language" not in linhas[0]:
        return []
    cont = Counter((r["language"] or "").strip() or "(sem linguagem)" for r in linhas)
    return [
        _linha("linguagem", lang, "INFO", n, f"{n / len(linhas):.1%}")
        for lang, n in sorted(cont.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def rel_datas_cache(commits_dir: Path | None, fim=None) -> list[dict]:
    """Datas dos commits no cache: ausentes/ilegíveis e posteriores ao fim da janela."""
    if commits_dir is None or not Path(commits_dir).is_dir():
        return []
    total = sem_data = invalidas = futuras = 0
    for arq in sorted(Path(commits_dir).glob("*.json")):
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for comp in (dados.get("comparacoes") or {}).values():
            for c in comp.get("commits") or []:
                total += 1
                bruto = c.get("author_date")
                if not bruto:
                    sem_data += 1
                    continue
                d = _inst(bruto)
                if d is None:
                    invalidas += 1
                elif fim is not None and d.date() > fim:
                    futuras += 1
    status = "ALERTA" if sem_data or invalidas else "INFO"
    out = [_linha("datas", "commits sem author_date ou com data ilegível", status, sem_data + invalidas,
                  f"de {total} commits no cache")]
    if fim is not None:
        out.append(_linha("datas", f"commits com author_date depois do fim da janela ({fim})", "INFO", futuras, ""))
    return out


# --- leitura do funil.md e do dicionário ------------------------------------------------------

_LINHA_TABELA = re.compile(r"^\|\s*(?P<etapa>[^|]+?)\s*\|\s*(?P<entram>[\d.]+)\s*\|\s*(?P<saem>[\d.—-]+)\s*\|\s*(?P<restam>[\d.]+)\s*\|\s*$")


def ler_funil_md(arquivo: Path) -> list[dict] | None:
    """Linhas da tabela de etapas do `funil.md`; None se o arquivo não existe."""
    if not Path(arquivo).is_file():
        return None
    etapas = []
    for linha in Path(arquivo).read_text(encoding="utf-8").splitlines():
        m = _LINHA_TABELA.match(linha)
        if not m or not re.match(r"^\d", m["etapa"]):  # só "0. ...", "1. ..." (ignora "Amostra final")
            continue
        saem = None if m["saem"] in ("—", "-") else int(m["saem"].replace(".", ""))
        etapas.append({
            "etapa": m["etapa"], "entram": int(m["entram"].replace(".", "")),
            "saem": saem, "restam": int(m["restam"].replace(".", "")),
        })
    return etapas


def ler_dicionario(arquivo: Path | None) -> set[str] | None:
    """Nomes de coluna do dicionário (CSV com coluna coluna/nome/campo, ou MD com `nome` na 1ª coluna)."""
    if arquivo is None or not Path(arquivo).is_file():
        return None
    arquivo = Path(arquivo)
    if arquivo.suffix.lower() == ".csv":
        linhas = ler_csv(arquivo)
        for chave in ("coluna", "nome", "campo", "column", "name"):
            if linhas and chave in linhas[0]:
                return {r[chave].strip() for r in linhas if r[chave].strip()}
        raise ValueError(f"{arquivo}: sem coluna 'coluna' ou 'nome'")
    nomes = set()
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*`?([A-Za-z_][\w]*)`?\s*\|", linha)
        if m:
            nomes.add(m.group(1))
    return nomes


# --- orquestração -----------------------------------------------------------------------------

def verificar(
    metricas: list[dict],
    funil: list[dict] | None = None,
    funil_md: list[dict] | None = None,
    dicionario: set[str] | None = None,
    commits_dir: Path | None = None,
    janela_fim=None,
) -> list[dict]:
    funil = funil or []
    por_repo = {r[COL_REPO]: r for r in funil}
    resultado: list[dict] = [
        inv_faixa(metricas, COL_CFR_A, 0, 1, "0 ≤ CFR (a) ≤ 1"),
        inv_faixa(metricas, COL_CFR_B, 0, 1, "0 ≤ CFR (b) ≤ 1"),
        *(inv_faixa(metricas, c, 0, None, f"lead time ≥ 0 ({c})") for c in COLS_LEAD_TIME),
        inv_particao_lead_time(metricas, por_repo),
        inv_particao_cfr_b(metricas),
        inv_dicionario(metricas, dicionario),
        *inv_funil(funil, metricas, funil_md),
        *rel_duplicatas(metricas),
        *rel_nulos(metricas),
        *rel_censura_e_404(metricas),
        *rel_datas_cache(commits_dir, janela_fim),
        *rel_linguagem(metricas),
    ]
    if not metricas:
        resultado.insert(0, _linha("invariante", "dataset não vazio", "FALHA", 0, "CSV de métricas sem linhas"))
    return resultado


def escrever_csv(arquivo: Path, linhas: list[dict]) -> None:
    with Path(arquivo).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_SAIDA, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def escrever_md(arquivo: Path, linhas: list[dict], n_repos: int, origem: str) -> None:
    contagem = Counter(l["status"] for l in linhas if l["grupo"] == "invariante")
    partes = [
        "# Qualidade dos dados",
        "",
        f"Origem: `{origem}` · {n_repos} repositórios. Gerado por `python -m scripts.data_quality`.",
        "",
        f"Invariantes: **{contagem.get('OK', 0)} OK**, **{contagem.get('FALHA', 0)} FALHA**, "
        f"{contagem.get('N/A', 0)} não verificáveis (coluna ou arquivo ausente).",
    ]
    titulos = {
        "invariante": "Invariantes", "duplicatas": "Duplicatas", "nulos": "Valores vazios",
        "datas": "Datas", "censura": "Censura", "404": "Comparações com 404",
        "cobertura": "Cobertura e exclusões", "linguagem": "Distribuição por linguagem",
    }
    for grupo, titulo in titulos.items():
        itens = [l for l in linhas if l["grupo"] == grupo]
        if not itens:
            continue
        partes += ["", f"## {titulo}", "", "| Verificação | Status | Valor | Detalhe |", "|---|---|---:|---|"]
        partes += [
            f"| {l['verificacao']} | {l['status']} | {l['valor']} | {str(l['detalhe']).replace('|', '/')} |"
            for l in itens
        ]
    Path(arquivo).write_text("\n".join(partes) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m scripts.data_quality", description="Qualidade dos dados e invariantes.")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--metricas", help="CSV de métricas (padrão: <saidas>/resultados.csv)")
    p.add_argument("--funil", help="funil.csv (padrão: <saidas>/funil.csv); o funil.md é lido ao lado")
    p.add_argument("--dicionario", help="dicionário de dados (.csv ou .md); sem ele a invariante fica N/A")
    p.add_argument("--saida", help="diretório de saída (padrão: <saidas>)")
    args = p.parse_args(argv)
    try:
        config = load_config(args.config)
        saidas = Path(args.saida) if args.saida else config.saidas_dir
        metricas_csv = Path(args.metricas) if args.metricas else config.saidas_dir / "resultados.csv"
        funil_csv = Path(args.funil) if args.funil else config.saidas_dir / "funil.csv"
        metricas = ler_csv(metricas_csv)
        funil = ler_csv(funil_csv) if funil_csv.is_file() else []
        linhas = verificar(
            metricas, funil, ler_funil_md(funil_csv.with_suffix(".md")), ler_dicionario(
                Path(args.dicionario) if args.dicionario else None),
            Path(config.cache_dir) / "commits", config.janela_fim,
        )
        saidas.mkdir(parents=True, exist_ok=True)
        escrever_csv(saidas / "data_quality.csv", linhas)
        escrever_md(saidas / "data_quality.md", linhas, len(metricas), str(metricas_csv))
    except (ConfigError, OSError, ValueError, KeyError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1

    falhas = [l for l in linhas if l["status"] == "FALHA"]
    for l in falhas:
        print(f"FALHA [{l['grupo']}] {l['verificacao']}: {l['valor']} ({l['detalhe']})", file=sys.stderr)
    print(f"{len(linhas)} verificações; {len(falhas)} falha(s). Relatório em {saidas}/data_quality.md")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
