"""Testes de scripts.sample_gold (Issue #22) — sorteio reproduzível e planilhas de rotulagem."""

import csv
import json
from datetime import date

import pytest

from pipeline.collect_releases import arquivo_cache
from scripts import sample_gold as sg

INI = date(2025, 1, 1)
FIM = date(2025, 12, 31)


def _releases(n, prerelease_em=()):
    return [
        {
            "id": 1000 + i,
            "tag_name": f"v1.{i}.0",
            "draft": False,
            "prerelease": i in prerelease_em,
            "published_at": f"2025-{i + 1:02d}-10T12:00:00Z",
            "created_at": f"2025-{i + 1:02d}-10T11:00:00Z",
            "html_url": f"https://github.com/o/r/releases/tag/v1.{i}.0",
        }
        for i in range(n)
    ]


def _cache(tmp_path, nomes, n_releases=8):
    cache = tmp_path / "cache"
    for k, nome in enumerate(nomes):
        arq = arquivo_cache(cache, nome)
        arq.parent.mkdir(parents=True, exist_ok=True)
        rels = [{**r, "id": r["id"] + 1000 * (k + 1)} for r in _releases(n_releases)]  # ids únicos, como no GitHub
        arq.write_text(json.dumps({"full_name": nome, "releases": rels}), encoding="utf-8")
    return cache


def _csv_repos(tmp_path, nomes, nome="repos.csv"):
    arq = tmp_path / nome
    with arq.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["full_name", "status"])
        for n in nomes:
            w.writerow([n, "concluido"])
    return arq


NOMES = [f"org{i:02d}/repo{i:02d}" for i in range(80)]


def test_sortear_repos_e_reproduzivel_e_independe_da_ordem():
    a = sg.sortear_repos(NOMES)
    b = sg.sortear_repos(list(reversed(NOMES)) + NOMES[:5])  # outra ordem + duplicatas
    assert a == b
    assert len(a) == sg.N_REPOS == len(set(a))
    assert set(a) <= set(NOMES)


def test_sortear_repos_muda_com_outra_semente():
    assert sg.sortear_repos(NOMES, seed=1) != sg.sortear_repos(NOMES, seed=2)


def test_sortear_repos_lista_pequena_e_erro():
    with pytest.raises(ValueError, match="60"):
        sg.sortear_repos(NOMES[:10])


def test_sortear_releases_cinco_distintas_na_janela_e_cronologicas():
    rels = _releases(12, prerelease_em=(3,))
    pares = sg.sortear_releases(rels, INI, FIM, "o/r")
    ids = [r["id"] for _, r in pares]
    assert len(ids) == 5 == len(set(ids))
    assert 1003 not in ids  # pré-release não é deploy
    datas = [r["published_at"] for _, r in pares]
    assert datas == sorted(datas)
    assert pares == sg.sortear_releases(list(reversed(rels)), INI, FIM, "o/r")


def test_sortear_releases_ignora_fora_da_janela():
    rels = _releases(12)
    pares = sg.sortear_releases(rels, date(2025, 6, 1), FIM, "o/r", n=50)
    assert all(r["published_at"] >= "2025-06-01" for _, r in pares)
    # a anterior da 1ª da janela está fora dela (necessária para o compare)
    assert pares[0][0]["published_at"] < "2025-06-01"


def test_sortear_releases_menos_que_n_devolve_todas():
    assert len(sg.sortear_releases(_releases(3), INI, FIM, "o/r")) == 3


def test_gerar_planilhas_identicas_nas_releases_e_sem_heuristica(tmp_path):
    cache = _cache(tmp_path, NOMES)
    saida = tmp_path / "ouro"
    amostra = sg.gerar(_csv_repos(tmp_path, NOMES), cache, INI, FIM, saida)

    assert len(amostra) == 60 * 5
    assert len({a["full_name"] for a in amostra}) == 60

    conteudos = {}
    for nome in sg.AVALIADORES_PADRAO:
        with (saida / f"labels_{nome}.csv").open(encoding="utf-8-sig", newline="") as f:
            leitor = csv.DictReader(f)
            assert tuple(leitor.fieldnames) == sg.COLUNAS_PLANILHA
            conteudos[nome] = list(leitor)
    ids = {n: [r["release_id"] for r in linhas] for n, linhas in conteudos.items()}
    assert ids["A"] == ids["B"] == ids["C"] == [str(a["release_id"]) for a in amostra]
    for linha in conteudos["A"]:
        assert linha["tipo_projeto"] == linha["corretiva"] == linha["releases_sao_entregas_reais"] == ""
        assert linha["release_url"].startswith("https://github.com/")
    assert not {"heuristica", "dora_geral", "stars"} & set(sg.COLUNAS_PLANILHA)


