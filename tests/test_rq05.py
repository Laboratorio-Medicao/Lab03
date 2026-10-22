"""Testes da RQ05: Spearman entre DF e CFR (a)/(b) (Issue #37)."""
import csv
import math
import warnings
from pathlib import Path

import pandas as pd
import pytest
from scipy import stats

from analysis import rq05_spearman as rq05

RAIZ = Path(__file__).parent.parent


def _df(df_vals, a, b, avaliadas=None):
    n = len(df_vals)
    return pd.DataFrame({
        "full_name": [f"r/{i}" for i in range(n)],
        "deployment_frequency": df_vals,
        "cfr_a": a,
        "cfr_b": b,
        "n_releases_avaliadas_cfr_b": avaliadas if avaliadas is not None else [30] * n,
    })


def test_monotonica_nao_linear_e_rank_e_nao_pearson():
    x = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    d = _df(x, [v ** 3 / 1000 for v in x], [1 / v for v in x])
    t = rq05.tabela(d).set_index("variante")
    assert t.loc["a", "rho"] == pytest.approx(1.0)
    assert t.loc["b", "rho"] == pytest.approx(-1.0)
    assert (t.loc["a", "ic95_inf"], t.loc["a", "ic95_sup"]) == pytest.approx((1.0, 1.0))
    assert (t.loc["b", "ic95_inf"], t.loc["b", "ic95_sup"]) == pytest.approx((-1.0, -1.0))


def test_igual_ao_spearmanr_com_empates_e_ic_contem_rho():
    x = [0.1, 0.1, 0.2, 0.3, 0.3, 0.3, 0.8, 1.5, 2.0, 4.0]
    y = [0.0, 0.0, 0.1, 0.0, 0.2, 0.5, 0.1, 0.3, 0.3, 0.9]
    r = rq05.correlacao(_df(x, y, y), "cfr_a")
    esperado = stats.spearmanr(x, y)
    assert r["rho"] == pytest.approx(esperado.statistic)
    assert r["p_valor"] == pytest.approx(esperado.pvalue)
    assert -1 <= r["ic95_inf"] <= r["rho"] <= r["ic95_sup"] <= 1
    assert r["n_cfr_zero"] == 3


def test_ic_bonett_wright():
    rho, n = 0.4, 103
    se = math.sqrt((1 + rho ** 2 / 2) / (n - 3))
    zc = stats.norm.ppf(0.975)
    esperado = (math.tanh(math.atanh(rho) - zc * se), math.tanh(math.atanh(rho) + zc * se))
    assert rq05.ic_spearman(rho, n) == pytest.approx(esperado)


def test_nan_em_cfr_b_exclui_so_da_variante_b():
    x = [0.1, 0.2, 0.4, 0.8, 1.6, 3.2]
    d = _df(x, [0.1, 0.3, 0.2, 0.5, 0.4, 0.6], [0.0, None, 0.2, None, 0.4, 0.9])
    t = rq05.tabela(d).set_index("variante")
    assert (t.loc["a", "n"], t.loc["a", "n_excluidos"], t.loc["a", "excluidos"]) == (6, 0, "")
    assert (t.loc["b", "n"], t.loc["b", "n_excluidos"]) == (4, 2)
    assert t.loc["b", "excluidos"] == "r/1; r/3"


def test_n2_sem_rho():
    r = rq05.correlacao(_df([0.1, 0.2], [0.1, 0.2], [0.1, 0.2]), "cfr_a")
    assert math.isnan(r["rho"]) and math.isnan(r["p_valor"]) and math.isnan(r["ic95_inf"])
    assert r["forca"] == "" and r["direcao"] == ""


def test_n3_tem_rho_e_p_mas_sem_ic():
    r = rq05.correlacao(_df([1.0, 2.0, 3.0], [1.0, 3.0, 2.0], [0, 0, 0]), "cfr_a")
    assert r["rho"] == pytest.approx(0.5)
    assert r["p_valor"] == pytest.approx(0.6667, abs=1e-3)
    assert math.isnan(r["ic95_inf"]) and math.isnan(r["ic95_sup"]) and r["direcao"] == ""
    assert r["forca"] == "forte"


def test_entrada_constante_vira_nan_sem_aviso():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        r = rq05.correlacao(_df([0.1, 0.2, 0.3, 0.4, 0.5], [0.0] * 5, [0.0] * 5), "cfr_a")
    assert math.isnan(r["rho"]) and math.isnan(r["p_valor"]) and r["forca"] == ""


