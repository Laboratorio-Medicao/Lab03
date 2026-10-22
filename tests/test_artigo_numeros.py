"""Rastreabilidade do artigo: números, tabelas e figuras de Resultados vêm das saídas analíticas (Issue #42)."""
import re

import pandas as pd
import pytest

from analysis import artigo_numeros as an
from analysis import common, rq02_divergencia, rq08_rework_rate


def test_conferencia_artigo_x_saidas_sem_erros():
    assert an.verificar() == []


def test_macros_batem_com_csv_de_saida():
    mac = an.macros()
    desc = pd.read_csv(an.ANALISE / "rq01_rq04_descritiva.csv").set_index("coluna")
    assert mac["DfMed"] == an.n(desc.loc["deployment_frequency", "mediana"], 2)
    assert mac["CfrbN"] == str(int(desc.loc["cfr_b", "n"]))
    assert mac["RhoNB"] == str(int(pd.read_csv(an.ANALISE / "rq05_spearman.csv").set_index("variante").loc["b", "n"]))


def test_rq06_contagem_de_significativos_vem_da_tabela():
    t = pd.read_csv(an.ANALISE / "rq06_testes.csv")
    assert an.macros()["SeisSig"] == str(int((t["significativo_holm"] == True).sum()))  # noqa: E712
    assert t["p_bruto"].notna().sum() == int(an.macros()["SeisTestes"]) == 30


def test_resultados_tex_nao_tem_numero_decimal_digitado():
    tex = re.sub(r"%.*", "", (an.RESULTADOS_TEX).read_text(encoding="utf-8"))
    sobra = set(re.findall(r"(?<![\\\w{])\d+[,.]\d+", tex)) - {"0,689", "0,70", "0,01", "0,08", "0,26"}
    assert not sobra, f"número digitado em resultados.tex: {sobra}"


def test_figuras_copiadas_existem():
    for _, nome in an.FIGURAS:
        assert (an.FIGS / nome).stat().st_size > 0


def test_formatacao_pt_br():
    assert an.n(1.234, 2) == "1{,}23"
    assert an.pct(0.1234) == "12{,}3"
    assert an.p_tex(0.0004) == "$<0{,}001$"


def test_rq02_divergencia_indicadores():
    df = pd.DataFrame({"lt_release_median_h": [10.0, 30.0, 5.0, 8.0], "lt_commit_median_h": [10.0, 10.0, 10.0, 4.0],
                       "n_releases_avaliadas": [5, 6, 7, 8]})
    ind = rq02_divergencia.indicadores(df).set_index("indicador")["valor"]
    assert ind["n"] == 4
    assert ind["prop_a_maior_que_2b"] == pytest.approx(0.25)  # só 30/10 = 3 > 2 (8/4 = 2 não é > 2)
    assert ind["prop_a_menor_que_b"] == pytest.approx(0.25)   # 5/10
    assert ind["prop_b_maior_que_2a"] == 0


def test_rq08_roda_so_com_insumos_versionados(tmp_path):
    saida = tmp_path / "analise"  # saída vazia: nada de outputs/analise nem de cache
    r = rq08_rework_rate.executar(common.CSV_PADRAO, rq08_rework_rate.RELEASES_PADRAO, saida,
                                  rq08_rework_rate.PREDICOES_PADRAO)
    assert (saida / "rq08_rework_rate.csv").exists()
    assert rq08_rework_rate.RELEASES_PADRAO.parent.name == "rq08"
    assert r is not None


def test_toda_citacao_tem_entrada_no_bib():
    erros = [e for e in an.verificar() if "citação" in e]
    assert not erros, erros


def test_figuras_compostas_do_artigo(tmp_path):
    from analysis import figuras_artigo

    figuras_artigo.executar(common.CSV_PADRAO, tmp_path)
    assert (tmp_path / "fig_rq01_rq02_rq04.png").stat().st_size > 0
    assert (tmp_path / "fig_rq05.png").stat().st_size > 0


def test_tex_sem_cerquilha_sem_escape():
    """`#` fora de comentário quebra a compilação (`macro parameter character #`); use `\\#`."""
    import re

    for tex in sorted((an.RAIZ / "artigo").glob("*.tex")):
        sem_comentario = re.sub(r"(?<!\\)%.*", "", tex.read_text(encoding="utf-8"))
        ruins = re.findall(r"(?<!\\)#(?!1)", sem_comentario)  # #1 é o argumento de \newcommand (\pend, \prov)
        assert not ruins, f"{tex.name}: '#' sem escape ({len(ruins)})"
