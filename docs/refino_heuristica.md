# Refino e status de validação da heurística de release corretiva (Issue #28)

**Status: heurística NÃO VALIDADA.** Nenhuma das 10 versões testadas atingiu F1 ≥ 0,70 contra o consenso da
amostra-ouro (rodada oficial de 15/10, com os três rótulos commitados nas Issues #23, #24 e #25; os números
anteriores deste documento vinham de outra versão dos rótulos e foram substituídos). O campo `escolhida` de `avaliacao_heuristica.csv` é só a regra interna do script ("maior F1
quando nenhuma chega a 0,70") e **não** significa validação.

## Verificação do que é exigido (texto exato)

| Fonte | Trecho | Consequência |
|---|---|---|
| Enunciado §5, RQ 03 (b) | "Essa heurística **precisa** ser validada contra a amostra rotulada manualmente (seção 6)." | Validação é requisito para o CFR (b); **não cumprido**. |
| Enunciado §6, passo 5 | "Se o F1 ficar abaixo de 0,70, refine a heurística e reavalie. Documente no artigo cada versão testada e o F1 obtido por ela." | Refinamos (v8, v9, v10) e documentamos todas as versões abaixo. |
| Fonte da Verdade S02-016 | "Heurística **validada** contra a amostra rotulada (condição para usar CFR b)" | Condição **não cumprida**; CFR (b) sai como exploratório. |
| Fonte da Verdade, aceite S02 | "F1 final ≥ 0,70 **ou** histórico de refinamentos com F1 de cada versão documentado" | A segunda alternativa está atendida por esta tabela. |

Nenhum dos dois documentos diz como escolher a versão final se nenhuma chega a 0,70: a estratégia abaixo é
**decisão do grupo**, provisória.

**Pendência de validação:** F1 ≥ 0,70 numa amostra independente da usada para desenhar a v8/v9/v10 (ou
recoleta de `body` para a v10 e nova rodada). Até lá, não declarar a heurística validada.

## Versões testadas (n = 300 releases; 85 corretivas pelo consenso = 28,3%)

Precisão, recall e F1 em todas as releases em que a versão é aplicável (`n`); **F1 comum** no subconjunto de
295 releases em que todas são aplicáveis (a v9/v10 exigem release notes, e as 5 releases do repositório removido
`1bananachicken/MaaNTE` não as têm). A comparação e a coluna `escolhida` usam o F1 comum.

| Versão | Regra | n | Precisão | Recall | F1 | F1 comum | Marcadas | Taxa prevista |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | só patch E palavra estrita (definida antes dos dados) | 300 | 0,423 | 0,741 | 0,539 | 0,546 | 149 | 49,7% |
| v2 | patch OU palavra estrita | 300 | 0,329 | 0,988 | 0,494 | 0,485 | 255 | 85,0% |
| v3 | só palavra estrita | 300 | 0,313 | 0,835 | 0,455 | 0,460 | 227 | 75,7% |
| v4 | só patch (não comparável: palavra estrita) | 300 | 0,429 | 0,894 | 0,580 | 0,570 | 177 | 59,0% |
| v5 | patch E palavra ampla | 300 | 0,432 | 0,788 | 0,558 | 0,565 | 155 | 51,7% |
| v6 | patch OU palavra ampla | 300 | 0,328 | 0,988 | 0,493 | 0,484 | 256 | 85,3% |
| v7 | só palavra ampla | 300 | 0,321 | 0,882 | 0,470 | 0,475 | 234 | 78,0% |
| v8 | commit de correção e nenhum de feature | 300 | 0,625 | 0,412 | 0,497 | 0,507 | 56 | 18,7% |
| v9 | v8 OU release notes com correção e sem novidade | 295 | 0,627 | 0,573 | 0,599 | 0,599 | 75 | 25,4% |
| **v10** | rejeita major/minor; patch: v8 OU nota ampla (≥4 fixes); não-SemVer: v9 | 295 | **0,699** | **0,600** | **0,646** | **0,646** | — | — |

Fonte: `data/amostra_ouro/avaliacao_heuristica.csv` (gerado por `python -m scripts.evaluate_heuristic
--permitir-sem-notas 1bananachicken/MaaNTE`). As previsões de cada versão são as mesmas da rodada anterior
(mesmas marcadas); mudou a referência (consenso).

## Estratégia adotada (provisória, sem recoleta) — **a rever pelo grupo**

A estratégia abaixo foi decidida com os números da rodada anterior. **Na rodada oficial, a v8 deixou de ser a
melhor versão calculável só com commits:** v4 (F1 0,580) e v5 (0,558) ficaram acima da v8 (0,497). O
`metrics.csv` (#21) continua com a v8 até o grupo decidir.

| Papel | Versão | Motivo (rodada anterior) | Números da rodada oficial |
|---|---|---|---|
| Estimativa principal **exploratória** do CFR (b) | **v8** | Era a melhor F1 entre as versões calculáveis com os dados já coletados (só commits) | P 0,625 · R 0,412 · F1 0,497; subestima: prevê 18,7% contra 28,3% de referência |
| Análise de **sensibilidade** | **v4** | Mostra o efeito da definição mais simples (só patch) | P 0,429 · R 0,894 · F1 0,580 (agora a melhor calculável); superestima: prevê 59,0% contra 28,3% (≈ 2,1×) |
| Variante **experimental, fora do dataset final** | **v10** | Maior F1 de todas; rejeita major/minor, nota ampla para patch | P 0,699 · R 0,600 · F1 0,646 (n = 295). Usa release notes (`body`); recoletar releases com `body` para aplicar ao conjunto completo. |

## Por que as versões v1–v7 falham (falsos positivos da v4, rodada oficial)
101 falsos positivos, 66 deles em releases com bump de patch e a palavra `fix` que o consenso não considera
corretivas: quase toda release contém algum `fix` e o bump de patch é rotina. O número da versão e a mera
presença da palavra não dizem qual era o objetivo principal da release.

## Riscos e limitações (entram em Ameaças à validade)
1. **Otimismo do F1 (viés de seleção).** v8–v10 foram desenhadas **depois** de ver os erros das versões
   anteriores na mesma amostra em que são avaliadas, e escolhida entre 10 versões; além disso, entraram no
   repositório antes de os rótulos de dois avaliadores serem commitados (PRs #67 e #68). O F1 da v10 é um
   limite otimista.
2. **Consenso não totalmente independente.** Na rodada anterior, dois avaliadores seguiram sugestões
   compartilhadas. Nos arquivos commitados, a concordância em `corretiva` é
   82,0% (ALuiz19 × marcosffp), 63,3% (ALuiz19 × GuilhermeVieira05) e 56,0% (GuilhermeVieira05 × marcosffp);
   a aderência à sugestão não pode ser recalculada (arquivos fora do Git). O kappa de `corretiva` é 0,27
   (razoável): o critério em si é ambíguo.
3. **Taxa prevista × referência.** A v4 infla o CFR (b) (59,0% contra 28,3%); a v8 o deprime (18,7%); a v10
   fica próxima da taxa agregada, mas com FP e FN que se compensam: o erro por repositório continua.
4. **CFR (b) × CFR (a) não são comparáveis em nível.** (a) é falha de pipeline (`conclusion` de workflow
   runs); (b) é proxy de entrega e herda os erros da heurística (precisão e recall acima). As diferenças
   entre (a) e (b) misturam construtos distintos **e** erro de classificação; não interpretar a diferença
   como efeito real sem essa ressalva.
5. **Censura e commits indisponíveis.** Releases com `compare` 404 ou truncado têm palavra-chave
   possivelmente ausente (puxa o CFR (b) para baixo); releases nos últimos 7 dias da janela são censuradas.
6. **Repositório removido.** `1bananachicken/MaaNTE` (5 releases) foi removido do GitHub depois do sorteio e
   mantido por decisão do grupo; dois avaliadores o rotularam sem acesso ao conteúdo, e nele a v9/v10 não é
   avaliável e as demais versões ficam sem commits.

## Impacto nas RQs afetadas
| RQ | Impacto |
|---|---|
| RQ 03 (b) | Exploratória: reportar a versão principal e a de sensibilidade (hoje v8 e v4; a rever, ver acima), com P/R/F1 ao lado; não chamar de validada |
| RQ 05 (variante b) | Correlação DF × CFR (b) exploratória; discutir o viés de cada versão |
| RQ 07 (combinações com CFR (b), ex.: C2) | A categoria DORA depende de uma heurística não validada; incluir a sensibilidade v4/v8 |
| RQ 08 (rework rate, bônus) | Herda a mesma limitação |
| RQ 01, 02, 04, RQ 03 (a) | Não dependem da heurística |

## Pendências que impedem a validação
1. F1 ≥ 0,70 em **amostra independente** (nova amostra rotulada sem sugestões compartilhadas).
   Com os sinais atuais e κ = 0,27 no gabarito, atingir 0,70 na mesma amostra parece próximo do teto
   empírico — é necessária ou uma amostra mais consistente ou novos sinais.
2. Recoleta de `body` para o conjunto completo, se a v10 for usada como estimativa principal.
3. Aceite do grupo/professor sobre usar CFR (b) exploratório (lacuna não definida no material).
