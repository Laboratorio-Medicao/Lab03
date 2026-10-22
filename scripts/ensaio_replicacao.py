"""Ensaio de autorreplicação: sorteia 30 repos de data/metrics.csv (semente 42),
executa o pipeline sobre eles com saídas separadas e compara o resultado
com data/metrics.csv usando replicacao/compara.py.

Uso:
    python -m scripts.ensaio_replicacao [--csv data/metrics.csv]
        [--saida outputs/ensaio_replicacao] [--config config.yaml]
        [--repos-file replicacao/repos_30.txt] [--sem-pipeline]

--sem-pipeline: pula a execução do pipeline (usa saídas já existentes em --saida).
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).parent.parent
log = logging.getLogger("ensaio_replicacao")


def sortear_repos(csv: Path, n: int = 30, semente: int = 42) -> pd.DataFrame:
    df = pd.read_csv(csv)
    return df.sample(n=n, random_state=semente)[["full_name"]].reset_index(drop=True)


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def salvar_repos_file(repos: pd.DataFrame, destino: Path, sha_origem: str) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    linhas = [
        f"# Sorteio: df.sample(n=30, random_state=42) de data/metrics.csv",
        f"# sha256(data/metrics.csv): {sha_origem}",
        f"# Gerado em: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
    ] + list(repos["full_name"])
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def executar_pipeline(
    config: Path,
    repos_file: Path,
    saida_dir: Path,
) -> tuple[int, float]:
    """Executa o pipeline e devolve (returncode, elapsed_seconds)."""
    saida_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "pipeline",
        "--config", str(config),
        "--repos-file", str(repos_file),
    ]
    inicio = time.monotonic()
    result = subprocess.run(cmd, cwd=str(RAIZ), capture_output=False)
    elapsed = time.monotonic() - inicio
    return result.returncode, elapsed


def registrar_log(
    caminho: Path,
    repos_file: Path,
    n_repos: int,
    sha_metricas: str,
    returncode: int,
    elapsed: float,
    resultado_compara: dict | None,
) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    linhas = [
        f"# Ensaio de autorreplicação",
        f"data: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"SO: {platform.system()} {platform.release()} {platform.machine()}",
        f"Python: {sys.version}",
        f"repos_file: {repos_file}",
        f"n_repos: {n_repos}",
        f"sha256(data/metrics.csv): {sha_metricas}",
        f"pipeline_returncode: {returncode}",
        f"pipeline_tempo_s: {elapsed:.1f}",
    ]
    if resultado_compara is not None:
        r = resultado_compara
        linhas += [
            f"comparados: {r['n_comparados']}/{n_repos}",
            f"ausentes_replicado: {len(r['ausentes_replicado'])}",
        ]
        for col, val in r["diferencas_relativas"].items():
            linhas.append(f"  dif_rel_{col}: {val:.4f}" if val is not None else f"  dif_rel_{col}: —")
        for col, pct in r["concordancia_classe"].items():
            import math
            linhas.append(f"  concordancia_{col}: {pct:.1f}%" if not math.isnan(pct) else f"  concordancia_{col}: —")
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def run(
    csv: Path = RAIZ / "data" / "metrics.csv",
    saida_dir: Path = RAIZ / "outputs" / "ensaio_replicacao",
    config: Path = RAIZ / "config.yaml",
    repos_file: Path = RAIZ / "replicacao" / "repos_30.txt",
    sem_pipeline: bool = False,
) -> dict:
    sha = sha256_arquivo(csv)
    repos = sortear_repos(csv)
    salvar_repos_file(repos, repos_file, sha)
    log.info("Sorteados %d repos → %s", len(repos), repos_file)

    returncode, elapsed = 0, 0.0
    if not sem_pipeline:
        log.info("Executando pipeline sobre os 30 repos…")
        returncode, elapsed = executar_pipeline(config, repos_file, saida_dir)
        log.info("Pipeline concluído em %.1fs (returncode=%d)", elapsed, returncode)
    else:
        log.info("--sem-pipeline: pulando execução")

    resultado_compara = None
    replicado_csv = saida_dir / "repos_final.csv"
    if replicado_csv.exists():
        try:
            from replicacao.compara import run as compara_run
            resultado_compara = compara_run(csv, replicado_csv, saida_dir, n_alvo=len(repos))
            log.info("Comparação concluída: %d/%d repos comparados",
                     resultado_compara["n_comparados"], len(repos))
        except ImportError:
            log.warning("replicacao.compara não disponível; pulando comparação")
    else:
        log.warning("CSV replicado não encontrado em %s; pulando comparação", replicado_csv)

    registrar_log(
        saida_dir / "ensaio.log",
        repos_file, len(repos), sha, returncode, elapsed, resultado_compara,
    )

    return {
        "n_repos": len(repos),
        "sha_metricas": sha,
        "returncode": returncode,
        "elapsed": elapsed,
        "resultado_compara": resultado_compara,
    }


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", default=str(RAIZ / "data" / "metrics.csv"))
    parser.add_argument("--saida", default=str(RAIZ / "outputs" / "ensaio_replicacao"))
    parser.add_argument("--config", default=str(RAIZ / "config.yaml"))
    parser.add_argument("--repos-file", default=str(RAIZ / "replicacao" / "repos_30.txt"))
    parser.add_argument("--sem-pipeline", action="store_true")
    args = parser.parse_args(argv)

    resultado = run(
        csv=Path(args.csv),
        saida_dir=Path(args.saida),
        config=Path(args.config),
        repos_file=Path(args.repos_file),
        sem_pipeline=args.sem_pipeline,
    )
    print(f"Sorteados: {resultado['n_repos']} repos")
    print(f"sha256(metrics.csv): {resultado['sha_metricas']}")
    if not args.sem_pipeline:
        print(f"Pipeline: returncode={resultado['returncode']}, tempo={resultado['elapsed']:.1f}s")
    if resultado["resultado_compara"]:
        r = resultado["resultado_compara"]
        print(f"Comparados: {r['n_comparados']}/{resultado['n_repos']}")


if __name__ == "__main__":
    main()
