"""Testes da RQ06: fatores × métricas, Kruskal-Wallis/Mann-Whitney, Holm e tamanho de efeito (Issue #38)."""
import csv
import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats
from statsmodels.stats.multitest import multipletests

from analysis import rq06_fatores as rq06
from analysis.common import RAIZ


def _delta_forca_bruta(x, y):
    maior = sum(1 for a in x for b in y if a > b)
    menor = sum(1 for a in x for b in y if a < b)
    return (maior - menor) / (len(x) * len(y))


# ---------- tamanho de efeito ----------

def test_epsilon2_e_h_sobre_n_menos_1():
    a, b, c = [1, 2, 3, 4, 5], [3, 4, 5, 6, 7], [6, 7, 8, 9, 10]
    h = stats.kruskal(a, b, c).statistic
    assert rq06.epsilon2(h, 15) == pytest.approx(h / 14)


def test_epsilon2_h0_e_eta2_h():
    assert rq06.epsilon2_h0(4, 301) == pytest.approx(3 / 300)
    assert rq06.eta2_h(10.0, 3, 53) == pytest.approx((10 - 3 + 1) / 50)
    assert rq06.eta2_h(1.0, 3, 53) < 0  # abaixo do esperado sob H0


@pytest.mark.parametrize("x,y", [
    ([1, 2, 3, 4, 5], [3, 3, 4, 8, 9]),          # com empates
    ([10, 20, 30], [1, 2, 3, 4]),                 # x domina
    ([5, 5, 5, 5, 5], [5, 5, 6, 4, 5]),           # quase tudo empatado
])
def test_cliff_delta_bate_com_forca_bruta(x, y):
    assert rq06.delta_entre(x, y) == pytest.approx(_delta_forca_bruta(x, y))
    u1 = stats.mannwhitneyu(x, y, alternative="two-sided").statistic
    assert rq06.cliff_delta(u1, len(x), len(y)) == pytest.approx(_delta_forca_bruta(x, y))


def test_cliff_delta_extremos_e_sinal():
    assert rq06.delta_entre([10, 11, 12], [1, 2, 3]) == 1
    assert rq06.delta_entre([1, 2, 3], [10, 11, 12]) == -1
    assert rq06.delta_entre([1, 2, 3], [1, 2, 3]) == 0


@pytest.mark.parametrize("valor,esperado", [
    (0.0, "desprezível"), (0.1469, "desprezível"), (0.147, "pequeno"), (-0.3299, "pequeno"),
    (0.33, "médio"), (-0.4739, "médio"), (0.474, "grande"), (-1.0, "grande"), (float("nan"), ""),
])
def test_magnitude_cliff_romano(valor, esperado):
    assert rq06.magnitude_cliff(valor) == esperado


@pytest.mark.parametrize("valor,esperado", [
    (0.0, "desprezível"), (0.0099, "desprezível"), (0.01, "pequeno"), (0.0799, "pequeno"),
    (0.08, "médio"), (0.2599, "médio"), (0.26, "grande"), (0.9, "grande"), (float("nan"), ""),
])
def test_magnitude_epsilon2_mangiafico(valor, esperado):
    assert rq06.magnitude_epsilon2(valor) == esperado


# ---------- fatores ----------

def test_quartis_rotulos_e_tamanhos():
    s = pd.Series(range(1, 101), dtype=float)
    g = rq06.grupo_quartis(s)
    assert g.value_counts().to_dict() == {"Q1": 25, "Q2": 25, "Q3": 25, "Q4": 25}
    assert g.iloc[0] == "Q1" and g.iloc[-1] == "Q4"


def test_quartis_valor_na_borda_vai_para_o_quartil_inferior():
    s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9], dtype=float)  # Q1 = 3 (interpolação linear)
    g = rq06.grupo_quartis(s)
    assert g[s == 3].iloc[0] == "Q1" and g[s == 4].iloc[0] == "Q2"


