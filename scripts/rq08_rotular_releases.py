"""RQ08 (Issue #39): rótulo corretiva/CFR (b) de cada release de deploy da janela, a partir do cache.

Etapa de extração do rework rate. `data/metrics.csv` traz só os agregados do CFR (b), não o nº de
releases corretivas, então os rótulos por release vêm do cache da coleta (`releases/` com `body` e
`commits/`), com a mesma montagem de `scripts.compute_metrics.calcular_variantes` e a heurística
oficial (v12). Não faz chamadas HTTP (stub `_ClienteSemHTTP`): repositório sem dado no cache vira erro
registrado em `rq08_extracao_erros.csv`.

Para cada repositório, os agregados dos rótulos (janela, avaliadas, censuradas, falhas, CFR (b),
mensagens incompletas) são conferidos com `metricas.cfr_entrega.resumo_cfr_entrega` sobre os mesmos
itens; divergência é erro do repositório, nunca silenciosa.

    python -m scripts.rq08_rotular_releases --cache cache [--repos data/metrics.csv] [--saida data/rq08]

Saídas em `--saida`: `rq08_releases.csv` (uma linha por release de deploy da janela),
`rq08_extracao_erros.csv` e `rq08_extracao.json` (manifesto). A análise, só com CSV, está em
`analysis.rq08_rework_rate`.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
from bisect import bisect_left, bisect_right
from datetime import date, datetime, timezone
from pathlib import Path

log = logging.getLogger("scripts.rq08_rotular_releases")

VERSAO = "v12"  # mesma versão do CFR (b) de data/metrics.csv (`heuristic_version`)
COLUNAS = [
    "full_name", "tag_name", "published_at", "published_at_anterior", "status", "status_compare",
    "truncado", "mensagens_incompletas", "corretiva", "avaliada_cfr_b", "falhou_cfr_b",
    "categoria_corretiva", "heuristic_version",
]
CATEGORIAS = ["com_antecedente", "antecedente_censurado", "antecedente_fora_janela", "sem_anterior_7d"]


def rotular(
    itens: list[dict], anteriores: dict, janela: tuple[datetime, datetime], datas_deploy: list | None = None,
) -> list[dict]:
    """Rótulos por release a partir dos itens já classificados pela heurística.

    `itens`: saída de `classificar_releases` (com `published_at`, `heuristic_corrective`, `status`...),
    só releases de deploy da janela. `anteriores`: `tag_name` → `published_at` da release de deploy
    anterior (pode estar fora da janela; `None` se não houver). `datas_deploy`: `published_at` de todas
    as releases de deploy do repositório, inclusive as de antes da janela (padrão: janela + anteriores).

    Regras do CFR (b) (`metricas.cfr_entrega.cfr_entrega`): R é avaliada se R + 7 d ≤ fim; R falhou
    se existe S corretiva da janela com R < S ≤ R + 7 d. Categoria de cada S corretiva (exclusivas):
    `com_antecedente` (há R avaliada da janela em [S − 7 d, S)), `antecedente_censurado` (há R da
    janela nesse intervalo, nenhuma avaliada), `antecedente_fora_janela` (a anterior é de antes da
    janela e está a até 7 d) ou `sem_anterior_7d` (resíduo: nenhuma release de deploy em [S − 7 d, S),
    inclusive sem anterior ou com a anterior empatada no horário com S). Sempre R < S estrito, como no
    CFR (b); "anterior" da categoria 3 = última release de deploy com data estritamente menor que S.
    """
    from metricas.cfr_entrega import PRAZO_CORRECAO
    from metricas.dora import _dt

    inicio, fim = _dt(janela[0]), _dt(janela[1])
    linhas = sorted(
        (r for r in itens if r.get("published_at") and inicio <= _dt(r["published_at"]) <= fim),
        key=lambda r: _dt(r["published_at"]),
    )
    datas = [_dt(r["published_at"]) for r in linhas]
    corretivas = [d for d, r in zip(datas, linhas) if r.get("heuristic_corrective")]
    todas = datas_deploy if datas_deploy is not None else [*datas, *(a for a in anteriores.values() if a)]
    todas = sorted({_dt(x) for x in todas})
    saida = []
    for d, r in zip(datas, linhas):
        corretiva = bool(r.get("heuristic_corrective"))
        avaliada = d + PRAZO_CORRECAO <= fim
        falhou = False
        if avaliada:
            i = bisect_right(corretivas, d)
            falhou = i < len(corretivas) and corretivas[i] <= d + PRAZO_CORRECAO
        anterior = anteriores.get(r.get("tag_name"))
        categoria = ""
        if corretiva:
            janela_s = (d - PRAZO_CORRECAO, d)
            na_faixa = datas[bisect_left(datas, janela_s[0]):bisect_left(datas, d)]
            if any(x + PRAZO_CORRECAO <= fim for x in na_faixa):
                categoria = "com_antecedente"
            elif na_faixa:
                categoria = "antecedente_censurado"
            elif (j := bisect_left(todas, d)) > 0 and janela_s[0] <= todas[j - 1] < inicio:
                categoria = "antecedente_fora_janela"
            else:
                categoria = "sem_anterior_7d"
        saida.append({
            "tag_name": r.get("tag_name"),
            "published_at": r.get("published_at"),
            "published_at_anterior": anterior or "",
            "status": r.get("status"),
            "status_compare": r.get("status_compare") or "",
            "truncado": bool(r.get("truncado")),
            "mensagens_incompletas": bool(r.get("mensagens_incompletas")),
            "corretiva": corretiva,
            "avaliada_cfr_b": avaliada,
            "falhou_cfr_b": bool(falhou),
            "categoria_corretiva": categoria,
            "heuristic_version": r.get("heuristic_version"),
        })
    return saida


def agregados(linhas: list[dict]) -> dict:
    """Contadores do CFR (b) a partir dos rótulos (mesmas chaves de `resumo_cfr_entrega`)."""
    n = len(linhas)
    av = sum(1 for l in linhas if l["avaliada_cfr_b"])
    falhas = sum(1 for l in linhas if l["falhou_cfr_b"])
    return {
        "n_releases_janela": n,
        "n_releases_avaliadas_cfr_b": av,
        "n_releases_censuradas_cfr_b": n - av,
        "n_releases_falha_cfr_b": falhas,
        "cfr_b": falhas / av if n >= 2 and av > 0 else None,
        "n_releases_mensagens_incompletas_cfr_b": sum(1 for l in linhas if l["mensagens_incompletas"]),
    }


def conferir_com_resumo(linhas: list[dict], resumo: dict) -> list[str]:
    """Campos em que os agregados dos rótulos diferem de `resumo_cfr_entrega` (esperado: nenhum)."""
    ag = agregados(linhas)
    dif = []
    for k, v in ag.items():
        ref = resumo.get(k)
        if v is None or ref is None:
            if (v is None) != (ref is None):
                dif.append(k)
        elif not math.isclose(float(v), float(ref), rel_tol=0, abs_tol=1e-12):
            dif.append(k)
    return dif


def rotular_repositorio(full_name: str, client, cache_dir: Path, janela: tuple, versao: str = VERSAO) -> list[dict]:
    """Lê o cache, aplica a heurística e devolve os rótulos (levanta erro se a conferência falhar)."""
    from metricas.cfr_entrega import resumo_cfr_entrega
    from metricas.heuristica import classificar_releases
    from pipeline.collect_commits import collect_commits
    from pipeline.collect_releases import collect_releases, pares_com_anterior

    releases = collect_releases(client, full_name, cache_dir)
    pares = pares_com_anterior(releases, janela[0].date(), janela[1].date())
    commits_data = collect_commits(client, full_name, pares, cache_dir)
    # mesma montagem de scripts.compute_metrics.calcular_variantes (release notes via `body`)
    corpo = {r.get("tag_name"): r["body"] for r in releases if "body" in r}
    itens = [{**r, "body": corpo[r["tag_name"]]} if r.get("tag_name") in corpo else r
             for r in commits_data["releases"]]
    classificadas = classificar_releases(itens, versao)
    extras = {r["tag_name"]: r for r in commits_data["releases"]}
    for c in classificadas:
        e = extras.get(c["tag_name"], {})
        c["status_compare"] = e.get("status_compare")
        c["truncado"] = e.get("truncado")
    anteriores = {r["tag_name"]: (a["published_at"] if a is not None else None) for a, r in pares}
    from pipeline.collect_releases import e_deploy

    datas_deploy = [r["published_at"] for r in releases if e_deploy(r)]
    linhas = rotular(classificadas, anteriores, janela, datas_deploy)
    dif = conferir_com_resumo(linhas, resumo_cfr_entrega(itens, janela, versao))
    if dif:
        raise AssertionError(f"rótulos divergem de resumo_cfr_entrega em {dif}")
    return [{"full_name": full_name, **l} for l in linhas]


def _coletado_em(cache_dir: Path, nomes: list[str]) -> list[str]:
    from pipeline.collect_releases import arquivo_cache

    datas = []
    for n in nomes:
        arq = arquivo_cache(cache_dir, n)
        if arq.exists():
            c = json.loads(arq.read_text(encoding="utf-8")).get("coletado_em")
            if c:
                datas.append(c)
    return sorted(datas)


def extrair(repos_csv: Path, cache_dir: Path, saida: Path, janela: tuple, versao: str = VERSAO) -> dict:
    from pipeline.cache import CachedHttpClient
    from scripts.compute_metrics import _ClienteSemHTTP

    client = CachedHttpClient(_ClienteSemHTTP(), cache_dir)
    nomes = [l["full_name"] for l in csv.DictReader(repos_csv.open(encoding="utf-8"))]
    linhas, erros = [], []
    for i, nome in enumerate(nomes, 1):
        try:
            linhas.extend(rotular_repositorio(nome, client, cache_dir, janela, versao))
        except Exception as exc:  # noqa: BLE001 - registra e segue; a análise trata como NaN
            log.error("[%d/%d] %s: %s", i, len(nomes), nome, exc)
            erros.append({"full_name": nome, "erro": f"{type(exc).__name__}: {exc}"})
    saida.mkdir(parents=True, exist_ok=True)
    with (saida / "rq08_releases.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)
    with (saida / "rq08_extracao_erros.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["full_name", "erro"])
        w.writeheader()
        w.writerows(erros)
    coletas = _coletado_em(cache_dir, nomes)
    manifesto = {
        "extraido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "heuristic_version": versao,
        "janela_inicio": janela[0].isoformat(),
        "janela_fim": janela[1].isoformat(),
        "repos_entrada": len(nomes),
        "repos_ok": len(nomes) - len(erros),
        "repos_erro": len(erros),
        "releases_rotuladas": len(linhas),
        "cache_coletado_em_min": coletas[0] if coletas else None,
        "cache_coletado_em_max": coletas[-1] if coletas else None,
    }
    (saida / "rq08_extracao.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
    return manifesto


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config.yaml", help="janela (usada se --inicio/--fim faltarem)")
    ap.add_argument("--repos", type=Path, default=Path("data/metrics.csv"), help="CSV com coluna full_name")
    ap.add_argument("--cache", type=Path, default=Path("cache"))
    ap.add_argument("--saida", type=Path, default=Path("data/rq08"))
    ap.add_argument("--inicio", default=None, help="início da janela YYYY-MM-DD")
    ap.add_argument("--fim", default=None, help="fim da janela YYYY-MM-DD")
    a = ap.parse_args(argv)
    from scripts.compute_metrics import _janela

    if a.inicio and a.fim:
        inicio, fim = date.fromisoformat(a.inicio), date.fromisoformat(a.fim)
    else:
        from pipeline.config import load_config
        cfg = load_config(a.config)
        inicio, fim = cfg.janela_inicio, cfg.janela_fim
    m = extrair(a.repos, a.cache, a.saida, _janela(inicio, fim))
    print(json.dumps(m, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    main()
