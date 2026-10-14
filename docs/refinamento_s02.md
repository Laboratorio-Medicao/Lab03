# Refinamento da Sprint S02 (Issue #18)

Refinamento feito em 2026-10-14 sobre `main` em `2505dcc`. Cada card da milestone
"S02 — Amostra Completa e Validação Manual" tem abaixo: dono, critério de aceite verificável,
dependências e o estado conferido no repositório nessa data.

## Objetivo e entregáveis (E§10, #17)

- Amostra final com **≥ 300 repositórios** após os filtros.
- Métricas em todas as variantes obrigatórias: DF, lead time (a)/(b), CFR (a)/(b), recuperação e
  classificação DORA.
- Dataset `.csv` com dicionário de dados.
- Validação manual: amostra-ouro de 60 repositórios, kappa de Fleiss nas 3 dimensões, consenso e
  P/R/F1 da heurística corretiva (F1 ≥ 0,70, ou refinamentos documentados).
- Artigo: seção de Metodologia.
- Snapshot do Kanban.

## Cards: critérios de aceite e estado

| # | Card | Dono | Tipo | Critério de aceite (como provar) | Depende de | Estado em 2026-10-14 | Ação |
|---|---|---|---|---|---|---|---|
| 19 | Coleta ≥ 300 e consolidação | Guilherme | código/dados | `outputs/repos_final.csv` com ≥ 300 repositórios, iguais aos `selecionado` do funil; funil final; contagens de censurados e de releases ignoradas por 404; lista congelada (commit citado) antes do sorteio, com sha256 em `sorteio.json` | #18 | PR #58 mergeado; `repos_final.csv` com 300 linhas | Conferir o critério e mover para Done |
| 20 | Dicionário de dados | Guilherme | código | `DICIONARIO_DE_DADOS.md/.csv` e teste que falha com coluna sem entrada | #18, #19 | Feito (`tests/test_dicionario.py`) | — |
| 21 | Variantes e arquivo de métricas | Guilherme | código | Arquivo de métricas com DF, LT (a)/(b), CFR (a)/(b), recuperação, classificação, colunas das combinações C1–C3 (RQ07) e flags de censura; todas as colunas no dicionário; `scripts.data_quality` lendo esse arquivo sem `FALHA` e com as invariantes de CFR (b) em `OK` (não `N/A`). **O CFR (b) usa a `heuristic_version` final avaliada na #28**: se a #28 refinar a heurística, a #21 é recalculada | #18, #19, #27, #28 | Não iniciado | Decidir o nome do arquivo (ver divergência 8); pode começar com a v1 da heurística |
| 22 | Sorteio da amostra-ouro | Marcos | código | `sample_gold.py` com semente 42, 5 releases por repositório iguais para os 3, planilhas com links | #18, #19 | Feito | — |
| 23 | Rotulagem — Marcos | Marcos | rotulagem | `labels_marcosffp.csv` passa em `validar_rotulos` (300/300 `corretiva`, 60/60 tipo e entrega real) e é commitado com `#23`, sem ver a saída da heurística | #18, #22 | **Fechada, mas o arquivo está vazio** (0/300, 0/60) | Reabrir (divergência 1) |
| 24 | Rotulagem — Arthur | Arthur | rotulagem | Igual à #23, para `labels_ALuiz19.csv`, commitado com `#24` | #18, #22 | Aberta; arquivo vazio | Fazer em paralelo com a #27 |
| 25 | Rotulagem — Guilherme | Guilherme | rotulagem | Igual à #23, para `labels_GuilhermeVieira05.csv` | #18, #22 | Feito (300/300, 60/60) | — |
| 26 | Fleiss, consenso e protocolo | Marcos | código/dados | `scripts.agreement` gera `concordancia.csv` (3 kappas, Landis & Koch) e `consenso.csv` sem `pendente`, a partir dos 3 rótulos; `PROTOCOLO_CONSENSO.md` | #18, #23, #24, #25 | **Fechada**: código e protocolo prontos; `concordancia.csv` e `consenso.csv` não existem | Reabrir até o consenso existir (divergência 2) |
| 27 | Heurística corretiva e CFR (b) | Arthur | código | `heuristica.py` com `heuristic_version` e saída por release `heuristic_corrective`; `metricas.cfr_entrega`: R falha se **qualquer** release de deploy em (R, R+7d] for corretiva (7 dias inclusive, não só a próxima, L08); releases nos últimos 7 dias da janela são censuradas (fora do denominador); devolve `cfr_b`, `n_releases_avaliadas_cfr_b`, `n_releases_censuradas_cfr_b` e `n_releases_janela` (constantes `COL_*` de `scripts/data_quality.py`). Testes: v2.3.0→v2.3.1 falhou, v2.4.0→v2.5.0 não falhou, corretiva que não é a próxima release, exatamente 7 dias, não-SemVer, prefixo `v`, `-rc1` e censura. Cobertura de `metricas` ≥ 80% | #18 (*) | Não iniciado | Prioridade 1 do Arthur |
| 28 | Avaliação P/R/F1 e refino | Arthur | código | `evaluate_heuristic.py` com `precision_recall_fscore_support` contra `consenso.csv` (linhas da dimensão `corretiva`, coluna `rotulo_consenso`); tabela versão → P/R/F1 com **todas** as versões testadas (E§6), versionada no repo; F1 ≥ 0,70 ou refinamentos documentados; heurística final definida | #18, #26, #27 | Não iniciado | Código e testes podem avançar; a rodada real espera o consenso |
| 29 | (Bônus) Qualidade dos dados | Marcos | código | `data_quality.md/.csv` com as invariantes | #18, #21 | Script pronto; `outputs/data_quality.md` ainda é da amostra de 100, com CFR (b) e dicionário em `N/A` | Rodar de novo depois da #21 (opcional) |
| 30 | (Bônus) Análise de erros | Arthur | código | Matriz de confusão, lista de FP/FN, taxonomia de causas e comparação entre versões da heurística | #18, #28 | Não iniciado | Depois da #28 |
| 31 | Artigo — Metodologia | todos | escrita | Seção de Metodologia (`.tex`): fonte de dados, funil, janela, definições e variantes, protocolo de validação, κ e tabela versão → F1 | #18, #21, #26, #28 | `artigo/` só tem `introducao.tex` | Depois de #26, #28 e #21 |
| 32 | Snapshot do Kanban | Arthur | dados | Snapshot do board ao fim da S02 em `data/kanban-snapshots/`; WIP, assignees e cartões conferidos | #19–#31 | Não iniciado | Último card da sprint |

