# Avaliação da heurística de release corretiva

Gerado por `python -m scripts.evaluate_heuristic` (Issue #28). Referência: consenso da dimensão `corretiva` em `consenso.csv`; 300 releases da amostra-ouro, **85 corretivas** no consenso. Métricas com `precision_recall_fscore_support` (positivo = corretiva).

## Comparação no subconjunto comum (n = 295, usada na escolha)

Releases em que todas as versões são avaliáveis.

| Versão | Regra | Precisão | Recall | F1 |
|---|---|---:|---:|---:|
| v1 | só patch E palavra estrita | 0.42 | 0.77 | 0.55 |
| v2 | só patch OU palavra estrita | 0.32 | 0.99 | 0.48 |
| v3 | só palavra estrita (ignora SemVer) | 0.31 | 0.87 | 0.46 |
| v4 | só patch (não comparável: palavra estrita) | 0.42 | 0.89 | 0.57 |
| v5 | só patch E palavra ampla | 0.43 | 0.82 | 0.57 |
| v6 | só patch OU palavra ampla | 0.32 | 0.99 | 0.48 |
| v7 | só palavra ampla (ignora SemVer) | 0.32 | 0.91 | 0.47 |
| v8 | commit de correção e nenhum de feature | 0.62 | 0.43 | 0.51 |
| v9 **(escolhida)** | v8 OU release notes com correção e sem novidade | 0.63 | 0.57 | 0.60 |

## Todas as releases avaliáveis de cada versão (comportamento de produção)

| Versão | n | TP | FP | FN | TN | Precisão | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v1 | 300 | 63 | 86 | 22 | 129 | 0.42 | 0.74 | 0.54 |
| v2 | 300 | 84 | 171 | 1 | 44 | 0.33 | 0.99 | 0.49 |
| v3 | 300 | 71 | 156 | 14 | 59 | 0.31 | 0.84 | 0.46 |
| v4 | 300 | 76 | 101 | 9 | 114 | 0.43 | 0.89 | 0.58 |
| v5 | 300 | 67 | 88 | 18 | 127 | 0.43 | 0.79 | 0.56 |
| v6 | 300 | 84 | 172 | 1 | 43 | 0.33 | 0.99 | 0.49 |
| v7 | 300 | 75 | 159 | 10 | 56 | 0.32 | 0.88 | 0.47 |
| v8 | 300 | 35 | 21 | 50 | 194 | 0.62 | 0.41 | 0.50 |
| v9 | 295 | 47 | 28 | 35 | 185 | 0.63 | 0.57 | 0.60 |

**Versão escolhida: v9** (F1 comum = 0.60). Regra de escolha: fica a v1, definida antes de ver os dados, se F1 comum ≥ 0.70; senão, a de maior F1 comum (empate → menor número).

- Releases com mensagens incompletas (`compare` 404 ou truncado): 5.
- Releases sem release notes (HTTP 404/410), **não avaliáveis** pelas versões que exigem notas: 5 (1bananachicken/MaaNTE v1.0.1, 1bananachicken/MaaNTE v1.1.0, 1bananachicken/MaaNTE v1.1.1, 1bananachicken/MaaNTE v1.4.1, 1bananachicken/MaaNTE v1.5.0). Nelas as demais versões também ficam sem commits quando o `compare` dá 404 e tendem a marcá-las como não corretivas por falta de dado: por isso a comparação usa o subconjunto comum.
- Viés de seleção: as versões foram comparadas na mesma amostra, sem conjunto de validação separado; o F1 da versão escolhida tende a ser otimista (registrar em Ameaças à validade).
- **Ação:** a versão escolhida difere de `HEURISTIC_VERSION` (v1) em `metricas/heuristica.py`: atualize a constante e recalcule o CFR (b) (#21).
