"""Testes de scripts.analise_erros_heuristica (Issue #30) — taxonomia, matriz, comparação e anotações.

Fixtures fictícias, feitas à mão: nenhum repositório ou tag da amostra-ouro real. Os insumos da #28 são
gerados com as próprias funções de scripts.evaluate_heuristic.
"""

import csv

import pytest

from metricas.heuristica import VERSOES, corretiva
from scripts import analise_erros_heuristica as ae
from scripts import evaluate_heuristic as ev

SIM_NAO = {True: "sim", False: "nao", None: ""}


NOTAS_VAZIAS = {"nota_correcao": False, "nota_novidade": False}  # v9 exige sinais de notas presentes


def linha(rid, patch, estrita, ampla, status="ok", incompletas=False, full_name="org/lib"):
    sinais = {"semver_patch": patch, "palavra_chave": estrita, "palavra_chave_ampla": ampla}
    return {
        "release_id": str(rid), "full_name": full_name, "tag_name": f"v1.0.{rid}", "base": "v1.0.0",
        "status": status, "mensagens_incompletas": SIM_NAO[incompletas],
        **{k: SIM_NAO[v] for k, v in sinais.items()},
        **{v: SIM_NAO[corretiva({**sinais, **NOTAS_VAZIAS}, v)] for v in VERSOES},
    }


# ---- taxonomia: FP ----


@pytest.mark.parametrize("versao, sinais, esperada", [
    ("v1", (None, True, True), "palavra_sem_semver"),
    ("v1", (True, True, True), "patch_e_palavra_sem_correcao"),
    ("v4", (True, False, True), "patch_sem_palavra"),       # v4 não olha palavra; usa a estrita da versão
    ("v2", (True, False, False), "patch_sem_palavra"),
    ("v2", (False, True, True), "palavra_sem_patch"),
    ("v7", (False, False, True), "palavra_sem_patch"),      # v7 usa a palavra ampla
])
def test_causa_fp(versao, sinais, esperada):
    assert ae.causa(linha(1, *sinais), versao, "FP") == esperada


# ---- taxonomia: FN (precedência e contrafactuais) ----


@pytest.mark.parametrize("versao, kwargs, esperada", [
    ("v1", dict(patch=None, estrita=False, ampla=False, status="sem_anterior"), "sem_release_anterior"),
    ("v1", dict(patch=True, estrita=False, ampla=False, status="404", incompletas=True), "commits_indisponiveis"),
    ("v4", dict(patch=False, estrita=False, ampla=False, status="404", incompletas=True), "sem_sinal"),
    ("v4", dict(patch=None, estrita=False, ampla=False, status="404", incompletas=True), "commits_indisponiveis"),
    ("v1", dict(patch=True, estrita=False, ampla=True), "palavra_ampla_nao_estrita"),
    ("v1", dict(patch=False, estrita=False, ampla=True), "palavra_sem_patch"),  # ampliar não resolveria
    ("v1", dict(patch=False, estrita=True, ampla=True), "palavra_sem_patch"),
    ("v4", dict(patch=False, estrita=False, ampla=True), "palavra_sem_patch"),
    ("v4", dict(patch=False, estrita=False, ampla=False), "sem_sinal"),
    ("v2", dict(patch=False, estrita=False, ampla=True), "palavra_ampla_nao_estrita"),
    ("v1", dict(patch=True, estrita=False, ampla=False), "patch_sem_palavra"),
    ("v3", dict(patch=True, estrita=False, ampla=False), "patch_sem_palavra"),
    ("v1", dict(patch=None, estrita=False, ampla=False), "nao_semver_sem_palavra"),
    ("v5", dict(patch=None, estrita=False, ampla=False), "nao_semver_sem_palavra"),
    ("v1", dict(patch=False, estrita=False, ampla=False), "sem_sinal"),
])
def test_causa_fn(versao, kwargs, esperada):
    assert ae.causa(linha(1, **kwargs), versao, "FN") == esperada


def test_causa_versao_fora_do_mapa():
    with pytest.raises(ev.AvaliacaoError, match="PALAVRA_DA_VERSAO"):
        ae.causa(linha(1, True, True, True), "v99", "FP")


def test_mapa_cobre_todas_as_versoes():
    assert set(ae.PALAVRA_DA_VERSAO) | set(ae.VERSOES_DE_CONTEUDO) == set(VERSOES)


