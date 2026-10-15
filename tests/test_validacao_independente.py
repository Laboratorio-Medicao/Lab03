"""Testes do fluxo de validação independente (sorteio, pacote cego, avaliação de uso único)."""

from __future__ import annotations

import csv
import json
from datetime import date

import pytest

from scripts import validacao_independente as vi
from scripts.sample_gold import COLUNAS_PLANILHA, linhas_planilha


# --------------------------------------------------------------------------------------- sorteio

def test_elegiveis_exclui_usados_e_mesmo_dono_sem_diferenciar_caixa():
    candidatos = ["Org/a", "org/b", "Outro/c", "novo/d", "Novo/D", "solo/e"]
    quadro, c = vi.elegiveis(candidatos, ["ORG/a"], mesmo_dono=True)
    assert quadro == ["novo/d", "Outro/c", "solo/e"]
    assert "Org/a" not in quadro and "org/b" not in quadro  # mesmo dono de um usado
    assert c["excluidos_ja_usados"] == 1 and c["excluidos_mesmo_dono"] == 1
    assert c["candidatos_unicos"] == 5  # "novo/d" e "Novo/D" são o mesmo


def test_elegiveis_sem_regra_de_dono_so_remove_usados():
    quadro, c = vi.elegiveis(["org/a", "org/b"], ["org/a"], mesmo_dono=False)
    assert quadro == ["org/b"] and c["excluidos_mesmo_dono"] == 0


def test_sortear_repos_deterministico_e_ordenado():
    quadro = [f"o{i}/r" for i in range(50)]
    a = vi.sortear_repos(quadro, 10, 7342)
    assert a == vi.sortear_repos(list(reversed(quadro)), 10, 7342)
    assert a == sorted(a) and len(set(a)) == 10
    assert a != vi.sortear_repos(quadro, 10, 1)


def test_sortear_repos_quadro_pequeno_falha():
    with pytest.raises(vi.ValidacaoError):
        vi.sortear_repos(["a/b"], 2, 1)


def _csv(path, nomes):
    path.write_text("full_name\n" + "\n".join(nomes) + "\n", encoding="utf-8")


def test_cmd_sortear_sem_sobreposicao_e_uso_unico(tmp_path):
    _csv(tmp_path / "final.csv", [f"o{i}/r" for i in range(30)])
    _csv(tmp_path / "usados.csv", ["o0/r", "o1/r", "o2/r"])
    info = vi.cmd_sortear(tmp_path / "final.csv", tmp_path / "usados.csv", tmp_path / "out", 10, 5, True)
    assert not set(info["sorteados"]) & {"o0/r", "o1/r", "o2/r"}
    assert info["excluidos_ja_usados"] == 3 and info["n_repos"] == 10
    assert json.loads((tmp_path / "out/sorteio_repos.json").read_text())["seed"] == 5
    with pytest.raises(vi.ValidacaoError):
        vi.cmd_sortear(tmp_path / "final.csv", tmp_path / "usados.csv", tmp_path / "out", 10, 5, True)


# ------------------------------------------------------------------------------- métricas e bootstrap

def test_prf_exemplo_do_professor():
    y = [True] * 50 + [False] * 10
    p = [True] * 30 + [False] * 20 + [True] * 10
    m = vi.prf(y, p)
    assert (m["tp"], m["fp"], m["fn"]) == (30, 10, 20)
    assert m["precisao"] == pytest.approx(0.75) and m["recall"] == pytest.approx(0.60)
    assert m["f1"] == pytest.approx(2 * 0.75 * 0.6 / 1.35)


def test_prf_sem_positivos_previstos_nao_divide_por_zero():
    assert vi.prf([True, False], [False, False])["f1"] == 0.0


def test_bootstrap_por_repositorio_deterministico_e_contem_o_ponto():
    repos = [f"r{i}/x" for i in range(20) for _ in range(5)]
    y = [(i % 3 == 0) for i in range(100)]
    p = [(i % 3 == 0) != (i % 11 == 0) for i in range(100)]
    a = vi.bootstrap_por_repositorio(y, p, repos, b=500, seed=1)
    assert a == vi.bootstrap_por_repositorio(y, p, repos, b=500, seed=1)
    lo, hi = a["f1_ic95"]
    assert lo <= vi.prf(y, p)["f1"] <= hi and a["n_repositorios"] == 20


# ------------------------------------------------------------------------------------------ pacote

class _Resp:
    def __init__(self, corpo, headers=None, status=200):
        self._c, self.headers, self.status_code = corpo, headers or {}, status

    def json(self):
        return self._c


