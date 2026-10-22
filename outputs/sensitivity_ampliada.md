# RQ07 (Bônus) — Sensibilidade ampliada

## Resultados por variação

| Variação | n | Mudaram | % mudou | κ linear |
|---|---:|---:|---:|---:|
| cfr_b_janela_3d_vs_7d | 299 | 6 | 2.0% | 0.98 |
| cfr_b_janela_14d_vs_7d | 299 | 14 | 4.7% | 0.965 |
| min_releases_5 | 300 | 0 | 0.0% | 1.0 |
| min_releases_10 | 232 | 0 | 0.0% | 1.0 |
| censura_rq04_excluir_alta | 277 | 0 | 0.0% | 1.0 |
| cortes_mais10pct | 300 | 14 | 4.7% | 0.945 |
| cortes_menos10pct | 300 | 18 | 6.0% | 0.929 |

## Notas metodológicas

- **CFR(b) janela**: lower bound usa `falha/janela_total` (proxy janela ~3 d); upper bound usa
  `(falha+censuradas)/janela_total` (proxy ~14 d). Recomputa apenas a classificação; os
  valores exatos exigem re-execução do pipeline com `PRAZO_CORRECAO` ajustado.
- **Mínimo releases**: repos com `n_releases_janela < mínimo` têm classificação marcada como
  indefinida; κ e % medem a estabilidade em relação ao conjunto completo.
- **Censura RQ04**: repos com `prop_episodios_censurados > 0,5` têm `rec_class` excluída;
  κ mede concordância no subconjunto restante.
- **Cortes ±10%**: todos os limiares DF/LT/CFR/rec deslocados pelo mesmo fator;
  reclassificação de `dora_c1` a partir das métricas brutas.

Fonte: `data/metrics.csv` · Script: `scripts/sensitivity_ampliada.py`