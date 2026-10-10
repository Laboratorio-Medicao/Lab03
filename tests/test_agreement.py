"""Testes de scripts.agreement (Issue #26) — kappa de Fleiss, Landis & Koch e consenso."""

import csv
import math

import pytest

from scripts import agreement as ag
from scripts import sample_gold as sg
from tests.test_sample_gold import FIM, INI, _cache, _csv_repos

NOMES = [f"org{i:02d}/repo{i:02d}" for i in range(60)]


def test_concordancia_perfeita_da_kappa_um():
    itens = [["a", "a", "a"], ["b", "b", "b"], ["a", "a", "a"], ["b", "b", "b"]]
    assert ag.kappa_fleiss(itens) == pytest.approx(1.0)
    assert ag.interpretar(1.0) == "quase perfeita"


def test_kappa_de_fleiss_exemplo_conhecido():
    # 4 itens, 3 avaliadores, 2 categorias: P_i = 1, 1/3, 1/3, 1; P_bar = 2/3.
    # pa=3/6 e pb=3/6 -> P_e = 0.5 -> kappa = (2/3 - 1/2) / (1 - 1/2) = 1/3.
    itens = [["a", "a", "a"], ["a", "a", "b"], ["a", "b", "b"], ["b", "b", "b"]]
    assert ag.kappa_fleiss(itens) == pytest.approx(1 / 3)
    assert ag.interpretar(1 / 3) == "razoável"


def test_sem_variacao_e_indefinido():
    k = ag.kappa_fleiss([["sim", "sim", "sim"]] * 5)
    assert math.isnan(k) and ag.interpretar(k) == "indefinido"


def test_kappa_sem_itens_e_erro():
    with pytest.raises(ValueError):
        ag.kappa_fleiss([])


@pytest.mark.parametrize("k,esperado", [
    (-0.1, "pobre"), (0.0, "leve"), (0.20, "leve"), (0.21, "razoável"), (0.40, "razoável"),
    (0.41, "moderada"), (0.60, "moderada"), (0.61, "substancial"), (0.80, "substancial"),
    (0.81, "quase perfeita"),
])
def test_landis_koch(k, esperado):
    assert ag.interpretar(k) == esperado


def test_resolver_unanimidade_maioria_pendente():
    assert ag.resolver(["a", "a", "a"]) == ("a", "unanimidade")
    assert ag.resolver(["a", "b", "a"]) == ("a", "maioria")
    assert ag.resolver(["a", "b", "c"]) == ("", "pendente")


def test_concordancia_simples():
    assert ag.concordancia_simples([["a", "a", "a"], ["a", "b", "a"]]) == 0.5


# --- ponta a ponta com planilhas geradas pelo sample_gold -------------------------------------

@pytest.fixture
def ouro(tmp_path):
    saida = tmp_path / "ouro"
    sg.gerar(_csv_repos(tmp_path, NOMES), _cache(tmp_path, NOMES), INI, FIM, saida, ("ana", "bia", "caio"))
    return saida


def _preencher(planilha, tipo, entrega, corretiva):
    """tipo/entrega: f(repo_idx) -> valor; corretiva: f(linha_idx) -> valor."""
    with planilha.open(encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    anterior, r = None, -1
    for n, linha in enumerate(linhas):
        if linha["full_name"] != anterior:
            r += 1
            anterior = linha["full_name"]
            linha["tipo_projeto"], linha["releases_sao_entregas_reais"] = tipo(r), entrega(r)
        linha["corretiva"] = corretiva(n)
    with planilha.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sg.COLUNAS_PLANILHA)
        w.writeheader()
        w.writerows(linhas)


TIPOS = ("biblioteca_framework", "aplicacao_servico", "ferramenta_cli", "outro")


def _tres(ouro, ana, bia, caio):
    for nome, (t, e, c) in zip(("ana", "bia", "caio"), (ana, bia, caio)):
        _preencher(ouro / f"labels_{nome}.csv", t, e, c)
    return [str(ouro / f"labels_{n}.csv") for n in ("ana", "bia", "caio")]


def _ler(arq):
    with arq.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_ponta_a_ponta_concordancia_total(ouro):
    t = lambda r: TIPOS[r % 4]  # noqa: E731
    e = lambda r: "sim" if r % 2 else "nao"  # noqa: E731
    c = lambda n: "sim" if n % 5 == 0 else "nao"  # noqa: E731
    arquivos = _tres(ouro, (t, e, c), (t, e, c), (t, e, c))
    assert ag.main(arquivos) == 0
    conc = {r["dimensao"]: r for r in _ler(ouro / "concordancia.csv")}
    assert {d: r["kappa_fleiss"] for d, r in conc.items()} == {
        "tipo_projeto": "1.0000", "entrega_real": "1.0000", "corretiva": "1.0000"}
    assert conc["tipo_projeto"]["n_itens"] == "60" and conc["corretiva"]["n_itens"] == "300"
    consenso = _ler(ouro / "consenso.csv")
    assert len(consenso) == 60 + 60 + 300
    assert {r["metodo"] for r in consenso} == {"unanimidade"}
    assert set(consenso[0]) >= {"ana", "bia", "caio", "rotulo_consenso"}


def test_maioria_e_pendente_com_desempate_da_reuniao(ouro, capsys):
    base_t = lambda r: "outro"  # noqa: E731
    e = lambda r: "sim"  # noqa: E731
    c = lambda n: "nao"  # noqa: E731
    # repo 0: 1-1-1 em tipo; repo 1: 2 a 1; resto unânime
    ana = lambda r: "biblioteca_framework" if r == 0 else "outro"  # noqa: E731
    bia = lambda r: "aplicacao_servico" if r == 0 else "outro"  # noqa: E731
    caio = lambda r: "ferramenta_cli" if r in (0, 1) else "outro"  # noqa: E731
    arquivos = _tres(ouro, (ana, e, c), (bia, e, c), (caio, e, c))
    assert ag.main(arquivos) == 2  # pendente
    consenso = _ler(ouro / "consenso.csv")
    tipo = [r for r in consenso if r["dimensao"] == "tipo_projeto"]
    assert tipo[0]["metodo"] == "pendente" and tipo[0]["rotulo_consenso"] == ""
    assert tipo[1]["metodo"] == "maioria" and tipo[1]["rotulo_consenso"] == "outro"
    assert "pendente" in capsys.readouterr().err

    with (ouro / "desempate.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(ag.COLUNAS_DESEMPATE)
        w.writerow(["tipo_projeto", tipo[0]["item_id"], "aplicacao_servico", "README descreve um serviço"])
    assert ag.main(arquivos) == 0
    tipo = [r for r in _ler(ouro / "consenso.csv") if r["dimensao"] == "tipo_projeto"]
    assert tipo[0]["metodo"] == "reuniao" and tipo[0]["rotulo_consenso"] == "aplicacao_servico"
    assert "serviço" in tipo[0]["justificativa"]


def test_recusa_planilha_incompleta(ouro, capsys):
    arquivos = [str(ouro / f"labels_{n}.csv") for n in ("ana", "bia", "caio")]  # em branco
    assert ag.main(arquivos) == 1
    assert "incompleta" in capsys.readouterr().err


def test_nome_avaliador():
    assert ag.nome_avaliador("data/x/labels_marcos.csv") == "marcos"
