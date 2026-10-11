"""Consolida o dataset final após a execução completa do pipeline (Issue #19).

Lê outputs/resultados.csv, filtra os repositórios com status=concluido, conta
episódios censurados e releases ignoradas por 404 e gera repos_final.csv — o
dataset congelado para o sorteio da amostra-ouro.

Uso:
    python -m pipeline.consolidate_dataset --config config.yaml
    python -m pipeline.consolidate_dataset --resultados outputs/resultados.csv \
                                            --saida outputs/repos_final.csv
"""

import argparse
import csv
import sys
from pathlib import Path


# Colunas de auditoria que não fazem parte do dataset analítico final.
_COLUNAS_INTERNAS = {"status", "erro"}


def consolidar(resultados_csv: Path, repos_final_csv: Path) -> dict:
    """Filtra concluídos, escreve repos_final.csv e devolve métricas do funil.

    Retorna um dict com:
      - n_total: linhas em resultados.csv
      - n_concluidos: repos com status=concluido
      - n_erros: repos com status != concluido
      - n_episodios_censurados: soma de n_episodios_censurados dos concluídos
      - n_episodios: soma de n_episodios dos concluídos
      - n_releases_ignored_404: soma de n_releases_ignored_404 dos concluídos
    """
    rows = list(csv.DictReader(resultados_csv.open(encoding="utf-8")))

    concluidos = [r for r in rows if r.get("status") == "concluido"]
    erros = [r for r in rows if r.get("status") != "concluido"]

    def _soma(campo: str, subset: list[dict]) -> int:
        total = 0
        for r in subset:
            try:
                total += int(r.get(campo) or 0)
            except (ValueError, TypeError):
                pass
        return total

    metricas = {
        "n_total": len(rows),
        "n_concluidos": len(concluidos),
        "n_erros": len(erros),
        "n_episodios_censurados": _soma("n_episodios_censurados", concluidos),
        "n_episodios": _soma("n_episodios", concluidos),
        "n_releases_ignored_404": _soma("n_releases_ignored_404", concluidos),
    }

    if concluidos:
        fieldnames = [c for c in concluidos[0].keys() if c not in _COLUNAS_INTERNAS]
        repos_final_csv.parent.mkdir(parents=True, exist_ok=True)
        with repos_final_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(concluidos)

    return metricas


def _imprimir_funil(m: dict, repos_final_csv: Path) -> None:
    print("=" * 60)
    print("FUNIL FINAL — CONSOLIDAÇÃO DO DATASET")
    print("=" * 60)
    print(f"  Repositórios coletados (resultados.csv) : {m['n_total']:>5}")
    print(f"  Concluídos com sucesso                  : {m['n_concluidos']:>5}")
    print(f"  Com erro / incompletos                  : {m['n_erros']:>5}")
    print()
    print("QUALIDADE DOS CONCLUÍDOS")
    print(f"  Episódios de falha identificados        : {m['n_episodios']:>5}")
    print(f"  Episódios censurados (sem recuperação)  : {m['n_episodios_censurados']:>5}", end="")
    if m["n_episodios"]:
        pct = 100 * m["n_episodios_censurados"] / m["n_episodios"]
        print(f"  ({pct:.1f} %)")
    else:
        print()
    print(f"  Releases ignoradas por 404              : {m['n_releases_ignored_404']:>5}")
    print()
    if m["n_concluidos"]:
        print(f"  Dataset congelado salvo em: {repos_final_csv}")
    else:
        print("  AVISO: nenhum repo concluído — repos_final.csv não foi gerado.")
    print("=" * 60)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config.yaml", help="caminho para config.yaml")
    parser.add_argument("--resultados", default=None, help="sobrescreve o caminho de resultados.csv")
    parser.add_argument("--saida", default=None, help="sobrescreve o caminho de repos_final.csv")
    args = parser.parse_args(argv)

    if args.resultados and args.saida:
        resultados_csv = Path(args.resultados)
        repos_final_csv = Path(args.saida)
    else:
        from pipeline.config import load_config

        cfg = load_config(args.config)
        resultados_csv = cfg.saidas_dir / "resultados.csv"
        repos_final_csv = cfg.saidas_dir / "repos_final.csv"

    if not resultados_csv.is_file():
        print(f"ERRO: arquivo não encontrado: {resultados_csv}", file=sys.stderr)
        sys.exit(1)

    metricas = consolidar(resultados_csv, repos_final_csv)
    _imprimir_funil(metricas, repos_final_csv)


if __name__ == "__main__":
    main()
