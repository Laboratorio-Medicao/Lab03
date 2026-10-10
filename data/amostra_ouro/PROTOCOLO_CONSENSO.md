# Protocolo de consenso da amostra-ouro

Aplicado aos rótulos independentes dos três avaliadores (E§6, passo 4). O cálculo é feito por
`python -m scripts.agreement`, que gera `concordancia.csv` (kappa de Fleiss) e `consenso.csv`.

## Antes do consenso

1. Cada avaliador rotula sozinho, sem consultar os demais e sem ver a saída da heurística de
   release corretiva. Cada um commita **somente** o seu `labels_<nome>.csv`, com `#N` da sua Issue.
2. O kappa de Fleiss é calculado **antes** de qualquer discussão, sobre os rótulos independentes
   (3 dimensões: tipo do projeto, releases = entregas reais, corretiva). Kappa baixo é achado, não
   defeito: vai para o artigo, com a interpretação de Landis & Koch.
3. Os três arquivos de rótulos nunca são fundidos nem alterados depois do cálculo do kappa; o
   consenso fica em arquivo próprio.

## Regras de desempate (por item e dimensão)

| Situação | Rótulo de consenso | `metodo` |
|---|---|---|
| Os 3 avaliadores iguais | o rótulo comum | `unanimidade` |
| 2 a 1 | o rótulo da maioria simples | `maioria` |
| 1-1-1 (só possível com 3 ou mais categorias: tipo do projeto e entrega real) | decidido em reunião dos três | `reuniao` |

- "incerto" (dimensão ii) é um rótulo como os outros: entra na contagem e pode ser o consenso.
- Casos 1-1-1 ficam `pendente` em `consenso.csv` até a reunião. Cada decisão é registrada em
  `desempate.csv` (`dimensao,item_id,rotulo,justificativa`), com o critério usado, e aplicada
  rodando o comando de novo. O consenso só é considerado completo sem nenhum `pendente`.
- Na reunião, discute-se apenas o item em desempate. Não se reabrem itens com maioria nem se
  mudam rótulos individuais.

## Uso do consenso

- `corretiva` é a referência para precision/recall/F1 da heurística (`evaluate_heuristic.py`, #28).
- `tipo_projeto` é o fator da RQ06 (válido só para os 60 repositórios rotulados).
- Registrar no artigo: kappa por dimensão, nº de itens por método (unanimidade, maioria, reunião)
  e este protocolo.
