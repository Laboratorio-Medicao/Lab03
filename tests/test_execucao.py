"""Testes da integração (Issue #6) com seleção, coleta e métricas falsas: sem rede, sem GitHub real."""

import csv
import logging
from datetime import date
from pathlib import Path

import pytest

from pipeline import cli
from pipeline.config import Config, SelecaoConfig
from pipeline.execucao import Etapas, anexar_log_em_arquivo, executar, validar_amostra
from pipeline.selection import RepoRecord, ResultadoSelecao

INICIO, FIM = date(2025, 1, 1), date(2025, 12, 31)


def repo(nome, status="selecionado", etapa="final", motivo=""):
    return RepoRecord(nome, 1500, "Python", "main", "2020-01-01T00:00:00Z", status=status, etapa=etapa, motivo=motivo)


def config(tmp_path, alvo=100):
    return Config(
        token_env="GITHUB_TOKEN", janela_inicio=INICIO, janela_fim=FIM,
        cache_dir=tmp_path / "cache", saidas_dir=tmp_path / "out", selecao=SelecaoConfig(amostra_alvo=alvo),
    )


class Cliente:
    def __init__(self):
        self.chamadas = 0

    def estatisticas(self):
        return {"requisicoes": self.chamadas}


class Pipeline:
    """Registra a ordem das etapas e o que cada uma recebeu."""

    def __init__(self, registros, falhar=()):
        self.registros, self.falhar = registros, set(falhar)
        self.ordem, self.coletados, self.calculados = [], [], []

    def selecionar(self, client, sel, inicio, fim):
        self.ordem.append("selecao")
        return ResultadoSelecao(registros=self.registros, brutos=len(self.registros))

    def coletar(self, client, r, inicio, fim):
        self.ordem.append("coleta")
        self.coletados.append(r.full_name)
        if r.full_name in self.falhar:
            raise RuntimeError("HTTP 500")
        client.chamadas += 1
        return {"releases": 7}

    def calcular(self, r, dados, inicio, fim):
        self.ordem.append("metricas")
        self.calculados.append((r.full_name, dados))
        return {"n_releases": dados["releases"]}

    def etapas(self):
        return Etapas(coletar=self.coletar, calcular=self.calcular, selecionar=self.selecionar)


def cem():
    return [repo(f"org/r{i:03d}") for i in range(100)]


def lerCsv(caminho):
    with Path(caminho).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_ordem_selecao_coleta_metricas(tmp_path):
    p = Pipeline([repo("a/x"), repo("b/y")])
    executar(config(tmp_path), Cliente(), p.etapas(), 100)
    assert p.ordem == ["selecao", "coleta", "metricas", "coleta", "metricas"]


def test_selecao_alimenta_coleta_so_com_selecionados(tmp_path):
    regs = [repo("a/x"), repo("b/y", "descartado", "releases", "lt_5_releases"), repo("c/z")]
    p = Pipeline(regs)
    executar(config(tmp_path), Cliente(), p.etapas(), 100)
    assert p.coletados == ["a/x", "c/z"]


def test_coleta_entrega_dados_as_metricas(tmp_path):
    p = Pipeline([repo("a/x")])
    executar(config(tmp_path), Cliente(), p.etapas(), 100)
    assert p.calculados == [("a/x", {"releases": 7})]
    linhas = lerCsv(tmp_path / "out" / "resultados.csv")
    assert linhas == [{"full_name": "a/x", "status": "concluido", "erro": "", "n_releases": "7"}]


def test_cem_repositorios(tmp_path):
    p = Pipeline(cem())
    r = executar(config(tmp_path), Cliente(), p.etapas(), 100)
    assert (r.selecionados, r.processados, r.concluidos, r.erros) == (100, 100, 100, 0)
    assert len(lerCsv(tmp_path / "out" / "resultados.csv")) == 100


def test_nao_processa_repositorio_duplicado(tmp_path):
    p = Pipeline([repo("a/x"), repo("A/X"), repo("b/y")])
    r = executar(config(tmp_path), Cliente(), p.etapas(), 100)
    assert p.coletados == ["a/x", "b/y"]
    assert r.duplicados == 1


def test_validar_amostra_rejeita_full_name_invalido():
    with pytest.raises(ValueError):
        validar_amostra([repo("sembarra")], 100)


def test_acima_do_alvo_corta_e_registra(tmp_path, caplog):
    p = Pipeline(cem() + [repo("org/extra")])
    with caplog.at_level(logging.WARNING):
        r = executar(config(tmp_path), Cliente(), p.etapas(), 100)
    assert (r.processados, r.fora_da_amostra) == (100, 1)
    assert "org/extra" not in p.coletados
    assert "fora da amostra" in caplog.text