def test_criterio_q1_usa_minimo_real_e_demais_intervalo_aberto():
    df = pd.DataFrame({"stars": [1006.0, 1500, 2000, 2500, 3000, 3500, 4000, 9000]})
    fat = pd.DataFrame({"popularidade": rq06.grupo_quartis(df["stars"])})
    assert rq06.criterio("popularidade", "Q1", df, fat).startswith("stars em [1006, ")
    assert rq06.criterio("popularidade", "Q2", df, fat).startswith("stars em (")


def test_linguagem_rara_vira_outras_e_vazia_fica_fora():
    s = pd.Series(["Go"] * 3 + ["Rust"] + [None])
    g = rq06.grupo_linguagem(s, minimo=2)
    assert list(g[:4]) == ["Go", "Go", "Go", rq06.OUTRAS] and pd.isna(g.iloc[4])


def test_tipo_exclui_outro_e_repos_fora_do_consenso():
    consenso = pd.DataFrame({
        "dimensao": ["tipo_projeto"] * 3 + ["corretiva"],
        "item_id": ["a/a", "b/b", "c/c", "123"],
        "rotulo_consenso": ["aplicacao_servico", "outro", "ferramenta_cli", "sim"],
    })
    tipos = rq06.tipos_do_consenso(consenso)
    g = rq06.grupo_tipo(pd.Series(["a/a", "b/b", "c/c", "d/d"]), tipos)
    assert g.iloc[0] == "aplicacao_servico" and g.iloc[2] == "ferramenta_cli"
    assert pd.isna(g.iloc[1]) and pd.isna(g.iloc[3])


def test_ordem_grupos_outras_por_ultimo():
    g = pd.Series(["Go", "Go", rq06.OUTRAS, "Rust", rq06.OUTRAS, rq06.OUTRAS, None])
    assert rq06.ordem_grupos("linguagem", g) == ["Go", "Rust", rq06.OUTRAS]
    assert rq06.ordem_grupos("idade", pd.Series(["Q3", "Q1"])) == ["Q1", "Q3"]


# ---------- testes estatísticos ----------

def _dados(tamanhos, deslocamento=1.0, semente=0):
    rng = np.random.default_rng(semente)
    v, g = [], []
    for i, (nome, n) in enumerate(tamanhos.items()):
        v += list(rng.normal(i * deslocamento, 1, n))
        g += [nome] * n
    return pd.Series(v), pd.Series(g, dtype=object)


def test_testar_tres_grupos_usa_kruskal():
    v, g = _dados({"Q1": 10, "Q2": 10, "Q3": 10})
    r = rq06.testar(v, g, ["Q1", "Q2", "Q3"])
    h = stats.kruskal(v[g == "Q1"], v[g == "Q2"], v[g == "Q3"]).statistic
    assert r["teste"] == "kruskal" and r["k_grupos"] == 3 and r["n"] == 30
    assert r["estatistica"] == pytest.approx(h) and r["efeito"] == pytest.approx(h / 29)
    assert r["efeito_nome"] == "epsilon2" and r["efeito_grupos"] == ""
    assert r["epsilon2_h0"] == pytest.approx(2 / 29) and r["eta2_h"] == pytest.approx((h - 2) / 27)


def test_testar_dois_grupos_usa_mann_whitney_e_sinal_segue_a_ordem():
    v, g = _dados({"A": 8, "B": 9}, deslocamento=-5)  # B bem menor que A
    r = rq06.testar(v, g, ["A", "B"])
    assert r["teste"] == "mannwhitney" and r["efeito_nome"] == "cliff_delta"
    assert r["efeito_grupos"] == "A × B" and r["efeito"] == pytest.approx(1.0)
    assert r["efeito"] == pytest.approx(_delta_forca_bruta(v[g == "A"], v[g == "B"]))
    assert math.isnan(r["eta2_h"])


def test_testar_descarta_grupo_pequeno_e_pode_virar_mann_whitney():
    v, g = _dados({"Q1": 10, "Q2": 10, "Q3": 4})
    r = rq06.testar(v, g, ["Q1", "Q2", "Q3"])
    assert r["teste"] == "mannwhitney" and r["grupos_excluidos"] == "Q3=4"
    assert r["n_por_grupo"] == "Q1=10; Q2=10" and r["n"] == 20 and r["grupos_testados"] == ["Q1", "Q2"]


