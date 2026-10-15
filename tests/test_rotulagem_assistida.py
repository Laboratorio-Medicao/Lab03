"""Testes da rotulagem assistida: fases, imutabilidade, cegamento, exportação e compatibilidade com `avaliar`."""

from __future__ import annotations

import csv
import json
import threading
import urllib.request
from pathlib import Path

import pytest

from scripts import rotulagem_assistida as ra
from scripts import validacao_independente as vi

AVALIADORES = ["A", "B", "C"]
ITENS = [("1", "a/x", "1.0.1", "1.0.0", ["fix: crash"]), ("2", "a/x", "1.1.0", "1.0.1", ["feat: add y"]),
         ("3", "b/y", "2.0.1", "2.0.0", ["fix: bug"]), ("4", "b/y", "2.1.0", "2.0.1", ["docs: z"])]


def _pacote(tmp_path: Path, com_sugestoes: bool = True) -> Path:
    amostra = [{"full_name": f, "repo_url": f"https://github.com/{f}", "release_id": i, "tag_name": t,
                "published_at": "2026-02-01T00:00:00Z", "release_url": f"https://github.com/{f}/releases/tag/{t}",
                "compare_url": f"https://github.com/{f}/compare/{b}...{t}"} for i, f, t, b, _ in ITENS]
    vi._escrever_csv(tmp_path / "amostra_validacao.csv", vi.COLUNAS_AMOSTRA, amostra)
    congelado = {i: {"full_name": f, "tag_name": t, "base": b, "published_at": "2026-02-01T00:00:00Z", "status": "ok",
                     "truncado": False, "body": "Notas da release " + t,
                     "commits": [{"sha": "s", "message": m, "n_parents": 1, "author_date": "2026-01-01T00:00:00Z"}
                                 for m in ms]} for i, f, t, b, ms in ITENS}
    (tmp_path / "dados_congelados.json").write_text(json.dumps(congelado), encoding="utf-8")
    for n in AVALIADORES:
        vi._escrever_csv(tmp_path / f"labels_{n}.csv", vi.COLUNAS_PLANILHA, vi.linhas_planilha(amostra))
    cong = {"versao_heuristica": "v12", "heuristica_sha256": vi._sha256(vi.ARQ_HEURISTICA),
            "dados_congelados_sha256": vi._sha256(tmp_path / "dados_congelados.json"),
            "amostra_sha256": vi._sha256(tmp_path / "amostra_validacao.csv"), "avaliadores": AVALIADORES}
    (tmp_path / "congelamento.json").write_text(json.dumps(cong), encoding="utf-8")
    if com_sugestoes:
        with (tmp_path / ra.ARQ_SUGESTOES).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["release_id", "corretiva", "motivo", "fonte"])
            w.writeheader()
            w.writerow({"release_id": "1", "corretiva": "sim", "motivo": "nota fala em crash", "fonte": "IA (teste)"})
            w.writerow({"release_id": "2", "corretiva": "nao", "motivo": "feature", "fonte": "IA (teste)"})
    return tmp_path


def _preencher(reg: ra.Registro, corretiva: dict[str, str]):
    for rid, v in corretiva.items():
        reg.decidir(ra.item_release(rid), v, "inicial")
    for fn in ("a/x", "b/y"):
        reg.decidir(ra.item_repo(fn, "tipo_projeto"), "biblioteca_framework", "inicial")
        reg.decidir(ra.item_repo(fn, "releases_sao_entregas_reais"), "sim", "inicial")


# ------------------------------------------------------------------------------------------ fases

def test_sugestao_so_depois_da_decisao_inicial(tmp_path):
    reg = ra.Registro(_pacote(tmp_path), "A")
    with pytest.raises(ra.RotulagemError, match="depois da sua decisão inicial"):
        reg.sugestao_exibida(ra.item_release("1"), "IA")
    reg.decidir(ra.item_release("1"), "nao", "inicial")
    reg.sugestao_exibida(ra.item_release("1"), "IA")
    assert reg.estado()[ra.item_release("1")]["sugestao_vista"] is True


