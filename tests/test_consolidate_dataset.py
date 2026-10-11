"""Testes de pipeline.consolidate_dataset (Issue #19)."""

import csv

import pytest

from pipeline.consolidate_dataset import consolidar


COLUNAS = [
    "full_name", "status", "erro", "stars",
    "n_episodios", "n_episodios_censurados", "n_releases_ignored_404",
    "cfr_a", "dora_geral",
]


def _csv(tmp_path, rows):
    p = tmp_path / "resultados.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return p


def _row(full_name="org/repo", status="concluido", erro="",
         stars=1000, n_episodios=2, n_censurados=0, n_404=0, cfr=0.1, dora="Elite"):
    return {
        "full_name": full_name,
        "status": status,
        "erro": erro,
        "stars": stars,
        "n_episodios": n_episodios,
        "n_episodios_censurados": n_censurados,
        "n_releases_ignored_404": n_404,
        "cfr_a": cfr,
        "dora_geral": dora,
    }


# ---- filtragem ----

def test_apenas_concluidos_vao_pro_final(tmp_path):
    src = _csv(tmp_path, [
        _row("a/a", status="concluido"),
        _row("b/b", status="erro"),
    ])
    out = tmp_path / "repos_final.csv"
    m = consolidar(src, out)
    rows = list(csv.DictReader(out.open()))
    assert [r["full_name"] for r in rows] == ["a/a"]
    assert m["n_concluidos"] == 1
    assert m["n_erros"] == 1


def test_sem_concluidos_nao_cria_arquivo(tmp_path):
    src = _csv(tmp_path, [_row("a/a", status="erro")])
    out = tmp_path / "repos_final.csv"
    consolidar(src, out)
    assert not out.exists()


def test_todos_concluidos_preserva_ordem(tmp_path):
    src = _csv(tmp_path, [_row(f"org/r{i}") for i in range(5)])
    out = tmp_path / "repos_final.csv"
    consolidar(src, out)
    names = [r["full_name"] for r in csv.DictReader(out.open())]
    assert names == [f"org/r{i}" for i in range(5)]


# ---- colunas internas removidas ----

def test_status_e_erro_nao_aparecem_no_final(tmp_path):
    src = _csv(tmp_path, [_row()])
    out = tmp_path / "repos_final.csv"
    consolidar(src, out)
    fieldnames = list(csv.DictReader(out.open()).fieldnames or [])
    assert "status" not in fieldnames
    assert "erro" not in fieldnames


def test_colunas_metricas_preservadas(tmp_path):
    src = _csv(tmp_path, [_row(cfr=0.25, dora="High")])
    out = tmp_path / "repos_final.csv"
    consolidar(src, out)
    row = next(csv.DictReader(out.open()))
    assert row["cfr_a"] == "0.25"
    assert row["dora_geral"] == "High"


# ---- contagens de censura e 404 ----

def test_soma_episodios_censurados(tmp_path):
    src = _csv(tmp_path, [
        _row("a/a", n_censurados=3, n_episodios=5),
        _row("b/b", n_censurados=1, n_episodios=2),
        _row("c/c", status="erro", n_censurados=99),  # não entra
    ])
    out = tmp_path / "repos_final.csv"
    m = consolidar(src, out)
    assert m["n_episodios_censurados"] == 4
    assert m["n_episodios"] == 7


def test_soma_releases_ignored_404(tmp_path):
    src = _csv(tmp_path, [
        _row("a/a", n_404=2),
        _row("b/b", n_404=0),
        _row("c/c", n_404=5),
    ])
    out = tmp_path / "repos_final.csv"
    m = consolidar(src, out)
    assert m["n_releases_ignored_404"] == 7


def test_campo_vazio_nao_quebra_soma(tmp_path):
    src = _csv(tmp_path, [_row(n_censurados=2), _row(n_censurados=0)])
    src.write_text(
        src.read_text().replace(",2,", ",,", 1)  # zera primeiro n_episodios_censurados
    )
    out = tmp_path / "repos_final.csv"
    m = consolidar(src, out)  # não deve lançar exceção
    assert m["n_episodios_censurados"] >= 0


# ---- métricas do funil ----

def test_metricas_retornadas_completas(tmp_path):
    src = _csv(tmp_path, [_row(), _row("b/b", status="erro")])
    out = tmp_path / "repos_final.csv"
    m = consolidar(src, out)
    assert set(m) >= {"n_total", "n_concluidos", "n_erros",
                      "n_episodios_censurados", "n_episodios", "n_releases_ignored_404"}
    assert m["n_total"] == 2


def test_csv_vazio_nao_cria_arquivo_e_retorna_zeros(tmp_path):
    src = tmp_path / "vazio.csv"
    src.write_text("full_name,status,erro\n", encoding="utf-8")
    out = tmp_path / "repos_final.csv"
    m = consolidar(src, out)
    assert m["n_total"] == 0
    assert m["n_concluidos"] == 0
    assert not out.exists()