def test_abaixo_do_alvo_nao_completa_nem_relaxa(tmp_path, caplog):
    p = Pipeline([repo(f"org/r{i}") for i in range(40)] + [repo("org/d", "descartado", "runs", "lt_50_runs")])
    with caplog.at_level(logging.WARNING):
        r = executar(config(tmp_path), Cliente(), p.etapas(), 100)
    assert r.processados == 40
    assert "abaixo do alvo" in caplog.text


def test_funil_vem_dos_registros_reais(tmp_path):
    regs = [repo("a/x"), repo("b/y", "descartado", "actions", "no_actions"), repo("c/z", "descartado", "runs", "lt_50_runs")]
    executar(config(tmp_path), Cliente(), Pipeline(regs).etapas(), 100)
    linhas = {l["full_name"]: l for l in lerCsv(tmp_path / "out" / "funil.csv")}
    assert set(linhas) == {"a/x", "b/y", "c/z"}
    assert (linhas["b/y"]["status"], linhas["b/y"]["motivo"]) == ("descartado", "no_actions")
    assert linhas["a/x"]["status"] == "selecionado"
    assert (tmp_path / "out" / "funil.md").is_file()


def test_falha_de_coleta_e_registrada_e_execucao_segue(tmp_path, caplog):
    p = Pipeline([repo("a/x"), repo("b/y"), repo("c/z")], falhar=["b/y"])
    with caplog.at_level(logging.INFO):
        r = executar(config(tmp_path), Cliente(), p.etapas(), 100)
    assert (r.processados, r.concluidos, r.erros) == (3, 2, 1)
    por_nome = {l["full_name"]: l for l in lerCsv(tmp_path / "out" / "resultados.csv")}
    assert por_nome["b/y"]["status"] == "erro"
    assert "RuntimeError: HTTP 500" in por_nome["b/y"]["erro"]
    assert "b/y: falha" in caplog.text
    assert "erros: 1" in caplog.text


def test_log_tem_contagens_e_consumo_do_cliente(tmp_path, caplog):
    regs = [repo("a/x"), repo("b/y", "descartado", "releases", "lt_5_releases")]
    cliente = Cliente()
    cliente.chamadas = 10  # consumo anterior à execução não entra na conta
    with caplog.at_level(logging.INFO):
        r = executar(config(tmp_path), cliente, Pipeline(regs).etapas(), 100)
    assert r.consumo_cache == {"requisicoes": 1}
    for trecho in ("execução iniciada", "candidatos: 2", "lt_5_releases", "selecionados (aprovados nos filtros): 1",
                   "processados: 1", "concluídos: 1", "encerrada", "janela: 2025-01-01 a 2025-12-31"):
        assert trecho in caplog.text


def test_log_sem_contadores_do_cliente_avisa(tmp_path, caplog):
    with caplog.at_level(logging.INFO):
        executar(config(tmp_path), object(), Pipeline([repo("a/x")]).etapas(), 100)
    assert "contadores não disponíveis" in caplog.text


def test_log_em_arquivo_sem_token(tmp_path):
    token = "ghp_SEGREDO_NAO_PODE_VAZAR"
    handler = anexar_log_em_arquivo(tmp_path / "out")
    try:
        executar(config(tmp_path), Cliente(), Pipeline([repo("a/x")]).etapas(), 100)
    finally:
        logging.getLogger("pipeline").removeHandler(handler)
        handler.close()
    texto = (tmp_path / "out" / "execucao.log").read_text(encoding="utf-8")
    assert "execução iniciada" in texto
    assert token not in texto


def test_sem_coleta_configurada_faz_so_selecao_e_funil(tmp_path):
    p = Pipeline([repo("a/x")])
    r = executar(config(tmp_path), Cliente(), Etapas(None, None, p.selecionar), 100)
    assert (r.selecionados, r.processados) == (1, 0)
    assert (tmp_path / "out" / "funil.csv").is_file()


def test_comando_unico_executa_o_fluxo_completo(tmp_path, monkeypatch, caplog):
    p = Pipeline(cem())
    monkeypatch.setattr(cli, "executar", lambda cfg, client, etapas, alvo: executar(cfg, client, p.etapas(), alvo))
    with caplog.at_level(logging.INFO):
        cli.run(config(tmp_path), "tok", Cliente(), p.etapas())
    assert len(p.coletados) == 100
    assert (tmp_path / "out" / "execucao.log").is_file()
    assert "execução concluída: 100 concluídos, 0 erros" in caplog.text
