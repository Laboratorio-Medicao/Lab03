"""Change Failure Rate — CFR(a) agregando todos os workflows (Issue #14).

CFR(a) = falhas / (sucessos + falhas), ignorando runs com conclusão neutra.
"""

from __future__ import annotations

# Mapeamento dos 9 valores possíveis de `conclusion` na API do GitHub Actions.
# None (run ainda em andamento) também é tratado como "ignored".
_CONCLUSAO: dict[str | None, str] = {
    "success": "success",
    "failure": "failure",
    "timed_out": "failure",
    "startup_failure": "failure",
    "cancelled": "ignored",
    "skipped": "ignored",
    "neutral": "ignored",
    "action_required": "ignored",
    "stale": "ignored",
    None: "ignored",
}


def classify_conclusion(conclusion: str | None) -> str:
    """Retorna 'success', 'failure' ou 'ignored' para cada valor de conclusion."""
    return _CONCLUSAO.get(conclusion, "ignored")


def cfr(runs: list[dict]) -> float | None:
    """CFR(a): proporção de falhas entre os runs válidos (success + failure).

    Retorna None se não houver runs válidos (sem divisão por zero).
    """
    validos = [r for r in runs if classify_conclusion(r.get("conclusion")) != "ignored"]
    if not validos:
        return None
    falhas = sum(1 for r in validos if classify_conclusion(r.get("conclusion")) == "failure")
    return falhas / len(validos)