def test_decisao_final_exige_inicial_e_confirmacao_explicita(tmp_path):
    reg = ra.Registro(_pacote(tmp_path), "A")
    it = ra.item_release("1")
    with pytest.raises(ra.RotulagemError, match="antes da final|confirmação"):
        reg.decidir(it, "sim", "final", confirmou=True)  # sem inicial
    reg.decidir(it, "nao", "inicial")
    with pytest.raises(ra.RotulagemError, match="confirmação explícita"):
        reg.decidir(it, "sim", "final")  # "Aceitar" sem confirmar não vira decisão
    ev = reg.decidir(it, "sim", "final", confirmou=True, sugestao_valor="sim")
    assert ev["origem"] == "humano_via_interface" and ev["valor_coincide_com_sugestao"] is True
    assert reg.estado()[it]["final"] == "sim" and reg.estado()[it]["inicial"] == "nao"


def test_inicial_imutavel_depois_de_ver_a_sugestao_mas_livre_antes(tmp_path):
    reg = ra.Registro(_pacote(tmp_path), "A")
    it = ra.item_release("1")
    reg.decidir(it, "nao", "inicial")
    reg.decidir(it, "sim", "inicial")  # pode mudar antes de ver
    reg.sugestao_exibida(it, "IA")
    with pytest.raises(ra.RotulagemError, match="imutável"):
        reg.decidir(it, "nao", "inicial")
    reg.decidir(it, "sim", "inicial")  # repetir o mesmo valor é inofensivo


def test_valores_invalidos_sao_recusados(tmp_path):
    reg = ra.Registro(_pacote(tmp_path), "A")
    with pytest.raises(ra.RotulagemError):
        reg.decidir(ra.item_release("1"), "talvez", "inicial")
    with pytest.raises(ra.RotulagemError):
        reg.decidir(ra.item_repo("a/x", "tipo_projeto"), "sim", "inicial")


def test_log_registra_usuario_horario_e_nao_mistura_usuarios(tmp_path):
    pasta = _pacote(tmp_path)
    ra.Registro(pasta, "A").decidir(ra.item_release("1"), "sim", "inicial", "obs A")
    ra.Registro(pasta, "B").decidir(ra.item_release("1"), "nao", "inicial")
    ev = ra.Registro(pasta, "A").eventos()
    assert len(ev) == 1 and ev[0]["usuario_informado"] == "A" and ev[0]["ts"] and ev[0]["valor"] == "sim"
    assert ra.Registro(pasta, "B").estado()[ra.item_release("1")]["inicial"] == "nao"
    assert (pasta / "rotulagem/A.jsonl").exists() and (pasta / "rotulagem/B.jsonl").exists()


def test_observacao_nao_altera_decisao(tmp_path):
    reg = ra.Registro(_pacote(tmp_path), "A")
    it = ra.item_release("1")
    reg.decidir(it, "sim", "inicial")
    reg.anotar(it, "notas ambíguas")
    e = reg.estado()[it]
    assert e["inicial"] == "sim" and e["obs"] == "notas ambíguas"
    reg.decidir(it, "sim", "inicial")  # nova decisão sem observação não apaga a anterior
    assert reg.estado()[it]["obs"] == "notas ambíguas"


# ------------------------------------------------------------------------------- exportação e avaliação

def test_exportacao_valida_e_compativel_com_o_avaliar(tmp_path):
    pasta = _pacote(tmp_path)
    pac = ra.Pacote(pasta)
    consenso = {"1": "sim", "2": "nao", "3": "sim", "4": "nao"}
    for nome in AVALIADORES:
        reg = ra.Registro(pasta, nome)
        _preencher(reg, consenso)
        r = ra.exportar(pac, reg)
        assert r["completo"] and r["pendencias"] == 0 and r["autenticacao"].startswith("nenhuma")
    res = vi.cmd_avaliar(pasta, b=100)  # pipeline de avaliação existente, sem alteração
    assert res["n_releases"] == 4 and res["avaliacao_independente"] is True


