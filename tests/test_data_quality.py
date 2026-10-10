"""Testes de scripts.data_quality (Issue #29) — invariantes e relatório de qualidade."""

import csv
import json

import pytest

from scripts import data_quality as dq


def _repo(nome="a/b", **kw):
    base = {
        "full_name": nome, "language": "Python", "cfr_a": "0.1", "lt_release_median_h": "5",
        "lt_commit_median_h": "2", "n_releases_avaliadas": "3", "n_sem_anterior": "1",
        "n_releases_ignored_404": "1", "n_sem_commits_novos": "0", "n_episodios": "4",
        "n_episodios_censurados": "1", "n_commits_negativos": "0", "n_runs_dias_saturados": "0",
    }
    base.update(kw)
    return base


def _status(linhas, trecho):
    achadas = [l for l in linhas if trecho in l["verificacao"]]
    assert len(achadas) == 1, trecho
    return achadas[0]["status"]


def test_cfr_fora_da_faixa_falha():
    r = dq.inv_faixa([_repo("a/b", cfr_a="1.2"), _repo("c/d", cfr_a="-0.1"), _repo("e/f")], "cfr_a", 0, 1, "n")
    assert r["status"] == "FALHA" and r["valor"] == 2 and "a/b" in r["detalhe"]


def test_cfr_nos_limites_passa_e_vazio_e_ignorado():
    r = dq.inv_faixa([_repo(cfr_a="0"), _repo("c/d", cfr_a="1"), _repo("e/f", cfr_a="")], "cfr_a", 0, 1, "n")
    assert r["status"] == "OK"


def test_coluna_ausente_e_na():
    assert dq.inv_faixa([_repo()], "cfr_b", 0, 1, "n")["status"] == "N/A"


def test_lead_time_negativo_falha():
    r = dq.inv_faixa([_repo(lt_release_median_h="-0.5")], "lt_release_median_h", 0, None, "n")
    assert r["status"] == "FALHA"


def test_particao_do_lead_time():
    funil = {"a/b": {"full_name": "a/b", "n_releases_window": "5"}}
    assert dq.inv_particao_lead_time([_repo()], funil)["status"] == "OK"  # 3+1+1+0 = 5
    funil["a/b"]["n_releases_window"] = "6"
    r = dq.inv_particao_lead_time([_repo()], funil)
    assert r["status"] == "FALHA" and "5 != 6" in r["detalhe"]
    assert dq.inv_particao_lead_time([_repo()], {})["status"] == "N/A"


def test_particao_cfr_b_quando_colunas_existem():
    ok = _repo(n_releases_avaliadas_cfr_b="8", n_releases_censuradas_cfr_b="2", n_releases_janela="10")
    ruim = _repo("c/d", n_releases_avaliadas_cfr_b="8", n_releases_censuradas_cfr_b="1", n_releases_janela="10")
    assert dq.inv_particao_cfr_b([ok])["status"] == "OK"
    assert dq.inv_particao_cfr_b([ok, ruim])["status"] == "FALHA"
    assert dq.inv_particao_cfr_b([_repo()])["status"] == "N/A"


def test_dicionario():
    linhas = [_repo()]
    todas = set(linhas[0])
    assert dq.inv_dicionario(linhas, todas)["status"] == "OK"
    r = dq.inv_dicionario(linhas, todas - {"cfr_a"})
    assert r["status"] == "FALHA" and "cfr_a" in r["detalhe"]
    assert dq.inv_dicionario(linhas, None)["status"] == "N/A"


def test_funil_somas():
    tabela = [
        {"etapa": "0. x", "entram": 10, "saem": None, "restam": 10},
        {"etapa": "1. y", "entram": 10, "saem": 4, "restam": 6},
    ]
    funil = [{"full_name": "a/b", "status": "selecionado", "motivo": ""},
             {"full_name": "c/d", "status": "descartado", "motivo": "lt_5_releases"}]
    assert all(r["status"] == "OK" for r in dq.inv_funil(funil, [_repo("a/b")], tabela))

    tabela[1]["restam"] = 7
    assert dq.inv_funil(funil, [_repo("a/b")], tabela)[0]["status"] == "FALHA"

    r = dq.inv_funil(funil, [_repo("a/b"), _repo("x/y")], None)
    assert r[-1]["status"] == "FALHA" and "só no dataset: x/y" in r[-1]["detalhe"]

    funil[1]["motivo"] = ""
    assert dq.inv_funil(funil, [_repo("a/b")], None)[1]["status"] == "FALHA"  # descartado sem motivo


def test_duplicatas_sem_diferenciar_caixa():
    r = dq.rel_duplicatas([_repo("Org/Repo"), _repo("org/repo"), _repo("x/y")])
    assert r[0]["status"] == "FALHA" and r[0]["valor"] == 1


def test_nulos_ignoram_coluna_erro():
    linhas = [_repo(erro="", language=""), _repo("c/d", erro="", language="Go")]
    nomes = [l["verificacao"] for l in dq.rel_nulos(linhas)]
    assert nomes == ["language"]


