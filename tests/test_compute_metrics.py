"""Testes de scripts.compute_metrics (Issue #21).

Verifica o cálculo das variantes (CFR b, df_c2, df_c3) e as classificações
DORA por combinação C1–C3, usando fixtures sintéticas sem chamadas HTTP.
"""

from __future__ import annotations

import csv
import math
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from scripts.compute_metrics import (
    COLUNAS_EXTRAS,
    VERSAO_HEURISTICA,
    _janela,
    adicionar_classificacoes,
    calcular_variantes,
    compute,
)

# ---------------------------------------------------------------------------
# Fixtures de infra
# ---------------------------------------------------------------------------

INICIO = date(2025, 1, 1)
FIM = date(2025, 12, 31)
JANELA = _janela(INICIO, FIM)


class _FakeClient:
    """Stub que devolve releases, commits e tags fixos sem HTTP."""

    def __init__(self, releases, commits_releases, tags):
        self._releases = releases
        self._commits_releases = commits_releases
        self._tags = tags

    def get(self, path, params=None):
        raise RuntimeError("_FakeClient não deve fazer chamadas HTTP")


@pytest.fixture()
def cache_dir(tmp_path):
    """Cache vazio com sub-pastas de releases e tags pré-populadas."""
    (tmp_path / "releases").mkdir()
    (tmp_path / "tags").mkdir()
    return tmp_path


def _escrever_cache_releases(cache_dir: Path, full_name: str, releases: list[dict]):
    """Grava o JSON de releases no formato esperado por collect_releases."""
    import json
    partes = full_name.strip().lower().split("/")
    arquivo = cache_dir / "releases" / f"{partes[0]}__{partes[1]}.json"
    arquivo.write_text(
        json.dumps({"full_name": full_name, "coletado_em": "2025-12-31T00:00:00+00:00",
                    "total": len(releases), "releases": releases}),
        encoding="utf-8",
    )


def _escrever_cache_tags(cache_dir: Path, full_name: str, tags: list[dict]):
    import json
    partes = full_name.strip().lower().split("/")
    arquivo = cache_dir / "tags" / f"{partes[0]}__{partes[1]}.json"
    arquivo.write_text(
        json.dumps({"full_name": full_name, "coletado_em": "2025-12-31T00:00:00+00:00",
                    "total": len(tags), "sem_data": 0, "tags": tags}),
        encoding="utf-8",
    )


def _escrever_cache_commits(cache_dir: Path, client, full_name: str, releases_cache: list[dict],
                             janela: tuple):
    """Garante que os .json de compare estejam no cache usando CachedHttpClient sobre um stub."""
    from unittest.mock import MagicMock, patch
    import json
    from pipeline.cache import CachedHttpClient
    from pipeline.collect_releases import pares_com_anterior
    from pipeline.collect_commits import collect_commits

    # Stub que devolve {"commits": [], "total_commits": 0} para qualquer compare
    def _stub_compare(path, params=None):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {"commits": [], "total_commits": 0}
        mock.headers = {}
        return mock

    real_client = MagicMock()
    real_client.get.side_effect = _stub_compare
    cached = CachedHttpClient(real_client, cache_dir)
    pares = pares_com_anterior(releases_cache, janela[0].date(), janela[1].date())
    return collect_commits(cached, full_name, pares, cache_dir)


# ---------------------------------------------------------------------------
# Releases e tags para os testes
# ---------------------------------------------------------------------------

