"""Funções de cálculo das métricas DORA.

Cada métrica entra em Issue própria (lead time, CFR, recuperação, DF e
classificação) e deve ser exposta por este pacote — é ele que o CI mede com
`pytest --cov=metricas --cov-fail-under=80`.
"""