(*) **"#27 depende de #24", reinterpretado:** a *implementação* da heurística pode avançar já. O que exige a
#24 (e a #23) concluída é **executar a heurística sobre as releases da amostra-ouro**, o que acontece na #28.
Regra: ninguém roda nem divulga a saída da heurística na amostra-ouro antes de os 3 arquivos de rótulos
passarem em `validar_rotulos` (E§6: rotular "sem ver a saída da heurística").

## Dependências e caminho crítico

```text
#23, #24 (+ #25 feita) ──► #26 consenso ──► #28 P/R/F1 + refino ──► heurística final
                                              ▲                       │
#27 heurística v1 ────────────────────────────┘                       ▼
                                      #21 métricas (CFR b final) ──► #31 Metodologia ──► #32 snapshot
#28 ──► #30 (bônus)          #21 ──► #29 rerun (bônus, fora do caminho crítico)
```

O caminho crítico (fonte da verdade, §8) é: rótulos → consenso → P/R/F1 e refino → heurística final →
CFR (b) → Metodologia. Hoje ele está travado nos rótulos da #23 e da #24.

## Código por integrante (E§10)

A ausência de commit de código atribuível a um integrante zera a parcela individual dele na sprint.

| Integrante | Cards de código | Situação |
|---|---|---|
| GuilhermeVieira05 | #19, #20, #21 | Cumprido (commits da #19 e da #20) |
| marcosffp | #22, #26, #29 | Cumprido (commits da #22, #26 e #29) |
| ALuiz19 | #27, #28, #30 | **Planejado, ainda não cumprido**: nenhum commit de código na S02 (rotulagem não conta). A #27 resolve isso |

## WIP e ordem de puxada

Limite: **3 cartões In progress por pessoa**. Hoje: Arthur 1 (#18), Guilherme 0, Marcos 0.

| Integrante | Ordem sugerida |
|---|---|
| Arthur | #24 e #27 em paralelo (com a #18 dá 3) → #28 → #31 → #30 → #32 |
| Guilherme | Fechar a #19 → #21 (com a v1 da heurística, recalcular com a final) → #31 |
| Marcos | Reabrir e concluir a #23 → rodar a #26 com os 3 rótulos → #29 (rerun) → #31 |

## Divergências encontradas e ação

1. **#23 fechada com `labels_marcosffp.csv` vazio.** O commit `5251d95` (#23) entregou só o validador e o
   padrão de nome. → Marcos reabre a #23, move para In progress e commita os rótulos.
2. **#26 fechada sem `concordancia.csv` nem `consenso.csv`.** O código e o protocolo estão prontos, mas o
   critério do card (consenso registrado) depende dos 3 rótulos. → Reabrir até o consenso existir (Marcos).
3. **#19 aberta (Ready) com a entrega já mergeada** (PR #58). → Guilherme confere o critério e move para Done.
4. **`outputs/data_quality.md` desatualizado** (amostra de 100). → Rodar de novo depois da #21.
5. **Nomes dos arquivos de rótulo.** O padrão adotado é `labels_<login>.csv` (validador, `LEIAME.md`), mas
   os nomes antigos (`labels_marcos/arthur/guilherme.csv`) seguem nas Issues #23–#25, no `README.md`
   (l. 185–186), em `scripts/agreement.py` (l. 5–6 e 182) e em `scripts/validar_rotulos.py` (l. 5). →
   Padronizar no login, num card de código (sugestão: dono da #26).
6. **Janela de observação provisória** (lacuna L01, `config.yaml`). Trocar a janela invalida a coleta e o
   sorteio. → Confirmar as datas com o professor o quanto antes.
7. **Cache não versionado.** A avaliação da #28 precisa das mensagens de commit das 300 releases da
   amostra-ouro, que só existem no cache de quem rodou a coleta. → Combinar entre compartilhar o cache e
   fazer uma coleta seletiva via API.
8. **Nome do arquivo de métricas.** A fonte da verdade (S02-003) e a #21 falam em `metrics.csv`; hoje o
   pipeline gera `outputs/resultados.csv`, que é o padrão do `data_quality`. → Guilherme decide na #21 e o
   dicionário e o `data_quality` passam a apontar para o arquivo escolhido.

## Riscos da sprint

- Rótulos atrasados (#23, #24) travam o consenso, o F1, o CFR (b) final e a Metodologia.
- F1 < 0,70 exige refino e nova rodada da #21.
- Janela provisória: mudar as datas obriga a refazer coleta e sorteio.
- Arthur sem commit de código na S02 até a #27 ser mergeada.