# ---- fixture: pasta com os insumos da #28 ----

# release_id -> (sinais, consenso)
CASOS = {
    "1": ((True, True, True), 1),      # TP na v1
    "2": ((True, True, True), 0),      # FP na v1: patch e palavra sem correção
    "3": ((True, False, True), 1),     # FN na v1: palavra ampla, não estrita (v5 acerta)
    "4": ((False, False, False), 0),   # TN
    "5": ((False, True, True), 1),     # FN na v1: palavra sem patch (v2 acerta)
}


def _escrever(caminho, colunas, linhas):
    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(colunas), lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


@pytest.fixture
def amostra_dir(tmp_path):
    d = tmp_path / "amostra_ouro"
    d.mkdir()
    linhas = [linha(rid, *sinais) for rid, (sinais, _) in CASOS.items()]
    consenso = {rid: c for rid, (_, c) in CASOS.items()}
    _escrever(d / ev.ARQ_HEURISTICA, ev.COLUNAS_HEURISTICA, linhas)
    _escrever(d / ev.ARQ_AVALIACAO, ev.COLUNAS_AVALIACAO, ev.avaliar_versoes(linhas, consenso))
    _escrever(d / "consenso.csv", ["dimensao", "item_id", "rotulo_consenso", "metodo"],
              [{"dimensao": "corretiva", "item_id": rid, "rotulo_consenso": "sim" if c else "nao", "metodo": "maioria"}
               for rid, c in consenso.items()])
    _escrever(d / "amostra_ouro.csv", ["release_id", "release_url", "compare_url"],
              [{"release_id": rid, "release_url": f"https://x/r/{rid}", "compare_url": f"https://x/c/{rid}"}
               for rid in CASOS])
    return d


def _ler(caminho):
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---- matriz, lista de erros e comparação ----


def test_executar_versao_v1(amostra_dir):
    r = ae.executar(amostra_dir, "v1")
    assert r["matriz"] == {"tp": 1, "fp": 1, "fn": 2, "tn": 1}
    erros = _ler(amostra_dir / ae.ARQ_ERROS)
    assert list(erros[0]) == list(ae.COLUNAS_ERROS)
    assert [(e["release_id"], e["tipo_erro"], e["causa_automatica"]) for e in erros] == [
        ("2", "FP", "patch_e_palavra_sem_correcao"),
        ("3", "FN", "palavra_ampla_nao_estrita"),
        ("5", "FN", "palavra_sem_patch"),
    ]
    assert erros[0]["release_url"] == "https://x/r/2" and erros[0]["causa_manual"] == ""


def test_comparar_versoes_corrige_e_piora(amostra_dir):
    linhas = _ler(amostra_dir / ev.ARQ_HEURISTICA)
    consenso = ev.consenso_corretiva(amostra_dir / "consenso.csv")
    comp = {c["versao"]: c for c in ae.comparar_versoes(linhas, consenso, "v1", _ler(amostra_dir / ev.ARQ_AVALIACAO))}
    assert (comp["v1"]["corrige"], comp["v1"]["piora"]) == (0, 0)
    assert (comp["v5"]["corrige"], comp["v5"]["piora"]) == (1, 0)   # acerta a release 3
    assert (comp["v2"]["corrige"], comp["v2"]["piora"]) == (2, 0)   # acerta 3 e 5
    assert comp["v2"]["f1"] == _ler(amostra_dir / ev.ARQ_AVALIACAO)[1]["f1"]  # lido da avaliação


def test_versao_padrao_e_a_escolhida(amostra_dir):
    escolhida = next(a["versao"] for a in _ler(amostra_dir / ev.ARQ_AVALIACAO) if a["escolhida"] == "sim")
    assert ae.executar(amostra_dir)["versao"] == escolhida


def test_versao_inexistente(amostra_dir):
    with pytest.raises(ev.AvaliacaoError, match="v99"):
        ae.executar(amostra_dir, "v99")


def test_insumo_ausente_sem_ler_rotulos(amostra_dir):
    (amostra_dir / ev.ARQ_AVALIACAO).unlink()
    (amostra_dir / "labels_x.csv").write_bytes(b"\xff\xfe nao e csv")  # nunca deve ser lido
    with pytest.raises(ev.AvaliacaoError, match="scripts.evaluate_heuristic"):
        ae.executar(amostra_dir)
    assert not (amostra_dir / ae.ARQ_ERROS).exists()