class _Api:
    """Duas releases de deploy por repositório + a primeira da história, com `body` e commits."""

    def get(self, path, params=None):
        if path.endswith("/releases"):
            return _Resp([
                {"id": 3, "tag_name": "v1.0.2", "draft": False, "prerelease": False,
                 "published_at": "2026-03-03T00:00:00Z", "created_at": "2026-03-03T00:00:00Z", "body": "patch release"},
                {"id": 2, "tag_name": "v1.0.1", "draft": False, "prerelease": False,
                 "published_at": "2026-02-02T00:00:00Z", "created_at": "2026-02-02T00:00:00Z", "body": "notes"},
                {"id": 1, "tag_name": "v1.0.0", "draft": False, "prerelease": False,
                 "published_at": "2026-01-01T00:00:00Z", "created_at": "2026-01-01T00:00:00Z", "body": None},
            ])
        commit = {"sha": "s", "parents": [{}], "commit": {"message": "fix: x", "author": {"date": "2026-01-02T00:00:00Z"},
                                                           "committer": {"date": "2026-01-02T00:00:00Z"}}}
        return _Resp({"total_commits": 1, "status": "ahead", "commits": [commit]})


def test_montar_pacote_exclui_primeira_da_historia_e_nao_executa_heuristica():
    linhas, congelado, avisos = vi.montar_pacote(["o/r"], _Api(), date(2025, 10, 2), date(2026, 10, 2))
    assert [l["tag_name"] for l in linhas] == ["v1.0.1", "v1.0.2"]  # v1.0.0 não tem anterior
    assert avisos and "só 2 releases" in avisos[0]
    assert set(congelado) == {"2", "3"} and congelado["3"]["body"] == "patch release"
    assert congelado["3"]["commits"][0]["message"] == "fix: x"
    texto = json.dumps(linhas) + json.dumps(congelado)
    assert "heuristic" not in texto and "v12" not in texto


def test_planilha_cega_nao_tem_previsao_nem_versao():
    assert not any("heur" in c or c.startswith("v1") or "pred" in c for c in COLUNAS_PLANILHA)
    assert not any(x in vi.PROTOCOLO.lower() for x in ("v12", "v10", "v1–", "heuristic_corrective"))


# --------------------------------------------------------------------------------------- avaliação

def _pacote_sintetico(tmp_path, consenso):
    """4 releases: previsões v12 conhecidas = [T, F, T, F]; `consenso` = rótulo de referência dos 4."""
    itens = [("1", "a/x", "1.0.1", "1.0.0", ["fix: crash"]), ("2", "a/x", "1.1.0", "1.0.1", ["feat: add y"]),
             ("3", "b/y", "2.0.1", "2.0.0", ["fix: bug"]), ("4", "b/y", "2.1.0", "2.0.1", ["docs: z"])]
    amostra = [{"full_name": f, "repo_url": f"https://github.com/{f}", "release_id": i, "tag_name": t,
                "published_at": "2026-02-01T00:00:00Z", "release_url": "u", "compare_url": f"c/{b}...{t}"}
               for i, f, t, b, _ in itens]
    vi._escrever_csv(tmp_path / "amostra_validacao.csv", vi.COLUNAS_AMOSTRA, amostra)
    congelado = {i: {"full_name": f, "tag_name": t, "base": b, "published_at": "2026-02-01T00:00:00Z", "status": "ok",
                     "truncado": False, "body": "", "commits": [{"sha": "s", "message": m, "n_parents": 1,
                                                                  "author_date": "2026-01-01T00:00:00Z"} for m in ms]}
                 for i, f, t, b, ms in itens}
    (tmp_path / "dados_congelados.json").write_text(json.dumps(congelado), encoding="utf-8")
    avaliadores = ["A", "B", "C"]
    for nome in avaliadores:
        linhas = linhas_planilha(amostra)
        vistos = set()
        for l, ((i, f, *_), y) in zip(linhas, zip(itens, consenso)):
            if f not in vistos:
                l["tipo_projeto"], l["releases_sao_entregas_reais"] = "biblioteca_framework", "sim"
                vistos.add(f)
            l["corretiva"] = "sim" if y else "nao"
        vi._escrever_csv(tmp_path / f"labels_{nome}.csv", vi.COLUNAS_PLANILHA, linhas)
    cong = {"versao_heuristica": "v12", "heuristica_sha256": vi._sha256(vi.ARQ_HEURISTICA),
            "dados_congelados_sha256": vi._sha256(tmp_path / "dados_congelados.json"),
            "amostra_sha256": vi._sha256(tmp_path / "amostra_validacao.csv"), "avaliadores": avaliadores}
    (tmp_path / "congelamento.json").write_text(json.dumps(cong), encoding="utf-8")


def test_avaliar_calcula_metricas_conhecidas_e_e_de_uso_unico(tmp_path):
    _pacote_sintetico(tmp_path, [True, False, False, True])  # pred [T,F,T,F] -> TP1 FP1 FN1 TN1
    r = vi.cmd_avaliar(tmp_path, b=200)
    assert (r["tp"], r["fp"], r["fn"], r["tn"]) == (1, 1, 1, 1)
    assert r["f1"] == pytest.approx(0.5) and r["meta_f1_070_atingida_no_ponto"] is False
    assert r["n_repositorios"] == 2 and r["intervalo_confianca"]["n_repositorios"] == 2
    with pytest.raises(vi.ValidacaoError, match="uso único"):
        vi.cmd_avaliar(tmp_path)


