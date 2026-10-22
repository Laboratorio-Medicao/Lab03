# RQ05 — Discussão: frequência de deploy × CFR (Issue #37)

Insumo para Resultados e Discussão do artigo (Issue #42). Este texto traz só a argumentação. Os números vêm de
`outputs/analise/rq05_spearman.md` e `rq05_spearman.csv`, gerados por `python -m analysis.rq05_spearman` a partir de
`data/metrics.csv`. Se o CSV mudar, regere as saídas e confira os números citados abaixo.

## Resultado em uma linha por variante

| Variante | n | ρ de Spearman | IC95% | p |
|---|---|---|---|---|
| (a) proxy de CI | 300 | −0,017 | [−0,130; 0,096] | 0,768 |
| (b) proxy de entrega (exploratório) | 299 | 0,624 | [0,542; 0,694] | < 0,001 |

Gráficos: `outputs/analise/rq05_df_cfr_a.png` e `rq05_df_cfr_b.png`. Nos dois, DF está em escala log e a linha
vermelha mostra a mediana do CFR por faixa de DF.

## Hipótese H5 vs. resultado

A H5 (`artigo/introducao.tex`) dizia: "Esperamos uma correlação de Spearman **fraca ou levemente negativa** entre
frequência de deploy e CFR".

- **(a) é compatível com a H5.** ρ ≈ 0, e a mediana do CFR (a) fica plana, entre 0,04 e 0,07, em todas as faixas de DF.
- **(b) contradiz a H5.** A correlação é positiva e forte, e o IC95% exclui valores fracos (limite inferior 0,542).
  Pela leitura ingênua, projetos que publicam mais teriam proporcionalmente mais releases "seguidas de correção". As
  seções abaixo mostram por que essa leitura não se sustenta.

## (a) A ausência de associação, lida pelo intervalo

O p = 0,77 sozinho não prova ausência de associação. O que dá para afirmar é que o **IC95% [−0,13; 0,10] exclui
associação monotônica moderada ou forte, em qualquer direção**: no máximo, existe uma associação fraca.

Frente à tese DORA, de que velocidade e estabilidade não são um *trade-off*:

- **A favor da versão fraca da tese.** Publicar mais vezes não vem acompanhado de CI que falha mais. Não há sinal de
  *trade-off* entre velocidade e estabilidade medida por CI.
- **Contra a versão forte da tese.** Também não aparece a associação negativa que "os melhores vão bem nas duas
  dimensões" sugeriria em nível populacional, isto é, projetos rápidos com CI mais estável. Velocidade e taxa de falha
  de CI parecem ortogonais nesta amostra.
- **Ressalva de construto.** CFR (a) mede falha de execução de CI no *default branch* (`push`), não falha em
  produção. Testes instáveis (*flaky*), *matrix builds* e falhas de infraestrutura de CI entram no numerador
  independentemente de quantas releases o projeto publica. Isso tende a diluir qualquer associação com DF.

## (b) Por que ρ ≈ 0,62 não deve ser lido como trade-off

1. **Dependência mecânica entre a métrica e o DF.** Uma release R conta como falha se houver uma release corretiva
   em até 7 dias depois dela (`metricas/cfr_entrega.py`). Com DF baixa, pouquíssimas releases têm qualquer sucessora
   em 7 dias, então o CFR (b) tende a 0 por construção. Com DF alta, há várias releases em cada janela de 7 dias, e
   basta uma delas parecer corretiva. Ou seja, o CFR (b) mede em parte o próprio ritmo de publicação.
2. **Efeito de denominador pequeno.** Entre os repositórios com menos de 10 releases avaliadas, 57% (40/70) têm
   CFR (b) = 0, contra 14% (31/229) entre os que têm 10 ou mais. A sensibilidade com cortes pré-declarados de
   releases avaliadas dá ρ = 0,617 (≥ 5; n = 296), 0,580 (≥ 10; n = 229) e 0,420 (≥ 20; n = 140). A associação
   continua positiva, mas cai.
   - **Ressalva:** DF e nº de releases avaliadas têm ρ = 0,982. O corte também restringe a faixa de DF, e restrição
     de faixa por si só reduz |ρ|. A queda não separa os dois efeitos; ela serve só para dimensionar o problema.
3. **Cultura de *patch release*.** Projetos de DF alta costumam publicar correções pequenas e rápidas (`x.y.z+1`)
   como prática normal de entrega. Para o DORA, uma correção rápida é sinal de boa capacidade de recuperação, mas no
   CFR (b) ela conta como falha da release anterior. É uma divergência de construto com "falha em produção".
4. **Heurística não validada.** A marcação de corretiva (v12) teve F1 independente de 0,689 (IC95% 0,563–0,790),
   abaixo da meta de 0,70. O CFR (b) é exploratório, e toda conclusão da RQ05b deve citar isso.
5. **Exclusão.** Um repositório fica fora de (b): `akveo/react-native-ui-kitten`, com 24 releases na janela, todas
   censuradas (últimos 7 dias). O `akto-api-security/akto` (maior DF da amostra, 25,4 releases/semana) entra desde a
   regeneração do `metrics.csv` (n = 299; a versão anterior do CSV o deixava sem CFR (b) e dava n = 298, ρ = 0,620).

**Conclusão para (b):** o resultado não sustenta um *trade-off* entre velocidade e estabilidade. Ele mostra que essa
operacionalização de CFR é sensível ao ritmo de publicação. A comparação com o *rework rate* (RQ08, Issue #39) ajuda
a separar "proporção de releases corretivas" de "releases que falharam".

## Correlação não implica causalidade

Mesmo a associação nula de (a) e a positiva de (b) não autorizam conclusões causais:

- **Confundidores.**
  - Tamanho do projeto, nº de contribuidores, tipo de projeto (biblioteca, aplicação, CLI) e maturidade da
    automação podem afetar DF e CFR ao mesmo tempo.
  - Por exemplo, projetos com *release* automatizada podem ter, ao mesmo tempo, DF alta e suítes de CI maiores.
  - A RQ06 (Issue #38) examina parte desses fatores.
- **Causalidade reversa.** Em (b), falhas geram *hotfixes*, e *hotfixes* aumentam a DF. Parte do DF alto pode ser
  consequência das falhas, e não o contrário.
- **Nível de agregação.** Cada ponto é um repositório (medianas e proporções no ano). Uma associação entre
  repositórios não diz o que acontece dentro de um projeto que passa a publicar mais (falácia ecológica).
- **Desenho observacional e construto.** Não há intervenção nem controle temporal. Release ≠ deploy e falha de CI ≠
  falha em produção.
- **Validade externa.** A amostra são os primeiros 300 repositórios em ordem alfabética que passam nos filtros, com
  mais de 1000 estrelas. Isso não representa projetos corporativos, que são a base dos relatórios DORA.

## Como citar no artigo (sugestão)

- Reportar ρ, IC95%, p (como "p < 0,001" quando menor) e n das duas variantes.
- Apresentar (a) como a evidência principal sobre a tese DORA.
- Apresentar (b) como exploratória, com a dependência mecânica e o F1 de 0,689 na mesma frase.
- Citar a sensibilidade de (b) só como diagnóstico, com a ressalva de restrição de faixa.
