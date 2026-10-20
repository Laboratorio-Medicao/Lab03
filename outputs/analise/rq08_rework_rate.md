# RQ08 (bônus) — Rework rate e diferença para o CFR (b)

Gerado por `python -m analysis.rq08_rework_rate` (Issue #39) a partir de `data/metrics.csv` e
`outputs/analise/rq08_releases.csv` (rótulos por release de `python -m scripts.rq08_rotular_releases`).
Não editar à mão.

## Definição operacional

- **Rework rate** do repositório = nº de releases de deploy **corretivas** na janela ÷ nº de releases de
  deploy na janela (E§5 RQ08; DORA 2024: proporção de deploys não planejados, feitos para corrigir um problema).
- **Release de deploy:** `draft=false`, `prerelease=false`, `published_at` em 2025-10-02 a 2026-10-02 (UTC,
  dia final inclusivo, 366 dias); é a mesma unidade do DF (C1) e do CFR (b).
- **Corretiva:** heurística **v12**, a mesma do CFR (b) (`heuristic_version`), sobre os mesmos itens
  (commits do `compare` + release notes). Release sem anterior nunca é corretiva e fica no denominador.
- **Sem censura:** a corretividade de S é conhecida quando S é publicada, então as releases dos últimos 7 dias
  entram. Por isso o rework é definido com ≥ 1 release, e o CFR (b) só com ≥ 2 releases e ≥ 1 avaliada.
- **Conferência:** os contadores do CFR (b) recontados dos rótulos (janela, avaliadas, censuradas, falhas,
  CFR (b), mensagens incompletas, compares divergentes/truncados) precisam bater com o `metrics.csv`. Base:
  299 repositórios com referência; divergentes: 1 (limite: 5%).
  1 repositório(s) da base saíram da RQ08 (1bananachicken/MaaNTE: sem rótulos (erro ou ausência na extração)). Mediana de DF dos excluídos: 0,344 releases/semana (incluídos: 0,363); mediana de releases na janela segundo o `metrics.csv`: 18 (incluídos: 19). Todos os repositórios com rótulos reproduzem exatamente os contadores do `metrics.csv`. Sem referência no CSV (CFR (b) não calculado na S02): akto-api-security/akto.

## Resultados

| Métrica | n | Mediana | Q1 | Q3 | IQR |
|---|---:|---:|---:|---:|---:|
| Rework rate | 298 | 0,286 | 0,136 | 0,464 | 0,328 |
| Rework rate (só releases avaliáveis do CFR b) | 297 | 0,293 | 0,138 | 0,467 | 0,329 |
| Rework rate (subconjunto pareado) | 297 | 0,287 | 0,135 | 0,464 | 0,329 |
| CFR (b) (subconjunto pareado) | 297 | 0,200 | 0,038 | 0,464 | 0,426 |
| Diferença rework − CFR (b) (pareado) | 297 | 0,000 | -0,114 | 0,200 | 0,314 |

- Pareado (n = 297): rework > CFR (b) em 142 repositórios, iguais em
  50 e rework < CFR (b) em 105. Wilcoxon pareado (zeros descartados):
  W = 12756,0, p = 0,023; rank-biserial pareado
  r = 0,167 (positivo = rework maior).
- Spearman: ρ(rework, CFR (b)) = 0,479 (p < 0,001, n = 297);
  ρ(DF, CFR (b)) = 0,620 (p < 0,001, n = 297);
  ρ(DF, rework) = 0,059 (p = 0,312, n = 298).
- Taxas agregadas (todas as releases juntas, dominadas pelos repositórios de alta cadência): rework
  0,269 (3582 de 13295 releases); CFR (b) 0,474.
- Corretivas por categoria (3582): com antecedente avaliada em até 7 d 2840
  (79,3%); antecedente só censurado 24
  (0,7%); antecedente antes do início da janela 5
  (0,1%); nenhuma release nos 7 d anteriores 713
  (19,9%). A razão entre releases que falharam e corretivas com antecedente é
  2,15; acima de 1, cada correção marca em média mais de uma
  release como falha no CFR (b).

## Em que o rework rate difere do CFR (b)

1. **Pergunta medida.** O CFR (b) pergunta se a release R *precisou* de correção. O rework pergunta se a
   release S *é* uma correção (deploy não planejado). O CFR (b) conta o **antecedente** (R que falhou); o
   rework conta o **consequente** (S corretiva).
2. **Prazo.** O CFR (b) só conta R se houver uma S corretiva em (R, R + 7 d]. O rework não exige uma release
   antecedente em até 7 dias. A v12 não mede a idade do defeito (o enunciado define corretiva como a que corrige
   defeito recente, e as duas métricas usam a mesma marcação), então uma S com a release anterior a mais de 7 d
   conta só no rework (713 corretivas nesta amostra).
3. **Censura.** O CFR (b) tira do denominador as releases dos últimos 7 dias da janela. O rework usa todas. A
   variante "só releases avaliáveis" isola esse efeito: mediana 0,293 contra
   0,286 com todas as releases. A diferença é pequena (< 0,02), então a censura não explica a diferença entre as métricas.
4. **Multiplicidade.** Uma S corretiva marca como falha **todas** as R avaliadas dos 7 dias anteriores. Em
   repositórios com rajadas de releases (alta DF), uma correção vira várias falhas, e o CFR (b) passa do
   rework. Uma S isolada conta só no rework. Uma corretiva pode, ao mesmo tempo, ser uma R que falhou (cadeia
   de *hotfixes*). Nesta amostra o sinal da comparação depende do peso: por repositório, a mediana do rework (0,287) supera a do CFR (b) (0,200), mas na taxa agregada o CFR (b) (0,474) supera o rework (0,269). Os repositórios de alta cadência pesam mais no agregado e concentram as rajadas.
5. **Dependência da cadência.** Como a janela de 7 dias do CFR (b) captura mais releases quando a DF é alta, o
   CFR (b) depende mecanicamente da DF. Nesta amostra, ρ(DF, CFR (b)) = 0,620 e
   ρ(DF, rework) = 0,059. O rework, que não tem janela de correspondência, é menos associado à cadência.
6. **Correlação em parte mecânica.** ρ(rework, CFR (b)) = 0,479 é positivo em parte porque as duas saem dos **mesmos
   rótulos** de corretiva. Isso não mostra que medem a mesma coisa. O Wilcoxon descreve a diferença de nível
   entre dois estimandos distintos; ele não testa se as duas são "a mesma métrica".
7. **Erro de classificação.** As duas herdam o erro da v12 (validação independente: precisão 0,729, recall
   0,654, F1 0,689, IC95% 0,563–0,790). A heurística **não está validada** (meta F1 ≥ 0,70 não atingida), e o
   rework, como o CFR (b), é **exploratório**. No rework o erro entra uma vez, como viés de nível. Na amostra
   independente (200 releases de 40 repositórios, 5 por
   repositório e só releases com anterior), a prevalência de corretivas é 0,390
   pelo consenso e 0,350 pela v12. A razão é 0,897 (= recall ÷ precisão;
   IC95% bootstrap por repositório 0,718–1,100).
   A estimativa pontual sugere que a v12 **subestima** o rework agregado, mas o IC inclui 1: não há evidência firme de viés de nível. Isso supõe que precisão e recall se transportem para a
   população. Esse fator **não** se aplica à mediana por repositório, e a amostra balanceada não é comparável
   às taxas agregadas. No CFR (b), um falso positivo ou negativo em S se propaga para várias R, e o efeito
   depende da cadência.

## Limitações

- Repositórios com publicação em lote (ex.: todas as releases nos últimos 7 dias da janela) entram no rework,
  mas não têm CFR (b) definido.
- Não há classificação DORA do rework: a tabela fixa da disciplina não tem faixa para essa métrica.
- A conferência com o `metrics.csv` é por contadores. Uma troca de rótulo que não altere nenhum contador do
  CFR (b) não seria detectada.
- Release com `compare` 404 ou truncado é classificada com os dados disponíveis (mesmo tratamento do CFR (b)).
