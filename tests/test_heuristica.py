"""Testes de metricas.heuristica (Issues #27 e #28) — exemplos da E§5, bordas da fonte_vdd e versões.

Fixtures fictícias, feitas à mão: nenhum repositório ou tag da amostra-ouro.
"""

import pytest

from metricas.heuristica import (
    HEURISTIC_VERSION,
    VERSOES,
    SemVer,
    apenas_patch,
    avaliar,
    classificar_releases,
    corretiva,
    parse_semver,
    sinais_conteudo,
    sinais_da_release,
    DadosAusentesError,
    tem_palavra_corretiva,
)

# ---- parse_semver ----


@pytest.mark.parametrize("tag, esperado", [
    ("2.3.1", SemVer("", 2, 3, 1, None)),
    ("v2.3.1", SemVer("", 2, 3, 1, None)),
    ("V2.3.1", SemVer("", 2, 3, 1, None)),
    ("release-2.3.1", SemVer("release-", 2, 3, 1, None)),
    ("@scope/pkg@2.3.1", SemVer("@scope/pkg@", 2, 3, 1, None)),
    ("pkg-v2.3.1", SemVer("pkg-", 2, 3, 1, None)),
    ("dev2.3.1", SemVer("dev", 2, 3, 1, None)),  # o `v` de "dev" não é marca de versão
    ("2.3.1-rc1", SemVer("", 2, 3, 1, "rc1")),
    ("v2.0.0-beta.2", SemVer("", 2, 0, 0, "beta.2")),
    ("2.3.1+build.5", SemVer("", 2, 3, 1, None)),
    ("1.2.3-x1.2.3", SemVer("", 1, 2, 3, "x1.2.3")),  # prefixo vazio tem preferência
    ("0.0.0", SemVer("", 0, 0, 0, None)),
])
def test_parse_semver_validos(tag, esperado):
    assert parse_semver(tag) == esperado


@pytest.mark.parametrize("tag", [
    "1.2", "1.2.3.4", "v1.2.3.4", "release-2020-01", "2026.10.01", "01.2.3", "nightly", "latest", "", None,
])
def test_parse_semver_nao_semver(tag):
    assert parse_semver(tag) is None


# ---- apenas_patch ----


@pytest.mark.parametrize("anterior, tag, esperado", [
    ("v2.3.0", "v2.3.1", True),
    ("v2.3.0", "2.3.1", True),            # só a marca `v` muda: comparável
    ("pkg-v1.0.0", "pkg-1.0.1", True),
    ("2.3.0", "2.3.5", True),
    ("v2.3.0", "v2.4.0", False),
    ("v2.4.0", "v2.5.0", False),
    ("v2.3.0", "v3.0.0", False),
    ("v2.3.1", "v2.3.1", False),
    ("v2.3.0", "v2.3.1-rc1", False),     # R é pré-release
    ("v2.3.1-rc1", "v2.3.1", False),     # final de um RC: núcleo igual
    ("v0.11.0", "v0.10.2", False),       # backport publicado depois (limitação conhecida)
])
def test_apenas_patch(anterior, tag, esperado):
    assert apenas_patch(anterior, tag) is esperado


@pytest.mark.parametrize("anterior, tag", [
    ("a@1.0.0", "b@1.0.1"),              # pacotes diferentes num monorepo
    ("release-2020-01", "release-2020-02"),
    ("v2.3.0", "nightly"),
    (None, "v1.0.0"),
])
def test_apenas_patch_nao_comparavel(anterior, tag):
    assert apenas_patch(anterior, tag) is None


# ---- tem_palavra_corretiva ----


@pytest.mark.parametrize("mensagem", [
    "fix: crash ao abrir arquivo",
    "fix(ui): botão desalinhado",
    "Fix typo in README",
    'Revert "feat: novo parser"',
    "hotfix para o deploy",
    "bug-fix no cache",
    "Merge pull request #12 from user/fix-crash",
    "chore: release\n\n* FIX: corrige leitura do config",  # corpo também conta
])
def test_palavra_corretiva_casa(mensagem):
    assert tem_palavra_corretiva([mensagem]) is True


