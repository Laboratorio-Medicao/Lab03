"""Verifica que todo CSV de saída tem entrada no DICIONARIO_DE_DADOS.csv (Issue #20).

Falha se qualquer coluna aparecer em um CSV mas não estiver documentada no dicionário.
Isso garante que novos campos adicionados ao pipeline são sempre documentados.
"""

import csv
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent
DICIONARIO = RAIZ / "DICIONARIO_DE_DADOS.csv"

# CSVs de saída verificados automaticamente — mapeados para o nome no dicionário.
# labels_<avaliador>.csv usa o nome genérico "labels_<avaliador>.csv" no dicionário.
CSVS_SAIDA = {
    RAIZ / "outputs" / "resultados.csv": "resultados.csv",
    RAIZ / "outputs" / "repos_final.csv": "repos_final.csv",
    RAIZ / "outputs" / "funil.csv": "funil.csv",
    RAIZ / "data" / "amostra_ouro" / "amostra_ouro.csv": "amostra_ouro.csv",
}

LABELS_DIR = RAIZ / "data" / "amostra_ouro"
LABELS_NOME_DICIONARIO = "labels_<avaliador>.csv"


def _carregar_dicionario() -> dict[str, set[str]]:
    """Devolve {arquivo: {colunas documentadas}}."""
    entradas: dict[str, set[str]] = {}
    with DICIONARIO.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            arq = row["arquivo"].strip()
            col = row["coluna"].strip()
            entradas.setdefault(arq, set()).add(col)
    return entradas


def _colunas_csv(caminho: Path) -> list[str]:
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
    return [c.strip() for c in header if c.strip()]


# ---- testes parametrizados por arquivo ----

@pytest.mark.parametrize("csv_path,nome_dicionario", [
    (p, n) for p, n in CSVS_SAIDA.items() if p.exists()
])
def test_todas_colunas_documentadas(csv_path, nome_dicionario):
    dicionario = _carregar_dicionario()
    documentadas = dicionario.get(nome_dicionario, set())
    colunas = _colunas_csv(csv_path)
    nao_documentadas = [c for c in colunas if c not in documentadas]
    assert not nao_documentadas, (
        f"{csv_path.name}: colunas sem entrada no dicionário: {nao_documentadas}\n"
        f"Adicione cada uma em DICIONARIO_DE_DADOS.csv (arquivo={nome_dicionario})."
    )


def test_labels_avaliadores_documentadas():
    if not LABELS_DIR.exists():
        pytest.skip("data/amostra_ouro/ ainda não existe")
    dicionario = _carregar_dicionario()
    documentadas = dicionario.get(LABELS_NOME_DICIONARIO, set())
    for labels_csv in sorted(LABELS_DIR.glob("labels_*.csv")):
        colunas = _colunas_csv(labels_csv)
        nao_documentadas = [c for c in colunas if c not in documentadas]
        assert not nao_documentadas, (
            f"{labels_csv.name}: colunas sem entrada no dicionário: {nao_documentadas}\n"
            f"Adicione cada uma em DICIONARIO_DE_DADOS.csv (arquivo={LABELS_NOME_DICIONARIO})."
        )


def test_dicionario_nao_esta_vazio():
    dicionario = _carregar_dicionario()
    assert dicionario, "DICIONARIO_DE_DADOS.csv está vazio ou sem linhas válidas"
    total = sum(len(v) for v in dicionario.values())
    assert total >= 10, f"Esperado ≥10 entradas, encontrado {total}"


def test_dicionario_tem_colunas_obrigatorias():
    """O CSV do dicionário deve ter as colunas estruturais esperadas."""
    with DICIONARIO.open(encoding="utf-8") as f:
        fieldnames = csv.DictReader(f).fieldnames or []
    for campo in ("arquivo", "coluna", "tipo", "unidade", "formula_origem"):
        assert campo in fieldnames, f"DICIONARIO_DE_DADOS.csv: coluna '{campo}' ausente"