def test_censura_404_e_linguagem():
    linhas = [_repo(), _repo("c/d", language="", n_releases_ignored_404="0", n_episodios_censurados="0")]
    rel = {l["verificacao"]: l for l in dq.rel_censura_e_404(linhas)}
    assert rel["episódios de falha censurados (RQ04)"]["valor"] == 1
    assert rel["releases ignoradas por 404 no compare"]["valor"] == 1
    ling = {l["verificacao"]: l["valor"] for l in dq.rel_linguagem(linhas)}
    assert ling == {"Python": 1, "(sem linguagem)": 1}


def test_dias_saturados_geram_alerta():
    rel = dq.rel_censura_e_404([_repo(n_runs_dias_saturados="2")])
    assert [l for l in rel if "saturados" in l["verificacao"]][0]["status"] == "ALERTA"


def test_datas_no_cache(tmp_path):
    d = tmp_path / "commits"
    d.mkdir()
    (d / "a__b.json").write_text(json.dumps({"comparacoes": {"v1...v2": {"commits": [
        {"author_date": "2025-05-01T00:00:00Z"}, {"author_date": None}, {"author_date": "lixo"},
        {"author_date": "2030-01-01T00:00:00Z"},
    ]}}}), encoding="utf-8")
    from datetime import date
    rel = dq.rel_datas_cache(d, date(2026, 1, 1))
    assert rel[0]["valor"] == 2 and rel[0]["status"] == "ALERTA"
    assert rel[1]["valor"] == 1
    assert dq.rel_datas_cache(tmp_path / "nao_existe") == []


def test_ler_funil_md(tmp_path):
    md = tmp_path / "funil.md"
    md.write_text(
        "| Etapa | Entram | Saem | Restam |\n|---|---:|---:|---:|\n"
        "| 0. Candidatos | 891 | — | 891 |\n| 1. Possui Actions | 891 | 446 | 445 |\n"
        "| Amostra final | 100 | — | 100 |\n", encoding="utf-8")
    t = dq.ler_funil_md(md)
    assert t == [{"etapa": "0. Candidatos", "entram": 891, "saem": None, "restam": 891},
                 {"etapa": "1. Possui Actions", "entram": 891, "saem": 446, "restam": 445}]
    assert dq.ler_funil_md(tmp_path / "x.md") is None


def test_ler_dicionario_csv_e_md(tmp_path):
    c = tmp_path / "d.csv"
    c.write_text("coluna,tipo\nfull_name,str\ncfr_a,float\n", encoding="utf-8")
    assert dq.ler_dicionario(c) == {"full_name", "cfr_a"}
    m = tmp_path / "d.md"
    m.write_text("| Coluna | Tipo |\n|---|---|\n| `full_name` | str |\n| cfr_a | float |\n", encoding="utf-8")
    assert {"full_name", "cfr_a"} <= dq.ler_dicionario(m)
    assert dq.ler_dicionario(None) is None


def test_verificar_dataset_vazio_falha():
    assert any(l["status"] == "FALHA" for l in dq.verificar([]))


# --- ponta a ponta ----------------------------------------------------------------------------

CONFIG = "janela:\n  inicio: 2025-01-01\n  fim: 2025-12-31\ncaminhos:\n  cache: {cache}\n  saidas: {saidas}\n"


def _montar(tmp_path, cfr_a="0.1"):
    saidas = tmp_path / "out"
    saidas.mkdir()
    (tmp_path / "config.yaml").write_text(CONFIG.format(cache=tmp_path / "cache", saidas=saidas), encoding="utf-8")
    linhas = [_repo("a/b", cfr_a=cfr_a), _repo("c/d")]
    with (saidas / "resultados.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    with (saidas / "funil.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["full_name", "status", "motivo", "n_releases_window"])
        w.writerows([["a/b", "selecionado", "", 5], ["c/d", "selecionado", "", 5], ["e/f", "descartado", "no_actions", ""]])
    return tmp_path / "config.yaml", saidas


def test_main_ok_gera_csv_e_md(tmp_path):
    config, saidas = _montar(tmp_path)
    assert dq.main(["--config", str(config)]) == 0
    with (saidas / "data_quality.csv").open(encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    assert tuple(linhas[0]) == dq.COLUNAS_SAIDA
    assert not [l for l in linhas if l["status"] == "FALHA"]
    texto = (saidas / "data_quality.md").read_text(encoding="utf-8")
    assert texto.startswith("# Qualidade dos dados") and "## Invariantes" in texto


def test_main_sai_1_com_invariante_violada(tmp_path, capsys):
    config, _ = _montar(tmp_path, cfr_a="1.5")
    assert dq.main(["--config", str(config)]) == 1
    assert "FALHA" in capsys.readouterr().err


def test_main_arquivo_ausente(tmp_path, capsys):
    config, saidas = _montar(tmp_path)
    (saidas / "resultados.csv").unlink()
    assert dq.main(["--config", str(config)]) == 1
