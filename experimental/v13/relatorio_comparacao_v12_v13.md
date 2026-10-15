# Relatório de comparação v12 × v13-experimental

> Comparação **reproduzível** com as amostras e os rótulos existentes; sem coleta, sem alteração de regras ou rótulos.
> A avaliação foi examinada antes de a v13 existir: **não é validação independente**.

## Fontes (caminhos confirmados)

| Item | Caminho |
|---|---|
| v12 (oficial) | `metricas/heuristica.py` (`avaliar(..., 'v12')`) |
| v13 (experimental) | `experimental/v13/heuristica_v13.py` |
| Desenvolvimento | `data/amostra_ouro/{amostra_ouro,consenso}.csv`; commits e notas no cache do worktree `implementar-validacao` |
| Avaliação | `data/validacao_independente/{dados_congelados.json,predicoes_v12.csv,labels_*.csv,resultado_validacao.json}` |
| Comparação anterior | `experimental/v13/{comparar.py,resultados_exploratorios.md,diferencas_v12_v13.csv}` (não alterados) |
| Testes | `experimental/v13/tests/test_v13.py`: 19 passed in 0.02s |

## Reprodução dos resultados anteriores

- Avaliação: v12 recalculada = `predicoes_v12.csv` em **200/200** releases; F1 0.6892 vs `resultado_validacao.json` 0.6892 (reproduzido).
- Desenvolvimento: F1 v12 recalculado = 0.7219 (relatório anterior: 0,7219 → reproduzido).

## Desenvolvimento (300 releases / 60 repositórios)

**Natureza:** NÃO independente. Estes dados foram usados para formular e ajustar v1–v12 (e a v13 herda o ajuste). Rótulos com κ de Fleiss 0,27 (definição ambígua).

| versão | TP | FP | FN | TN | Precisão | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| v12 | 61 | 23 | 24 | 192 | 0.726 | 0.718 | 0.7219 |
| v13-experimental | 61 | 23 | 24 | 192 | 0.726 | 0.718 | 0.7219 |

- Releases: 300 em 60 repositórios; positivos no consenso: 85.
- Discordâncias v12 × v13: **0** (0 corrigidas, 0 pioradas).
- F1 v12 IC95% por repositório: [0.630; 0.798]; F1 v13: [0.630; 0.798].
- ΔF1 (v13 − v12) = **+0.0000**, IC95% [+0.000; +0.000]; P(Δ>0) = 0.00; P(Δ=0) = 1.00 (10000 réplicas, semente 20261016).

Nenhuma classificação mudou.

## Avaliação (200 releases / 40 repositórios) — comparação exploratória PÓS-HOC

**Natureza:** Já examinada: o resultado e os erros da v12 foram vistos antes de formular a H1. NÃO é validação independente da v13. Rótulos com κ de Fleiss 0,87.

| versão | TP | FP | FN | TN | Precisão | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| v12 | 51 | 19 | 27 | 103 | 0.729 | 0.654 | 0.6892 |
| v13-experimental | 53 | 19 | 25 | 103 | 0.736 | 0.679 | 0.7067 |

- Releases: 200 em 40 repositórios; positivos no consenso: 78.
- Discordâncias v12 × v13: **2** (2 corrigidas, 0 pioradas).
- F1 v12 IC95% por repositório: [0.561; 0.792]; F1 v13: [0.576; 0.809].
- ΔF1 (v13 − v12) = **+0.0175**, IC95% [+0.000; +0.056]; P(Δ>0) = 0.63; P(Δ=0) = 0.37 (10000 réplicas, semente 20261016).

| Repositório | Release | Referência | v12 | v13 | Efeito |
|---|---|---|---|---|---|
| 1Panel-dev/MaxKB | `v2.10.5-lts` | sim | nao | sim | corrigiu erro |
| 1Panel-dev/MaxKB | `v2.10.6-lts` | sim | nao | sim | corrigiu erro |

Concentração: {'1Panel-dev/MaxKB': 2} → 1 repositório(s) respondem por todas as 2 mudanças.

## Avaliação: a conclusão depende da referência? (rótulos existentes, sem alteração)

| Referência | F1 v12 | F1 v13 | ΔF1 | classificações que mudam |
|---|---:|---:|---:|---:|
| consenso (maioria) | 0.6892 | 0.7067 | +0.0175 | 2 |
| só GuilhermeVieira05 | 0.6757 | 0.6933 | +0.0177 | 2 |
| só marcosffp | 0.6892 | 0.7067 | +0.0175 | 2 |
| só ALuiz19 | 0.7020 | 0.7190 | +0.0170 | 2 |
| unanimidade (3 dizem sim) | 0.6857 | 0.7042 | +0.0185 | 2 |

## Respostas objetivas

1. **A v13 melhorou a F1 em cada amostra?** Desenvolvimento: não, idêntica (0.7219 → 0.7219). Avaliação: sim, pontualmente (0.6892 → 0.7067).
2. **Atingiu F1 ≥ 0,70?** Desenvolvimento: sim (0.7219; a v12 já estava em 0.7219). Avaliação: sim (0.7067), **pós-hoc**.
3. **Consistente com melhora ou o IC inclui zero?** Avaliação: ΔF1 IC95% [+0.000; +0.056] — limite inferior em zero porque em 37% das réplicas nenhum dos 2 itens entra; P(Δ>0) = 0.63. O intervalo não exclui ausência de efeito. Desenvolvimento: Δ = 0 (sem cobertura).
4. **Classificações que mudaram:** 0 no desenvolvimento; 2 na avaliação (2 corrigidas, 0 pioradas), ambas no mesmo repositório (`1Panel-dev/MaxKB`).
5. **Evidência suficiente para promover a v13?** **Não.** Há melhora observada (2 itens), não há evidência estatística (IC inclui zero, 1 repositório) e não há validação independente (a H1 nasceu dos erros desta amostra; o desenvolvimento não tem casos `-lts`/`-stable`).

## Distinção pedida

| Nível | Situação |
|---|---|
| Melhora observada | **Sim**, +0,018 de F1 na avaliação (2 releases do MaxKB) |
| Evidência estatística de melhora | **Não**: IC95% do ΔF1 começa em 0; 1 repositório; P(Δ>0) = 0.63, P(Δ=0) = 0.37 |
| Validação independente | **Não existe**: amostra já examinada; desenvolvimento sem cobertura |

## Recomendação

**Manter a v13 como experimental** (não promover, não descartar ainda). Ela é inócua onde não há tags `-lts`/`-stable` e, por construção, só afeta esse padrão. Para decidir, a única via é **validação futura** em amostra nova e independente, rotulada antes de executar a heurística (fluxo já pronto em `scripts/validacao_independente.py`); como a H1 afeta poucas releases, essa amostra precisaria conter vários repositórios com sufixo de canal, caso contrário o teste seria novamente inconclusivo. Se não houver tal amostra, descarte (`rm -rf experimental/v13`) é preferível a promover sem evidência.