def test_exportacao_parcial_nao_e_completa(tmp_path):
    pasta = _pacote(tmp_path)
    reg = ra.Registro(pasta, "A")
    reg.decidir(ra.item_release("1"), "sim", "inicial")
    r = ra.exportar(ra.Pacote(pasta), reg)
    assert r["completo"] is False and r["pendencias"] > 0
    assert ra.progresso(ra.Pacote(pasta), reg)["completo"] is False


def test_exportacao_usa_decisao_final_e_preserva_a_inicial_no_log(tmp_path):
    pasta = _pacote(tmp_path)
    pac = ra.Pacote(pasta)
    reg = ra.Registro(pasta, "A")
    _preencher(reg, {"1": "nao", "2": "nao", "3": "nao", "4": "nao"})
    reg.sugestao_exibida(ra.item_release("1"), "IA")
    reg.decidir(ra.item_release("1"), "sim", "final", confirmou=True, sugestao_valor="sim")
    r = ra.exportar(pac, reg)
    linhas = list(csv.DictReader((pasta / "labels_A.csv").open(encoding="utf-8-sig")))
    assert [l["corretiva"] for l in linhas] == ["sim", "nao", "nao", "nao"]
    assert r["n_finais_apos_ver_sugestao"] == 1 and r["n_finais_iguais_a_sugestao"] == 1
    assert reg.estado()[ra.item_release("1")]["inicial"] == "nao"  # inicial preservada


def test_exportacao_recusa_sobrescrever_conteudo_alheio_e_respeita_forcar(tmp_path):
    pasta = _pacote(tmp_path)
    arq = pasta / "labels_A.csv"
    linhas = list(csv.DictReader(arq.open(encoding="utf-8-sig")))
    linhas[0]["corretiva"] = "sim"  # editado "à mão", fora da ferramenta
    vi._escrever_csv(arq, vi.COLUNAS_PLANILHA, linhas)
    pac, reg = ra.Pacote(pasta), ra.Registro(pasta, "A")
    with pytest.raises(ra.RotulagemError, match="não foi exportado por esta ferramenta"):
        ra.exportar(pac, reg)
    ra.exportar(pac, reg, forcar=True)
    assert (pasta / "labels_A.csv.bak").exists()


def test_usuario_fora_do_pacote_e_recusado(tmp_path):
    pasta = _pacote(tmp_path)
    with pytest.raises(ra.RotulagemError):
        ra.exportar(ra.Pacote(pasta), ra.Registro(pasta, "intruso"))


# ------------------------------------------------------------------------------------ sugestões e cegamento

def test_sugestao_exige_fonte_e_valor_valido(tmp_path):
    pasta = _pacote(tmp_path, com_sugestoes=False)
    (pasta / ra.ARQ_SUGESTOES).write_text("release_id,corretiva,motivo,fonte\n1,sim,x,\n", encoding="utf-8")
    with pytest.raises(ra.RotulagemError, match="fonte"):
        ra.Pacote(pasta)
    (pasta / ra.ARQ_SUGESTOES).write_text("release_id,corretiva,motivo,fonte\n1,talvez,x,IA\n", encoding="utf-8")
    with pytest.raises(ra.RotulagemError, match="inválido"):
        ra.Pacote(pasta)
    (pasta / ra.ARQ_SUGESTOES).write_text("release_id,corretiva,motivo,fonte\n999,sim,x,IA\n", encoding="utf-8")
    with pytest.raises(ra.RotulagemError, match="fora da amostra"):
        ra.Pacote(pasta)


def test_ferramenta_nao_usa_a_heuristica():
    import ast

    arvore = ast.parse(Path(ra.__file__).read_text(encoding="utf-8"))
    modulos = set()
    for n in ast.walk(arvore):
        if isinstance(n, ast.Import):
            modulos |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            modulos.add(n.module or "")
    assert not any(m.startswith("metricas") for m in modulos)
    assert "scripts.validacao_independente" not in modulos  # nada que execute a v12


