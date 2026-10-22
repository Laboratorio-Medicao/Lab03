# RQ05 — Spearman entre deployment frequency e CFR (a) e (b)

Gerado por `python -m analysis.rq05_spearman` a partir de `data/metrics.csv` (scipy 1.18.1). Discussão em `docs/rq05_discussao.md`.

## Resultado principal

| Variante | n | Excluídos | CFR = 0 | ρ | IC95% | p | Força | Direção (IC) |
|---|---|---|---|---|---|---|---|---|
| CFR (a) proxy de CI | 300 | 0 | 17 | -0,017 | [-0,130; 0,096] | 0,768 | desprezível | inconclusiva (IC contém 0) |
| CFR (b) proxy de entrega | 299 | 1 | 71 | 0,624 | [0,542; 0,694] | < 0,001 | forte | positiva |

IC95%: Fisher z, SE de Bonett e Wright (2000). α = 0,05. Força: |ρ| < 0,1 desprezível; < 0,3 fraca; < 0,5 moderada; ≥ 0,5 forte (Cohen, 1988; rótulo só descritivo). Direção: positiva/negativa só quando o IC95% exclui o 0.

Excluídos (pares incompletos, exclusão só da variante):

- CFR (b) proxy de entrega: akveo/react-native-ui-kitten

## Sensibilidade de CFR (b) ao nº mínimo de releases avaliadas (diagnóstico)

Cortes pré-declarados (5, 10, 20). **Ressalva:** DF e nº de releases avaliadas têm ρ = 0,982; o corte restringe a faixa de DF, e restrição de faixa por si só reduz |ρ|. Serve para dimensionar o efeito de denominador pequeno, não substitui o resultado principal.

| Mín. avaliadas | Variante | n | Excluídos | CFR = 0 | ρ | IC95% | p | Força | Direção (IC) |
|---|---|---|---|---|---|---|---|---|---|
| ≥ 5 | CFR (b) proxy de entrega | 296 | 0 | 69 | 0,617 | [0,534; 0,689] | < 0,001 | forte | positiva |
| ≥ 10 | CFR (b) proxy de entrega | 229 | 0 | 31 | 0,580 | [0,479; 0,666] | < 0,001 | forte | positiva |
| ≥ 20 | CFR (b) proxy de entrega | 140 | 0 | 4 | 0,420 | [0,267; 0,553] | < 0,001 | moderada | positiva |

CFR (b) = 0 por nº de releases avaliadas:

| Releases avaliadas | n | CFR (b) = 0 | Proporção |
|---|---|---|---|
| < 10 | 70 | 40 | 0,571 |
| >= 10 | 229 | 31 | 0,135 |

## Notas de método

- Pares completos por variante; zeros de CFR mantidos; nenhuma imputação.
- Empates recebem ranks médios (DF tem 91 valores distintos em 300; CFR (b) tem 71 zeros). O p-valor bilateral vem da aproximação t do `spearmanr`, aproximada na cauda: no texto usar "p < 0,001"; o valor completo fica no CSV.
- Gráficos: DF em escala log (varia mais de duas ordens de grandeza, sem zeros); CFR em escala linear [0, 1] (proporção limitada, com zeros). Linha vermelha = mediana de CFR em faixas de quantil de DF.
- CFR (b) é exploratório: heurística v12 não validada (F1 independente 0,689, IC95% 0,563–0,790).
