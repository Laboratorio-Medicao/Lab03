"""Heurística de release corretiva (RQ03 b, Issue #27).

Uma release S é **corretiva** quando o objetivo principal dela é corrigir um defeito recente (E§5). O
GitHub não registra isso; a heurística infere a partir de dois sinais sugeridos pelo enunciado:

- **SemVer:** a versão muda só no *patch* em relação à release anterior (`2.3.0 → 2.3.1`);
- **palavra-chave:** algum commit entre as duas releases tem `revert`, `hotfix` ou `fix` como
  **palavra inteira** na mensagem (assunto + corpo), sem diferenciar caixa.

Regra v1 (exemplo do professor, E§5: "só muda o patch **e** contém o commit fix"):

- sem release anterior → não corretiva;
- tags SemVer comparáveis → `apenas_patch AND palavra_chave`;
- tags não comparáveis (não-SemVer ou prefixos diferentes) → só `palavra_chave` (o critério SemVer
  não se aplica).

A heurística **precisa** ser validada contra a amostra-ouro (E§6). Para o refino (Issue #28), `VERSOES`
registra variantes candidatas combinando os mesmos sinais, mais uma **palavra-chave ampla** (`fixes`,
`fixed`, `bugfix`, `reverted`…); `scripts.evaluate_heuristic` avalia todas e escolhe a final. Em todas as
versões, tags não comparáveis usam só a palavra-chave da versão, e release sem anterior nunca é corretiva.
A versão usada sai em `heuristic_version`.
"""

from __future__ import annotations

import re
from typing import Callable, Iterable, Mapping, NamedTuple

HEURISTIC_VERSION = "v1"

_NUM = r"(?:0|[1-9]\d*)"
# O prefixo é opcional e não pode terminar em dígito nem ponto: `1.2.3.4` não vira `1.` + `2.3.4`.
_SEMVER = re.compile(
    rf"^(?P<prefixo>(?:.*?[^\d.])??)(?P<major>{_NUM})\.(?P<minor>{_NUM})\.(?P<patch>{_NUM})"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$"
)
# `v`/`V` sozinho ou logo após um separador é só marca de versão: `v1.0.0` ≡ `1.0.0`, `pkg-v1.0.0` ≡ `pkg-1.0.0`.
_MARCA_V = re.compile(r"(?:^|(?<=[-_@/]))[vV]$")
_PALAVRA_CORRETIVA = re.compile(r"\b(?:revert|hotfix|fix)\b", re.IGNORECASE)
_PALAVRA_CORRETIVA_AMPLA = re.compile(
    r"\b(?:revert(?:s|ed)?|hotfix(?:es)?|fix(?:es|ed|ing)?|bugfix(?:es)?)\b", re.IGNORECASE
)

STATUS_OK = "ok"
STATUS_404 = "404"


class SemVer(NamedTuple):
    prefixo: str
    major: int
    minor: int
    patch: int
    pre: str | None


def parse_semver(tag: str | None) -> SemVer | None:
    """`MAJOR.MINOR.PATCH[-pre][+build]` com prefixo opcional; `None` se a tag não for SemVer.

    O prefixo volta normalizado (sem a marca `v`) para comparar linhas de versão em monorepos
    (`pkg@1.0.0` × `outro@1.0.1`). Build metadata é ignorado.
    """
    m = _SEMVER.match((tag or "").strip())
    if not m:
        return None
    return SemVer(
        prefixo=_MARCA_V.sub("", m["prefixo"]),
        major=int(m["major"]),
        minor=int(m["minor"]),
        patch=int(m["patch"]),
        pre=m["pre"],
    )


def apenas_patch(tag_anterior: str | None, tag: str | None) -> bool | None:
    """`True` se `tag` só sobe o patch de `tag_anterior`; `None` se as tags não são comparáveis.

    Não comparáveis: alguma das duas fora de SemVer ou prefixos diferentes. Uma `tag` com pré-release
    (`2.3.1-rc1`) não é bump de patch, nem a final de um RC (`2.3.1-rc1 → 2.3.1`, núcleo igual).
    """
    antes, depois = parse_semver(tag_anterior), parse_semver(tag)
    if antes is None or depois is None or antes.prefixo != depois.prefixo:
        return None
    return (
        depois.pre is None
        and (depois.major, depois.minor) == (antes.major, antes.minor)
        and depois.patch > antes.patch
    )