def test_testar_remove_nan_e_conta():
    v, g = _dados({"Q1": 10, "Q2": 10, "Q3": 10})
    v.iloc[[0, 1, 15]] = np.nan
    g.iloc[29] = np.nan  # fora do fator: não conta como NaN da métrica
    r = rq06.testar(v, g, ["Q1", "Q2", "Q3"])
    assert r["n"] == 26 and r["n_excluidos_nan"] == 3


def test_testar_menos_de_dois_grupos_nao_executa():
    v, g = _dados({"Q1": 10, "Q2": 3})
    r = rq06.testar(v, g, ["Q1", "Q2"])
    assert r["teste"] == "nao_executado" and math.isnan(r["p_bruto"]) and r["observacao"]


@pytest.mark.parametrize("grupos", [["A", "B"], ["A", "B", "C"]])
def test_testar_valores_identicos_nao_executa(grupos):
    v = pd.Series([0.0] * (6 * len(grupos)))
    g = pd.Series([x for x in grupos for _ in range(6)])
    r = rq06.testar(v, g, grupos)
    assert r["teste"] == "nao_executado" and math.isnan(r["p_bruto"])
    assert "idênticos" in r["observacao"]


def test_holm_so_nos_executados_e_usa_reject():
    t = pd.DataFrame({"p_bruto": [0.01, np.nan, 0.04, 0.0001, 0.5]})
    h = rq06.aplicar_holm(t)
    rej, adj, _, _ = multipletests([0.01, 0.04, 0.0001, 0.5], alpha=0.05, method="holm")
    executados = h["p_bruto"].notna()
    assert h.loc[executados, "p_holm"].to_numpy() == pytest.approx(adj)
    assert list(h.loc[executados, "significativo_holm"]) == list(rej)
    assert math.isnan(h.loc[1, "p_holm"]) and pd.isna(h.loc[1, "significativo_holm"])


def test_melhor_grupo_respeita_sentido_empates_e_outras():
    g = pd.Series(["Q1"] * 5 + ["Q2"] * 5 + ["Q3"] * 5 + [rq06.OUTRAS] * 5)
    v = pd.Series([1.0] * 5 + [3.0] * 5 + [1.0] * 5 + [0.0] * 5)
    testados = ["Q1", "Q2", "Q3", rq06.OUTRAS]
    assert rq06.melhor_grupo("lt_release_median_h", v, g, testados) == "Q1|Q3"
    assert rq06.melhor_grupo("deployment_frequency", v, g, testados) == "Q2"
    assert rq06.melhor_grupo("deployment_frequency", v, g, ["Q1", "Q3"]) == "Q1|Q3"  # só os testados


def test_contraste_quartis_tipo_e_linguagem():
    g = pd.Series(["Q1"] * 6 + ["Q4"] * 6)
    v = pd.Series([1.0] * 6 + [9.0] * 6)
    c = rq06.contraste("idade", v, g, ["Q1", "Q4"])
    assert c["contraste"] == "Q4 × Q1" and c["delta_contraste"] == 1 and c["magnitude_contraste"] == "grande"
    gt = pd.Series(["aplicacao_servico"] * 6 + ["biblioteca_framework"] * 6)
    ct = rq06.contraste("tipo", pd.Series([1.0] * 6 + [2.0] * 6), gt,
                        ["aplicacao_servico", "biblioteca_framework"])
    assert ct["contraste"] == "aplicacao_servico × biblioteca_framework" and ct["delta_contraste"] == -1
    assert rq06.contraste("linguagem", v, g, ["Q1", "Q4"])["contraste"] == ""


def test_contraste_vazio_com_motivo_se_grupo_fora_do_teste():
    g = pd.Series(["Q1"] * 6 + ["Q4"] * 3)
    c = rq06.contraste("idade", pd.Series(np.arange(9.0)), g, ["Q1"])
    assert c["contraste"] == "" and math.isnan(c["delta_contraste"]) and "Q4" in c["motivo_contraste"]


