"""v13 (EXPERIMENTAL, NÃO VALIDADA): v12 + H1 (sufixo de canal `-lts`/`-stable` não é pré-release).

Isolada nesta pasta: `metricas/heuristica.py` (v12) não é alterada nem importada de forma que a mude.
Para descartar a candidata, apague `experimental/v13/`.

H1: o conjunto de releases do estudo só contém `prerelease=false`. Uma tag como `v2.10.5-lts` ou
`v4.7.4-stable` nomeia um canal de manutenção, não um candidato a versão; SemVer, porém, a lê como
pré-release e `apenas_patch` devolve `False`, o que faz a v12 bloquear a release. A v13 remove esse
sufixo (e somente esse) de `tag` e `tag_anterior` ao calcular os sinais de SemVer. Nada mais muda:
`rc`, `alpha`, `beta`, `preview` e demais sufixos continuam sendo pré-release.

Origem da hipótese: erros da amostra de avaliação (formulada **depois** de ver o resultado). Portanto
qualquer F1 calculado nessa amostra é exploratório/pós-hoc e não valida esta versão.
"""

from __future__ import annotations

import re
from typing import Iterable

from metricas import heuristica as v12

VERSAO = "v13-experimental"
_CANAL = re.compile(r"-(?:lts|stable)$", re.IGNORECASE)


def sem_sufixo_de_canal(tag: str | None) -> str | None:
    """`v2.10.5-lts` → `v2.10.5`; `v1.0.0-rc1`, `v1.0.0-beta.2` e tags sem sufixo ficam iguais."""
    if tag is None:
        return None
    return _CANAL.sub("", tag.strip())


def corretiva(tag_anterior: str | None, tag: str | None, mensagens: Iterable[str | None], notas: str | None = "") -> dict:
    """Mesmo contrato de `metricas.heuristica.avaliar(..., "v12")`, com H1 aplicado.

    Devolve `heuristic_corrective`, `heuristic_version` (= `v13-experimental`) e os sinais usados.
    """
    mensagens = list(mensagens)
    base = sem_sufixo_de_canal(tag_anterior)
    atual = sem_sufixo_de_canal(tag)
    if base is None:
        return {"heuristic_corrective": False, "heuristic_version": VERSAO,
                "semver_patch": None, "patch_da_tag": None, "palavra_chave": False, "palavra_chave_ampla": False}
    sinais = v12.sinais_da_release(base, atual, mensagens)
    sinais = {**sinais, **v12.sinais_conteudo(mensagens, notas if notas is not None else "")}
    return {"heuristic_corrective": bool(v12._v12(sinais)), "heuristic_version": VERSAO, **sinais}