def tem_palavra_corretiva(mensagens: Iterable[str | None], ampla: bool = False) -> bool:
    """Algum commit cita `revert`, `hotfix` ou `fix` como palavra inteira (`prefix`/`fixes` não contam).

    `ampla=True` aceita também flexões e `bugfix` (`fixes`, `fixed`, `fixing`, `reverted`, `hotfixes`…).
    """
    padrao = _PALAVRA_CORRETIVA_AMPLA if ampla else _PALAVRA_CORRETIVA
    return any(padrao.search(m) for m in mensagens if m)


class Versao(NamedTuple):
    descricao: str
    regra: Callable[[Mapping], bool]


def _combina(operador: str, palavra: str) -> Callable[[Mapping], bool]:
    """Regra que junta `semver_patch` à palavra-chave `palavra`; tags não comparáveis → só a palavra."""
    def regra(sinais: Mapping) -> bool:
        patch, chave = sinais["semver_patch"], sinais[palavra]
        if patch is None or operador == "palavra":
            return chave
        if operador == "e":
            return patch and chave
        if operador == "ou":
            return patch or chave
        return patch  # operador "patch"
    return regra


VERSOES: dict[str, Versao] = {
    "v1": Versao("só patch E palavra estrita", _combina("e", "palavra_chave")),
    "v2": Versao("só patch OU palavra estrita", _combina("ou", "palavra_chave")),
    "v3": Versao("só palavra estrita (ignora SemVer)", _combina("palavra", "palavra_chave")),
    "v4": Versao("só patch (não comparável: palavra estrita)", _combina("patch", "palavra_chave")),
    "v5": Versao("só patch E palavra ampla", _combina("e", "palavra_chave_ampla")),
    "v6": Versao("só patch OU palavra ampla", _combina("ou", "palavra_chave_ampla")),
    "v7": Versao("só palavra ampla (ignora SemVer)", _combina("palavra", "palavra_chave_ampla")),
}


def avaliar(
    tag_anterior: str | None,
    tag: str | None,
    mensagens: Iterable[str | None],
    versao: str = HEURISTIC_VERSION,
) -> dict:
    """Classifica `tag` em relação à release anterior e aos commits entre as duas.

    Devolve `heuristic_corrective`, `heuristic_version` e os sinais usados (`semver_patch`,
    `palavra_chave`, `palavra_chave_ampla`), úteis para a análise de erros da heurística.
    """
    if versao not in VERSOES:
        raise ValueError(f"versão da heurística desconhecida: {versao!r} (conhecidas: {sorted(VERSOES)})")
    sinais = sinais_da_release(tag_anterior, tag, mensagens)
    return {"heuristic_corrective": corretiva(sinais, versao), "heuristic_version": versao, **sinais}


def sinais_da_release(tag_anterior: str | None, tag: str | None, mensagens: Iterable[str | None]) -> dict:
    """Sinais da heurística para `tag`; sem release anterior não há sinal (nunca corretiva)."""
    if tag_anterior is None:
        return {"semver_patch": None, "palavra_chave": False, "palavra_chave_ampla": False}
    mensagens = list(mensagens)
    return {
        "semver_patch": apenas_patch(tag_anterior, tag),
        "palavra_chave": tem_palavra_corretiva(mensagens),
        "palavra_chave_ampla": tem_palavra_corretiva(mensagens, ampla=True),
    }


def corretiva(sinais: Mapping, versao: str = HEURISTIC_VERSION) -> bool:
    """Aplica a regra de `versao` aos sinais de `sinais_da_release`."""
    return bool(VERSOES[versao].regra(sinais))


def classificar_releases(releases_commits: Iterable[Mapping], versao: str = HEURISTIC_VERSION) -> list[dict]:
    """Aplica a heurística a cada item de `pipeline.collect_commits.collect_commits(...)["releases"]`.

    Cada item tem `tag_name`, `base` (tag da release anterior ou `None`), `published_at`, `status` e
    `commits[].message`. A saída mantém a ordem e acrescenta o resultado de `avaliar` e
    `mensagens_incompletas` (`compare` com 404 ou truncado: a palavra-chave pode faltar por falta de
    dado). `release_id` não existe nesse formato: a junção com os rótulos é por `(full_name, tag_name)`.
    """
    saida = []
    for r in releases_commits:
        mensagens = [c.get("message") for c in r.get("commits") or []] if r.get("status") == STATUS_OK else []
        item = {
            "tag_name": r.get("tag_name"),
            "published_at": r.get("published_at"),
            "base": r.get("base"),
            "status": r.get("status"),
            **avaliar(r.get("base"), r.get("tag_name"), mensagens, versao),
            "mensagens_incompletas": r.get("status") == STATUS_404 or bool(r.get("truncado")),
        }
        if "id" in r:
            item["id"] = r["id"]
        saida.append(item)
    return saida
