# Refino e status de validação da heurística de release corretiva (Issue #28)

**Status: heurística NÃO VALIDADA.** Nenhuma das 10 versões testadas atingiu F1 ≥ 0,70 contra o consenso da
amostra-ouro. O campo `escolhida` de `avaliacao_heuristica.csv` é só a regra interna do script ("maior F1
quando nenhuma chega a 0,70") e **não** significa validação.

## Verificação do que é exigido (texto exato)

| Fonte | Trecho | Consequência |
|---|---|---|
| Enunciado §5, RQ 03 (b) | "Essa heurística **precisa** ser validada contra a amostra rotulada manualmente (seção 6)." | Validação é requisito para o CFR (b); **não cumprido**. |
| Enunciado §6, passo 5 | "Se o F1 ficar abaixo de 0,70, refine a heurística e reavalie. Documente no artigo cada versão testada e o F1 obtido por ela." | Refinamos (v8, v9) e documentamos todas as versões abaixo. |
| Fonte da Verdade S02-016 | "Heurística **validada** contra a amostra rotulada (condição para usar CFR b)" | Condição **não cumprida**; CFR (b) sai como exploratório. |
| Fonte da Verdade, aceite S02 | "F1 final ≥ 0,70 **ou** histórico de refinamentos com F1 de cada versão documentado" | A segunda alternativa está atendida por esta tabela. |

Nenhum dos dois documentos diz como escolher a versão final se nenhuma chega a 0,70: a estratégia abaixo é
**decisão do grupo**, provisória.

**Pendência de validação:** F1 ≥ 0,70 numa amostra independente da usada para desenhar a v8/v9 (ou
recoleta de `body` para a v9 e nova rodada). Até lá, não declarar a heurística validada.

## Versões testadas (n = 300 releases; 85 corretivas pelo consenso = 28,3%; κ = 0,273)

> **Nota:** os números de v8 e v9 diferem dos documentados na Sprint S02 porque o consenso foi recomputado
> com os 3 avaliadores completos (κ = 0,273, 85 corretivas). O S02 usava consenso parcial com 75 corretivas.

| Versão | Regra | Precisão | Recall | F1 | Marcadas | Taxa prevista |
|---|---|---:|---:|---:|---:|---:|
| v1 | só patch E palavra estrita (definida antes dos dados) | 0,43 | 0,78 | 0,56 | — | — |
| v2 | patch OU palavra estrita | 0,33 | 0,99 | 0,49 | — | — |
| v3 | só palavra estrita | 0,32 | 0,87 | 0,47 | — | — |
| v4 | só patch (não comparável: palavra estrita) | 0,43 | 0,89 | 0,58 | — | — |
| v5 | patch E palavra ampla | 0,44 | 0,82 | 0,58 | — | — |
| v6 | patch OU palavra ampla | 0,33 | 0,99 | 0,49 | — | — |
| v7 | só palavra ampla | 0,33 | 0,92 | 0,48 | — | — |
| v8 | commit de correção e nenhum de feature | 0,62 | 0,41 | 0,50 | — | — |
| v9 | v8 OU release notes com correção e sem novidade | 0,63 | 0,55 | 0,59 | — | — |
| **v10** | rejeita major/minor; patch: v8 OU nota ampla (≥4 fixes); não-SemVer: v9 | **0,70** | **0,60** | **0,65** | — | — |

Fonte: `data/amostra_ouro/avaliacao_heuristica.csv` (gerado por `python -m scripts.evaluate_heuristic`).

## Estratégia adotada (provisória, sem recoleta)

| Papel | Versão | Motivo | Observação |
|---|---|---|---|
| Estimativa principal **exploratória** do CFR (b) | **v8** (P 0,62 · R 0,41 · F1 0,50) | Calculável com os dados já coletados (só commits, sem release notes) | Subestima: recall baixo |
| Análise de **sensibilidade** | **v4** (P 0,43 · R 0,89 · F1 0,58) | Mostra o efeito da definição mais simples (só patch) | Superestima: muitos falsos positivos |
| Variante **experimental, fora do dataset final** | **v10** (P 0,70 · R 0,60 · F1 0,65) | Maior F1 de todas as versões; rejeita major/minor, usa notas de forma mais permissiva para patch | Usa o corpo das release notes (`body`), que a coleta atual não guarda (`CAMPOS` em `pipeline/collect_releases.py`). Aplicá-la ao conjunto completo exige recoletar as releases com `body`. |

## Por que as versões v1–v7 falham (análise de erros da v4, `erros_heuristica.md`)
111 falsos positivos, 77 deles em releases com bump de patch e a palavra `fix` que o consenso não considera
corretivas: quase toda release contém algum `fix` e o bump de patch é rotina. O número da versão e a mera
presença da palavra não dizem qual era o objetivo principal da release.

## Riscos e limitações (entram em Ameaças à validade)
1. **Otimismo do F1 (viés de seleção).** v8–v10 foram desenhadas **depois** de ver os erros das versões
   anteriores na mesma amostra em que são avaliadas, e escolhida entre 10 versões. O 0,65 é, portanto, um
   limite otimista; numa divisão por repositório, o F1 real pode ser consideravelmente menor.
2. **Consenso com baixo kappa.** κ = 0,273 (razoável–fraco): os 3 avaliadores discordaram bastante sobre
   o que é corretiva, o que torna o "gabarito" ruidoso. O kappa baixo é o principal limitante estrutural
   para alcançar F1 ≥ 0,70 — há releases cujos sinais são idênticos mas cujos rótulos divergem.
3. **Taxa prevista × referência.** A v4 infla o CFR (b); a v8 o deprime; a v10 fica próxima da taxa
   de referência (28,3%), mas com FP e FN que se compensam: o erro por repositório continua.
4. **CFR (b) × CFR (a) não são comparáveis em nível.** (a) é falha de pipeline (`conclusion` de workflow
   runs); (b) é proxy de entrega e herda os erros da heurística (precisão e recall acima). As diferenças
   entre (a) e (b) misturam construtos distintos **e** erro de classificação; não interpretar a diferença
   como efeito real sem essa ressalva.
5. **Censura e commits indisponíveis.** Releases com `compare` 404 ou truncado têm palavra-chave
   possivelmente ausente (puxa o CFR (b) para baixo); releases nos últimos 7 dias da janela são censuradas.

## Impacto nas RQs afetadas
| RQ | Impacto |
|---|---|
| RQ 03 (b) | Exploratória: reportar v8 como principal e v4 como sensibilidade, com P/R/F1 ao lado; não chamar de validada |
| RQ 05 (variante b) | Correlação DF × CFR (b) exploratória; discutir o viés de cada versão |
| RQ 07 (combinações com CFR (b), ex.: C2) | A categoria DORA depende de uma heurística não validada; incluir a sensibilidade v4/v8 |
| RQ 08 (rework rate, bônus) | Herda a mesma limitação |
| RQ 01, 02, 04, RQ 03 (a) | Não dependem da heurística |

## Pendências que impedem a validação
1. F1 ≥ 0,70 em **amostra independente** (nova amostra rotulada com rotulagem sem sugestões compartilhadas).
   Com os sinais atuais e κ = 0,273 no gabarito, atingir 0,70 na mesma amostra parece próximo do teto
   empírico — é necessária ou uma amostra mais consistente ou novos sinais.
2. Recoleta de `body` para o conjunto completo, se a v10 for usada como estimativa principal.
3. Aceite do grupo/professor sobre usar CFR (b) exploratório (lacuna não definida no material).