@pytest.mark.parametrize("mensagem", [
    "feat: add prefix option",
    "test: new fixture",
    "docs: suffix rules",
    "fixes #10",
    "fixed the build",
    "bugfix release",
    "",
])
def test_palavra_corretiva_nao_casa(mensagem):
    assert tem_palavra_corretiva([mensagem]) is False


def test_palavra_corretiva_lista_vazia_e_mensagem_none():
    assert tem_palavra_corretiva([]) is False
    assert tem_palavra_corretiva([None, "feat: x"]) is False
    assert tem_palavra_corretiva([None, "fix: x"]) is True


# ---- avaliar (regra v1) ----


def test_exemplo_professor_patch_com_fix_e_corretiva():
    r = avaliar("v2.3.0", "v2.3.1", ["fix: crash ao abrir arquivo"], "v1")
    assert r == {
        "heuristic_corrective": True,
        "heuristic_version": "v1",
        "semver_patch": True,
        "patch_da_tag": True,
        "palavra_chave": True,
        "palavra_chave_ampla": True,
    }


def test_patch_sem_fix_nao_e_corretiva():
    assert avaliar("v2.3.0", "v2.3.1", ["feat: nova opção"], "v1")["heuristic_corrective"] is False


def test_minor_com_fix_nao_e_corretiva():
    r = avaliar("v2.4.0", "v2.5.0", ["fix: algo"], "v1")
    assert r["heuristic_corrective"] is False
    assert r["semver_patch"] is False and r["palavra_chave"] is True


def test_minor_sem_fix_nao_e_corretiva():
    assert avaliar("v2.3.0", "v2.4.0", ["feat: x"], "v1")["heuristic_corrective"] is False


def test_nao_semver_usa_so_palavra_chave():
    com_fix = avaliar("release-2020-01", "release-2020-02", ["hotfix: login"], "v1")
    assert com_fix["heuristic_corrective"] is True and com_fix["semver_patch"] is None
    assert avaliar("release-2020-01", "release-2020-02", ["feat: x"], "v1")["heuristic_corrective"] is False


def test_sem_release_anterior_nao_e_corretiva():
    r = avaliar(None, "v1.0.1", ["fix: x"], "v1")
    assert r["heuristic_corrective"] is False
    assert r["semver_patch"] is None and r["palavra_chave"] is False


def test_versao_desconhecida_e_erro():
    with pytest.raises(ValueError, match="desconhecida"):
        avaliar("v1.0.0", "v1.0.1", [], versao="v99")


# ---- classificar_releases (formato de collect_commits) ----


def item(tag, base, status="ok", mensagens=(), truncado=False, published_at="2025-05-12T00:00:00Z"):
    return {
        "tag_name": tag,
        "published_at": published_at,
        "base": base,
        "status": status,
        "status_compare": "ahead" if status == "ok" else None,
        "total_commits": len(mensagens) if status == "ok" else None,
        "truncado": truncado,
        "commits": [{"sha": "x", "author_date": published_at, "message": m} for m in mensagens],
    }


def test_classificar_releases_status_e_ordem():
    saida = classificar_releases([
        item("v1.0.0", None, status="sem_anterior"),
        item("v1.0.1", "v1.0.0", mensagens=["fix: a", None]),
        item("v1.0.2", "v1.0.1", status="404"),
        item("v1.0.3", "v1.0.2", mensagens=["fix: b"], truncado=True),
    ], "v1")
    assert [r["tag_name"] for r in saida] == ["v1.0.0", "v1.0.1", "v1.0.2", "v1.0.3"]
    assert [r["heuristic_corrective"] for r in saida] == [False, True, False, True]
    assert [r["mensagens_incompletas"] for r in saida] == [False, False, True, True]
    assert all(r["heuristic_version"] == "v1" for r in saida)
    assert saida[1]["base"] == "v1.0.0" and saida[1]["status"] == "ok"
    assert "id" not in saida[0]


def test_classificar_releases_repassa_id_e_ignora_mensagens_fora_do_ok():
    r = {**item("v1.0.1", "v1.0.0", status="404"), "id": 7, "commits": [{"message": "fix: x"}]}
    saida = classificar_releases([r], "v1")[0]
    assert saida["id"] == 7
    assert saida["palavra_chave"] is False


