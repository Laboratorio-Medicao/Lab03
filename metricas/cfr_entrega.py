"""Change Failure Rate — CFR (b), proxy de entrega (RQ03 b, Issue #27).

Uma release de deploy R **falhou** se for seguida, em até 7 dias, por uma release corretiva (E§5).
Decisões (fonte_vdd.md L08 e tabela de casos de `cfr_release`):

- vale **qualquer** release de deploy S com `R < S ≤ R + 7 dias` marcada como corretiva, não só a
  próxima; exatamente 7 d 0 h depois ainda conta;
- R publicada nos últimos 7 dias da janela (`R + 7 dias > fim`) é **censurada**: fica fora do
  denominador, porque ainda não se sabe se haverá correção;
- com menos de 2 releases de deploy na janela, o CFR (b) é **indefinido** (`None`): só as releases da
  janela podem ser S, então com uma release não há o que observar. Os contadores continuam preenchidos.

A marcação de corretiva vem de `metricas.heuristica`. Unidade: proporção em [0, 1].
"""

from __future__ import annotations

from bisect import bisect_right
from datetime import timedelta
from typing import Iterable, Mapping

from metricas.dora import _dt
from metricas.heuristica import HEURISTIC_VERSION, classificar_releases

PRAZO_CORRECAO = timedelta(days=7)


def cfr_entrega(releases: Iterable[Mapping], window: tuple) -> dict:
    """CFR (b) a partir das releases de deploy já classificadas (`published_at`, `heuristic_corrective`).

    `window`: (início, fim) como datetime ou ISO-8601, como em `dora.deployment_frequency`; quem chama
    com datas usa `pipeline.etapas._janela` (fim = 23:59:59 do último dia). Itens sem `published_at`
    são descartados. `n_releases_avaliadas_cfr_b + n_releases_censuradas_cfr_b = n_releases_janela`.
    """
    inicio, fim = _dt(window[0]), _dt(window[1])
    na_janela = sorted(
        ((_dt(r["published_at"]), bool(r.get("heuristic_corrective"))) for r in releases if r.get("published_at")),
        key=lambda par: par[0],
    )
    na_janela = [par for par in na_janela if inicio <= par[0] <= fim]
    corretivas = [data for data, corretiva in na_janela if corretiva]

    avaliadas = [data for data, _ in na_janela if data + PRAZO_CORRECAO <= fim]
    # 1ª corretiva estritamente depois de R (lista ordenada); R falhou se ela vier em até 7 dias.
    falhas = 0
    for r in avaliadas:
        i = bisect_right(corretivas, r)
        if i < len(corretivas) and corretivas[i] <= r + PRAZO_CORRECAO:
            falhas += 1
    definido = len(na_janela) >= 2 and len(avaliadas) > 0
    return {
        "cfr_b": falhas / len(avaliadas) if definido else None,
        "n_releases_avaliadas_cfr_b": len(avaliadas),
        "n_releases_censuradas_cfr_b": len(na_janela) - len(avaliadas),
        "n_releases_janela": len(na_janela),
        "n_releases_falha_cfr_b": falhas,
    }


def resumo_cfr_entrega(releases_commits: Iterable[Mapping], window: tuple, versao: str = HEURISTIC_VERSION) -> dict:
    """Heurística + CFR (b) numa chamada, a partir de `collect_commits(...)["releases"]`.

    `n_releases_mensagens_incompletas_cfr_b` é diagnóstico (releases da janela com `compare` 404 ou
    truncado, em que a palavra-chave pode ter faltado) e não entra na invariante de contagem.
    """
    classificadas = classificar_releases(releases_commits, versao)
    inicio, fim = _dt(window[0]), _dt(window[1])
    incompletas = sum(
        1 for r in classificadas
        if r["mensagens_incompletas"] and r["published_at"] and inicio <= _dt(r["published_at"]) <= fim
    )
    return {
        **cfr_entrega(classificadas, window),
        "n_releases_mensagens_incompletas_cfr_b": incompletas,
        "heuristic_version": versao,
    }
