"""Testes da RQ08 — rework rate (Issue #39): rótulos por release, conferência, estatísticas e saídas."""
import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from analysis import rq08_rework_rate as rq08
from metricas.cfr_entrega import cfr_entrega
from scripts import rq08_rotular_releases as rot

UTC = timezone.utc
JANELA = (datetime(2025, 10, 2, tzinfo=UTC), datetime(2026, 10, 2, 23, 59, 59, tzinfo=UTC))
RAIZ = Path(__file__).resolve().parent.parent


def _iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def _item(tag, quando, corretiva=False, **kw):
    return {"tag_name": tag, "published_at": _iso(quando), "heuristic_corrective": corretiva,
            "status": "ok", "status_compare": "ahead", "truncado": False, "mensagens_incompletas": False,
            "heuristic_version": "v12", **kw}


def _rotular(itens, anteriores=None, datas_deploy=None):
    anteriores = anteriores or {}
    return rot.rotular(itens, anteriores, JANELA, datas_deploy)


def _por_tag(linhas):
    return {l["tag_name"]: l for l in linhas}


# --- rótulos por release -----------------------------------------------------------------------------

def test_rajada_cfr_b_maior_que_rework():
    d = datetime(2026, 1, 1, tzinfo=UTC)
    itens = [_item("r1", d), _item("r2", d + timedelta(days=1)), _item("r3", d + timedelta(days=2)),
             _item("s", d + timedelta(days=4), corretiva=True)]
    linhas = _rotular(itens)
    ag = rot.agregados(linhas)
    assert ag["n_releases_falha_cfr_b"] == 3 and ag["cfr_b"] == pytest.approx(3 / 4)
    assert sum(l["corretiva"] for l in linhas) / len(linhas) == pytest.approx(1 / 4)
    assert _por_tag(linhas)["s"]["categoria_corretiva"] == "com_antecedente"


def test_corretiva_isolada_conta_so_no_rework():
    d = datetime(2026, 1, 1, tzinfo=UTC)
    linhas = _rotular([_item("r1", d), _item("s", d + timedelta(days=31), corretiva=True)])
    assert rot.agregados(linhas)["cfr_b"] == 0
    assert _por_tag(linhas)["s"]["categoria_corretiva"] == "sem_anterior_7d"


def test_corretiva_nos_ultimos_7_dias_entra_no_rework_e_e_censurada_no_cfr_b():
    itens = [_item("r0", datetime(2026, 1, 1, tzinfo=UTC)),
             _item("r1", datetime(2026, 9, 30, tzinfo=UTC)),
             _item("s", datetime(2026, 10, 1, tzinfo=UTC), corretiva=True)]
    linhas = _rotular(itens)
    ag = rot.agregados(linhas)
    assert ag["n_releases_janela"] == 3 and ag["n_releases_avaliadas_cfr_b"] == 1
    assert ag["n_releases_censuradas_cfr_b"] == 2 and ag["n_releases_falha_cfr_b"] == 0
    assert _por_tag(linhas)["s"]["categoria_corretiva"] == "antecedente_censurado"


def test_antecedente_antes_da_janela():
    anterior = datetime(2025, 9, 30, tzinfo=UTC)
    s = datetime(2025, 10, 3, tzinfo=UTC)
    linhas = _rotular([_item("s", s, corretiva=True)], {"s": _iso(anterior)}, [_iso(anterior), _iso(s)])
    assert linhas[0]["categoria_corretiva"] == "antecedente_fora_janela"
    assert linhas[0]["published_at_anterior"] == _iso(anterior)


def test_empate_de_horario_cai_no_residuo_e_soma_fecha():
    d = datetime(2026, 3, 1, tzinfo=UTC)
    itens = [_item("p", d), _item("s", d, corretiva=True)]  # mesmo published_at (publicação em lote)
    linhas = _rotular(itens, {"s": _iso(d), "p": None})
    assert _por_tag(linhas)["s"]["categoria_corretiva"] == "sem_anterior_7d"
    assert _por_tag(linhas)["p"]["falhou_cfr_b"] is False  # R < S estrito, como no CFR (b)
    assert sum(1 for l in linhas if l["categoria_corretiva"]) == sum(l["corretiva"] for l in linhas)


