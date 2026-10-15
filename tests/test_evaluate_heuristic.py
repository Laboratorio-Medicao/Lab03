"""Testes de scripts.evaluate_heuristic (Issue #28) — guarda de independência, consenso, P/R/F1 e escolha.

Fixtures fictícias, feitas à mão: nenhum repositório ou tag da amostra-ouro real.
"""

import csv
import json
from urllib.parse import unquote

import pytest

from metricas.heuristica import VERSOES
from scripts import evaluate_heuristic as ev

AVALIADORES = ["ana", "bia", "caio"]

# Amostra fictícia: 2 repos, 4 releases.
AMOSTRA = [
    {"full_name": "org/lib", "release_id": "11", "tag_name": "v1.0.0", "published_at": "2025-03-01T00:00:00Z",
     "compare_url": ""},
    {"full_name": "org/lib", "release_id": "12", "tag_name": "v1.0.1", "published_at": "2025-03-05T00:00:00Z",
     "compare_url": "https://github.com/org/lib/compare/v1.0.0...v1.0.1"},
    {"full_name": "org/app", "release_id": "21", "tag_name": "app/2.1.0", "published_at": "2025-04-01T00:00:00Z",
     "compare_url": "https://github.com/org/app/compare/app/2.0.0...app/2.1.0"},
    {"full_name": "org/app", "release_id": "22", "tag_name": "app/2.1.1", "published_at": "2025-04-03T00:00:00Z",
     "compare_url": "https://github.com/org/app/compare/app/2.1.0...app/2.1.1"},
]
# Commits por "base...head" no compare fictício.
COMMITS = {
    "v1.0.0...v1.0.1": ["fix: crash ao abrir"],
    "app/2.0.0...app/2.1.0": ["feat: nova tela", "fixes #3"],
    "app/2.1.0...app/2.1.1": ["docs: readme"],
}


class Resp:
    def __init__(self, corpo, status=200):
        self._corpo, self.status_code, self.headers = corpo, status, {}

    def json(self):
        return self._corpo


class FakeClient:
    def __init__(self, comparacoes, status=None):
        self.comparacoes, self.status, self.chamadas = comparacoes, status or {}, []

    def get(self, path, params=None):
        self.chamadas.append(path)
        if "/releases/" in path:  # release notes (v9)
            return Resp({"body": "### Fixed\n* crash ao abrir" if path.endswith("/21") else "Nova tela"})
        chave = unquote(path.split("/compare/", 1)[1])
        if chave in self.status:
            return Resp({"message": "erro"}, status=self.status[chave])
        msgs = self.comparacoes[chave]
        n, pp = int(params["page"]), int(params["per_page"])
        commits = [{"sha": f"s{i}", "commit": {"author": {"date": "2025-01-01T00:00:00Z"},
                                               "committer": {"date": "2025-01-01T00:00:00Z"}, "message": m},
                    "parents": [{}]} for i, m in enumerate(msgs)]
        return Resp({"status": "ahead", "total_commits": len(commits), "commits": commits[(n - 1) * pp:n * pp]})


class ClienteProibido:
    def get(self, path, params=None):
        raise AssertionError("a API não deveria ser chamada")


def _csv(caminho, linhas, colunas):
    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def _planilha(linhas_amostra, completa=True):
    vistos, linhas = set(), []
    for l in linhas_amostra:
        primeira = l["full_name"] not in vistos
        vistos.add(l["full_name"])
        linhas.append({
            "full_name": l["full_name"], "tag_name": l["tag_name"], "release_id": l["release_id"],
            "tipo_projeto": "outro" if primeira else "",
            "releases_sao_entregas_reais": "sim" if primeira else "",
            "corretiva": "nao" if completa else "",
        })
    return linhas


@pytest.fixture
def amostra_dir(tmp_path):
    """Pasta da amostra-ouro com amostra, sorteio, 3 planilhas completas e consenso (12 e 22 corretivas)."""
    d = tmp_path / "amostra_ouro"
    d.mkdir()
    _csv(d / "amostra_ouro.csv", AMOSTRA, ["full_name", "release_id", "tag_name", "published_at", "compare_url"])
    (d / "sorteio.json").write_text(json.dumps({"avaliadores": AVALIADORES}), encoding="utf-8")
    colunas = ["full_name", "tipo_projeto", "releases_sao_entregas_reais", "release_id", "tag_name", "corretiva"]
    for a in AVALIADORES:
        _csv(d / f"labels_{a}.csv", _planilha(AMOSTRA), colunas)
    consenso = [{"dimensao": "tipo_projeto", "item_id": "org/lib", "rotulo_consenso": "outro", "metodo": "unanimidade"}]
    consenso += [
        {"dimensao": "corretiva", "item_id": l["release_id"],
         "rotulo_consenso": "sim" if l["release_id"] in ("12", "22") else "nao", "metodo": "maioria"}
        for l in AMOSTRA
    ]
    _csv(d / "consenso.csv", consenso, ["dimensao", "item_id", "rotulo_consenso", "metodo"])
    return d