# ---- palavra-chave ampla e versões candidatas (Issue #28) ----


@pytest.mark.parametrize("mensagem", ["fixes #10", "fixed the build", "fixing tests", "bugfix release",
                                      "Reverted change", "reverts #3", "hotfixes", "fix: x"])
def test_palavra_ampla_casa(mensagem):
    assert tem_palavra_corretiva([mensagem], ampla=True) is True


@pytest.mark.parametrize("mensagem", ["feat: add prefix option", "test: new fixture", "fixer upper", ""])
def test_palavra_ampla_nao_casa(mensagem):
    assert tem_palavra_corretiva([mensagem], ampla=True) is False


def test_sinais_sem_anterior_e_com_anterior():
    assert sinais_da_release(None, "v1.0.1", ["fix: x"]) == {
        "semver_patch": None, "patch_da_tag": None, "palavra_chave": False, "palavra_chave_ampla": False,
    }
    assert sinais_da_release("v1.0.0", "v1.0.1", (m for m in ["fixes #2"])) == {
        "semver_patch": True, "patch_da_tag": True, "palavra_chave": False, "palavra_chave_ampla": True,
    }


def sinais(patch, estrita, ampla):
    return {"semver_patch": patch, "palavra_chave": estrita, "palavra_chave_ampla": ampla}


# (semver_patch, estrita, ampla) -> resultado esperado de v1..v7
TABELA_VERSOES = [
    ((True, True, True), [True, True, True, True, True, True, True]),
    ((True, False, False), [False, True, False, True, False, True, False]),
    ((True, False, True), [False, True, False, True, True, True, True]),
    ((False, True, True), [False, True, True, False, False, True, True]),
    ((False, False, True), [False, False, False, False, False, True, True]),
    ((False, False, False), [False] * 7),
    ((None, True, True), [True, True, True, True, True, True, True]),
    ((None, False, True), [False, False, False, False, True, True, True]),
    ((None, False, False), [False] * 7),
]


@pytest.mark.parametrize("entrada, esperado", TABELA_VERSOES)
def test_regras_das_versoes(entrada, esperado):
    obtido = [corretiva(sinais(*entrada), f"v{i}") for i in range(1, 8)]
    assert obtido == esperado


def test_versoes_registradas_com_descricao_e_v1_padrao():
    assert list(VERSOES) == [f"v{i}" for i in range(1, 13)]
    assert all(v.descricao for v in VERSOES.values())
    assert HEURISTIC_VERSION == "v1"


def test_avaliar_com_outra_versao():
    r = avaliar("v2.3.0", "v2.3.1", ["feat: x"], versao="v2")
    assert r["heuristic_corrective"] is True and r["heuristic_version"] == "v2"


# ---- v8/v9: sinais de conteúdo ----
def test_sinais_conteudo_ignora_ruido_e_conta_correcao_e_feature():
    from metricas.heuristica import sinais_conteudo

    s = sinais_conteudo(["chore: bump deps", "Merge pull request #1", "fix: crash", "feat: tela", "Fix typo"])
    assert (s["n_correcoes"], s["n_features"]) == (2, 1)
    assert (s["nota_correcao"], s["nota_novidade"]) == (None, None)


def test_sinais_conteudo_notas_e_url_nao_contam():
    from metricas.heuristica import sinais_conteudo

    s = sinais_conteudo([], "See https://x.io/fix/fixes for details. Added support for Y")
    assert (s["nota_correcao"], s["nota_novidade"]) == (False, True)


def test_v8_e_v9():
    ruim = ["feat: x", "fix: y"]
    assert avaliar("v1.0.0", "v1.0.1", ["fix: y"], versao="v8")["heuristic_corrective"] is True
    assert avaliar("v1.0.0", "v1.1.0", ruim, versao="v8")["heuristic_corrective"] is False
    # v9: sem commit de correção, mas notas dizem correção e sem novidade
    assert avaliar("v1.0.0", "v1.0.1", ["Atualiza"], versao="v9", notas="Fixed a crash")["heuristic_corrective"] is True
    assert avaliar("v1.0.0", "v1.0.1", ["Atualiza"], versao="v9", notas="Fixed a crash. New feature")["heuristic_corrective"] is False
    # sem release anterior nunca é corretiva
    assert avaliar(None, "v1.0.0", ["fix: y"], versao="v8")["heuristic_corrective"] is False


