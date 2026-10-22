"""Deployment frequency e classificação DORA (tabela fixa da disciplina).

Fontes: E§5 RQ01 e RQ07 (enunciado), fonte_vdd.md §5.1 e §5.5. A tabela é a
**adaptada pela disciplina**, não a oficial do relatório DORA.

Unidades: deployment frequency em releases/semana; lead time e tempo de
recuperação em **horas**; CFR como proporção em [0, 1].
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone
from typing import Iterable, Mapping, Sequence

ELITE, HIGH, MEDIUM, LOW = "Elite", "High", "Medium", "Low"
SCORES = {ELITE: 4, HIGH: 3, MEDIUM: 2, LOW: 1}
_POR_SCORE = {v: k for k, v in SCORES.items()}

HORAS_DIA = 24.0
HORAS_SEMANA = 168.0
HORAS_30_DIAS = 720.0

# L11 (decisão documentada): 1 mês = 1/12 do ano de 365 dias => 1 release/mês
# = 12 / (365/7) = 84/365 ≈ 0,2301 release/semana.
DF_UM_POR_MES = 12 * 7 / 365


def _dt(valor) -> datetime:
    """Aceita datetime ou ISO-8601 (com 'Z'); datas ingênuas são tratadas como UTC."""
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor


def _valida(valor: float, nome: str) -> float:
    if valor is None or isinstance(valor, bool) or math.isnan(valor) or valor < 0:
        raise ValueError(f"{nome} inválido: {valor!r} (esperado número >= 0)")
    return valor


def deployment_frequency(releases: Iterable[Mapping], window: tuple) -> float:
    """Releases publicadas na janela ÷ semanas da janela (releases/semana).

    `releases`: mapeamentos com `draft`, `prerelease` e `published_at`.
    `window`: (início, fim) como datetime ou ISO-8601; semanas = (fim − início)/7 dias.
    Conta só `draft=false` e `prerelease=false` com `published_at` em
    [início, fim] (ambos inclusivos). Itens sem `published_at` são descartados.
    """
    inicio, fim = _dt(window[0]), _dt(window[1])
    if fim <= inicio:
        raise ValueError("janela inválida: fim deve ser posterior ao início")
    semanas = (fim - inicio).total_seconds() / (7 * 86400)
    n = 0
    for r in releases:
        if r.get("draft") or r.get("prerelease") or not r.get("published_at"):
            continue
        if inicio <= _dt(r["published_at"]) <= fim:
            n += 1
    return n / semanas


def classify_df(releases_por_semana: float, semanas: float | None = None) -> str:
    """`semanas`: duração da janela em semanas. O corte "1 release/mês" é 12 releases na janela
    (12/semanas); a janela oficial inclui o dia final e tem 366 dias, então usar o corte fixo de 365
    dias rebaixaria para Low quem publica exatamente 12 releases. Sem `semanas`, usa 84/365."""
    v = _valida(releases_por_semana, "deployment frequency")
    corte = 12 / semanas if semanas else DF_UM_POR_MES
    if v >= 7:
        return ELITE
    if v >= 1:
        return HIGH
    if v >= corte:
        return MEDIUM
    return LOW


def classify_lt(horas: float) -> str:
    """Mediana do lead time, em horas."""
    v = _valida(horas, "lead time")
    if v < HORAS_DIA:
        return ELITE
    if v < HORAS_SEMANA:
        return HIGH
    if v < HORAS_30_DIAS:
        return MEDIUM
    return LOW


def classify_cfr(taxa: float) -> str:
    """Change failure rate como proporção (0,15 = 15%)."""
    v = _valida(taxa, "CFR")
    if v > 1:
        raise ValueError(f"CFR inválido: {taxa!r} (esperado proporção em [0, 1])")
    if v <= 0.15:
        return ELITE
    if v <= 0.30:
        return HIGH
    if v <= 0.45:
        return MEDIUM
    return LOW


def classify_recovery(horas: float) -> str:
    """Mediana do tempo de recuperação, em horas."""
    v = _valida(horas, "tempo de recuperação")
    if v < 1:
        return ELITE
    if v < HORAS_DIA:
        return HIGH
    if v < HORAS_SEMANA:
        return MEDIUM
    return LOW


def semanas_da_janela(window: tuple) -> float:
    """Duração da janela (início, fim) em semanas, a mesma usada em `deployment_frequency`."""
    return (_dt(window[1]) - _dt(window[0])).total_seconds() / (7 * 86400)


def classify_overall_parcial(scores: Sequence[int]) -> str:
    """Categoria geral com as métricas definidas (1 a 4 notas): mediana com floor.

    Decisão do grupo (L10; não há registro de resposta do professor no repositório): métrica indefinida não exclui o repositório;
    o chamador deve sinalizar a classificação parcial (`n_metricas_dora` < 4).
    """
    notas = list(scores)
    if not 1 <= len(notas) <= 4:
        raise ValueError(f"esperadas de 1 a 4 notas, recebidas {len(notas)}")
    if any(isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 4 for n in notas):
        raise ValueError(f"notas devem ser inteiros em 1..4: {notas!r}")
    return _POR_SCORE[math.floor(statistics.median(notas))]


def classify_overall(scores: Sequence[int]) -> str:
    """Categoria geral: mediana das 4 notas (Elite=4 … Low=1), arredondada para baixo.

    Exige exatamente 4 notas inteiras em 1..4 (L10: métrica indefinida NÃO
    DEFINIDO NA FONTE — aqui é erro explícito, sem assumir regra).
    """
    notas = list(scores)
    if len(notas) != 4:
        raise ValueError(f"esperadas 4 notas, recebidas {len(notas)}")
    if any(isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 4 for n in notas):
        raise ValueError(f"notas devem ser inteiros em 1..4: {notas!r}")
    return _POR_SCORE[math.floor(statistics.median(notas))]


def score(categoria: str) -> int:
    """Elite→4, High→3, Medium→2, Low→1."""
    return SCORES[categoria]
