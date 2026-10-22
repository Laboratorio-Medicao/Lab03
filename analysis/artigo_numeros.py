"""Gera os números, tabelas e figuras de Resultados e Discussão a partir das saídas analíticas (Issue #42).

Todo número de `artigo/resultados.tex` vem de uma macro de `artigo/gerado/numeros.tex`, e as tabelas vêm de
`artigo/gerado/*.tex`; nada é digitado à mão. Rastreabilidade: macro → CSV de `outputs/analise/` (ou
`outputs/sensitivity_dora.csv`) → `data/metrics.csv`.

    python -m analysis.artigo_numeros [--check]

Sem `--check`, reescreve `artigo/gerado/` e copia os PNGs citados para `artigo/figs/`. Com `--check`, não
escreve nada: falha (código 1) se os arquivos versionados diferem do que seria gerado agora, se uma figura
citada no `.tex` não existe ou se `resultados.tex` usa macro não definida.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

from analysis import common
from metricas import dora

RAIZ = common.RAIZ
ANALISE = RAIZ / "outputs" / "analise"
SENS = RAIZ / "outputs" / "sensitivity_dora.csv"
SENS_PNG = RAIZ / "outputs" / "sensitivity_transicao.png"
DESTINO = RAIZ / "artigo" / "gerado"
FIGS = RAIZ / "artigo" / "figs"
RESULTADOS_TEX = RAIZ / "artigo" / "resultados.tex"
FIGURAS = [  # (origem, nome em artigo/figs)
    (ANALISE / "fig_rq01_rq02_rq04.png", "fig_rq01_rq02_rq04.png"),
    (ANALISE / "fig_rq05.png", "fig_rq05.png"),
    (ANALISE / "rq06_efeitos.png", "rq06_efeitos.png"),
    (SENS_PNG, "sensitivity_transicao.png"),
]
ROTULO_FATOR = {"linguagem": "Linguagem", "popularidade": "Popularidade", "contribuidores": "Contribuidores",
                "idade": "Idade", "tipo": "Tipo"}


def n(v: float, casas: int = 1) -> str:
    """Número no formato pt-BR. A vírgula decimal sai como `{,}`: dentro de $...$ uma vírgula nua ganha espaço
    (`0, 624`), e `{,}` evita isso sem afetar o texto corrido."""
    return f"{v:.{casas}f}".replace(".", "{,}").replace("-", "\\ensuremath{-}")


def pct(v: float, casas: int = 1) -> str:
    return n(v * 100, casas)


def p_tex(p: float) -> str:
    if p < 0.001:
        return "$<0{,}001$"
    return "$" + n(p, 3 if p >= 0.01 else 4).replace(",", "{,}") + "$"


def _csv(nome: str, base: Path = ANALISE) -> pd.DataFrame:
    return pd.read_csv(base / nome)


def macros() -> dict[str, str]:
    m: dict[str, str] = {}
    df = common.ler_metricas()
    total = len(df)
    desc = _csv("rq01_rq04_descritiva.csv").set_index("coluna")

    def trio(prefixo: str, col: str, f, casas: int):
        r = desc.loc[col]
        m[prefixo + "Med"], m[prefixo + "Qum"], m[prefixo + "Qtres"] = (f(r["mediana"], casas), f(r["q1"], casas), f(r["q3"], casas))
        m[prefixo + "Iqr"], m[prefixo + "N"] = f(r["iqr"], casas), str(int(r["n"]))

    trio("Df", "deployment_frequency", lambda v, c: n(v, c), 2)
    trio("Lta", "lt_release_median_h", lambda v, c: n(v, c), 1)
    trio("Ltb", "lt_commit_median_h", lambda v, c: n(v, c), 1)
    trio("Cfra", "cfr_a", lambda v, c: pct(v, c), 1)
    trio("Cfrb", "cfr_b", lambda v, c: pct(v, c), 1)
    trio("Rec", "rec_median_h", lambda v, c: n(v, c), 1)
    m["LtaDias"] = n(desc.loc["lt_release_median_h", "mediana"] / 24, 1)
    m["Total"] = str(total)

    por_metrica = _csv("dora_class_por_metrica.csv").set_index("categoria")
    for cat in common.CATEGORIAS:
        m[f"DfClasse{cat}"] = pct(por_metrica.loc[cat, "df_class"] / total)
        m[f"UmClasse{cat}"] = pct(por_metrica.loc[cat, "dora_c1"] / total)
        m[f"UmN{cat}"] = str(int(por_metrica.loc[cat, "dora_c1"]))

    # RQ02: divergência por repositório
    d = _csv("rq02_divergencia.csv").set_index("indicador")["valor"]
    m["RazMed"], m["RazQum"], m["RazQtres"] = n(d["razao_mediana"], 2), n(d["razao_q1"], 2), n(d["razao_q3"], 2)
    m["RazAdobroB"], m["RazAmenorB"] = pct(d["prop_a_maior_que_2b"], 0), pct(d["prop_a_menor_que_b"], 0)
    m["RazBdobroA"], m["RazMeio"] = pct(d["prop_b_maior_que_2a"], 0), pct(d["prop_entre_metade_e_dobro"], 0)
    m["RazWilcoxonP"] = p_tex(d["wilcoxon_pareado_p"])
    m["RazRho"], m["RazRhoP"] = n(d["spearman_log_razao_vs_n_releases_rho"], 2), p_tex(d["spearman_log_razao_vs_n_releases_p"])

    # RQ04: censura
    c = _csv("rq04_censura_resumo.csv").set_index("indicador")["valor"]
    m["CensEp"], m["CensTot"] = f"{int(c['episodios_censurados']):,}".replace(",", "."), f"{int(c['episodios_total']):,}".replace(",", ".")
    m["CensPct"] = pct(c["prop_global"])
    m["CensRepoMed"], m["CensRepoQtres"] = pct(c["prop_repo_mediana"], 0), pct(c["prop_repo_q3"])
    m["CensReposCom"], m["CensReposAlgum"] = str(int(c["repos_com_episodios"])), str(int(c["repos_com_algum_censurado"]))
    m["CensReposSem"] = str(int(c["repos_sem_episodios"]))
    so_cens = int(((df["n_episodios"] > 0) & df["rec_median_h"].isna()).sum())
    m["CensSoCens"], m["RecSemValor"] = str(so_cens), str(int(df["rec_median_h"].isna().sum()))

    # RQ05
    r5 = _csv("rq05_spearman.csv").set_index("variante")
    for v in "ab":
        x = r5.loc[v]
        m[f"Rho{v.upper()}"], m[f"RhoN{v.upper()}"] = n(x["rho"], 3), str(int(x["n"]))
        m[f"RhoIc{v.upper()}"] = f"[{n(x['ic95_inf'], 2)};\\,{n(x['ic95_sup'], 2)}]".replace(",", "{,}", 0)
        m[f"RhoP{v.upper()}"] = p_tex(x["p_valor"])
    sens5 = _csv("rq05_sensibilidade_cfr_b.csv").set_index("min_releases_avaliadas")
    m["RhoBVinte"], m["RhoBVinteN"] = n(sens5.loc[20, "rho"], 2), str(int(sens5.loc[20, "n"]))
    m["RhoBCinco"] = n(sens5.loc[5, "rho"], 2)

    # RQ06
    t6 = _csv("rq06_testes.csv")
    m["SeisTestes"] = str(int(t6["p_bruto"].notna().sum()))
    m["SeisSig"] = str(int((t6["significativo_holm"] == True).sum()))  # noqa: E712
    eps_sig = t6.loc[t6["significativo_holm"] == True, "efeito"]  # noqa: E712
    m["EpsSigMin"], m["EpsSigMax"] = n(eps_sig.min(), 2), n(eps_sig.max(), 2)
    g6 = _csv("rq06_grupos.csv")

    def grupo(fator, grupo_, col, campo="mediana"):
        return g6[(g6.fator == fator) & (g6.grupo == grupo_) & (g6.coluna == col)].iloc[0][campo]

    m["IdadeDfQum"], m["IdadeDfQquatro"] = n(grupo("idade", "Q1", "deployment_frequency"), 2), n(grupo("idade", "Q4", "deployment_frequency"), 2)
    m["IdadeCfrbQum"], m["IdadeCfrbQquatro"] = pct(grupo("idade", "Q1", "cfr_b"), 1), pct(grupo("idade", "Q4", "cfr_b"), 1)
    m["IdadeLtaQum"], m["IdadeLtaQquatro"] = n(grupo("idade", "Q1", "lt_release_median_h"), 0), n(grupo("idade", "Q4", "lt_release_median_h"), 0)
    m["ContribLtaQum"], m["ContribLtaQquatro"] = n(grupo("contribuidores", "Q1", "lt_release_median_h"), 0), n(grupo("contribuidores", "Q4", "lt_release_median_h"), 0)
    m["TipoN"] = str(int(t6[t6.fator == "tipo"]["n"].max()))
    pop = t6[t6.fator == "popularidade"]
    m["PopMinPHolm"] = n(pop["p_holm"].min(), 2)

    # RQ07
    s7 = _csv("sensitivity_dora.csv", RAIZ / "outputs").set_index("par")
    for par, nome in (("C1×C2", "UmDois"), ("C1×C3", "UmTres"), ("C2×C3", "DoisTres")):
        m[f"Sens{nome}Pct"], m[f"Sens{nome}Kappa"] = n(s7.loc[par, "pct_mudou"], 1), n(s7.loc[par, "kappa_linear"], 2)
    for c_, nome in (("c1", "CUm"), ("c2", "CDois"), ("c3", "CTres")):
        m[f"Parcial{nome}"] = str(int((df[f"n_metricas_dora_{c_}"] < 4).sum()))
    amp = _csv("sensitivity_ampliada.csv", RAIZ / "outputs").set_index("variacao")
    inf = amp.loc[["cfr_b_janela_3d_vs_7d", "cfr_b_janela_14d_vs_7d", "cortes_mais10pct", "cortes_menos10pct"]]
    m["AmpInfMinPct"], m["AmpInfMaxPct"] = n(inf["pct_mudou"].min(), 1), n(inf["pct_mudou"].max(), 1)
    m["AmpInfKappaMin"] = n(inf["kappa_linear"].min(), 2)

    # RQ08
    d8 = _csv("rq08_descritiva.csv").set_index("coluna")
    m["RwMed"], m["RwQum"], m["RwQtres"] = pct(d8.loc["rework_rate", "mediana"].iloc[0]), pct(d8.loc["rework_rate", "q1"].iloc[0]), pct(d8.loc["rework_rate", "q3"].iloc[0])
    m["RwN"] = str(int(d8.loc["rework_rate", "n"].iloc[0]))
    m["RwCfrbMed"] = pct(d8.loc["cfr_b", "mediana"])
    m["RwDifIqr"] = n(d8.loc["diferenca_rework_cfr_b", "iqr"] * 100, 1)
    m["RwDifQum"], m["RwDifQtres"] = pct(d8.loc["diferenca_rework_cfr_b", "q1"]), pct(d8.loc["diferenca_rework_cfr_b", "q3"])
    c8 = _csv("rq08_comparacao.csv").set_index("indicador")["valor"]
    m["RwSpearman"], m["RwWilcoxonP"] = n(c8["spearman_rework_cfr_b_rho"], 2), p_tex(c8["wilcoxon_p"])
    m["RwExcluidos"] = str(int(c8["repos_divergentes"]))
    return m


def tabela_resumo() -> str:
    df = common.ler_metricas()
    desc = _csv("rq01_rq04_descritiva.csv").set_index("coluna")
    fn = {"deployment_frequency": lambda v: dora.classify_df(v, common.SEMANAS_JANELA),
          "lt_release_median_h": dora.classify_lt, "lt_commit_median_h": dora.classify_lt,
          "cfr_a": dora.classify_cfr, "cfr_b": dora.classify_cfr, "rec_median_h": dora.classify_recovery}
    nomes = [("RQ01", "Deployment frequency (rel./sem.)", "deployment_frequency", 2, False),
             ("RQ02", "Lead time (a), por release (h)", "lt_release_median_h", 1, False),
             ("RQ02", "Lead time (b), por commit (h)", "lt_commit_median_h", 1, False),
             ("RQ03", "CFR (a), proxy de CI (\\%)", "cfr_a", 1, True),
             ("RQ03", "CFR (b), proxy de entrega (\\%)", "cfr_b", 1, True),
             ("RQ04", "Recuperação (h)", "rec_median_h", 1, False)]
    linhas = []
    for rq, nome, col, casas, em_pct in nomes:
        r = desc.loc[col]
        f = (lambda v: pct(v, casas)) if em_pct else (lambda v: n(v, casas))
        classes = df[col].dropna().map(lambda v: fn[col](float(v)))
        cont = [int((classes == c).sum()) for c in common.CATEGORIAS]
        linhas.append(f"{rq} & {nome} & {int(r['n'])} & {f(r['mediana'])} & {f(r['q1'])} & {f(r['q3'])} & {f(r['iqr'])} & "
                      f"{fn[col](float(r['mediana']))} & {'/'.join(map(str, cont))} \\\\")
    return "\n".join([
        "% Gerado por analysis/artigo_numeros.py a partir de outputs/analise/rq01_rq04_descritiva.csv. Não editar.",
        "\\begin{tabular}{llrrrrrll}", "\\hline",
        "RQ & Métrica & $n$ & Mediana & Q1 & Q3 & IQR & Classe (mediana) & E/H/M/L \\\\ \\hline",
        *linhas, "\\hline", "\\end{tabular}"]) + "\n"


def tabela_rq06() -> str:
    t = _csv("rq06_testes.csv")
    s = t[t["significativo_holm"] == True].copy()  # noqa: E712
    s = s.sort_values("p_holm")
    linhas = []
    for _, r in s.iterrows():
        linhas.append(f"{ROTULO_FATOR[r['fator']]} & {r['metrica'].replace('proxy de entrega', 'proxy de entrega')} & "
                      f"{int(r['n'])} & {n(r['estatistica'], 1)} & {p_tex(r['p_holm'])} & {n(r['efeito'], 3)} & {r['magnitude']} \\\\")
    return "\n".join([
        "% Gerado por analysis/artigo_numeros.py a partir de outputs/analise/rq06_testes.csv. Não editar.",
        "\\begin{tabular}{llrrrrl}", "\\hline",
        "Fator & Métrica & $n$ & $H$ & $p_{\\mathrm{Holm}}$ & $\\varepsilon^2$ & Magnitude \\\\ \\hline",
        *linhas, "\\hline", "\\end{tabular}"]) + "\n"


def tabela_rq07() -> str:
    s = _csv("sensitivity_dora.csv", RAIZ / "outputs")
    linhas = [f"{r['par'].replace('×', '$\\times$')} & {int(r['n'])} & {int(r['n_mudou'])} & {n(r['pct_mudou'], 1)} & {n(r['kappa_linear'], 2)} \\\\"
              for _, r in s.iterrows()]
    return "\n".join([
        "% Gerado por analysis/artigo_numeros.py a partir de outputs/sensitivity_dora.csv. Não editar.",
        "\\begin{tabular}{lrrrr}", "\\hline",
        "Par & $n$ & Mudaram & \\% que mudou & $\\kappa$ linear \\\\ \\hline",
        *linhas, "\\hline", "\\end{tabular}"]) + "\n"


def arquivos_gerados() -> dict[str, str]:
    mac = macros()
    corpo = ["% Gerado por analysis/artigo_numeros.py. Não editar: reexecute o script.",
             *[f"\\newcommand{{\\N{k}}}{{{v}}}" for k, v in sorted(mac.items())],
             "% variantes com ponto decimal (resumo em inglês)",
             *[f"\\newcommand{{\\NEn{k}}}{{{re.sub(r'(?<=\d),(?=\d)', '.', v.replace('{,}', '.'))}}}" for k, v in sorted(mac.items())]]
    return {"numeros.tex": "\n".join(corpo) + "\n", "tabela_resumo.tex": tabela_resumo(),
            "tabela_rq06.tex": tabela_rq06(), "tabela_rq07.tex": tabela_rq07()}


def verificar() -> list[str]:
    erros = []
    for nome, texto in arquivos_gerados().items():
        alvo = DESTINO / nome
        if not alvo.exists() or alvo.read_text(encoding="utf-8") != texto:
            erros.append(f"artigo/gerado/{nome} difere das saídas atuais (rode python -m analysis.artigo_numeros)")
    for origem, nome in FIGURAS:
        if not (FIGS / nome).exists():
            erros.append(f"artigo/figs/{nome} ausente")
        elif origem.exists() and (FIGS / nome).read_bytes() != origem.read_bytes():
            erros.append(f"artigo/figs/{nome} difere de {origem.relative_to(RAIZ)}")
    if RESULTADOS_TEX.exists():
        tex = RESULTADOS_TEX.read_text(encoding="utf-8")
        definidas = set(re.findall(r"\\newcommand\{\\(N\w+)\}", arquivos_gerados()["numeros.tex"]))
        for usada in sorted(set(re.findall(r"\\(N[A-Z]\w*)", tex)) - definidas):
            erros.append(f"macro \\{usada} usada em resultados.tex e não definida")
        for fig in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex):
            if not (RAIZ / "artigo" / fig).exists():
                erros.append(f"figura citada em resultados.tex não existe: artigo/{fig}")
        for tab in re.findall(r"\\input\{(gerado/[^}]+)\}", tex):
            if not (RAIZ / "artigo" / (tab + ".tex" if not tab.endswith(".tex") else tab)).exists():
                erros.append(f"tabela citada em resultados.tex não existe: artigo/{tab}")
    chaves = set(re.findall(r"^@\w+\{([^,]+),", (RAIZ / "artigo" / "referencias.bib").read_text(encoding="utf-8"), re.M))
    for tex_ in sorted((RAIZ / "artigo").glob("*.tex")):
        sem_comentario = re.sub(r"(?<!\\)%.*", "", tex_.read_text(encoding="utf-8"))
        for grupo in re.findall(r"\\cite\w*\{([^}]+)\}", sem_comentario):
            for chave in (c.strip() for c in grupo.split(",")):
                if chave not in chaves:
                    erros.append(f"{tex_.name}: citação sem entrada em referencias.bib: {chave}")
    return erros


def gerar() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    for nome, texto in arquivos_gerados().items():
        (DESTINO / nome).write_text(texto, encoding="utf-8")
    for origem, nome in FIGURAS:
        shutil.copyfile(origem, FIGS / nome)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="só verifica; não escreve")
    a = ap.parse_args(argv)
    if a.check:
        erros = verificar()
        for e in erros:
            print("ERRO:", e)
        print("conferência OK" if not erros else f"{len(erros)} erro(s)")
        return 1 if erros else 0
    gerar()
    print(f"gerado: artigo/gerado/ ({len(arquivos_gerados())} arquivos) e artigo/figs/ ({len(FIGURAS)} figuras)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