def test_matriz_divergente_da_avaliacao(amostra_dir):
    avaliacao = _ler(amostra_dir / ev.ARQ_AVALIACAO)
    avaliacao[0]["tp"] = "99"
    _escrever(amostra_dir / ev.ARQ_AVALIACAO, ev.COLUNAS_AVALIACAO, avaliacao)
    with pytest.raises(ev.AvaliacaoError, match="rodadas diferentes"):
        ae.executar(amostra_dir, "v1")


def test_releases_desalinhadas_com_consenso(amostra_dir):
    linhas = _ler(amostra_dir / ev.ARQ_HEURISTICA)[:-1]
    _escrever(amostra_dir / ev.ARQ_HEURISTICA, ev.COLUNAS_HEURISTICA, linhas)
    with pytest.raises(ev.AvaliacaoError, match="diferem"):
        ae.executar(amostra_dir, "v1")


# ---- anotações manuais ----


def test_anotacoes_preservadas_por_release_ao_trocar_versao(amostra_dir):
    ae.executar(amostra_dir, "v1")
    erros = _ler(amostra_dir / ae.ARQ_ERROS)
    for e in erros:
        e["causa_manual"] = {"2": "fix em docs", "3": "fixes no corpo do PR"}.get(e["release_id"], "")
    _escrever(amostra_dir / ae.ARQ_ERROS, ae.COLUNAS_ERROS, erros)

    r = ae.executar(amostra_dir, "v5")  # v5 acerta a release 3: a anotação dela sai do CSV
    por_id = {e["release_id"]: e for e in _ler(amostra_dir / ae.ARQ_ERROS)}
    assert por_id["2"]["causa_manual"] == "fix em docs" and por_id["2"]["versao"] == "v5"
    assert "3" not in por_id
    assert r["descartadas"] == 1


def test_main_imprime_aviso_de_descarte(amostra_dir, capsys):
    ae.executar(amostra_dir, "v1")
    erros = _ler(amostra_dir / ae.ARQ_ERROS)
    erros[1]["causa_manual"] = "anotada"  # release 3
    _escrever(amostra_dir / ae.ARQ_ERROS, ae.COLUNAS_ERROS, erros)
    assert ae.main(["--amostra-dir", str(amostra_dir), "--versao", "v2"]) == 0
    saida = capsys.readouterr().out
    assert "TP=3" in saida and "aviso: 1 anotação" in saida


def test_main_erro_de_insumo(tmp_path, capsys):
    assert ae.main(["--amostra-dir", str(tmp_path)]) == 1
    assert "insumos ausentes" in capsys.readouterr().err


# ---- relatório ----


def test_relatorio(amostra_dir):
    ae.executar(amostra_dir, "v1")
    md = (amostra_dir / ae.ARQ_RELATORIO).read_text(encoding="utf-8")
    assert "| **Heurística: corretiva** | 1 (TP) | 1 (FP) |" in md
    assert "| FN | `palavra_ampla_nao_estrita` | 1 |" in md
    assert "| v5 |" in md and "Ameaças à validade" in md
    assert "1 das 2 releases marcadas como corretivas são falsos positivos (50%)" in md
    assert "[org/lib v1.0.2](https://x/r/2)" in md


# ---- versões não avaliáveis em algumas releases (v9 sem notas) ----


def test_linhas_nao_avaliaveis_ficam_fora_da_matriz_e_da_comparacao(amostra_dir):
    linhas = _ler(amostra_dir / ev.ARQ_HEURISTICA)
    for l in linhas:
        if l["release_id"] == "3":
            l["v9"] = ""  # sem release notes
    consenso = ev.consenso_corretiva(amostra_dir / "consenso.csv")
    m = ae.matriz(linhas, consenso, "v9")
    assert sum(m.values()) == len(linhas) - 1
    assert all(e["release_id"] != "3" for e in ae.listar_erros(linhas, consenso, "v9", {}))
    avaliacao = _ler(amostra_dir / ev.ARQ_AVALIACAO)
    comp = {c["versao"]: c for c in ae.comparar_versoes(linhas, consenso, "v1", avaliacao)}
    # a release 3 (v1 erra, v5 acerta) sai do recorte comum: v5 não "corrige" mais nada
    assert comp["v5"]["corrige"] == 0