def test_gerar_e_deterministico_byte_a_byte(tmp_path):
    cache = _cache(tmp_path, NOMES)
    repos = _csv_repos(tmp_path, NOMES)
    sg.gerar(repos, cache, INI, FIM, tmp_path / "um")
    sg.gerar(repos, cache, INI, FIM, tmp_path / "dois")
    for arq in (tmp_path / "um").iterdir():
        assert arq.read_bytes() == (tmp_path / "dois" / arq.name).read_bytes()
    meta = json.loads((tmp_path / "um" / "sorteio.json").read_text(encoding="utf-8"))
    assert meta["seed"] == 42 and len(meta["lista_entrada_sha256"]) == 64


def test_compare_url_vazia_so_na_primeira_da_historia(tmp_path):
    nomes = NOMES[:3]
    cache = _cache(tmp_path, nomes, n_releases=5)
    amostra = sg.montar_amostra(nomes, cache, INI, FIM)
    primeira = [a for a in amostra if a["tag_name"] == "v1.0.0"]
    assert primeira and all(a["compare_url"] == "" for a in primeira)
    outras = [a for a in amostra if a["tag_name"] == "v1.3.0"]
    assert outras[0]["compare_url"].endswith("/compare/v1.2.0...v1.3.0")


def test_cache_ausente_da_erro_claro(tmp_path):
    with pytest.raises(FileNotFoundError, match="pipeline"):
        sg.montar_amostra(["o/r"], tmp_path / "cache", INI, FIM)


def test_ler_repos_filtra_status_e_exige_full_name(tmp_path):
    arq = tmp_path / "r.csv"
    arq.write_text("full_name,status\na/b,concluido\nc/d,erro\na/b,concluido\n", encoding="utf-8")
    assert sg.ler_repos(arq) == ["a/b"]
    ruim = tmp_path / "x.csv"
    ruim.write_text("nome\na/b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="full_name"):
        sg.ler_repos(ruim)


def test_ler_repos_sem_coluna_status_aceita_tudo(tmp_path):
    arq = tmp_path / "r.csv"
    arq.write_text("full_name\nb/b\na/a\n", encoding="utf-8")
    assert sg.ler_repos(arq) == ["a/a", "b/b"]


def test_recusa_sobrescrever_planilha_preenchida(tmp_path):
    cache = _cache(tmp_path, NOMES)
    repos = _csv_repos(tmp_path, NOMES)
    saida = tmp_path / "ouro"
    sg.gerar(repos, cache, INI, FIM, saida)
    assert sg.planilhas_preenchidas(saida) == []
    sg.gerar(repos, cache, INI, FIM, saida)  # em branco: pode regerar

    planilha = saida / "labels_A.csv"
    planilha.write_text(planilha.read_text(encoding="utf-8-sig").replace(",,,", ",outro,sim,", 1),
                        encoding="utf-8-sig")
    assert sg.planilhas_preenchidas(saida) == [planilha]
    with pytest.raises(ValueError, match="--forcar"):
        sg.gerar(repos, cache, INI, FIM, saida)
    sg.gerar(repos, cache, INI, FIM, saida, forcar=True)
    assert sg.planilhas_preenchidas(saida) == []


def test_lista_padrao_prefere_repos_final(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert sg._lista_padrao(tmp_path / "outputs") == tmp_path / "outputs" / "resultados.csv"
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "repos_final.csv").write_text("full_name\n", encoding="utf-8")
    assert sg._lista_padrao(tmp_path / "outputs") == sg.LISTA_FINAL
