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
A versão usada sai em `heuristic_version` e é **sempre explícita**: `avaliar`, `corretiva` e
`classificar_releases` não têm versão padrão (`HEURISTIC_VERSION` é só a referência da regra v1).

v8/v9 (refino da Issue #28, depois de a v1–v7 ficarem abaixo de F1 0,70 na amostra-ouro) olham o
**conteúdo** da release, não o número da versão: contam commits de correção e de feature (`sinais_conteudo`)
e, na v9, as *release notes* (as mesmas que os avaliadores leram, E§6). Ver `docs/refino_heuristica.md`.
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

# --- sinais de conteúdo (v8/v9) -------------------------------------------------------------------
# Commits "de ruído" (manutenção, docs, versão) não dizem qual era o objetivo da release e saem da conta.
_RUIDO = re.compile(
    r"^\W*\[?(?:chore|docs?|ci|build|deps?|bump|test|tests|style|refactor|release|merge|update|prepare"
    r"|version|v?\d)|^Merge |dependabot|bump ",
    re.IGNORECASE,
)
_ASSUNTO_CORRECAO = re.compile(
    r"^\W*\[?(?:hot|bug)?fix(?:es|ed)?\b|^\W*revert\b|\b(?:hotfix|bugfix)\b", re.IGNORECASE
)
_ASSUNTO_FEATURE = re.compile(
    r"^\W*\[?(?:feat|feature|add|support|implement|introduce)\b", re.IGNORECASE
)
_NOTA_CORRECAO = re.compile(
    r"\b(?:bug ?fix(?:es)?|fix(?:es|ed)?|hotfix|patch release|security (?:fix|release)|regression"
    r"|crash(?:es)?|revert(?:ed)?|vulnerabilit\w+|corrig\w+)\b|🩹|🐛",
    re.IGNORECASE,
)
_NOTA_NOVIDADE = re.compile(
    r"\b(?:new features?|features?|added|adds?|introduc\w+|enhancements?|improvements?|support for"
    r"|now (?:supports?|available))\b|✨|🚀|💝",
    re.IGNORECASE,
)
_LIMPA_NOTA = re.compile(r"https?://\S+|\(#\d+\)|#\d+")
_MAX_NOTA = 1500

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


def sinais_conteudo(mensagens: Iterable[str | None], notas: str | None = None) -> dict:
    """Sinais de conteúdo da v8/v9: commits de correção/feature e termos nas release notes.

    `n_correcoes` e `n_features` contam só commits substantivos (assunto fora de `_RUIDO`). Sem `notas`
    (não coletadas), `nota_correcao` e `nota_novidade` são `None` e a v9 cai na regra da v8.
    """
    assuntos = [(m or "").split("\n")[0] for m in mensagens]
    substantivos = [a for a in assuntos if a and not _RUIDO.search(a)]
    sinais = {
        "n_correcoes": sum(1 for a in substantivos if _ASSUNTO_CORRECAO.search(a)),
        "n_features": sum(1 for a in substantivos if _ASSUNTO_FEATURE.search(a)),
        "nota_correcao": None,
        "nota_novidade": None,
    }
    if notas is not None:
        texto = _LIMPA_NOTA.sub(" ", notas)[:_MAX_NOTA]
        sinais["nota_correcao"] = bool(_NOTA_CORRECAO.search(texto))
        sinais["nota_novidade"] = bool(_NOTA_NOVIDADE.search(texto))
    return sinais


class Versao(NamedTuple):
    descricao: str
    regra: Callable[[Mapping], bool]
    usa_conteudo: bool = False  # precisa dos sinais de `sinais_conteudo`
    exige_notas: bool = False  # a regra olha as release notes (`body`): sem elas a versão não roda


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


def _correcao_sem_feature(sinais: Mapping) -> bool:
    return (sinais.get("n_correcoes") or 0) >= 1 and (sinais.get("n_features") or 0) == 0


def _nota_corretiva(sinais: Mapping) -> bool:
    return bool(sinais.get("nota_correcao")) and not sinais.get("nota_novidade")


VERSOES: dict[str, Versao] = {
    "v1": Versao("só patch E palavra estrita", _combina("e", "palavra_chave")),
    "v2": Versao("só patch OU palavra estrita", _combina("ou", "palavra_chave")),
    "v3": Versao("só palavra estrita (ignora SemVer)", _combina("palavra", "palavra_chave")),
    "v4": Versao("só patch (não comparável: palavra estrita)", _combina("patch", "palavra_chave")),
    "v5": Versao("só patch E palavra ampla", _combina("e", "palavra_chave_ampla")),
    "v6": Versao("só patch OU palavra ampla", _combina("ou", "palavra_chave_ampla")),
    "v7": Versao("só palavra ampla (ignora SemVer)", _combina("palavra", "palavra_chave_ampla")),
    "v8": Versao("commit de correção e nenhum de feature", _correcao_sem_feature, usa_conteudo=True),
    "v9": Versao(
        "v8 OU release notes com correção e sem novidade",
        lambda s: _correcao_sem_feature(s) or _nota_corretiva(s),
        usa_conteudo=True,
        exige_notas=True,
    ),
}


class DadosAusentesError(ValueError):
    """A versão pedida depende de um dado que não foi fornecido (ex.: release notes da v9)."""


def _exigir_versao(versao: str) -> None:
    if versao not in VERSOES:
        raise ValueError(f"versão da heurística desconhecida: {versao!r} (conhecidas: {sorted(VERSOES)})")


def avaliar(
    tag_anterior: str | None,
    tag: str | None,
    mensagens: Iterable[str | None],
    versao: str,
    notas: str | None = None,
) -> dict:
    """Classifica `tag` em relação à release anterior e aos commits entre as duas.

    Devolve `heuristic_corrective`, `heuristic_version` e os sinais usados (`semver_patch`,
    `palavra_chave`, `palavra_chave_ampla`), úteis para a análise de erros da heurística.

    `versao` é obrigatória. Versão que exige release notes (v9) com `notas=None` e release anterior
    existente levanta `DadosAusentesError`: nunca cai em outra regra mantendo o rótulo da pedida. Notas
    vazias (`""`) são dado presente (release sem texto).
    """
    _exigir_versao(versao)
    if VERSOES[versao].exige_notas and notas is None and tag_anterior is not None:
        raise DadosAusentesError(
            f"a versão {versao} exige as release notes (`body`) de {tag!r}, que não foram fornecidas; "
            "não é possível executá-la sem elas (nenhuma outra regra foi aplicada)"
        )
    mensagens = list(mensagens)
    sinais = sinais_da_release(tag_anterior, tag, mensagens)
    if VERSOES[versao].usa_conteudo and tag_anterior is not None:
        sinais = {**sinais, **sinais_conteudo(mensagens, notas)}
    # sem release anterior nunca é corretiva e não há sinal de conteúdo a exigir
    resultado = False if tag_anterior is None else corretiva(sinais, versao)
    return {"heuristic_corrective": resultado, "heuristic_version": versao, **sinais}


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


def corretiva(sinais: Mapping, versao: str) -> bool:
    """Aplica a regra de `versao` aos sinais de `sinais_da_release` (+ `sinais_conteudo` para v8/v9).

    Versão que exige release notes (v9) levanta `DadosAusentesError` se `nota_correcao` ou
    `nota_novidade` faltarem ou forem `None` (notas não coletadas); `False` é sinal presente (notas
    coletadas, mesmo vazias). Quem chama trata a release sem anterior (nunca corretiva) antes.
    """
    _exigir_versao(versao)
    if VERSOES[versao].exige_notas and (
        sinais.get("nota_correcao") is None or sinais.get("nota_novidade") is None
    ):
        raise DadosAusentesError(
            f"a versão {versao} exige os sinais das release notes (`nota_correcao`, `nota_novidade`), "
            "ausentes; não é possível executá-la sem eles (nenhuma outra regra foi aplicada)"
        )
    return bool(VERSOES[versao].regra(sinais))


def classificar_releases(releases_commits: Iterable[Mapping], versao: str) -> list[dict]:
    """Aplica a heurística a cada item de `pipeline.collect_commits.collect_commits(...)["releases"]`.

    Cada item tem `tag_name`, `base` (tag da release anterior ou `None`), `published_at`, `status` e
    `commits[].message`. A saída mantém a ordem e acrescenta o resultado de `avaliar` e
    `mensagens_incompletas` (`compare` com 404 ou truncado: a palavra-chave pode faltar por falta de
    dado). `release_id` não existe nesse formato: a junção com os rótulos é por `(full_name, tag_name)`.

    `versao` é obrigatória e validada antes de qualquer item. As release notes vêm da chave `body` de
    cada item (ausente = não coletada); para a v9, a falta delas levanta `DadosAusentesError` e nada é
    devolvido (sem resultado parcial).
    """
    _exigir_versao(versao)
    saida = []
    for r in releases_commits:
        mensagens = [c.get("message") for c in r.get("commits") or []] if r.get("status") == STATUS_OK else []
        item = {
            "tag_name": r.get("tag_name"),
            "published_at": r.get("published_at"),
            "base": r.get("base"),
            "status": r.get("status"),
            **avaliar(
                r.get("base"), r.get("tag_name"), mensagens, versao,
                notas=(r.get("body") or "") if "body" in r else None,
            ),
            "mensagens_incompletas": r.get("status") == STATUS_404 or bool(r.get("truncado")),
        }
        if "id" in r:
            item["id"] = r["id"]
        saida.append(item)
    return saida