def test_avaliar_sem_rotulos_completos_nao_calcula_nada(tmp_path):
    _pacote_sintetico(tmp_path, [True, False, False, True])
    (tmp_path / "labels_C.csv").unlink()
    with pytest.raises(vi.ValidacaoError, match="nenhum F1"):
        vi.cmd_avaliar(tmp_path)
    assert not (tmp_path / "resultado_validacao.json").exists()


def test_avaliar_recusa_rotulo_em_branco(tmp_path):
    _pacote_sintetico(tmp_path, [True, False, False, True])
    arq = tmp_path / "labels_B.csv"
    linhas = list(csv.DictReader(arq.open(encoding="utf-8-sig")))
    linhas[2]["corretiva"] = ""
    vi._escrever_csv(arq, vi.COLUNAS_PLANILHA, linhas)
    with pytest.raises(vi.ValidacaoError, match="incompleta"):
        vi.cmd_avaliar(tmp_path)


def test_avaliar_recusa_heuristica_alterada_depois_do_congelamento(tmp_path):
    _pacote_sintetico(tmp_path, [True, False, False, True])
    cong = json.loads((tmp_path / "congelamento.json").read_text())
    cong["heuristica_sha256"] = "0" * 64
    (tmp_path / "congelamento.json").write_text(json.dumps(cong))
    with pytest.raises(vi.ValidacaoError, match="mudou depois do congelamento"):
        vi.cmd_avaliar(tmp_path)


def test_avaliar_recusa_dados_adulterados(tmp_path):
    _pacote_sintetico(tmp_path, [True, False, False, True])
    (tmp_path / "dados_congelados.json").write_text("{}", encoding="utf-8")
    with pytest.raises(vi.ValidacaoError, match="alterado depois do congelamento"):
        vi.cmd_avaliar(tmp_path)


# ------------------------------------------------------------------ cliente em camadas e falhas explícitas

def _grava_cache(dir_, path, params, corpo, status=200, headers=None):
    from pipeline.cache import _chave
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / f"{_chave(path, params)}.json").write_text(
        json.dumps({"status_code": status, "headers": headers or {}, "body": corpo}), encoding="utf-8")


def test_cliente_em_camadas_le_do_cache_de_leitura_sem_escrever_nele(tmp_path):
    leitura, novo = tmp_path / "producao", tmp_path / "novo"
    _grava_cache(leitura, "/repos/o/r/releases", {"per_page": 100}, [{"id": 1}])
    antes = sorted(p.name for p in leitura.iterdir())
    c = vi.ClienteEmCamadas(novo, [leitura])
    assert c.get("/repos/o/r/releases", {"per_page": 100}).json() == [{"id": 1}]
    assert c.contagem == {"leitura": 1, "cache_novo": 0, "api": 0}
    assert sorted(p.name for p in leitura.iterdir()) == antes  # nada escrito no cache de leitura
    with pytest.raises(vi.ValidacaoError):  # sem API e fora dos caches
        c.get("/repos/o/outro/releases", {"per_page": 100})


def test_cliente_em_camadas_grava_resposta_nova_so_no_cache_novo_e_conta_api(tmp_path):
    class Api:
        chamadas = 0

        def get(self, path, params=None):
            Api.chamadas += 1
            return _Resp([{"id": 9}], {})

    leitura, novo = tmp_path / "producao", tmp_path / "novo"
    leitura.mkdir()
    c = vi.ClienteEmCamadas(novo, [leitura], Api())
    c.get("/repos/o/r/releases", {"per_page": 100})
    c.get("/repos/o/r/releases", {"per_page": 100})  # segunda vez: cache novo, sem API
    assert Api.chamadas == 1 and c.contagem == {"leitura": 0, "cache_novo": 1, "api": 1}
    assert len(list(novo.glob("*.json"))) == 1 and not list(leitura.iterdir())
    assert c.por_repo["o/r"]["api"] == 1


def test_pacote_registra_repositorio_com_falha_sem_substitui_lo():
    from pipeline.selection import ApiError

    class Api2(_Api):
        def get(self, path, params=None):
            if "/ruim/" in path:
                return _Resp({}, {}, 404)
            return super().get(path, params)

    falhas: list = []
    linhas, congelado, _ = vi.montar_pacote(["bom/r", "ruim/r"], Api2(), date(2025, 10, 2), date(2026, 10, 2), falhas=falhas)
    assert {l["full_name"] for l in linhas} == {"bom/r"}
    assert [f["full_name"] for f in falhas] == ["ruim/r"] and "ApiError" in falhas[0]["motivo"]
    with pytest.raises(ApiError):
        vi.montar_pacote(["ruim/r"], Api2(), date(2025, 10, 2), date(2026, 10, 2))
