"""Testes de scripts.validar_rotulos (Issue #23)."""

import csv
from datetime import date

import pytest

from scripts import sample_gold as sg
from scripts import validar_rotulos as vr
from tests.test_sample_gold import FIM, INI, _cache, _csv_repos

NOMES = [f"org{i:02d}/repo{i:02d}" for i in range(60)]


@pytest.fixture
def ouro(tmp_path):
    saida = tmp_path / "ouro"
    sg.gerar(_csv_repos(tmp_path, NOMES), _cache(tmp_path, NOMES), INI, FIM, saida, ("marcos", "x", "y"))
    return saida


def _preencher(planilha, alterar=None):
    with planilha.open(encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    anterior = None
    for linha in linhas:
        if linha["full_name"] != anterior:
            linha["tipo_projeto"], linha["releases_sao_entregas_reais"] = "biblioteca_framework", "sim"
            anterior = linha["full_name"]
        linha["corretiva"] = "nao"
    if alterar:
        alterar(linhas)
    with planilha.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sg.COLUNAS_PLANILHA)
        w.writeheader()
        w.writerows(linhas)


def test_planilha_em_branco_tem_pendencias(ouro):
    problemas = vr.validar(ouro / "labels_marcos.csv")
    assert len(problemas) == 60 * 2 + 300


def test_planilha_completa_e_valida(ouro):
    _preencher(ouro / "labels_marcos.csv")
    assert vr.validar(ouro / "labels_marcos.csv") == []
    assert vr.main([str(ouro / "labels_marcos.csv")]) == 0


def test_valor_invalido_e_apontado(ouro):
    _preencher(ouro / "labels_marcos.csv", lambda ls: ls[3].update(corretiva="talvez"))
    problemas = vr.validar(ouro / "labels_marcos.csv")
    assert len(problemas) == 1 and "linha 5" in problemas[0] and "talvez" in problemas[0]
    assert vr.main([str(ouro / "labels_marcos.csv")]) == 1


def test_linha_removida_ou_reordenada_e_detectada(ouro):
    _preencher(ouro / "labels_marcos.csv", lambda ls: ls.pop(7))
    assert "release_id diferem" in vr.validar(ouro / "labels_marcos.csv")[0]