def test_servidor_so_entrega_sugestao_depois_de_liberada_e_nao_vaza_heuristica(tmp_path):
    pasta = _pacote(tmp_path)
    srv = ra.criar_servidor(ra.Pacote(pasta), ra.Registro(pasta, "A"), porta=0)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        def get(p):
            return urllib.request.urlopen(base + p).read().decode()

        def post(p, b):
            rq = urllib.request.Request(base + p, json.dumps(b).encode(), {"Content-Type": "application/json"})
            try:
                return 200, json.loads(urllib.request.urlopen(rq).read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read())

        e0 = get("/api/estado")
        assert "nota fala em crash" not in e0 and "IA (teste)" not in e0  # sugestão não é enviada ao navegador
        assert not any(x in (e0 + get("/")).lower() for x in ("v12", "heuristic", "palavra_chave", "semver_patch"))
        it = ra.item_release("1")
        assert post("/api/sugestao", {"item": it})[0] == 400  # antes da decisão inicial
        assert post("/api/decisao", {"item": it, "valor": "nao", "fase": "inicial"})[0] == 200
        assert post("/api/sugestao", {"item": it})[0] == 200
        assert "nota fala em crash" in get("/api/estado")
        assert post("/api/decisao", {"item": it, "valor": "sim", "fase": "final"})[0] == 400  # sem confirmação
        assert post("/api/decisao", {"item": it, "valor": "sim", "fase": "final", "confirmou": True})[0] == 200
        assert post("/api/exportar", {})[0] == 200
    finally:
        srv.shutdown()


# ------------------------------------------------------------------------- modo comparação com a IA

def _hash_arquivos(pasta: Path) -> dict[str, str]:
    import hashlib
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in pasta.iterdir() if p.is_file()}


def test_comparacao_exige_sugestoes_e_usuario_valido(tmp_path):
    pasta = _pacote(tmp_path, com_sugestoes=False)
    with pytest.raises(ra.RotulagemError, match="exige"):
        ra.Comparacao(ra.Pacote(pasta), "A")
    pasta2 = _pacote(tmp_path / "x", com_sugestoes=True) if (tmp_path / "x").mkdir() is None else None
    with pytest.raises(ra.RotulagemError, match="não é avaliador"):
        ra.Comparacao(ra.Pacote(pasta2), "intruso")


def test_comparacao_acoes_exigem_confirmacao_e_registram_origem(tmp_path):
    comp = ra.Comparacao(ra.Pacote(_pacote(tmp_path)), "A")
    with pytest.raises(ra.RotulagemError, match="confirmação"):
        comp.agir("1", "confirmou")
    e1 = comp.agir("1", "confirmou", confirmou=True)  # IA sugeriu "sim"
    assert e1["valor_ia"] == "sim" and e1["valor_final_humano"] == "sim" and e1["decisao_vendo_sugestao"] is True
    assert e1["origem"] == "humano_via_interface_comparacao" and "IA" in e1["fonte_ia"]
    e2 = comp.agir("2", "alterou", "sim", confirmou=True)  # IA sugeriu "nao"
    assert e2["valor_final_humano"] == "sim"
    e3 = comp.agir("2", "rejeitou", confirmou=True)
    assert e3["valor_final_humano"] is None
    assert comp.estado()["2"]["acao"] == "rejeitou"  # último evento vale
    with pytest.raises(ra.RotulagemError, match="igual ao da sugestão"):
        comp.agir("1", "alterou", "sim", confirmou=True)
    with pytest.raises(ra.RotulagemError, match="sem sugestão"):
        comp.agir("3", "confirmou", confirmou=True)  # item 3 não tem sugestão no pacote de teste
    comp.limpar("2")
    assert "2" not in comp.estado()


def test_comparacao_nao_toca_labels_nem_log_do_modo_normal_nem_o_pacote_congelado(tmp_path):
    pasta = _pacote(tmp_path)
    antes = _hash_arquivos(pasta)
    comp = ra.Comparacao(ra.Pacote(pasta), "A")
    comp.agir("1", "confirmou", confirmou=True)
    comp.agir("2", "alterou", "sim", confirmou=True)
    comp.concluir()
    depois = _hash_arquivos(pasta)
    assert depois == antes  # labels_*.csv, amostra, dados e congelamento intactos
    assert not (pasta / "rotulagem").exists()
    assert sorted(p.name for p in (pasta / "comparacao_ia").iterdir()) == [
        "A.jsonl", "A_comparacao.csv", "A_comparacao_resumo.json"]