_R1 = {
    "id": 1, "tag_name": "v1.0.0", "draft": False, "prerelease": False,
    "published_at": "2025-03-01T12:00:00+00:00",
    "created_at": "2025-03-01T12:00:00+00:00",
    "target_commitish": "main", "html_url": "https://github.com/test/repo/releases/tag/v1.0.0",
}
_R2 = {
    "id": 2, "tag_name": "v1.1.0", "draft": False, "prerelease": False,
    "published_at": "2025-06-01T12:00:00+00:00",
    "created_at": "2025-06-01T12:00:00+00:00",
    "target_commitish": "main", "html_url": "https://github.com/test/repo/releases/tag/v1.1.0",
}
_R3_PRE = {
    "id": 3, "tag_name": "v1.2.0-rc1", "draft": False, "prerelease": True,
    "published_at": "2025-08-01T12:00:00+00:00",
    "created_at": "2025-08-01T12:00:00+00:00",
    "target_commitish": "main", "html_url": "https://github.com/test/repo/releases/tag/v1.2.0-rc1",
}
_T1 = {"name": "v0.9.0", "sha": "abc", "data": "2025-02-01", "author_date": "2025-02-01T00:00:00+00:00", "committer_date": "2025-02-01T00:00:00+00:00"}
_T2 = {"name": "v1.0.0", "sha": "def", "data": "2025-03-01", "author_date": "2025-03-01T00:00:00+00:00", "committer_date": "2025-03-01T00:00:00+00:00"}
_T3 = {"name": "v1.1.0", "sha": "ghi", "data": "2025-06-01", "author_date": "2025-06-01T00:00:00+00:00", "committer_date": "2025-06-01T00:00:00+00:00"}
_T4_FORA = {"name": "v0.0.1", "sha": "zzz", "data": "2024-01-01", "author_date": "2024-01-01T00:00:00+00:00", "committer_date": "2024-01-01T00:00:00+00:00"}


# ---------------------------------------------------------------------------
# Testes de calcular_variantes
# ---------------------------------------------------------------------------

def test_df_c2_inclui_prerelease(cache_dir):
    """df_c2 conta releases + pré-releases; df em repos_final.csv conta só releases."""
    releases = [_R1, _R2, _R3_PRE]
    _escrever_cache_releases(cache_dir, "test/repo", releases)
    _escrever_cache_tags(cache_dir, "test/repo", [_T1, _T2, _T3])
    _escrever_cache_commits(cache_dir, None, "test/repo", releases, JANELA)

    from pipeline.cache import CachedHttpClient

    class _NoHTTP:
        def get(self, path, params=None):
            raise RuntimeError("HTTP proibido")

    client = CachedHttpClient(_NoHTTP(), cache_dir)
    v = calcular_variantes("test/repo", client, cache_dir, JANELA, "v8")
    assert v["n_releases_deploy_c2"] == 3  # 2 releases + 1 pré-release


def test_df_c2_maior_que_c1(cache_dir):
    """DF C2 deve ser ≥ DF C1 (pré-releases só aumentam)."""
    releases = [_R1, _R2, _R3_PRE]
    _escrever_cache_releases(cache_dir, "test/repo", releases)
    _escrever_cache_tags(cache_dir, "test/repo", [_T1, _T2])
    _escrever_cache_commits(cache_dir, None, "test/repo", releases, JANELA)

    from pipeline.cache import CachedHttpClient

    class _NoHTTP:
        def get(self, path, params=None):
            raise RuntimeError()

    client = CachedHttpClient(_NoHTTP(), cache_dir)
    v = calcular_variantes("test/repo", client, cache_dir, JANELA, "v8")
    window_weeks = (JANELA[1] - JANELA[0]).total_seconds() / (7 * 86400)
    df_c1 = 2 / window_weeks  # 2 releases não-prerelease
    assert v["df_c2"] >= df_c1


def test_df_c3_conta_tags_na_janela(cache_dir):
    """df_c3 conta só tags com author_date dentro da janela."""
    releases = [_R1, _R2]
    _escrever_cache_releases(cache_dir, "test/repo", releases)
    _escrever_cache_tags(cache_dir, "test/repo", [_T1, _T2, _T3, _T4_FORA])
    _escrever_cache_commits(cache_dir, None, "test/repo", releases, JANELA)

    from pipeline.cache import CachedHttpClient

    class _NoHTTP:
        def get(self, path, params=None):
            raise RuntimeError()

    client = CachedHttpClient(_NoHTTP(), cache_dir)
    v = calcular_variantes("test/repo", client, cache_dir, JANELA, "v8")
    # _T4_FORA está em 2024 → fora; _T1, _T2, _T3 dentro
    assert v["n_tags_janela"] == 3


