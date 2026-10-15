# Avaliação da heurística de release corretiva

Gerado por `python -m scripts.evaluate_heuristic` (Issue #28). Referência: consenso da dimensão `corretiva` em `consenso.csv`; 300 releases da amostra-ouro, **85 corretivas** no consenso. Métricas com `precision_recall_fscore_support` (positivo = corretiva).

| Versão | Regra | TP | FP | FN | TN | Precisão | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | só patch E palavra estrita | 66 | 86 | 19 | 129 | 0.43 | 0.78 | 0.56 |
| v2 | só patch OU palavra estrita | 84 | 173 | 1 | 42 | 0.33 | 0.99 | 0.49 |
| v3 | só palavra estrita (ignora SemVer) | 74 | 158 | 11 | 57 | 0.32 | 0.87 | 0.47 |
| v4 | só patch (não comparável: palavra estrita) | 76 | 101 | 9 | 114 | 0.43 | 0.89 | 0.58 |
| v5 | só patch E palavra ampla | 70 | 88 | 15 | 127 | 0.44 | 0.82 | 0.58 |
| v6 | só patch OU palavra ampla | 84 | 174 | 1 | 41 | 0.33 | 0.99 | 0.49 |
| v7 | só palavra ampla (ignora SemVer) | 78 | 161 | 7 | 54 | 0.33 | 0.92 | 0.48 |
| v8 | commit de correção e nenhum de feature | 35 | 21 | 50 | 194 | 0.62 | 0.41 | 0.50 |
| v9 | v8 OU release notes com correção e sem novidade | 47 | 28 | 38 | 187 | 0.63 | 0.55 | 0.59 |
| v10 **(escolhida)** | rejeita major/minor; patch: v8 OU nota corretiva ampla (≥4 fixes); não-SemVer: v9 | 51 | 22 | 34 | 193 | 0.70 | 0.60 | 0.65 |

**Versão escolhida: v10** (F1 = 0.65). Regra de escolha: fica a v1, definida antes de ver os dados, se F1 ≥ 0.70; senão, a de maior F1 (empate → menor número).

- Releases com mensagens incompletas (`compare` 404 ou truncado): 0.
- Viés de seleção: as versões foram comparadas na mesma amostra, sem conjunto de validação separado; o F1 da versão escolhida tende a ser otimista (registrar em Ameaças à validade).
- **Ação:** a versão escolhida difere de `HEURISTIC_VERSION` (v1) em `metricas/heuristica.py`: atualize a constante e recalcule o CFR (b) (#21).