def test_comparacao_csv_e_resumo_marcam_origem_automatica_e_nao_validacao(tmp_path):
    pasta = _pacote(tmp_path)
    comp = ra.Comparacao(ra.Pacote(pasta), "A")
    comp.agir("1", "confirmou", confirmou=True)
    comp.agir("2", "alterou", "sim", confirmou=True)
    r = comp.concluir()
    assert r["n_confirmou"] == 1 and r["n_alterou"] == 1 and r["n_pendente"] == 0 and r["completo"] is True
    assert r["n_releases"] == 2  # só as releases com sugestão automática são comparáveis
    assert r["consumido_por_avaliar"] is False and "NÃO entra na validação independente" in r["natureza"]
    assert r["concordancia_com_ia"] == pytest.approx(0.5) and r["autenticacao"].startswith("nenhuma")
    linhas = list(csv.DictReader((pasta / "comparacao_ia/A_comparacao.csv").open(encoding="utf-8-sig")))
    assert len(linhas) == 2
    por = {l["release_id"]: l for l in linhas}
    assert por["1"]["origem_da_sugestao"] == "AUTOMÁTICA (IA)" and por["1"]["acao_do_avaliador"] == "confirmou"
    assert por["2"]["alterou_a_sugestao"] == "sim" and por["2"]["resposta_humana"] == "sim"
    assert all(l["decisao_vendo_sugestao"] == "sim" for l in linhas)


def test_comparacao_nao_sobrescreve_csv_editado_fora_da_ferramenta(tmp_path):
    pasta = _pacote(tmp_path)
    comp = ra.Comparacao(ra.Pacote(pasta), "A")
    comp.agir("1", "confirmou", confirmou=True)
    comp.concluir()
    comp.concluir()  # regenerar a própria saída é permitido
    (pasta / "comparacao_ia/A_comparacao.csv").write_text("editado à mão", encoding="utf-8")
    with pytest.raises(ra.RotulagemError, match="alterado fora da ferramenta"):
        comp.concluir()
    comp.concluir(forcar=True)
    assert (pasta / "comparacao_ia/A_comparacao.csv.bak").read_text() == "editado à mão"


def test_avaliar_nao_le_a_pasta_de_comparacao():
    assert "comparacao_ia" not in Path(vi.__file__).read_text(encoding="utf-8")


def test_servidor_de_comparacao_endpoints_e_aviso_na_pagina(tmp_path):
    pasta = _pacote(tmp_path)
    comp = ra.Comparacao(ra.Pacote(pasta), "A")
    srv = ra.criar_servidor_comparacao(comp, porta=0)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        def post(p, b):
            rq = urllib.request.Request(base + p, json.dumps(b).encode(), {"Content-Type": "application/json"})
            try:
                return 200, json.loads(urllib.request.urlopen(rq).read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read())

        pagina = urllib.request.urlopen(base + "/").read().decode()
        assert "gerados automaticamente por IA" in pagina and "não são decisões" in pagina.lower().replace("\n", " ")
        d = json.loads(urllib.request.urlopen(base + "/api/comp/estado").read())
        assert d["progresso"]["total"] == 2 and set(d["sugestoes"]) == {"1", "2"}
        assert post("/api/comp/acao", {"release_id": "1", "acao": "confirmou"})[0] == 400  # sem confirmou
        assert post("/api/comp/acao", {"release_id": "1", "acao": "confirmou", "confirmou": True})[0] == 200
        code, r = post("/api/comp/concluir", {})
        assert code == 200 and r["n_confirmou"] == 1 and r["n_pendente"] == 1 and r["completo"] is False
    finally:
        srv.shutdown()


