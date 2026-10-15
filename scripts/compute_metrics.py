"""Calcula variantes de métricas e gera data/metrics.csv (Issue #21).

Lê o dataset congelado (outputs/repos_final.csv), recupera dados brutos do cache
(releases, commits, tags) e adiciona:

  - CFR (b) com heurística v8 (colunas cfr_b, n_releases_*, heuristic_version);
  - DF para as variantes C2 (release+pré-release) e C3 (tag);
  - Classificações DORA por combinação C1–C3 da RQ07;

e grava em data/metrics.csv. Não faz chamadas HTTP: usa apenas o cache em disco.

Uso:
    python -m scripts.compute_metrics --config config.yaml
    python -m scripts.compute_metrics --repos outputs/repos_final.csv \
                                     --cache cache/ \
                                     --saida data/metrics.csv \
                                     --inicio 2025-10-02 --fim 2026-10-02
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

log = logging.getLogger("scripts.compute_metrics")

VERSAO_HEURISTICA = "v12"  # versão final congelada (exige `body` nas releases); --versao troca


class _ClienteSemHTTP:
    """Stub: levanta erro se `compute_metrics` tentar qualquer chamada real à API."""

    def get(self, path, params=None):
        raise RuntimeError(
            f"compute_metrics tentou chamada HTTP inesperada: {path} — dado ausente no cache?"
        )


def _janela(inicio: date, fim: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(inicio, time.min, tzinfo=timezone.utc),
        datetime.combine(fim, time.max.replace(microsecond=0), tzinfo=timezone.utc),
    )


def _dt(valor) -> datetime:
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor


def _f(valor) -> str:
    """Formata float/int/None para CSV."""
    if valor is None:
        return ""
    return str(valor)


def _categoria(funcao, valor) -> str:
    return funcao(valor) if valor is not None and valor != "" else ""


def _overall_c(notas: list[int]) -> str:
    """Categoria geral da combinação: mediana (floor) das notas definidas; vazio sem nenhuma."""
    from metricas.dora import classify_overall_parcial
    return classify_overall_parcial(notas) if notas else ""


def calcular_variantes(
    full_name: str,
    client,
    cache_dir: Path,
    janela: tuple[datetime, datetime],
    versao: str = VERSAO_HEURISTICA,
) -> dict:
    """Variantes de métricas para um repositório a partir do cache.

    `versao`: versão da heurística do CFR (b). Versões que leem as release notes (v9+) usam o `body`
    das releases coletadas; sem ele, `DadosAusentesError` (nunca cai em outra regra).
    """
    from pipeline.collect_commits import collect_commits
    from pipeline.collect_releases import collect_releases, pares_com_anterior
    from pipeline.collect_tags import collect_tags
    from metricas.cfr_entrega import resumo_cfr_entrega
    from metricas.dora import (
        classify_cfr, classify_df, classify_lt, classify_recovery, score, DF_UM_POR_MES,
    )

    inicio_d = janela[0].date()
    fim_d = janela[1].date()

    releases = collect_releases(client, full_name, cache_dir)
    pares = pares_com_anterior(releases, inicio_d, fim_d)
    commits_data = collect_commits(client, full_name, pares, cache_dir)
    tags = collect_tags(client, full_name, cache_dir)

    window_weeks = (janela[1] - janela[0]).total_seconds() / (7 * 86400)

    # CFR (b): repassa as release notes (`body`) quando a coleta as guardou (a v9+ depende delas)
    corpo = {r.get("tag_name"): r["body"] for r in releases if "body" in r}
    itens = [{**r, "body": corpo[r["tag_name"]]} if r.get("tag_name") in corpo else r for r in commits_data["releases"]]
    cfr_b_dict = resumo_cfr_entrega(itens, janela, versao)

    # C2: DF com release + pré-release (não-draft, com published_at, dentro da janela)
    n_c2 = sum(
        1 for r in releases
        if not r.get("draft") and r.get("published_at")
        and janela[0] <= _dt(r["published_at"]) <= janela[1]
    )
    df_c2 = n_c2 / window_weeks

    # C3: DF com tags (dentro da janela, com data)
    n_tags_janela = sum(
        1 for t in tags
        if t.get("author_date") and janela[0] <= _dt(t["author_date"]) <= janela[1]
    )
    df_c3 = n_tags_janela / window_weeks if tags is not None else None

    return {
        **cfr_b_dict,
        "janela_semanas": window_weeks,
        "n_compare_divergentes": commits_data.get("n_divergentes"),
        "n_compare_truncados": commits_data.get("n_truncadas"),
        "n_releases_deploy_c2": n_c2,
        "df_c2": df_c2,
        "df_c2_class": classify_df(df_c2, window_weeks),
        "n_tags_janela": n_tags_janela,
        "df_c3": df_c3,
        "df_c3_class": classify_df(df_c3, window_weeks) if df_c3 is not None else "",
    }


def _num_s(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def adicionar_classificacoes(linha_base: dict, variantes: dict) -> dict:
    """Computa classificações DORA para C1, C2 e C3 a partir das métricas base e variantes."""
    from metricas.dora import classify_cfr, classify_df, classify_lt, classify_recovery, score

    semanas = _num_s(variantes.get("janela_semanas"))

    def _num(v):
        try:
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    # Métricas base (C1 já calculado pelo pipeline)
    lt_a = _num(linha_base.get("lt_release_median_h"))
    lt_b = _num(linha_base.get("lt_commit_median_h"))
    cfr_a = _num(linha_base.get("cfr_a"))
    cfr_b = _num(variantes.get("cfr_b"))
    rec = _num(linha_base.get("rec_median_h"))
    df_ref = _num(linha_base.get("deployment_frequency"))
    df_c2 = _num(variantes.get("df_c2"))
    df_c3 = _num(variantes.get("df_c3"))

    def _score(fn, val):
        return score(fn(val)) if val is not None else None

    def _score_df(val):
        return score(classify_df(val, semanas)) if val is not None else None

    # C1: release | LT(a) | CFR(a) (reference — matches existing dora_geral)
    c1_notas = [
        _score_df(df_ref),
        _score(classify_lt, lt_a),
        _score(classify_cfr, cfr_a),
        _score(classify_recovery, rec),
    ]
    n_c1 = [n for n in c1_notas if n is not None]
    dora_c1 = _overall_c(n_c1)

    # C2: release+pré-release | LT(b) | CFR(b)
    c2_notas = [
        _score_df(df_c2),
        _score(classify_lt, lt_b),
        _score(classify_cfr, cfr_b),
        _score(classify_recovery, rec),
    ]
    n_c2 = [n for n in c2_notas if n is not None]
    dora_c2 = _overall_c(n_c2)

    # C3: tag | LT(b) | CFR(a)
    c3_notas = [
        _score_df(df_c3),
        _score(classify_lt, lt_b),
        _score(classify_cfr, cfr_a),
        _score(classify_recovery, rec),
    ]
    n_c3 = [n for n in c3_notas if n is not None]
    dora_c3 = _overall_c(n_c3)

    return {
        "cfr_b_class": _categoria(classify_cfr, cfr_b) if cfr_b is not None else "",
        "dora_c1": dora_c1,
        "dora_c2": dora_c2,
        "dora_c3": dora_c3,
        "n_metricas_dora_c1": len(n_c1),
        "n_metricas_dora_c2": len(n_c2),
        "n_metricas_dora_c3": len(n_c3),
    }


COLUNAS_EXTRAS = [
    "cfr_b",
    "cfr_b_class",
    "n_releases_avaliadas_cfr_b",
    "n_releases_censuradas_cfr_b",
    "n_releases_janela",
    "n_releases_falha_cfr_b",
    "n_releases_mensagens_incompletas_cfr_b",
    "heuristic_version",
    "n_releases_deploy_c2",
    "df_c2",
    "df_c2_class",
    "n_tags_janela",
    "df_c3",
    "df_c3_class",
    "n_compare_divergentes",
    "n_compare_truncados",
    "dora_c1",
    "dora_c2",
    "dora_c3",
    "n_metricas_dora_c1",
    "n_metricas_dora_c2",
    "n_metricas_dora_c3",
]


def compute(
    repos_csv: Path,
    cache_dir: Path,
    saida: Path,
    janela: tuple[datetime, datetime],
    versao: str = VERSAO_HEURISTICA,
) -> dict:
    """Lê repos_final.csv, calcula variantes e grava metrics.csv. Devolve contadores."""
    from pipeline.cache import CachedHttpClient

    client = CachedHttpClient(_ClienteSemHTTP(), cache_dir)

    linhas = list(csv.DictReader(repos_csv.open(encoding="utf-8")))
    fieldnames = list(linhas[0].keys()) + COLUNAS_EXTRAS if linhas else COLUNAS_EXTRAS

    saida.parent.mkdir(parents=True, exist_ok=True)
    ok = erros = 0
    with saida.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for i, linha in enumerate(linhas, 1):
            nome = linha["full_name"]
            try:
                variantes = calcular_variantes(nome, client, cache_dir, janela, versao)
                classificacoes = adicionar_classificacoes(linha, variantes)
                extra = {**variantes, **classificacoes}
                row = {**linha, **{k: _f(extra.get(k)) for k in COLUNAS_EXTRAS}}
                writer.writerow(row)
                ok += 1
                if i % 50 == 0:
                    log.info("[%d/%d] %s", i, len(linhas), nome)
            except Exception as exc:
                log.error("[%d/%d] %s: ERRO — %s", i, len(linhas), nome, exc)
                row = {**linha, **{k: "" for k in COLUNAS_EXTRAS}}
                writer.writerow(row)
                erros += 1
    log.info("metrics.csv: %d OK, %d erros → %s", ok, erros, saida)
    return {"n_ok": ok, "n_erros": erros, "n_total": len(linhas)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--repos", default=None, help="caminho de repos_final.csv")
    parser.add_argument("--cache", default=None, help="diretório de cache")
    parser.add_argument("--saida", default=None, help="caminho de saída (data/metrics.csv)")
    parser.add_argument("--inicio", default=None, help="início da janela YYYY-MM-DD")
    parser.add_argument("--fim", default=None, help="fim da janela YYYY-MM-DD")
    parser.add_argument("--versao", default=VERSAO_HEURISTICA, help="versão da heurística do CFR (b)")
    args = parser.parse_args(argv)

    if args.repos and args.cache and args.saida and args.inicio and args.fim:
        repos_csv = Path(args.repos)
        cache_dir = Path(args.cache)
        saida = Path(args.saida)
        inicio = date.fromisoformat(args.inicio)
        fim_d = date.fromisoformat(args.fim)
    else:
        from pipeline.config import load_config
        cfg = load_config(args.config)
        repos_csv = Path(args.repos) if args.repos else cfg.saidas_dir / "repos_final.csv"
        cache_dir = Path(args.cache) if args.cache else Path(cfg.cache_dir)
        saida = Path(args.saida) if args.saida else Path("data/metrics.csv")
        inicio = cfg.janela_inicio
        fim_d = cfg.janela_fim

    if not repos_csv.is_file():
        print(f"ERRO: arquivo não encontrado: {repos_csv}", file=sys.stderr)
        sys.exit(1)

    janela = _janela(inicio, fim_d)
    resultado = compute(repos_csv, cache_dir, saida, janela, args.versao)
    print(f"metrics.csv gravado: {resultado['n_ok']}/{resultado['n_total']} OK"
          + (f", {resultado['n_erros']} ERRO(S)" if resultado["n_erros"] else ""))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