@pytest.mark.parametrize("inf,sup,esperado", [
    (0.1, 0.5, "positiva"), (-0.5, -0.1, "negativa"), (-0.1, 0.2, "inconclusiva (IC contém 0)"),
    (float("nan"), float("nan"), ""),
])
def test_direcao_pelo_ic(inf, sup, esperado):
    assert rq05.direcao(inf, sup) == esperado


def test_forca_rotulos():
    assert [rq05.forca(v) for v in (0.05, -0.2, 0.4, -0.7)] == ["desprezível", "fraca", "moderada", "forte"]


def test_sensibilidade_aplica_cortes():
    x = [0.1 * (i + 1) for i in range(30)]
    d = _df(x, x, [v / 3 for v in x], avaliadas=list(range(1, 31)))
    s = rq05.sensibilidade_cfr_b(d)
    assert list(s["min_releases_avaliadas"]) == [5, 10, 20]
    assert list(s["n"]) == [26, 21, 11]
    assert set(s["variante"]) == {"b"}


def test_zeros_por_avaliadas():
    d = _df([0.1, 0.2, 0.3, 0.4], [0, 0, 0, 0], [0.0, 0.5, 0.0, None], avaliadas=[4, 6, 12, 20])
    z = rq05.zeros_por_avaliadas(d).set_index("releases_avaliadas")
    assert (z.loc["< 10", "n"], z.loc["< 10", "n_cfr_b_zero"]) == (2, 1)
    assert (z.loc[">= 10", "n"], z.loc[">= 10", "n_cfr_b_zero"]) == (1, 1)


def test_fmt_p():
    assert rq05.fmt_p(5e-33) == "< 0,001" and rq05.fmt_p(0.7682) == "0,768" and rq05.fmt_p(float("nan")) == "—"


def _executar_sintetico(tmp_path):
    # poucos valores distintos de DF (empates) e um NaN em CFR (b): o gráfico não pode derrubar `executar`
    x = [0.1, 0.1, 0.1, 0.5, 0.5, 2.0, 2.0, 8.0]
    d = _df(x, [0.0, 0.1, 0.2, 0.1, 0.3, 0.2, 0.0, 0.4], [0.0, 0.0, None, 0.2, 0.3, 0.5, 0.6, 0.9],
            avaliadas=[4, 4, None, 12, 12, 25, 25, 90])
    csv_path = tmp_path / "m.csv"
    d.to_csv(csv_path, index=False)
    saida = tmp_path / "out"
    return rq05.executar(csv_path, saida), saida


def test_executar_gera_todas_as_saidas(tmp_path):
    r, saida = _executar_sintetico(tmp_path)
    esperados = {"rq05_spearman.csv", "rq05_sensibilidade_cfr_b.csv", "rq05_spearman.md",
                 "rq05_df_cfr_a.png", "rq05_df_cfr_b.png"}
    assert esperados <= {p.name for p in saida.iterdir()}
    t = pd.read_csv(saida / "rq05_spearman.csv")
    assert list(t["variante"]) == ["a", "b"] and list(t.columns) == rq05.COLUNAS
    assert list(t["n"]) == [8, 7]
    assert "RQ05" in (saida / "rq05_spearman.md").read_text(encoding="utf-8")


def test_executar_com_um_unico_valor_de_df_nao_quebra(tmp_path):
    d = _df([0.5] * 5, [0.1, 0.2, 0.3, 0.4, 0.5], [0.1, 0.2, 0.3, 0.4, 0.5])
    csv_path = tmp_path / "m.csv"
    d.to_csv(csv_path, index=False)
    r = rq05.executar(csv_path, tmp_path / "out")
    assert r["spearman"]["rho"].isna().all()


def test_colunas_geradas_estao_no_dicionario(tmp_path):
    _, saida = _executar_sintetico(tmp_path)
    documentadas: dict[str, set[str]] = {}
    with (RAIZ / "DICIONARIO_DE_DADOS.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            documentadas.setdefault(row["arquivo"].strip(), set()).add(row["coluna"].strip())
    for nome in ("rq05_spearman.csv", "rq05_sensibilidade_cfr_b.csv"):
        colunas = pd.read_csv(saida / nome, nrows=0).columns
        faltando = [c for c in colunas if c not in documentadas.get(nome, set())]
        assert not faltando, f"{nome}: colunas sem entrada no dicionário: {faltando}"


@pytest.mark.skipif(not (RAIZ / "data" / "metrics.csv").exists(), reason="data/metrics.csv ausente")
def test_trava_de_regressao_no_csv_real():
    t = rq05.tabela(pd.read_csv(RAIZ / "data" / "metrics.csv")).set_index("variante")
    assert (t.loc["a", "n"], t.loc["b", "n"]) == (300, 299)
    assert t.loc["b", "excluidos"] == "akveo/react-native-ui-kitten"