def test_empate_com_anterior_fora_da_janela_usa_a_ultima_estritamente_anterior():
    q = datetime(2025, 9, 30, tzinfo=UTC)
    d = datetime(2025, 10, 3, tzinfo=UTC)
    itens = [_item("p", d), _item("s", d, corretiva=True)]
    linhas = _rotular(itens, {"p": _iso(q), "s": _iso(d)}, [_iso(q), _iso(d), _iso(d)])
    assert _por_tag(linhas)["s"]["categoria_corretiva"] == "antecedente_fora_janela"


def test_rotulos_equivalem_ao_cfr_entrega_e_categorias_somam():
    rng = random.Random(39)
    for _ in range(200):
        n = rng.randint(1, 25)
        datas = sorted(JANELA[0] + timedelta(hours=rng.randint(0, 366 * 24)) for _ in range(n))
        itens = [_item(f"t{i}", d, corretiva=rng.random() < 0.4) for i, d in enumerate(datas)]
        linhas = _rotular(itens)
        ref = cfr_entrega(itens, JANELA)
        assert rot.conferir_com_resumo(linhas, {**ref, "n_releases_mensagens_incompletas_cfr_b": 0}) == []
        cats = [l["categoria_corretiva"] for l in linhas if l["corretiva"]]
        assert all(c in rot.CATEGORIAS for c in cats)
        assert len(cats) == sum(l["corretiva"] for l in linhas)


def test_conferir_com_resumo_aponta_campo_divergente():
    d = datetime(2026, 1, 1, tzinfo=UTC)
    linhas = _rotular([_item("a", d), _item("b", d + timedelta(days=1), corretiva=True)])
    ref = {**rot.agregados(linhas), "n_releases_falha_cfr_b": 0}
    assert rot.conferir_com_resumo(linhas, ref) == ["n_releases_falha_cfr_b"]


# --- extração a partir de um cache sintético (sem HTTP) ----------------------------------------------

def _cache_sintetico(cache: Path) -> None:
    rels = [
        {"id": 1, "tag_name": "v1.0.0", "draft": False, "prerelease": False, "published_at": "2025-09-01T00:00:00Z",
         "created_at": "2025-09-01T00:00:00Z", "body": "Initial release"},
        {"id": 2, "tag_name": "v1.1.0", "draft": False, "prerelease": False, "published_at": "2025-11-01T00:00:00Z",
         "created_at": "2025-11-01T00:00:00Z", "body": "New features: added support for X"},
        {"id": 3, "tag_name": "v1.1.1", "draft": False, "prerelease": False, "published_at": "2025-11-03T00:00:00Z",
         "created_at": "2025-11-03T00:00:00Z", "body": "Bug fixes"},
        {"id": 4, "tag_name": "v1.2.0-rc1", "draft": False, "prerelease": True, "published_at": "2025-11-04T00:00:00Z",
         "created_at": "2025-11-04T00:00:00Z", "body": "rc"},
    ]
    (cache / "releases").mkdir(parents=True)
    (cache / "commits").mkdir(parents=True)
    (cache / "releases" / "o__r.json").write_text(json.dumps({"full_name": "o/r", "coletado_em": "2026-10-08T00:00:00+00:00",
                                                              "releases": rels}), encoding="utf-8")

    def cmp(base, head, msgs):
        return {"base": base, "head": head, "status": "ok", "status_compare": "ahead", "total_commits": len(msgs),
                "truncado": False, "commits": [{"sha": str(i), "message": m} for i, m in enumerate(msgs)]}

    (cache / "commits" / "o__r.json").write_text(json.dumps({"full_name": "o/r", "comparacoes": {
        "v1.0.0...v1.1.0": cmp("v1.0.0", "v1.1.0", ["feat: add X", "fix: typo"]),
        "v1.1.0...v1.1.1": cmp("v1.1.0", "v1.1.1", ["fix: crash ao abrir arquivo"]),
    }}), encoding="utf-8")
    # repositório cuja primeira release da história está na janela (sem anterior: nunca corretiva)
    (cache / "releases" / "o__novo.json").write_text(json.dumps({"full_name": "o/novo", "releases": [
        {"id": 9, "tag_name": "0.1.0", "draft": False, "prerelease": False, "published_at": "2026-01-01T00:00:00Z",
         "created_at": "2026-01-01T00:00:00Z", "body": "fix everything"}]}), encoding="utf-8")