def test_cfr_b_registra_a_versao_pedida(cache_dir):
    """heuristic_version registra a versão passada (o padrão do módulo é a v12 congelada)."""
    releases = [_R1, _R2]
    _escrever_cache_releases(cache_dir, "test/repo", releases)
    _escrever_cache_tags(cache_dir, "test/repo", [_T1])
    _escrever_cache_commits(cache_dir, None, "test/repo", releases, JANELA)

    from pipeline.cache import CachedHttpClient

    class _NoHTTP:
        def get(self, path, params=None):
            raise RuntimeError()

    client = CachedHttpClient(_NoHTTP(), cache_dir)
    v = calcular_variantes("test/repo", client, cache_dir, JANELA, "v8")
    assert v["heuristic_version"] == "v8"


def test_cfr_b_retorna_contadores(cache_dir):
    """calcular_variantes deve incluir todos os contadores de cfr_entrega."""
    releases = [_R1, _R2]
    _escrever_cache_releases(cache_dir, "test/repo", releases)
    _escrever_cache_tags(cache_dir, "test/repo", [])
    _escrever_cache_commits(cache_dir, None, "test/repo", releases, JANELA)

    from pipeline.cache import CachedHttpClient

    class _NoHTTP:
        def get(self, path, params=None):
            raise RuntimeError()

    client = CachedHttpClient(_NoHTTP(), cache_dir)
    v = calcular_variantes("test/repo", client, cache_dir, JANELA, "v8")
    for campo in ("cfr_b", "n_releases_avaliadas_cfr_b", "n_releases_censuradas_cfr_b",
                  "n_releases_janela", "n_releases_falha_cfr_b"):
        assert campo in v, f"campo ausente: {campo}"


# ---------------------------------------------------------------------------
# Testes de adicionar_classificacoes
# ---------------------------------------------------------------------------

def test_classificacoes_c1_coerente_com_base():
    """dora_c1 deve coincidir com dora_geral se as métricas forem iguais."""
    linha = {
        "deployment_frequency": "0.5",  # releases/semana → Medium
        "lt_release_median_h": "24.0",   # 1 dia → High
        "lt_commit_median_h": "24.0",
        "cfr_a": "0.1",                  # ≤15% → Elite
        "rec_median_h": "2.0",           # 2h → High
        "dora_geral": "High",
    }
    variantes = {"cfr_b": None, "df_c2": 0.6, "df_c3": 0.4}
    c = adicionar_classificacoes(linha, variantes)
    assert c["dora_c1"] == "High"  # mediana(3,3,4,3) = 3 = High (floor)


def test_dora_c2_parcial_quando_cfr_b_indefinido():
    """cfr_b None (heurística sem releases suficientes): dora_c2 usa as 3 métricas definidas e sinaliza."""
    linha = {
        "deployment_frequency": "1.0",
        "lt_release_median_h": "12.0",
        "lt_commit_median_h": "12.0",
        "cfr_a": "0.2",
        "rec_median_h": "0.5",
    }
    variantes = {"cfr_b": None, "df_c2": 1.5, "df_c3": 2.0}
    c = adicionar_classificacoes(linha, variantes)
    # DF 1,5 → High (3); LT 12 h → Elite (4); REC 0,5 h → Elite (4) → mediana 4 → Elite
    assert c["dora_c2"] == "Elite" and c["n_metricas_dora_c2"] == 3


def test_dora_sem_nenhuma_metrica_fica_vazio():
    c = adicionar_classificacoes({}, {"cfr_b": None})
    assert c["dora_c1"] == "" and c["n_metricas_dora_c1"] == 0


def test_doze_releases_na_janela_de_366_dias_sao_medium():
    """1 release/mês = 12 releases na janela: com 366 dias não pode cair em Low."""
    from metricas.dora import classify_df, semanas_da_janela
    janela = (datetime(2025, 10, 2, tzinfo=timezone.utc), datetime(2026, 10, 2, 23, 59, 59, tzinfo=timezone.utc))
    semanas = semanas_da_janela(janela)
    assert classify_df(12 / semanas, semanas) == "Medium"
    assert classify_df(11 / semanas, semanas) == "Low"