def test_pagina_de_comparacao_tem_js_sem_quebra_de_linha_em_string():
    js = ra.PAGINA_COMP.split("<script>")[1]
    assert not [l for l in js.split("\n") if l.count("'") % 2 == 1 and "`" not in l]


def test_comparacao_item_sem_acao_fica_pendente_no_csv(tmp_path):
    pasta = _pacote(tmp_path)
    comp = ra.Comparacao(ra.Pacote(pasta), "A")
    comp.agir("1", "confirmou", confirmou=True)
    r = comp.concluir()
    por = {l["release_id"]: l for l in csv.DictReader((pasta / "comparacao_ia/A_comparacao.csv").open(encoding="utf-8-sig"))}
    assert por["2"]["acao_do_avaliador"] == "pendente" and por["2"]["resposta_humana"] == ""
    assert r["completo"] is False and r["n_pendente"] == 1


# ------------------------------------------------------------------------------ preenchimento em lote

def test_lote_preserva_acoes_humanas_e_preenche_so_pendentes_com_o_valor_exato_da_ia(tmp_path):
    pasta = _pacote(tmp_path)
    comp = ra.Comparacao(ra.Pacote(pasta), "A")
    comp.agir("1", "alterou", "nao", confirmou=True)  # IA sugeriu "sim"; humano alterou
    antes = comp.log.read_text(encoding="utf-8").splitlines()
    assert comp.pendentes() == ["2"]
    with pytest.raises(ra.RotulagemError, match="confirmação explícita"):
        comp.preencher_em_lote()
    r = comp.preencher_em_lote(confirmou=True)
    assert r["n_preenchidos"] == 1 and r["ja_resolvidos"] == 1
    depois = comp.log.read_text(encoding="utf-8").splitlines()
    assert depois[:len(antes)] == antes and len(depois) == len(antes) + 1  # só acréscimo
    est = comp.estado()
    assert est["1"]["acao"] == "alterou" and est["1"]["decisao_vendo_sugestao"] is True  # humano intacto
    lote = est["2"]
    assert lote["tipo"] == "acao_lote" and lote["origem"] == ra.ORIGEM_LOTE and lote["acao"] == ra.ACAO_LOTE
    assert lote["valor_registrado"] == "nao" == lote["valor_ia"]  # exatamente a sugestão (item 2: "nao")
    assert lote["decisao_humana"] is False and lote["valor_final_humano"] is None and lote["ts"]


def test_lote_nao_e_confirmacao_manual_no_csv_e_no_resumo(tmp_path):
    pasta = _pacote(tmp_path)
    comp = ra.Comparacao(ra.Pacote(pasta), "A")
    comp.agir("1", "confirmou", confirmou=True)
    comp.preencher_em_lote(confirmou=True)
    r = comp.concluir()
    assert r["completo"] is True and r["n_confirmou"] == 1 and r["n_preenchido_em_lote_ia"] == 1
    assert r["n_decisoes_humanas"] == 1 and r["n_registrados_em_lote_nao_humanos"] == 1
    assert r["n_com_resposta_humana"] == 1 and r["concordancia_com_ia"] == 1.0  # só itens humanos contam
    por = {l["release_id"]: l for l in csv.DictReader((pasta / "comparacao_ia/A_comparacao.csv").open(encoding="utf-8-sig"))}
    assert por["1"]["decisao_humana"] == "sim" and por["1"]["decisao_vendo_sugestao"] == "sim"
    l2 = por["2"]
    assert l2["decisao_humana"] == "nao" and l2["resposta_humana"] == "" and l2["valor_registrado"] == "nao"
    assert l2["acao_do_avaliador"] == "preenchido_em_lote_ia" and l2["origem_do_registro"] == ra.ORIGEM_LOTE
    assert l2["decisao_vendo_sugestao"] == "nao"


