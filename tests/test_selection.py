import csv
from datetime import date

import pytest

from pipeline import selection as sel
from pipeline.config import SelecaoConfig
from pipeline.funil import escrever_funil, resumo
from pipeline.selection import (
    TETO_RESULTADOS,
    ResultadoSelecao,
    avaliar,
    contar_contribuidores,
    contar_releases,
    contar_runs,
    fatias_iniciais,
    search_candidatos,
    selecionar,
)

INICIO, FIM = date(2025, 1, 1), date(2025, 12, 31)


class Resp:
    def __init__(self, dados, headers=None, status=200):
        self._dados, self.headers, self.status_code = dados, headers or {}, status

    def json(self):
        return self._dados


class FakeClient:
    """Cliente falso: `rotas` mapeia path -> função(params) -> Resp. Registra as chamadas."""

    def __init__(self, rotas):
        self.rotas, self.chamadas = rotas, []

    def get(self, path, params=None):
        params = dict(params or {})
        self.chamadas.append((path, params))
        for prefixo, fn in self.rotas.items():
            if path == prefixo or (prefixo.endswith("*") and path.startswith(prefixo[:-1])):
                return fn(params)
        raise AssertionError(f"rota inesperada: {path}")

    def chamadas_em(self, trecho):
        return [c for c in self.chamadas if trecho in c[0]]


def item(nome, estrelas=2500, lang="Python", branch="main", criado="2020-01-01T00:00:00Z"):
    return {"full_name": nome, "stargazers_count": estrelas, "language": lang, "default_branch": branch, "created_at": criado}


def release(dia, draft=False, pre=False):
    return {"draft": draft, "prerelease": pre, "published_at": f"{dia}T12:00:00Z", "tag_name": "v"}


def n_releases(n):
    return [release(f"2025-03-{i + 1:02d}") for i in range(n)]


def run(conclusion="success"):
    return {"conclusion": conclusion, "event": "push"}


def rota_runs(validos, extras=()):
    runs = [run() for _ in range(validos)] + [run(c) for c in extras]
    return lambda p: Resp({"total_count": len(runs), "workflow_runs": runs}) if p["created"].startswith("2025-01") else Resp({"total_count": 0, "workflow_runs": []})


def cliente_repo(workflows=3, releases=None, runs_validos=50, contribuidores_link=None, extras_runs=()):
    releases = n_releases(5) if releases is None else releases
    link = {"Link": f'<https://api.github.com/repos/o/r/contributors?per_page=1&anon=true&page={contribuidores_link}>; rel="last"'} if contribuidores_link else {}
    return FakeClient({
        "/repos/o/r/actions/workflows": lambda p: Resp({"total_count": workflows}),
        "/repos/o/r/releases": lambda p: Resp(releases),
        "/repos/o/r/actions/runs": rota_runs(runs_validos, extras_runs),
        "/repos/o/r/contributors": lambda p: Resp([{"login": "a"}], link),
    })


CFG = SelecaoConfig()


# ---- Teste 1: fatiamento e teto de 1.000


def busca_com_total(totais):
    """Search fake: `totais(consulta)` dá o total_count; devolve até 100 itens por página."""

    def fn(params):
        q = params["q"]
        total = totais(q)
        n = min(total, TETO_RESULTADOS, 100)
        return Resp({"total_count": total, "items": [item(f"x/{q}-{i}") for i in range(n)]})

    return FakeClient({"/search/repositories": fn})


def test_fatias_iniciais_cobrem_faixas_e_linguagens():
    cfg = SelecaoConfig(faixas_estrelas=(1000, 2000, 5000), linguagens=("Python", "Java"))
    consultas = [f.consulta(cfg) for f in fatias_iniciais(cfg)]
    assert len(consultas) == 6  # 3 faixas x 2 linguagens
    assert 'stars:1000..1999 language:"Python" fork:false archived:false' in consultas
    assert 'stars:>=5000 language:"Java" fork:false archived:false' in consultas


def test_nenhuma_consulta_depende_de_mais_de_1000_resultados():
    # a faixa larga tem 3.000; as sub-faixas têm 900 -> a busca deve subdividir
    def total(q):
        return 3000 if "1000..1999" in q else 900

    client = busca_com_total(total)
    cfg = SelecaoConfig(faixas_estrelas=(1000, 2000))
    res = search_candidatos(client, cfg)
    assert all(not f.saturada and f.total_count <= TETO_RESULTADOS for f in res.fatias)
    assert len(res.fatias) > 2  # a faixa 1000..1999 foi dividida em duas
    assert any("1000..1499" in f.consulta for f in res.fatias)