def test_dora_c3_usa_cfr_a():
    """dora_c3 usa CFR(a), não CFR(b): mesmo que cfr_b seja alto, dora_c3 não é afetado por ele."""
    linha = {
        "deployment_frequency": "1.0",
        "lt_release_median_h": "12.0",
        "lt_commit_median_h": "12.0",
        "cfr_a": "0.1",   # ≤15% → Elite (score 4)
        "rec_median_h": "0.5",  # <1h → Elite (score 4)
    }
    # cfr_b=0.5 (Low) deve ser ignorado em C3
    variantes = {"cfr_b": 0.5, "df_c2": 1.5, "df_c3": 1.0}
    c = adicionar_classificacoes(linha, variantes)
    # C3: df_c3=1.0 → High(3), lt(b)=12h → Elite(4), cfr_a=0.1 → Elite(4), rec=0.5h → Elite(4)
    # notas: [3,4,4,4] → mediana 4 → floor 4 → Elite
    assert c["dora_c3"] == "Elite"
    # se usasse cfr_b=0.5 (Low, score 1) em vez de cfr_a, dora_c3 seria != Elite
    assert c["dora_c3"] != "Low"


def test_cfr_b_class_definida_quando_cfr_b_existe():
    """cfr_b_class deve estar presente quando cfr_b é um número."""
    linha = {
        "deployment_frequency": "1.0",
        "lt_release_median_h": "12.0",
        "lt_commit_median_h": "12.0",
        "cfr_a": "0.2",
        "rec_median_h": "2.0",
    }
    variantes = {"cfr_b": 0.2, "df_c2": 1.0, "df_c3": 1.0}
    c = adicionar_classificacoes(linha, variantes)
    assert c["cfr_b_class"] in ("Elite", "High", "Medium", "Low")


# ---------------------------------------------------------------------------
# Testes de compute (integração com CSV)
# ---------------------------------------------------------------------------

def _repos_final(tmp_path, linhas: list[dict]) -> Path:
    """Grava um repos_final.csv mínimo."""
    campos = [
        "full_name", "stars", "language", "contributors", "age_days", "default_branch",
        "n_releases_total", "n_releases_deploy_total", "deployment_frequency",
        "lt_release_median_h", "lt_commit_median_h", "n_releases_avaliadas",
        "n_releases_ignored_404", "n_sem_anterior", "n_sem_commits_novos", "n_commits_negativos",
        "n_runs_coletados", "n_runs_dias_saturados", "n_runs_fora_de_push",
        "n_runs_sucesso", "n_runs_falha", "cfr_a", "rec_median_h",
        "n_episodios", "n_episodios_censurados", "prop_episodios_censurados", "n_tags",
        "df_class", "lt_class", "cfr_class", "rec_class", "dora_geral",
    ]
    f = tmp_path / "repos_final.csv"
    with f.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            w.writerow({k: l.get(k, "") for k in campos})
    return f


def test_compute_gera_colunas_extras(tmp_path):
    """compute() deve produzir todas as COLUNAS_EXTRAS no CSV de saída."""
    repos_csv = _repos_final(tmp_path, [{
        "full_name": "test/repo",
        "deployment_frequency": "1.0",
        "lt_release_median_h": "12.0",
        "lt_commit_median_h": "12.0",
        "cfr_a": "0.2",
        "rec_median_h": "2.0",
    }])
    saida = tmp_path / "metrics.csv"
    cache_dir = tmp_path / "cache"
    (cache_dir / "releases").mkdir(parents=True)
    (cache_dir / "tags").mkdir()
    _escrever_cache_releases(cache_dir, "test/repo", [_R1, _R2])
    _escrever_cache_tags(cache_dir, "test/repo", [_T1, _T2])
    _escrever_cache_commits(cache_dir, None, "test/repo", [_R1, _R2], JANELA)

    resultado = compute(repos_csv, cache_dir, saida, JANELA, "v8")

    assert resultado["n_ok"] == 1
    assert saida.exists()
    rows = list(csv.DictReader(saida.open()))
    assert len(rows) == 1
    for col in COLUNAS_EXTRAS:
        assert col in rows[0], f"coluna ausente: {col}"