def test_extrair_do_cache_sem_http(tmp_path):
    cache, saida = tmp_path / "cache", tmp_path / "saida"
    _cache_sintetico(cache)
    repos = tmp_path / "repos.csv"
    repos.write_text("full_name\no/r\no/novo\no/ausente\n", encoding="utf-8")
    m = rot.extrair(repos, cache, saida, JANELA)
    assert (m["repos_ok"], m["repos_erro"], m["releases_rotuladas"]) == (2, 1, 3)
    assert m["heuristic_version"] == "v12" and m["cache_coletado_em_min"] == "2026-10-08T00:00:00+00:00"
    linhas = {(l["full_name"], l["tag_name"]): l for l in csv.DictReader((saida / "rq08_releases.csv").open(encoding="utf-8"))}
    assert linhas[("o/r", "v1.1.1")]["corretiva"] == "True"
    assert linhas[("o/r", "v1.1.0")]["corretiva"] == "False" and linhas[("o/r", "v1.1.0")]["falhou_cfr_b"] == "True"
    assert linhas[("o/novo", "0.1.0")]["status"] == "sem_anterior" and linhas[("o/novo", "0.1.0")]["corretiva"] == "False"
    assert ("o/r", "v1.2.0-rc1") not in linhas  # pré-release não é deploy (C1)
    erros = list(csv.DictReader((saida / "rq08_extracao_erros.csv").open(encoding="utf-8")))
    assert [e["full_name"] for e in erros] == ["o/ausente"] and "HTTP" in erros[0]["erro"]
    assert json.loads((saida / "rq08_extracao.json").read_text(encoding="utf-8"))["repos_ok"] == 2


# --- agregação, conferência e estatísticas ------------------------------------------------------------

def _rel(nome, tag, dia, corretiva=False, avaliada=True, falhou=False, categoria=""):
    return {"full_name": nome, "tag_name": tag, "published_at": f"2026-01-{dia:02d}T00:00:00Z",
            "published_at_anterior": "", "status": "ok", "status_compare": "ahead", "truncado": False,
            "mensagens_incompletas": False, "corretiva": corretiva, "avaliada_cfr_b": avaliada,
            "falhou_cfr_b": falhou, "categoria_corretiva": categoria, "heuristic_version": "v12"}


def _metricas(**linhas):
    base = {"n_releases_censuradas_cfr_b": 0, "n_releases_mensagens_incompletas_cfr_b": 0,
            "n_compare_divergentes": 0, "n_compare_truncados": 0, "deployment_frequency": 1.0}
    return pd.DataFrame([{"full_name": k, **base, **v} for k, v in linhas.items()])


@pytest.fixture
def dados():
    rel = pd.DataFrame([
        _rel("a/a", "1", 1, falhou=True), _rel("a/a", "2", 2, corretiva=True, categoria="com_antecedente"),
        _rel("b/b", "1", 1), _rel("b/b", "2", 20, corretiva=True, categoria="sem_anterior_7d"),
        _rel("c/c", "1", 1, avaliada=False), _rel("c/c", "2", 1, avaliada=False),  # tudo censurado
        _rel("d/d", "1", 1), _rel("d/d", "2", 5),
    ])
    met = _metricas(**{
        "a/a": {"n_releases_janela": 2, "n_releases_avaliadas_cfr_b": 2, "n_releases_falha_cfr_b": 1, "cfr_b": 0.5},
        "b/b": {"n_releases_janela": 2, "n_releases_avaliadas_cfr_b": 2, "n_releases_falha_cfr_b": 0, "cfr_b": 0.0},
        "c/c": {"n_releases_janela": 2, "n_releases_avaliadas_cfr_b": 0, "n_releases_falha_cfr_b": 0,
                "cfr_b": float("nan"), "n_releases_censuradas_cfr_b": 2},
        "d/d": {"n_releases_janela": 2, "n_releases_avaliadas_cfr_b": 2, "n_releases_falha_cfr_b": 1, "cfr_b": 0.5},
        "z/akto": {"n_releases_janela": float("nan"), "n_releases_avaliadas_cfr_b": float("nan"),
                   "n_releases_falha_cfr_b": float("nan"), "cfr_b": float("nan")},
    })
    return met, rel