# ---- guarda de independência ----


def test_checar_rotulos_ok(amostra_dir):
    assert ev.checar_rotulos(amostra_dir) == []


def test_checar_rotulos_incompleto_nao_expoe_conteudo(amostra_dir):
    colunas = ["full_name", "tipo_projeto", "releases_sao_entregas_reais", "release_id", "tag_name", "corretiva"]
    _csv(amostra_dir / "labels_bia.csv", _planilha(AMOSTRA, completa=False), colunas)
    (amostra_dir / "labels_caio.csv").unlink()
    assert ev.checar_rotulos(amostra_dir) == ["labels_bia.csv: 4 pendência(s)", "labels_caio.csv: arquivo ausente"]


def test_executar_recusa_antes_de_tocar_na_api(amostra_dir):
    (amostra_dir / "labels_ana.csv").unlink()
    with pytest.raises(ev.AvaliacaoError, match="rotulagem incompleta"):
        ev.executar(amostra_dir, ClienteProibido(), None)
    assert not (amostra_dir / ev.ARQ_HEURISTICA).exists()


def test_main_recusa_com_rotulos_incompletos(amostra_dir, tmp_path, capsys):
    (amostra_dir / "labels_ana.csv").unlink()
    config = tmp_path / "config.yaml"
    config.write_text("caminhos:\n  cache: cache_teste\n", encoding="utf-8")
    assert ev.main(["--config", str(config), "--amostra-dir", str(amostra_dir)]) == 1
    assert "rotulagem incompleta" in capsys.readouterr().err
    assert not (amostra_dir / ev.ARQ_AVALIACAO).exists()


# ---- consenso ----


def test_consenso_corretiva_le_so_a_dimensao(amostra_dir):
    assert ev.consenso_corretiva(amostra_dir / "consenso.csv") == {"11": 0, "12": 1, "21": 0, "22": 1}


def test_consenso_pendente_e_erro_codigo_2(tmp_path):
    _csv(tmp_path / "c.csv", [{"dimensao": "corretiva", "item_id": "1", "rotulo_consenso": "", "metodo": "pendente"}],
         ["dimensao", "item_id", "rotulo_consenso", "metodo"])
    with pytest.raises(ev.AvaliacaoError) as e:
        ev.consenso_corretiva(tmp_path / "c.csv")
    assert e.value.codigo == 2


def test_consenso_ausente_ou_sem_dimensao(tmp_path):
    with pytest.raises(ev.AvaliacaoError, match="scripts.agreement"):
        ev.consenso_corretiva(tmp_path / "nao_existe.csv")
    _csv(tmp_path / "c.csv", [{"dimensao": "tipo_projeto", "item_id": "x", "rotulo_consenso": "outro", "metodo": "x"}],
         ["dimensao", "item_id", "rotulo_consenso", "metodo"])
    with pytest.raises(ev.AvaliacaoError, match="nenhuma linha"):
        ev.consenso_corretiva(tmp_path / "c.csv")


# ---- pares da amostra ----


def test_base_do_compare():
    assert ev.base_do_compare("", "v1.0.0") is None
    assert ev.base_do_compare("https://github.com/o/r/compare/v1.0.0...v1.0.1", "v1.0.1") == "v1.0.0"
    assert ev.base_do_compare("https://github.com/o/r/compare/app/2.0.0...app/2.1.0", "app/2.1.0") == "app/2.0.0"
    with pytest.raises(ev.AvaliacaoError):
        ev.base_do_compare("https://github.com/o/r/compare/v1...v2", "v3")


def test_pares_da_amostra_preserva_ordem_e_id():
    pares = ev.pares_da_amostra(AMOSTRA)
    assert list(pares) == ["org/lib", "org/app"]
    assert pares["org/lib"][0] == (None, {"tag_name": "v1.0.0", "published_at": "2025-03-01T00:00:00Z", "id": "11"})
    assert pares["org/app"][1][0] == {"tag_name": "app/2.1.0"}


# ---- coleta e aplicação das versões ----