def test_lote_segunda_vez_nao_duplica_e_acao_humana_posterior_substitui(tmp_path):
    pasta = _pacote(tmp_path)
    comp = ra.Comparacao(ra.Pacote(pasta), "A")
    comp.preencher_em_lote(confirmou=True)
    assert comp.preencher_em_lote(confirmou=True)["n_preenchidos"] == 0  # nada pendente
    comp.agir("2", "alterou", "sim", confirmou=True)  # humano revisa um item do lote
    e = comp.estado()["2"]
    assert e["tipo"] == "acao" and e["acao"] == "alterou" and e["valor_final_humano"] == "sim"
    assert [x["tipo"] for x in comp.eventos()].count("acao_lote") == 2  # histórico do lote preservado


def test_lote_nao_toca_labels_nem_pacote(tmp_path):
    pasta = _pacote(tmp_path)
    antes = _hash_arquivos(pasta)
    comp = ra.Comparacao(ra.Pacote(pasta), "A")
    comp.preencher_em_lote(confirmou=True)
    comp.concluir()
    assert _hash_arquivos(pasta) == antes and not (pasta / "rotulagem").exists()


def test_cli_lote_sem_confirmacao_nao_escreve_nada(tmp_path, capsys):
    pasta = _pacote(tmp_path)
    rc = ra.main(["--usuario", "A", "--pasta", str(pasta), "--comparacao", "--preencher-em-lote"])
    assert rc == 2 and not (pasta / "comparacao_ia").exists()
    assert "--confirmar-lote" in capsys.readouterr().out
    rc = ra.main(["--usuario", "A", "--pasta", str(pasta), "--comparacao", "--preencher-em-lote", "--confirmar-lote"])
    assert rc == 0 and (pasta / "comparacao_ia/A.jsonl").exists()


# ------------------------------------------------------------------ transcrição de gabarito (fora da interface)

def test_transcricao_registra_origem_propria_e_exporta_sem_fingir_cliques(tmp_path):
    pasta = _pacote(tmp_path)
    reg = ra.Registro(pasta, "A")
    for rid, v in {"1": "sim", "2": "nao", "3": "sim", "4": "nao"}.items():
        ev = reg.transcrever(ra.item_release(rid), v, "transcricao_de_gabarito_md", "gabarito.md", "assistente a pedido")
        assert ev["origem"] == "transcricao_de_gabarito_md" and ev["origem"] != "humano_via_interface"
        assert ev["documento_de_origem"] == "gabarito.md" and ev["sugestao_vista_antes"] is False
    r = ra.exportar(ra.Pacote(pasta), reg)
    assert r["decisoes_por_origem"] == {"transcricao_de_gabarito_md": 4}
    assert r["completo"] is False  # tipo_projeto/entrega_real não vieram no gabarito: seguem pendentes
    linhas = list(csv.DictReader((pasta / "labels_A.csv").open(encoding="utf-8-sig")))
    assert [l["corretiva"] for l in linhas] == ["sim", "nao", "sim", "nao"]
    assert all(l["tipo_projeto"] == "" for l in linhas)


def test_transcricao_nao_sobrescreve_decisao_existente_e_valida_valor(tmp_path):
    reg = ra.Registro(_pacote(tmp_path), "A")
    reg.decidir(ra.item_release("1"), "nao", "inicial")
    with pytest.raises(ra.RotulagemError, match="não sobrescreve"):
        reg.transcrever(ra.item_release("1"), "sim", "o", "d", "t")
    with pytest.raises(ra.RotulagemError):
        reg.transcrever(ra.item_release("2"), "talvez", "o", "d", "t")


def test_transcricao_com_substituicao_registra_o_valor_anterior_e_o_ultimo_vale(tmp_path):
    reg = ra.Registro(_pacote(tmp_path), "A")
    it = ra.item_repo("a/x", "tipo_projeto")
    reg.transcrever(it, "outro", "o", "d", "t")
    with pytest.raises(ra.RotulagemError, match="não sobrescreve"):
        reg.transcrever(it, "aplicacao_servico", "o", "d", "t")
    ev = reg.transcrever(it, "aplicacao_servico", "correcao", "d", "t", substituir=True)
    assert ev["substitui_valor_anterior"] == "outro"
    assert reg.estado()[it]["inicial"] == "aplicacao_servico"
    assert len([e for e in reg.eventos() if e["item"] == it]) == 2  # histórico preservado
