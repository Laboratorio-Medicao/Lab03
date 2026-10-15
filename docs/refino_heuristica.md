# Refino e status de validação da heurística de release corretiva (Issue #28)

**Status: heurística NÃO VALIDADA.** Nenhuma das 9 versões testadas atingiu F1 ≥ 0,70 contra o consenso da
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

## Versões testadas (n = 300 releases; 75 corretivas pelo consenso = 25,0%)

| Versão | Regra | Precisão | Recall | F1 | Marcadas | Taxa prevista |
|---|---|---:|---:|---:|---:|---:|
| v1 | só patch E palavra estrita (definida antes dos dados) | 0,362 | 0,720 | 0,482 | 149 | 49,7% |
| v2 | patch OU palavra estrita | 0,294 | 1,000 | 0,455 | 255 | 85,0% |
| v3 | só palavra estrita | 0,278 | 0,840 | 0,417 | 227 | 75,7% |
| v4 | só patch (não comparável: palavra estrita) | 0,373 | 0,880 | 0,524 | 177 | 59,0% |
| v5 | patch E palavra ampla | 0,374 | 0,773 | 0,504 | 155 | 51,7% |
| v6 | patch OU palavra ampla | 0,293 | 1,000 | 0,453 | 256 | 85,3% |
| v7 | só palavra ampla | 0,286 | 0,893 | 0,434 | 234 | 78,0% |
| v8 | commit de correção e nenhum de feature | 0,696 | 0,520 | 0,595 | 56 | 18,7% |
| v9 | v8 OU release notes com correção e sem novidade | 0,680 | 0,680 | 0,680 | 75 | 25,0% |

Fonte: `data/amostra_ouro/avaliacao_heuristica.csv` (gerado por `python -m scripts.evaluate_heuristic`).

## Estratégia adotada (provisória, sem recoleta)

| Papel | Versão | Motivo | Observação |
|---|---|---|---|
| Estimativa principal **exploratória** do CFR (b) | **v8** (P 0,696 · R 0,520 · F1 0,595) | Melhor F1 entre as versões calculáveis com os dados já coletados (só commits) | Subestima: prevê 18,7% contra 25,0% de referência |
| Análise de **sensibilidade** | **v4** (P 0,373 · R 0,880 · F1 0,524) | Mostra o efeito da definição mais simples (só patch) | Superestima: prevê 59,0% contra 25,0% (≈ 2,4×) |
| Variante **experimental, fora do dataset final** | **v9** (P 0,680 · R 0,680 · F1 0,680) | Melhor F1 e taxa prevista igual à de referência | Usa o corpo das release notes (`body`), que a coleta atual não guarda (`CAMPOS` em `pipeline/collect_releases.py`). Os números acima vêm da avaliação já existente; aplicá-la ao conjunto completo exige recoletar as releases com `body`. |

## Por que as versões v1–v7 falham (análise de erros da v4, `erros_heuristica.md`)
111 falsos positivos, 77 deles em releases com bump de patch e a palavra `fix` que o consenso não considera
corretivas: quase toda release contém algum `fix` e o bump de patch é rotina. O número da versão e a mera
presença da palavra não dizem qual era o objetivo principal da release.

## Riscos e limitações (entram em Ameaças à validade)
1. **Otimismo do F1 (viés de seleção).** v8 e v9 foram desenhadas **depois** de ver os erros da v1–v7 na
   mesma amostra em que são avaliadas, e escolhida entre 9 versões. Numa divisão por repositório, o F1 da
   v9 oscilou de ≈ 0,59 a ≈ 0,74 entre as metades. O 0,68 é, portanto, um limite otimista.
2. **Consenso não totalmente independente.** Dois dos três avaliadores partiram de sugestões compartilhadas
   (`data/amostra_ouro/LEIAME.md`); o kappa de `corretiva` foi 0,43 (moderado): o critério em si é ambíguo.
3. **Taxa prevista × referência.** A v4 infla o CFR (b) (59,0% contra 25,0%); a v8 o deprime (18,7%); a v9
   iguala a taxa agregada (25,0%), mas com 24 FP e 24 FN que se compensam: o erro por repositório continua.
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
1. F1 ≥ 0,70 em amostra independente (nova amostra rotulada) **ou** recoleta de `body` + nova rodada da v9.
2. Reavaliar com rotulagem independente de fato (sem sugestões compartilhadas) se houver tempo.
3. Aceite do grupo/professor sobre usar CFR (b) exploratório (lacuna não definida no material).