# ---------- execução ponta a ponta ----------

@pytest.fixture
def entradas(tmp_path):
    rng = np.random.default_rng(1)
    n = 80
    langs = ["Go"] * 30 + ["Python"] * 30 + ["Java"] * 10 + ["Nix"] * 8 + [None] * 2
    df = pd.DataFrame({
        "full_name": [f"o/r{i}" for i in range(n)],
        "stars": rng.integers(1000, 50000, n),
        "language": langs,
        "contributors": rng.integers(1, 500, n),
        "age_days": rng.uniform(30, 5000, n),
        "deployment_frequency": rng.lognormal(0, 1, n),
        "lt_release_median_h": rng.lognormal(4, 1, n),
        "lt_commit_median_h": rng.lognormal(4, 1, n),
        "cfr_a": rng.uniform(0, 0.3, n),
        "cfr_b": rng.uniform(0, 0.6, n),
        "rec_median_h": rng.lognormal(1, 1, n),
        "n_episodios": rng.integers(1, 20, n),
    })
    df.loc[[0, 1], "rec_median_h"] = np.nan
    df.loc[0, "n_episodios"] = 0  # sem falha
    csv_m = tmp_path / "metrics.csv"
    df.to_csv(csv_m, index=False)
    tipos = ["aplicacao_servico"] * 10 + ["biblioteca_framework"] * 10 + ["ferramenta_cli"] * 6 + ["outro"] * 4
    consenso = pd.DataFrame({"dimensao": "tipo_projeto", "item_id": df["full_name"][:30],
                             "descricao": df["full_name"][:30], "rotulo_consenso": tipos, "metodo": "unanimidade"})
    csv_c = tmp_path / "consenso.csv"
    consenso.to_csv(csv_c, index=False, encoding="utf-8-sig")
    return csv_m, csv_c, tmp_path / "out"


def test_executar_gera_saidas_e_tabela_unica(entradas):
    csv_m, csv_c, saida = entradas
    r = rq06.executar(csv_m, csv_c, saida)
    assert {"rq06_testes.csv", "rq06_grupos.csv", "rq06_fatores.csv", "rq06_efeitos.png"} <= \
        {p.name for p in saida.iterdir()}
    t = pd.read_csv(saida / "rq06_testes.csv")
    assert len(t) == len(rq06.FATORES) * 6 and list(t.columns) == rq06.COLUNAS_TESTES
    exe = t["p_bruto"].notna()
    _, adj, _, _ = multipletests(t.loc[exe, "p_bruto"], method="holm")
    assert t.loc[exe, "p_holm"].to_numpy() == pytest.approx(adj)
    tipo = t[t["fator"] == "tipo"].iloc[0]
    assert tipo["n"] == 26 and tipo["k_grupos"] == 3  # "outro" fora
    rec = t[(t["fator"] == "linguagem") & (t["coluna"] == "rec_median_h")].iloc[0]
    assert rec["n_excluidos_nan"] == 2 and "censurados" in rec["observacao"]
    g = r["grupos"]
    go_rec = g[(g["fator"] == "linguagem") & (g["grupo"] == "Go") & (g["coluna"] == "rec_median_h")].iloc[0]
    assert (go_rec["n_sem_episodios"], go_rec["n_so_censurados"]) == (1, 1)


def test_colunas_das_saidas_estao_no_dicionario(entradas):
    csv_m, csv_c, saida = entradas
    rq06.executar(csv_m, csv_c, saida)
    with (RAIZ / "DICIONARIO_DE_DADOS.csv").open(encoding="utf-8") as f:
        doc = {}
        for row in csv.DictReader(f):
            for col in row["coluna"].split(","):
                doc.setdefault(row["arquivo"].strip(), set()).add(col.strip())
    for nome in ("rq06_testes.csv", "rq06_grupos.csv", "rq06_fatores.csv"):
        colunas = pd.read_csv(saida / nome, nrows=0).columns
        faltando = [c for c in colunas if c not in doc.get(nome, set())]
        assert not faltando, f"{nome}: sem entrada no dicionário: {faltando}"