def test_faixa_indivisivel_acima_do_teto_e_marcada_saturada():
    client = busca_com_total(lambda q: 5 if "stars:>=" in q else 5000)
    res = search_candidatos(client, SelecaoConfig(stars_min=10, faixas_estrelas=(10, 12)))
    assert any(f.saturada for f in res.fatias)
    assert all(f.retornados <= TETO_RESULTADOS for f in res.fatias)


# ---- Teste 2: deduplicação


def test_mesmo_repo_em_duas_fatias_vira_um_candidato():
    def fn(params):
        return Resp({"total_count": 1, "items": [item("Org/Repo")]})

    cfg = SelecaoConfig(faixas_estrelas=(1000, 2000))
    res = search_candidatos(FakeClient({"/search/repositories": fn}), cfg)
    assert res.brutos == 2 and len(res.candidatos) == 1


def test_deduplicacao_ignora_caixa():
    itens = iter([item("Org/Repo"), item("org/repo")])
    client = FakeClient({"/search/repositories": lambda p: Resp({"total_count": 1, "items": [next(itens)]})})
    res = search_candidatos(client, SelecaoConfig(faixas_estrelas=(1000, 2000)))
    assert len(res.candidatos) == 1


def test_candidatos_em_ordem_deterministica():
    client = FakeClient({"/search/repositories": lambda p: Resp({"total_count": 2, "items": [item("z/z"), item("a/a")]})})
    res = search_candidatos(client, SelecaoConfig(faixas_estrelas=(1000,)))
    assert [c["full_name"] for c in res.candidatos] == ["a/a", "z/z"]


# ---- Testes 3 e 4: Actions


def test_sem_actions_descarta_com_motivo_e_nao_gasta_chamadas():
    client = cliente_repo(workflows=0)
    r = avaliar(client, item("o/r"), CFG, INICIO, FIM)
    assert (r.status, r.etapa, r.motivo) == ("descartado", "actions", "no_actions")
    assert client.chamadas_em("releases") == [] and client.chamadas_em("runs") == []


def test_com_actions_nao_descarta_por_no_actions():
    r = avaliar(cliente_repo(workflows=2), item("o/r"), CFG, INICIO, FIM)
    assert r.motivo != "no_actions"
    assert r.workflows_total_count == 2


# ---- Testes 5 e 6: releases


def test_quatro_releases_descarta():
    client = cliente_repo(releases=n_releases(4))
    r = avaliar(client, item("o/r"), CFG, INICIO, FIM)
    assert (r.status, r.etapa, r.motivo) == ("descartado", "releases", "lt_5_releases")
    assert client.chamadas_em("runs") == []  # etapa cara não é executada


def test_cinco_releases_passam():
    r = avaliar(cliente_repo(releases=n_releases(5)), item("o/r"), CFG, INICIO, FIM)
    assert r.n_releases_window == 5 and r.motivo != "lt_5_releases"


def test_releases_draft_prerelease_e_fora_da_janela_nao_contam():
    rels = n_releases(3) + [release("2025-04-01", draft=True), release("2025-04-02", pre=True), release("2024-12-31"), release("2026-01-01")]
    client = cliente_repo(releases=rels)
    assert contar_releases(client, "o/r", INICIO, FIM) == 3


def test_releases_nos_limites_da_janela_sao_inclusivas():
    rels = [release("2025-01-01"), release("2025-12-31")]
    assert contar_releases(cliente_repo(releases=rels), "o/r", INICIO, FIM) == 2


def test_releases_seguem_paginacao_link_next():
    paginas = {
        "1": Resp(n_releases(2), {"Link": '<https://api.github.com/repos/o/r/releases?per_page=100&page=2>; rel="next"'}),
        "2": Resp(n_releases(3)),
    }
    client = FakeClient({"/repos/o/r/releases": lambda p: paginas[p.get("page", "1")]})
    assert contar_releases(client, "o/r", INICIO, FIM) == 5


# ---- Testes 7 e 8: runs válidos