def test_coletar_e_aplicar_versoes(tmp_path):
    client = FakeClient(COMMITS, status={"app/2.1.0...app/2.1.1": 404})
    pares = ev.pares_da_amostra(AMOSTRA)
    linhas = ev.aplicar_versoes(ev.coletar_commits(pares, client, tmp_path / "cache"), ev.coletar_notas(AMOSTRA, client))
    por_id = {l["release_id"]: l for l in linhas}
    assert list(por_id) == ["11", "12", "21", "22"]
    assert por_id["11"]["status"] == "sem_anterior" and por_id["11"]["v1"] == "nao"
    assert por_id["12"]["semver_patch"] == "sim" and por_id["12"]["v1"] == "sim"
    # minor + "fixes": estrita não casa, ampla casa
    assert (por_id["21"]["palavra_chave"], por_id["21"]["palavra_chave_ampla"]) == ("nao", "sim")
    assert (por_id["21"]["v2"], por_id["21"]["v6"], por_id["21"]["v7"]) == ("nao", "sim", "sim")
    # 404: sem mensagens, marcado como incompleto; v4 (só patch) ainda marca
    assert por_id["22"]["mensagens_incompletas"] == "sim" and por_id["22"]["status"] == "404"
    assert (por_id["22"]["v1"], por_id["22"]["v4"]) == ("nao", "sim")
    assert set(ev.COLUNAS_HEURISTICA) == set(linhas[0])


def test_sem_token_usa_so_o_cache(tmp_path):
    cache = tmp_path / "cache"
    pares = ev.pares_da_amostra(AMOSTRA)
    ev.coletar_commits(pares, FakeClient(COMMITS), cache)  # popula o cache de commits
    releases = ev.coletar_commits(pares, ev.ClienteSemToken(), cache)
    assert releases["org/lib"][1]["commits"][0]["message"] == "fix: crash ao abrir"
    with pytest.raises(ev.AvaliacaoError, match="sem token"):
        ev.coletar_commits(pares, ev.ClienteSemToken(), tmp_path / "vazio")