# ---- v9 sem release notes e versão explícita (Sprint 2, correção de auditoria) ----
def test_v9_sem_notas_falha_e_nao_vira_v8():
    from metricas.heuristica import DadosAusentesError

    # a v8 aceitaria isto como corretiva; a v9 não pode devolver esse resultado com rótulo v9
    with pytest.raises(DadosAusentesError, match="release notes"):
        avaliar("v1.0.0", "v1.0.1", ["fix: y"], versao="v9")


def test_v9_com_notas_vazias_e_dado_presente():
    r = avaliar("v1.0.0", "v1.0.1", ["Atualiza"], versao="v9", notas="")
    assert r["heuristic_version"] == "v9" and r["heuristic_corrective"] is False


def test_v9_primeira_release_nao_exige_notas():
    r = avaliar(None, "v1.0.0", ["fix: y"], versao="v9")
    assert r["heuristic_version"] == "v9" and r["heuristic_corrective"] is False


def test_classificar_releases_v9_sem_body_falha_sem_resultado_parcial():
    from metricas.heuristica import DadosAusentesError

    releases = [item("v1.0.0", None, status="sem_anterior"), item("v1.0.1", "v1.0.0", mensagens=["fix: a"])]
    with pytest.raises(DadosAusentesError):
        classificar_releases(releases, "v9")


def test_classificar_releases_v9_com_body_aplica_regra_v9():
    releases = [
        item("v1.0.0", None, status="sem_anterior"),
        {**item("v1.0.1", "v1.0.0", mensagens=["Atualiza"]), "body": "Fixed a crash"},
        {**item("v1.0.2", "v1.0.1", mensagens=["Atualiza"]), "body": "Fixed a crash. New feature"},
        {**item("v1.0.3", "v1.0.2", mensagens=["fix: y"]), "body": None},  # release sem texto
    ]
    saida = classificar_releases(releases, "v9")
    assert [r["heuristic_version"] for r in saida] == ["v9"] * 4
    assert [r["heuristic_corrective"] for r in saida] == [False, True, False, True]


def test_versao_e_obrigatoria_em_avaliar_corretiva_e_classificar():
    with pytest.raises(TypeError):
        avaliar("v1.0.0", "v1.0.1", ["fix: y"])
    with pytest.raises(TypeError):
        corretiva({"semver_patch": True, "palavra_chave": True})
    with pytest.raises(TypeError):
        classificar_releases([])


def test_versao_desconhecida_rejeitada_em_todas_as_entradas():
    with pytest.raises(ValueError, match="desconhecida"):
        corretiva({"semver_patch": True, "palavra_chave": True}, "v99")
    with pytest.raises(ValueError, match="desconhecida"):
        classificar_releases([], "v99")


def test_corretiva_v9_direta_sem_sinais_de_notas_falha():
    from metricas.heuristica import DadosAusentesError

    base = {"semver_patch": True, "palavra_chave": True, "palavra_chave_ampla": True, "n_correcoes": 1, "n_features": 0}
    # a v8 aceitaria estes sinais como corretiva; a v9 não pode devolver isso com o rótulo v9
    assert corretiva(base, "v8") is True
    for sinais in (base, {**base, "nota_correcao": None, "nota_novidade": None},
                   {**base, "nota_correcao": True, "nota_novidade": None}):
        with pytest.raises(DadosAusentesError, match="release notes"):
            corretiva(sinais, "v9")


# ---- v10: rejeita major/minor; nota ampla para patch com ≥4 fixes ----

def _sinais_v10(patch, n_cor, n_feat, nota_cor, nota_nov):
    """Helper: dicionário de sinais de conteúdo completo para testar v10."""
    return {
        "semver_patch": patch, "palavra_chave": False, "palavra_chave_ampla": False,
        "n_correcoes": n_cor, "n_features": n_feat,
        "nota_correcao": nota_cor, "nota_novidade": nota_nov,
    }