def test_49_runs_validos_descarta():
    r = avaliar(cliente_repo(runs_validos=49), item("o/r"), CFG, INICIO, FIM)
    assert (r.status, r.etapa, r.motivo) == ("descartado", "runs", "lt_50_runs")
    assert r.n_runs_valid_window == 49


def test_50_runs_validos_passam():
    r = avaliar(cliente_repo(runs_validos=50), item("o/r"), CFG, INICIO, FIM)
    assert r.status == "selecionado" and r.n_runs_valid_window == 50


def test_runs_ignorados_nao_contam_como_validos():
    ignorados = ["cancelled", "skipped", "neutral", "action_required", "stale", None]
    client = cliente_repo(runs_validos=49, extras_runs=ignorados)
    consultados, validos = contar_runs(client, "o/r", "main", INICIO, FIM)
    assert (consultados, validos) == (55, 49)


def test_falhas_contam_como_validas():
    client = cliente_repo(runs_validos=47, extras_runs=["failure", "timed_out", "startup_failure"])
    assert contar_runs(client, "o/r", "main", INICIO, FIM)[1] == 50


def test_runs_consultam_default_branch_push_e_meses():
    client = cliente_repo()
    contar_runs(client, "o/r", "trunk", INICIO, FIM)
    chamadas = client.chamadas_em("actions/runs")
    assert len(chamadas) == 12  # um por mês da janela
    assert all(p["branch"] == "trunk" and p["event"] == "push" for _, p in chamadas)
    assert chamadas[0][1]["created"] == "2025-01-01..2025-01-31"
    assert chamadas[-1][1]["created"] == "2025-12-01..2025-12-31"


def test_mes_no_teto_de_1000_e_subdividido():
    def fn(p):
        ini, fim = p["created"].split("..")
        dias = (date.fromisoformat(fim) - date.fromisoformat(ini)).days
        total = 1000 if dias > 7 else 10
        return Resp({"total_count": total, "workflow_runs": [run()] * min(total, 100)})

    client = FakeClient({"/repos/o/r/actions/runs": fn})
    contar_runs(client, "o/r", "main", date(2025, 1, 1), date(2025, 1, 31))
    intervalos = [p["created"] for _, p in client.chamadas]
    assert len(intervalos) > 1 and intervalos[0] == "2025-01-01..2025-01-31"
    assert "2025-01-01..2025-01-16" in intervalos  # o mês no teto foi dividido ao meio


# ---- Testes 9 e 10: contribuidores e metadados


def test_contribuidores_usa_per_page_1_e_anon_true_e_le_ultima_pagina():
    client = cliente_repo(contribuidores_link=137)
    assert contar_contribuidores(client, "o/r") == 137
    (_, params), = client.chamadas_em("contributors")
    assert params == {"per_page": 1, "anon": "true"}


def test_contribuidores_sem_link_conta_o_corpo():
    assert contar_contribuidores(cliente_repo(), "o/r") == 1


def test_metadados_do_repo_selecionado():
    it = item("o/r", estrelas=4321, lang="Go", branch="trunk", criado="2024-01-01T00:00:00Z")
    client = cliente_repo(contribuidores_link=42)
    r = avaliar(client, it, CFG, INICIO, FIM)
    assert (r.stars, r.language, r.default_branch, r.contributors) == (4321, "Go", "trunk", 42)
    assert r.age_days == (date(2025, 12, 31) - date(2024, 1, 1)).days  # created_at -> fim da janela


def test_idade_pode_usar_o_inicio_da_janela():
    cfg = SelecaoConfig(idade_referencia="inicio")
    r = avaliar(cliente_repo(), item("o/r", criado="2024-01-01T00:00:00Z"), cfg, INICIO, FIM)
    assert r.age_days == (date(2025, 1, 1) - date(2024, 1, 1)).days


def test_linguagem_nula_e_preservada():
    r = avaliar(cliente_repo(), item("o/r", lang=None), CFG, INICIO, FIM)
    assert r.language is None


def test_erro_de_api_vira_descarte_registrado():
    client = FakeClient({"/repos/o/r/actions/workflows": lambda p: Resp({}, status=404)})
    r = avaliar(client, item("o/r"), CFG, INICIO, FIM)
    assert (r.status, r.etapa, r.motivo) == ("descartado", "actions", "api_error_404")


