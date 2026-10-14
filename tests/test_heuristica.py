"""Testes de metricas.heuristica (Issue #27) — exemplos da E§5 e bordas da fonte_vdd.

Fixtures fictícias, feitas à mão: nenhum repositório ou tag da amostra-ouro.
"""

import pytest

from metricas.heuristica import (
    HEURISTIC_VERSION,
    SemVer,
    apenas_patch,
    avaliar,
    classificar_releases,
    parse_semver,
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
    r = avaliar("v2.3.0", "v2.3.1", ["fix: crash ao abrir arquivo"])
    assert r == {
        "heuristic_corrective": True,
        "heuristic_version": HEURISTIC_VERSION,
        "semver_patch": True,
        "palavra_chave": True,
    }


def test_patch_sem_fix_nao_e_corretiva():
    assert avaliar("v2.3.0", "v2.3.1", ["feat: nova opção"])["heuristic_corrective"] is False


def test_minor_com_fix_nao_e_corretiva():
    r = avaliar("v2.4.0", "v2.5.0", ["fix: algo"])
    assert r["heuristic_corrective"] is False
    assert r["semver_patch"] is False and r["palavra_chave"] is True


def test_minor_sem_fix_nao_e_corretiva():
    assert avaliar("v2.3.0", "v2.4.0", ["feat: x"])["heuristic_corrective"] is False


def test_nao_semver_usa_so_palavra_chave():
    com_fix = avaliar("release-2020-01", "release-2020-02", ["hotfix: login"])
    assert com_fix["heuristic_corrective"] is True and com_fix["semver_patch"] is None
    assert avaliar("release-2020-01", "release-2020-02", ["feat: x"])["heuristic_corrective"] is False


def test_sem_release_anterior_nao_e_corretiva():
    r = avaliar(None, "v1.0.1", ["fix: x"])
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
    ])
    assert [r["tag_name"] for r in saida] == ["v1.0.0", "v1.0.1", "v1.0.2", "v1.0.3"]
    assert [r["heuristic_corrective"] for r in saida] == [False, True, False, True]
    assert [r["mensagens_incompletas"] for r in saida] == [False, False, True, True]
    assert all(r["heuristic_version"] == HEURISTIC_VERSION for r in saida)
    assert saida[1]["base"] == "v1.0.0" and saida[1]["status"] == "ok"
    assert "id" not in saida[0]


def test_classificar_releases_repassa_id_e_ignora_mensagens_fora_do_ok():
    r = {**item("v1.0.1", "v1.0.0", status="404"), "id": 7, "commits": [{"message": "fix: x"}]}
    saida = classificar_releases([r])[0]
    assert saida["id"] == 7
    assert saida["palavra_chave"] is False