def test_v10_major_minor_nunca_corretiva():
    """Bump major ou minor: nunca corretiva, mesmo com commits de fix ou notas de correção."""
    for n_cor, nota_cor in [(5, True), (10, False), (0, True)]:
        s = _sinais_v10(False, n_cor, 0, nota_cor, False)
        assert corretiva(s, "v10") is False


def test_v10_patch_so_fix_corretiva():
    """Patch + só commits de correção (sem features) → corretiva (mesma regra da v8)."""
    assert corretiva(_sinais_v10(True, 2, 0, False, False), "v10") is True


def test_v10_patch_nota_estrita_corretiva():
    """Patch + nota de correção sem novidade → corretiva (mesma regra da v9)."""
    assert corretiva(_sinais_v10(True, 0, 0, True, False), "v10") is True


def test_v10_patch_nota_com_novidade_e_poucos_fixes_nao_corretiva():
    """Patch + nota com correção E novidade, mas <4 commits de fix → não corretiva."""
    assert corretiva(_sinais_v10(True, 3, 1, True, True), "v10") is False
    assert corretiva(_sinais_v10(True, 0, 0, True, True), "v10") is False


def test_v10_patch_nota_com_novidade_e_4_plus_fixes_dominando_corretiva():
    """Patch + nota com ambos, mas ≥4 commits de fix dominando features → corretiva (novo em v10)."""
    assert corretiva(_sinais_v10(True, 4, 1, True, True), "v10") is True
    assert corretiva(_sinais_v10(True, 8, 3, True, True), "v10") is True


def test_v10_patch_nota_com_novidade_fixes_iguais_nao_corretiva():
    """Patch + nota com ambos, fixes == features (sem dominância) → não corretiva."""
    assert corretiva(_sinais_v10(True, 4, 4, True, True), "v10") is False


def test_v10_nao_semver_usa_regra_estrita_da_v9():
    """Não-SemVer: nota com correção E novidade (sem commits de fix) → não corretiva (regra estrita, igual à v9)."""
    # n_cor=0, n_feat=0: v8 não dispara; notas com ambos os sinais → não corretiva (igual à v9)
    assert corretiva(_sinais_v10(None, 0, 0, True, True), "v10") is False
    # n_cor=1, n_feat=0: v8 dispara → corretiva (independente das notas)
    assert corretiva(_sinais_v10(None, 1, 0, True, True), "v10") is True
    # nota estrita (sem novidade) → corretiva
    assert corretiva(_sinais_v10(None, 0, 0, True, False), "v10") is True


def test_v10_sem_release_anterior_nao_e_corretiva():
    r = avaliar(None, "v1.0.0", ["fix: y"], versao="v10", notas="Fixed a crash")
    assert r["heuristic_corrective"] is False


def test_v10_sem_notas_falha_com_release_anterior():
    from metricas.heuristica import DadosAusentesError
    with pytest.raises(DadosAusentesError, match="release notes"):
        avaliar("v1.0.0", "v1.0.1", ["fix: y"], versao="v10")


def test_corretiva_v9_com_sinais_completos_e_notas_vazias():
    base = {"n_correcoes": 0, "n_features": 0}
    assert corretiva({**base, "nota_correcao": True, "nota_novidade": False}, "v9") is True
    assert corretiva({**base, "nota_correcao": True, "nota_novidade": True}, "v9") is False
    # notas coletadas e vazias: sinais False (presentes), não ausentes
    assert corretiva({**base, "nota_correcao": False, "nota_novidade": False}, "v9") is False


def test_corretiva_versoes_anteriores_nao_exigem_sinais_de_notas():
    sinais = {"semver_patch": True, "palavra_chave": True, "palavra_chave_ampla": True}
    assert [corretiva(sinais, f"v{i}") for i in range(1, 8)] == [True] * 7
    assert corretiva({"n_correcoes": 1, "n_features": 0}, "v8") is True


# --- v11 (refino pós-auditoria): v10 OU (só patch E nota declara release de correção/segurança) ---------