# ---- Testes 11 e 12: funil, CSV e Markdown


def cliente_funil():
    """6 candidatos: 2 sem Actions, 1 com 4 releases, 1 com 49 runs, 2 selecionados."""
    candidatos = {
        "a/sem1": dict(workflows=0), "b/sem2": dict(workflows=0),
        "c/poucas": dict(releases=n_releases(4)), "d/runs": dict(runs_validos=49),
        "e/ok1": {}, "f/ok2": {},
    }

    class Cliente(FakeClient):
        def get(self, path, params=None):
            nome = path.split("/")[2] + "/" + path.split("/")[3] if path.startswith("/repos/") else None
            if path == "/search/repositories":
                return Resp({"total_count": 6, "items": [item(n) for n in candidatos]})
            cfg = candidatos[nome]
            sub = cliente_repo(**cfg)
            return sub.get(path.replace(nome, "o/r"), params)

    return Cliente({})


def selecao_de_exemplo():
    return selecionar(cliente_funil(), SelecaoConfig(faixas_estrelas=(1000,)), INICIO, FIM)


def test_funil_conta_cada_etapa_corretamente():
    s = resumo(selecao_de_exemplo().registros)
    assert s["candidatos"] == 6 and s["selecionados"] == 2
    assert [(e["entram"], e["saem"], e["restam"]) for e in s["etapas"]] == [(6, 2, 4), (4, 1, 3), (3, 1, 2)]
    assert s["motivos"] == {"lt_5_releases": 1, "lt_50_runs": 1, "no_actions": 2}


def test_funil_entram_menos_saem_igual_restam():
    s = resumo(selecao_de_exemplo().registros)
    for e in s["etapas"]:
        assert e["entram"] - e["saem"] == e["restam"]
    assert s["etapas"][-1]["restam"] == s["selecionados"]


def test_csv_e_md_gerados_e_consistentes(tmp_path):
    res = selecao_de_exemplo()
    csv_path, md_path = escrever_funil(res, tmp_path)
    assert csv_path.name == "funil.csv" and md_path.name == "funil.md"

    linhas = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    assert len(linhas) == 6
    motivos_csv = sorted(l["motivo"] for l in linhas if l["status"] == "descartado")
    assert motivos_csv == ["lt_50_runs", "lt_5_releases", "no_actions", "no_actions"]

    md = md_path.read_text(encoding="utf-8")
    for motivo in set(motivos_csv):
        assert f"| {motivo} | {motivos_csv.count(motivo)} |" in md
    assert "| Amostra final | 2 | — | 2 |" in md
    assert "| 1. Possui Actions | 6 | 2 | 4 |" in md
    assert "fork:false" in md  # fatias consultadas registradas


def test_csv_nao_contem_token(tmp_path):
    escrever_funil(selecao_de_exemplo(), tmp_path)
    for arq in tmp_path.iterdir():
        texto = arq.read_text(encoding="utf-8")
        assert "ghp_" not in texto and "github_pat_" not in texto


def test_selecao_e_reprodutivel():
    a = [r.full_name for r in selecao_de_exemplo().registros]
    b = [r.full_name for r in selecao_de_exemplo().registros]
    assert a == b == sorted(a, key=str.lower)


# ---- integração com a CLI e o config


def test_cli_run_gera_funil_na_pasta_de_saidas(tmp_path):
    from pipeline.cli import run
    from pipeline.config import load_config

    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        f"janela:\n  inicio: 2025-01-01\n  fim: 2025-12-31\ncaminhos:\n  saidas: {tmp_path / 'out'}\n"
        "selecao:\n  faixas_estrelas: [1000]\n",
        encoding="utf-8",
    )
    run(load_config(cfg_path), "token-falso", cliente_funil())
    assert (tmp_path / "out" / "funil.csv").is_file() and (tmp_path / "out" / "funil.md").is_file()


def test_cli_run_sem_cliente_nao_quebra(tmp_path):
    from pipeline.cli import run
    from pipeline.config import load_config

    run(load_config("config.yaml"), "token-falso", None)


def test_config_selecao_invalida(tmp_path):
    from pipeline.config import ConfigError, load_config

    arq = tmp_path / "c.yaml"
    arq.write_text("selecao:\n  faixas_estrelas: [5000, 1000]\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(arq)
