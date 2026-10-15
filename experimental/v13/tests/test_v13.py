"""Testes da v13 experimental (H1). Rodar: pytest experimental/v13/tests"""

import pytest

from experimental.v13.heuristica_v13 import VERSAO, corretiva, sem_sufixo_de_canal
from metricas.heuristica import avaliar

NOTA_FIX = "### Bug Fixes\n- Fixed a crash when saving"


@pytest.mark.parametrize("tag, esperado", [
    ("v2.10.5-lts", "v2.10.5"), ("v4.7.4-stable", "v4.7.4"), ("V1.0.0-LTS", "V1.0.0"),
    ("v1.0.0-rc1", "v1.0.0-rc1"), ("v2.0.0-beta.23", "v2.0.0-beta.23"), ("v1.0.0-alpha.3", "v1.0.0-alpha.3"),
    ("v1.0.0-preview", "v1.0.0-preview"), ("1.2.3", "1.2.3"), ("release-2020-01", "release-2020-01"), (None, None),
])
def test_sufixo_de_canal_so_remove_lts_e_stable(tag, esperado):
    assert sem_sufixo_de_canal(tag) == esperado


def test_h1_destrava_patch_com_sufixo_de_canal():
    # v12 bloqueia (sufixo = pré-release); v13 reconhece o patch e aplica a regra de conteúdo
    msgs = ["fix: crash on save"]
    assert avaliar("v2.10.4-lts", "v2.10.5-lts", msgs, "v12", notas=NOTA_FIX)["heuristic_corrective"] is False
    r = corretiva("v2.10.4-lts", "v2.10.5-lts", msgs, NOTA_FIX)
    assert r["heuristic_corrective"] is True and r["heuristic_version"] == VERSAO
    assert r["semver_patch"] is True and r["patch_da_tag"] is True


def test_h1_nao_destrava_pre_release_de_verdade():
    msgs = ["fix: crash on save"]
    for tag, base in (("v2.0.0-rc1", "v1.9.0"), ("v2.0.0-beta.2", "v2.0.0-beta.1"), ("v3.1.1-alpha.3", "v3.1.0")):
        assert avaliar(base, tag, msgs, "v12", notas=NOTA_FIX)["heuristic_corrective"] is False
        assert corretiva(base, tag, msgs, NOTA_FIX)["heuristic_corrective"] is False


@pytest.mark.parametrize("base, tag, msgs, notas", [
    ("v2.3.0", "v2.3.1", ["fix: crash ao abrir arquivo"], ""),                       # exemplo do professor
    ("v2.4.0", "v2.5.0", ["feat: nova opção"], ""),                                 # minor: bloqueado como na v12
    ("1.0.0", "1.0.1", ["feat: add x", "feat: add y"], "Added x. New features."),    # patch com novidade
    ("v5.0.0", "v5.0.1", ["Update docs"], "Security fix: bounds search params"),     # nota forte
    ("v1.0.0", "v1.1.0", ["fix: a", "fix: b"], "### Bug Fixes\n- a\n- b"),           # minor com fixes: v12 e v13 bloqueiam
])
def test_sem_sufixo_de_canal_v13_e_identica_a_v12(base, tag, msgs, notas):
    assert (corretiva(base, tag, msgs, notas)["heuristic_corrective"]
            == avaliar(base, tag, msgs, "v12", notas=notas)["heuristic_corrective"])


def test_sem_release_anterior_nunca_e_corretiva():
    assert corretiva(None, "v1.0.0-lts", ["fix: x"], NOTA_FIX)["heuristic_corrective"] is False


def test_v12_permanece_inalterada_pelo_modulo():
    # importar/usar a v13 não pode mudar o comportamento da v12 (bloqueio de sufixo continua)
    corretiva("v1.0.0-lts", "v1.0.1-lts", ["fix: x"], NOTA_FIX)
    assert avaliar("v1.0.0-lts", "v1.0.1-lts", ["fix: x"], "v12", notas=NOTA_FIX)["heuristic_corrective"] is False