def test_montar_confere_e_trata_nan(dados):
    t = rq08.montar(*dados).set_index("full_name")
    assert t.loc["a/a", "rework_rate"] == 0.5 and bool(t.loc["a/a", "confere_metrics"])
    assert t.loc["b/b", "diferenca_rework_cfr_b"] == 0.5
    # NaN == NaN (CFR (b) indefinido dos dois lados): confere e o rework existe, fora do pareado
    assert bool(t.loc["c/c", "confere_metrics"]) and t.loc["c/c", "rework_rate"] == 0
    assert math.isnan(t.loc["c/c", "rework_rate_avaliaveis"]) and pd.isna(t.loc["c/c", "diferenca_rework_cfr_b"])
    # d/d diverge (falhas 0 recontadas × 1 no CSV): sai da RQ08
    assert not t.loc["d/d", "confere_metrics"] and "n_releases_falha_cfr_b" in t.loc["d/d", "campos_divergentes"]
    assert pd.isna(t.loc["d/d", "rework_rate"]) and t.loc["d/d", "motivo_exclusao"] == "diverge do metrics.csv"
    assert t.loc["z/akto", "motivo_exclusao"] == "sem referência no metrics.csv" and pd.isna(t.loc["z/akto", "rework_rate"])
    soma = sum(t.loc["b/b", f"n_corretivas_{c}"] for c in rq08.CATEGORIAS)
    assert soma == t.loc["b/b", "n_releases_corretivas"]


def test_repositorio_sem_rotulos_e_excluido(dados):
    met, rel = dados
    t = rq08.montar(met, rel[rel["full_name"] != "a/a"]).set_index("full_name")
    assert t.loc["a/a", "motivo_exclusao"].startswith("sem rótulos") and pd.isna(t.loc["a/a", "rework_rate"])


def test_limite_de_divergencia(dados):
    t = rq08.montar(*dados)
    with pytest.raises(rq08.DivergenciaExcessiva):  # 1 de 4 (akto fora da base) = 25%
        rq08.checar_divergencia(t)
    assert rq08.checar_divergencia(t, limite=0.30) == {"base": 4, "divergentes": 1, "fracao": 0.25}


def test_ruido_de_ponto_flutuante_nao_vira_diferenca():
    rel = pd.DataFrame([_rel("a/a", str(i), i + 1, corretiva=(i == 10), categoria="com_antecedente" if i == 10 else "")
                        for i in range(11)])
    rel.loc[9, "falhou_cfr_b"] = True
    met = _metricas(**{"a/a": {"n_releases_janela": 11, "n_releases_avaliadas_cfr_b": 11,
                               "n_releases_falha_cfr_b": 1, "cfr_b": 1 / 11}})
    assert rq08.montar(met, rel)["diferenca_rework_cfr_b"].iloc[0] == 0


def test_rank_biserial_pareado():
    assert rq08.rank_biserial_pareado(pd.Series([0.1, 0.2, 0.3])) == 1
    assert rq08.rank_biserial_pareado(pd.Series([-0.1, -0.2, 0.0])) == -1  # zero descartado
    assert rq08.rank_biserial_pareado(pd.Series([-0.1, 0.2])) == pytest.approx((2 - 1) / 3)
    assert math.isnan(rq08.rank_biserial_pareado(pd.Series([0.0, None])))