def test_compute_preserva_colunas_base(tmp_path):
    """compute() não deve remover colunas já existentes em repos_final.csv."""
    repos_csv = _repos_final(tmp_path, [{
        "full_name": "test/repo",
        "stars": "1234",
        "deployment_frequency": "1.0",
        "lt_release_median_h": "12.0",
        "lt_commit_median_h": "12.0",
        "cfr_a": "0.2",
        "rec_median_h": "2.0",
    }])
    saida = tmp_path / "metrics.csv"
    cache_dir = tmp_path / "cache"
    (cache_dir / "releases").mkdir(parents=True)
    (cache_dir / "tags").mkdir()
    _escrever_cache_releases(cache_dir, "test/repo", [_R1, _R2])
    _escrever_cache_tags(cache_dir, "test/repo", [])
    _escrever_cache_commits(cache_dir, None, "test/repo", [_R1, _R2], JANELA)

    compute(repos_csv, cache_dir, saida, JANELA, "v8")

    rows = list(csv.DictReader(saida.open()))
    assert rows[0]["stars"] == "1234"
    assert rows[0]["full_name"] == "test/repo"


def test_compute_erro_nao_interrompe(tmp_path):
    """Um repo com cache ausente deve resultar em erro, mas os demais são processados."""
    repos_csv = _repos_final(tmp_path, [
        {"full_name": "test/repo_ok"},
        {"full_name": "test/repo_sem_cache"},
    ])
    saida = tmp_path / "metrics.csv"
    cache_dir = tmp_path / "cache"
    (cache_dir / "releases").mkdir(parents=True)
    (cache_dir / "tags").mkdir()
    _escrever_cache_releases(cache_dir, "test/repo_ok", [_R1, _R2])
    _escrever_cache_tags(cache_dir, "test/repo_ok", [_T1])
    _escrever_cache_commits(cache_dir, None, "test/repo_ok", [_R1, _R2], JANELA)
    # repo_sem_cache: sem releases cache → erro

    resultado = compute(repos_csv, cache_dir, saida, JANELA, "v8")

    assert resultado["n_total"] == 2
    rows = list(csv.DictReader(saida.open()))
    assert len(rows) == 2  # as 2 linhas foram escritas (erro com colunas vazias)


def test_compute_colunas_extras_completas(tmp_path):
    """COLUNAS_EXTRAS deve cobrir todas as colunas novas, sem duplicatas."""
    assert len(COLUNAS_EXTRAS) == len(set(COLUNAS_EXTRAS))
    for col in ("cfr_b", "df_c2", "df_c3", "dora_c1", "dora_c2", "dora_c3",
                "heuristic_version", "n_releases_janela"):
        assert col in COLUNAS_EXTRAS


def _client_sem_http(cache_dir):
    from pipeline.cache import CachedHttpClient

    class _NoHTTP:
        def get(self, path, params=None):
            raise RuntimeError("sem HTTP")

    return CachedHttpClient(_NoHTTP(), cache_dir)


def test_v11_sem_body_falha_explicitamente_e_com_body_registra_v11(cache_dir):
    """Versões v9+ leem as release notes: sem `body` levantam erro; com `body`, rodam e registram a versão."""
    from metricas.heuristica import DadosAusentesError

    _escrever_cache_releases(cache_dir, "test/repo", [_R1, _R2])
    _escrever_cache_tags(cache_dir, "test/repo", [])
    _escrever_cache_commits(cache_dir, None, "test/repo", [_R1, _R2], JANELA)
    client = _client_sem_http(cache_dir)
    with pytest.raises(DadosAusentesError):
        calcular_variantes("test/repo", client, cache_dir, JANELA, "v11")

    com_body = [{**_R1, "body": "First release"}, {**_R2, "body": "This is a patch release. Fixes a crash."}]
    _escrever_cache_releases(cache_dir, "test/repo", com_body)
    v = calcular_variantes("test/repo", client, cache_dir, JANELA, "v11")
    assert v["heuristic_version"] == "v11"
    assert VERSAO_HEURISTICA == "v12"  # versão final congelada
