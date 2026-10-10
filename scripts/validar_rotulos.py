"""Confere uma planilha de rótulos preenchida antes do commit (Issue #23).

Uso:

    python -m scripts.validar_rotulos data/amostra_ouro/labels_marcos.csv

Checa, sem interpretar o conteúdo dos rótulos:
- as linhas e a ordem batem com `amostra_ouro.csv` (mesmo `release_id`): ninguém alterou o sorteio;
- `tipo_projeto` e `releases_sao_entregas_reais` preenchidos na 1ª linha de cada repositório;
- `corretiva` preenchida em todas as linhas;
- só valores válidos (os mesmos do `LEIAME.md`).

Exit 0 = pronta para commitar; 1 = há pendências (listadas).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from scripts.sample_gold import CORRETIVA, ENTREGA_REAL, TIPOS_PROJETO


def _ler(arquivo: Path) -> list[dict]:
    with Path(arquivo).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validar(planilha: Path, amostra: Path | None = None) -> list[str]:
    """Lista de problemas (vazia = ok). `amostra` padrão: `amostra_ouro.csv` ao lado da planilha."""
    planilha = Path(planilha)
    amostra = Path(amostra) if amostra else planilha.parent / "amostra_ouro.csv"
    linhas = _ler(planilha)
    esperado = [str(r["release_id"]) for r in _ler(amostra)]
    obtido = [str(r.get("release_id", "")) for r in linhas]
    if obtido != esperado:
        return [f"release_id diferem de {amostra.name} ({len(obtido)} linhas, esperadas {len(esperado)}): "
                "não altere, remova nem reordene linhas"]

    problemas: list[str] = []

    def checar(n: int, linha: dict, coluna: str, validos: tuple[str, ...]) -> None:
        valor = (linha.get(coluna) or "").strip()
        rotulo = f"linha {n} ({linha['full_name']} {linha['tag_name']})"
        if not valor:
            problemas.append(f"{rotulo}: '{coluna}' vazia")
        elif valor not in validos:
            problemas.append(f"{rotulo}: '{coluna}'={valor!r} inválido (use {' | '.join(validos)})")

    repo_anterior = None
    for n, linha in enumerate(linhas, start=2):  # 1 = cabeçalho
        if linha["full_name"] != repo_anterior:
            checar(n, linha, "tipo_projeto", TIPOS_PROJETO)
            checar(n, linha, "releases_sao_entregas_reais", ENTREGA_REAL)
            repo_anterior = linha["full_name"]
        checar(n, linha, "corretiva", CORRETIVA)
    return problemas


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m scripts.validar_rotulos", description=__doc__.splitlines()[0])
    p.add_argument("planilha", help="labels_<nome>.csv preenchido")
    p.add_argument("--amostra", help="amostra_ouro.csv (padrão: ao lado da planilha)")
    args = p.parse_args(argv)
    try:
        problemas = validar(Path(args.planilha), Path(args.amostra) if args.amostra else None)
    except (OSError, KeyError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    if problemas:
        print(f"{len(problemas)} pendência(s):", file=sys.stderr)
        for texto in problemas[:50]:
            print(f"  - {texto}", file=sys.stderr)
        if len(problemas) > 50:
            print(f"  ... e mais {len(problemas) - 50}", file=sys.stderr)
        return 1
    print("OK: planilha completa e válida.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