def test_calibracao_razao_e_bootstrap_reprodutivel(tmp_path):
    p = tmp_path / "pred.csv"
    linhas = ["release_id,full_name,tag_name,consenso,pred_v12"]
    for r in range(10):
        for i in range(5):
            linhas.append(f"{r}{i},r{r},t{i},{'sim' if i < 2 else 'nao'},{'sim' if i < 1 + (r % 2) else 'nao'}")
    p.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    a, b = rq08.calibracao(p, b=500), rq08.calibracao(p, b=500)
    assert a == b
    assert a["prev_consenso"] == pytest.approx(0.4) and a["prev_v12"] == pytest.approx(0.3)
    assert a["razao"] == pytest.approx(0.75) and a["razao_ic95_inf"] <= 0.75 <= a["razao_ic95_sup"]
    assert math.isnan(rq08.calibracao(tmp_path / "nao_existe.csv")["razao"])


def test_calibracao_com_os_dados_da_validacao_independente():
    c = rq08.calibracao(rq08.PREDICOES_PADRAO, b=200)
    assert (c["n_releases"], c["n_repos"]) == (200, 40)
    assert c["razao"] == pytest.approx(70 / 78)  # = recall ÷ precisão da v12 (0,654 ÷ 0,729)


def test_executar_gera_saidas_documentadas(tmp_path, dados):
    met, rel = dados
    met = met[met["full_name"] != "d/d"]  # sem divergência
    csv_m, csv_r = tmp_path / "metrics.csv", tmp_path / "rq08_releases.csv"
    met.to_csv(csv_m, index=False)
    rel.to_csv(csv_r, index=False)
    saida = tmp_path / "saida"
    r = rq08.executar(csv_m, csv_r, saida, predicoes=None)
    for nome in ["rq08_rework_rate.csv", "rq08_descritiva.csv", "rq08_comparacao.csv", "rq08_rework_rate.png",
                 "rq08_rework_vs_cfr_b.png", "rq08_rework_rate.md"]:
        assert (saida / nome).exists(), nome
    assert r["comparacao"]["n_pareado"] == 2 and r["comparacao"]["repos_divergentes"] == 0
    assert "Em que o rework rate difere do CFR (b)" in (saida / "rq08_rework_rate.md").read_text(encoding="utf-8")

    documentadas: dict[str, set] = {}
    with (RAIZ / "DICIONARIO_DE_DADOS.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            documentadas.setdefault(row["arquivo"].strip(), set()).add(row["coluna"].strip())
    arquivos = {"rq08_rework_rate.csv": saida, "rq08_descritiva.csv": saida, "rq08_comparacao.csv": saida,
                "rq08_releases.csv": tmp_path}
    for nome, pasta in arquivos.items():
        colunas = pd.read_csv(pasta / nome, nrows=0).columns
        faltam = [c for c in colunas if c not in documentadas.get(nome, set())]
        assert not faltam, f"{nome}: colunas sem entrada no dicionário: {faltam}"
    indicadores = pd.read_csv(saida / "rq08_comparacao.csv")["indicador"]
    assert not [i for i in indicadores if i not in rq08.descricao_indicadores()], "indicador sem descrição"


@pytest.mark.parametrize("nome", ["rq08_releases.csv", "rq08_rework_rate.csv", "rq08_descritiva.csv",
                                  "rq08_comparacao.csv", "rq08_extracao_erros.csv"])
def test_saidas_versionadas_documentadas(nome):
    pasta = "data/rq08" if nome in ("rq08_releases.csv", "rq08_extracao_erros.csv") else "outputs/analise"
    caminho = RAIZ / pasta / nome
    if not caminho.exists():
        pytest.skip(f"{nome} ainda não gerado")
    with (RAIZ / "DICIONARIO_DE_DADOS.csv").open(encoding="utf-8") as f:
        documentadas = {r["coluna"].strip() for r in csv.DictReader(f) if r["arquivo"].strip() == nome}
    faltam = [c for c in pd.read_csv(caminho, nrows=0).columns if c not in documentadas]
    assert not faltam
