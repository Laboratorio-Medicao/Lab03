# RQ07 — Análise de sensibilidade das classificações DORA

## Resumo por par de combinações

| Par | n | Mudaram | % mudou | κ linear |
|---|---:|---:|---:|---:|
| C1×C2 | 300 | 121 | 40.3% | 0.464 |
| C1×C3 | 300 | 67 | 22.3% | 0.718 |
| C2×C3 | 300 | 88 | 29.3% | 0.607 |

## Matrizes de transição

> Linha = classificação em A · Coluna = classificação em B · Célula = nº de repos

### C1 → C2

|  | Elite | High | Medium | Low |
| --- | --- | --- | --- | --- |
| Elite | 5 | 21 | 0 | 2 |
| High | 1 | 81 | 51 | 2 |
| Medium | 0 | 24 | 76 | 7 |
| Low | 0 | 0 | 13 | 17 |

### C1 → C3

|  | Elite | High | Medium | Low |
| --- | --- | --- | --- | --- |
| Elite | 24 | 3 | 0 | 1 |
| High | 9 | 113 | 13 | 0 |
| Medium | 1 | 25 | 76 | 5 |
| Low | 1 | 0 | 9 | 20 |

### C2 → C3

|  | Elite | High | Medium | Low |
| --- | --- | --- | --- | --- |
| Elite | 5 | 1 | 0 | 0 |
| High | 25 | 98 | 3 | 0 |
| Medium | 4 | 41 | 89 | 6 |
| Low | 1 | 1 | 6 | 20 |

## Interpretação do κ linear

| Faixa | Interpretação |
|---|---|
| < 0,20 | Concordância fraca |
| 0,20–0,40 | Razoável |
| 0,40–0,60 | Moderada |
| 0,60–0,80 | Substancial |
| > 0,80 | Quase perfeita |

Fonte: `data/metrics.csv` · Script: `scripts/sensitivity_analysis.py`