def test_criar_cliente_sem_token(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    config = tmp_path / "config.yaml"
    config.write_text(f"caminhos:\n  cache: {tmp_path / 'c'}\n", encoding="utf-8")
    assert isinstance(ev.criar_cliente(ev.load_config(config)), ev.ClienteSemToken)
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    assert not isinstance(ev.criar_cliente(ev.load_config(config)), ev.ClienteSemToken)


# ---- P/R/F1 e escolha da versão ----


def _linhas_preditas(predicoes):
    return [{"release_id": str(i), **{v: p for v in VERSOES}} for i, p in enumerate(predicoes)]


def test_exemplo_do_professor_p_r_f1():
    """40 marcadas, 30 confirmadas, 50 corretivas no consenso → P=0,75, R=0,60, F1≈0,667."""
    consenso, pred = {}, []
    for i in range(100):
        consenso[str(i)] = 1 if i < 50 else 0
        pred.append("sim" if i < 30 or 50 <= i < 60 else "nao")
    tabela = ev.avaliar_versoes(_linhas_preditas(pred), consenso)
    v1 = tabela[0]
    assert (v1["tp"], v1["fp"], v1["fn"], v1["tn"]) == (30, 10, 20, 40)
    assert (v1["precisao"], v1["recall"]) == (0.75, 0.6)
    assert v1["f1"] == pytest.approx(0.6667, abs=1e-4)


def test_sem_predicoes_positivas_zero_division():
    tabela = ev.avaliar_versoes(_linhas_preditas(["nao", "nao"]), {"0": 1, "1": 0})
    assert (tabela[0]["precisao"], tabela[0]["recall"], tabela[0]["f1"]) == (0.0, 0.0, 0.0)


def test_release_ids_desalinhados_e_erro():
    with pytest.raises(ev.AvaliacaoError, match="diferem"):
        ev.avaliar_versoes(_linhas_preditas(["sim"]), {"0": 1, "9": 0})


def _tabela(f1s):
    return [{"versao": f"v{i}", "f1": f} for i, f in enumerate(f1s, start=1)]


@pytest.mark.parametrize("f1s, esperada", [
    ([0.70, 0.95, 0.5], "v1"),    # v1 atinge o mínimo: fica, mesmo com outra maior
    ([0.60, 0.65, 0.80], "v3"),   # v1 abaixo: maior F1
    ([0.50, 0.80, 0.80], "v2"),   # empate: menor número
])
def test_escolher_versao(f1s, esperada):
    assert ev.escolher_versao(_tabela(f1s)) == esperada


def test_escolhe_v10_acima_de_v9_pelo_numero():
    tabela = [{"versao": "v1", "f1": 0.1}, {"versao": "v10", "f1": 0.9}, {"versao": "v9", "f1": 0.9}]
    assert ev.escolher_versao(tabela) == "v9"


# ---- ponta a ponta ----


def test_executar_gera_os_tres_arquivos(amostra_dir, tmp_path):
    tabela = ev.executar(amostra_dir, FakeClient(COMMITS), tmp_path / "cache")
    assert [l["versao"] for l in tabela] == list(VERSOES)
    assert sum(l["escolhida"] == "sim" for l in tabela) == 1
    v1 = tabela[0]
    # consenso: 12 e 22 corretivas; v1 marca só 12
    assert (v1["tp"], v1["fp"], v1["fn"], v1["tn"]) == (1, 0, 1, 2)
    with (amostra_dir / ev.ARQ_AVALIACAO).open(encoding="utf-8-sig") as f:
        assert next(csv.reader(f)) == list(ev.COLUNAS_AVALIACAO)
    with (amostra_dir / ev.ARQ_HEURISTICA).open(encoding="utf-8-sig") as f:
        assert len(list(csv.DictReader(f))) == 4
    md = (amostra_dir / ev.ARQ_RELATORIO).read_text(encoding="utf-8")
    assert "**2 corretivas**" in md and "| v7" in md and "Viés de seleção" in md


def test_relatorio_pede_acao_quando_escolhida_difere_da_constante():
    tabela = [{"versao": v, "descricao": "d", "n": 2, "tp": 1, "fp": 0, "fn": 0, "tn": 1, "precisao": 1.0,
               "recall": 1.0, "f1": 1.0 if v == "v2" else 0.1, "escolhida": "sim" if v == "v2" else "nao"}
              for v in VERSOES]
    md = ev.relatorio_md(tabela, [{"mensagens_incompletas": "sim"}, {"mensagens_incompletas": "nao"}])
    assert "**Versão escolhida: v2**" in md and "atualize a constante" in md
    assert "mensagens incompletas (`compare` 404 ou truncado): 1" in md


def test_main_ponta_a_ponta(amostra_dir, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ev, "criar_cliente", lambda config: FakeClient(COMMITS))
    config = tmp_path / "config.yaml"
    config.write_text(f"caminhos:\n  cache: {tmp_path / 'cache'}\n", encoding="utf-8")
    assert ev.main(["--config", str(config), "--amostra-dir", str(amostra_dir)]) == 0
    saida = capsys.readouterr().out
    assert "v1: P=1.00 R=0.50" in saida and "<- escolhida" in saida


# ---- v9 sem notas: erro explícito, sem saída parcial (correção de auditoria) ----


def _releases_e_notas(tmp_path):
    client = FakeClient(COMMITS)
    releases = ev.coletar_commits(ev.pares_da_amostra(AMOSTRA), client, tmp_path / "cache")
    return releases, ev.coletar_notas(AMOSTRA, client)


@pytest.mark.parametrize("quebra", ["ausente", "none"])
def test_aplicar_versoes_sem_notas_de_release_com_anterior_falha(tmp_path, quebra):
    releases, notas = _releases_e_notas(tmp_path)
    if quebra == "ausente":
        del notas["12"]
    else:
        notas["12"] = None  # coleta falhou (ex.: 404)
    with pytest.raises(ev.AvaliacaoError, match="release notes indisponíveis"):
        ev.aplicar_versoes(releases, notas)
    with pytest.raises(ev.AvaliacaoError):
        ev.aplicar_versoes(releases)  # nenhuma nota coletada


def test_notas_da_release_sem_anterior_nao_sao_exigidas_e_vazia_e_dado(tmp_path):
    releases, notas = _releases_e_notas(tmp_path)
    notas["11"] = None  # 1ª release da história: não entra na regra
    notas["12"] = ""    # coletada e vazia: presente
    linhas = {l["release_id"]: l for l in ev.aplicar_versoes(releases, notas)}
    assert linhas["11"]["v9"] == "nao" and linhas["12"]["nota_correcao"] == "nao"


def test_executar_com_falha_na_coleta_de_notas_nao_grava_saidas(amostra_dir, tmp_path):
    class SemNotas(FakeClient):
        def get(self, path, params=None):
            if "/releases/" in path:
                return Resp({"message": "Not Found"}, status=404)
            return super().get(path, params)

    antes = {p.name: p.read_bytes() for p in amostra_dir.iterdir() if p.is_file()}
    with pytest.raises(ev.AvaliacaoError, match="release notes indisponíveis"):
        ev.executar(amostra_dir, SemNotas(COMMITS), tmp_path / "cache")
    for nome in (ev.ARQ_HEURISTICA, ev.ARQ_AVALIACAO, ev.ARQ_RELATORIO):
        assert not (amostra_dir / nome).exists()
    assert {p.name: p.read_bytes() for p in amostra_dir.iterdir() if p.is_file()} == antes