def _sinais_v11(tag_anterior, tag, mensagens, notas):
    return avaliar(tag_anterior, tag, mensagens, "v11", notas=notas)


def test_v11_nota_de_security_release_em_patch_sem_palavra_nos_commits():
    # FN da v10 na amostra-ouro: bump de patch, commits sem `fix`, nota "This is a security release"
    r = _sinais_v11("5.3.4", "5.3.5", ["Return comments to users who have access"], "**This is a security release** addressing two issues. Added new features.")
    assert r["nota_correcao_forte"] is True
    assert r["heuristic_corrective"] is True
    assert avaliar("5.3.4", "5.3.5", ["Return comments to users who have access"], "v10",
                   notas="**This is a security release** addressing two issues. Added new features.")["heuristic_corrective"] is False


def test_v11_nao_aplica_fora_de_patch():
    # minor/major: mesmo com a nota forte, v11 mantém a rejeição da v10
    assert _sinais_v11("2.3.0", "2.4.0", ["feat: x"], "This is a patch release")["heuristic_corrective"] is False
    assert _sinais_v11("2.3.0", "3.0.0", ["feat: x"], "security release")["heuristic_corrective"] is False


def test_v11_nota_fraca_nao_basta():
    # menção passageira a `fixed` sem se declarar release de correção continua negativa (regra da v10)
    r = _sinais_v11("1.0.0", "1.0.1", ["feat: add x", "feat: add y"], "Added x. Added y. Fixed typo. New features.")
    assert r["nota_correcao_forte"] is False
    assert r["heuristic_corrective"] is False


def test_v11_nao_regride_o_que_a_v10_aceita():
    msgs = ["fix: crash ao abrir arquivo"]
    assert avaliar("2.3.0", "2.3.1", msgs, "v10", notas="")["heuristic_corrective"] is True
    assert _sinais_v11("2.3.0", "2.3.1", msgs, "")["heuristic_corrective"] is True


def test_v11_exige_notas_e_sem_anterior_nunca_e_corretiva():
    with pytest.raises(DadosAusentesError):
        avaliar("1.0.0", "1.0.1", ["x"], "v11")
    assert avaliar(None, "1.0.0", [], "v11")["heuristic_corrective"] is False


def test_sinais_conteudo_sem_notas_deixa_nota_correcao_forte_none():
    assert sinais_conteudo(["fix: a"])["nota_correcao_forte"] is None


# --- v12: "patch" também pelo número da própria tag (release anterior cronológica em outra linha) ---------

def test_v12_backport_em_outra_linha_conta_como_patch_pela_propria_tag():
    # 5.0.1 publicada logo após 4.4.3: vista pela base cronológica é "major", mas é patch da linha 5.0
    notas = "Security fix: bounds the multiparameter position in search params"
    msgs = ["Update gem release docs", "Add CI with Rails 8.1", "fix: bound parameter depth", "Add DeepWiki badge"]
    v11 = avaliar("4.4.3", "5.0.1", msgs, "v11", notas=notas)
    v12 = avaliar("4.4.3", "5.0.1", msgs, "v12", notas=notas)
    assert v11["semver_patch"] is False and v11["patch_da_tag"] is True
    assert v11["heuristic_corrective"] is False  # v10/v11 rejeitam major/minor
    assert v12["heuristic_corrective"] is True


def test_v12_nao_trata_x_y_0_nem_prerelease_como_patch():
    notas = "This is a patch release. Fixes a crash."
    assert avaliar("1.0.0", "1.1.0", ["fix: x"], "v12", notas=notas)["patch_da_tag"] is False
    assert avaliar("1.0.0", "1.0.1-rc1", ["fix: x"], "v12", notas=notas)["patch_da_tag"] is False
    assert avaliar("v2025.1", "v2025.2", ["feat: x"], "v12", notas=notas)["patch_da_tag"] is False  # não-SemVer


def test_v12_sem_anterior_nunca_e_corretiva_e_exige_notas():
    assert avaliar(None, "1.0.1", [], "v12")["heuristic_corrective"] is False
    with pytest.raises(DadosAusentesError):
        avaliar("1.0.0", "1.0.1", ["fix: x"], "v12")
