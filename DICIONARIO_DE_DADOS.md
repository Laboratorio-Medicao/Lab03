# Dicionário de Dados

Documenta todas as colunas dos CSVs gerados pelo pipeline.
A versão machine-readable está em [`DICIONARIO_DE_DADOS.csv`](DICIONARIO_DE_DADOS.csv).
O teste `tests/test_dicionario.py` falha se qualquer coluna dos CSVs não tiver entrada aqui.

---

## `outputs/resultados.csv` e `outputs/repos_final.csv`

`resultados.csv` contém todos os repos processados (concluídos + erros).
`repos_final.csv` é idêntico, mas só com `status=concluido` e sem as colunas `status`/`erro`
— é o dataset congelado para o sorteio da amostra-ouro (#19).

| Coluna | Tipo | Unidade | Fórmula / Origem |
|---|---|---|---|
| `full_name` | str | — | GitHub: `owner/repo` |
| `status` | str | — | `concluido` ou `erro` |
| `erro` | str | — | Mensagem da exceção; vazio se `concluido` |
| `stars` | int | estrelas | GitHub API: `stargazers_count` |
| `language` | str | — | GitHub API: linguagem primária |
| `contributors` | int | pessoas | GitHub API: `/contributors?anon=1` |
| `age_days` | float | dias | `janela.fim − created_at` em dias |
| `default_branch` | str | — | GitHub API: `default_branch` |
| `n_releases_total` | int | releases | Total de releases sem filtro de janela |
| `n_releases_deploy_total` | int | releases | Releases não-draft, não-prerelease e com `published_at` |
| `deployment_frequency` | float | releases/semana | DF = releases de deploy publicadas na janela ÷ semanas da janela (dias ÷ 7) |
| `lt_release_median_h` | float | horas | Lead time **(a)** por release: `published_at(R) − author_date(commit mais antigo de R)`; mediana das releases avaliáveis (E§3) |
| `lt_commit_median_h` | float | horas | Lead time **(b)** por commit: `published_at(R) − author_date(c)` para cada commit `c`; mediana global (E§3) |
| `n_releases_avaliadas` | int | releases | Releases com `status=ok` e ≥1 commit válido |
| `n_releases_ignored_404` | int | releases | Releases excluídas por 404 no `/compare` (E§11) |
| `n_sem_anterior` | int | releases | 1ª release da história (sem compare); excluída do lead time (E§5) |
| `n_sem_commits_novos` | int | releases | Releases com compare OK mas sem commits novos (L07) |
| `n_commits_negativos` | int | commits | Commits com `author_date > published_at`; excluídos do lead time (L07) |
| `n_runs_coletados` | int | runs | Total de runs na janela (todos eventos e workflows) |
| `n_runs_dias_saturados` | int | dias | Dias que atingiram o teto de 1 000 runs da API (dados possivelmente incompletos) |
| `n_runs_fora_de_push` | int | runs | Runs excluídos por não serem evento `push` |
| `n_runs_sucesso` | int | runs | Runs push com `conclusion=success` |
| `n_runs_falha` | int | runs | Runs push com `conclusion∈{failure, timed_out, startup_failure}` |
| `cfr_a` | float | proporção | CFR **(a)**: `n_runs_falha / (n_runs_sucesso + n_runs_falha)`; `None` se sem runs válidos (E§4) |
| `rec_median_h` | float | horas | Recovery time: mediana dos episódios `failure→success` por `workflow_id`; `run_started_at(1ª falha)..updated_at(1º sucesso)` (E§5) |
| `n_episodios` | int | episódios | Total de episódios de falha (recuperados + censurados) |
| `n_episodios_censurados` | int | episódios | Episódios sem sucesso subsequente (censurados; excluídos de `rec_median_h`) |
| `prop_episodios_censurados` | float | proporção | `n_episodios_censurados / n_episodios`; `None` se `n_episodios=0` |
| `n_tags` | int | tags | Git tags do repositório (variante C3 da RQ07); `None` se `coleta.tags=false` |
| `df_class` | str | — | Classificação DORA de DF: `Elite/High/Medium/Low` (E§2); vazio se indefinido |
| `lt_class` | str | — | Classificação DORA de Lead Time (E§2); vazio se indefinido |
| `cfr_class` | str | — | Classificação DORA de CFR (E§2); vazio se indefinido |
| `rec_class` | str | — | Classificação DORA de Recovery (E§2); vazio se indefinido |
| `dora_geral` | str | — | Mediana (floor) das notas das métricas definidas; vazio só sem nenhuma (L10, decisão do grupo validada com o professor) |
| `n_metricas_dora` | int | contagem | Métricas (de 4) que entraram em `dora_geral`; <4 = classificação parcial |

---

## `outputs/funil.csv`

Uma linha por repositório candidato — registra o resultado de cada etapa do funil de seleção.

| Coluna | Tipo | Unidade | Fórmula / Origem |
|---|---|---|---|
| `full_name` | str | — | GitHub: `owner/repo` |
| `stars` | int | estrelas | GitHub API: `stargazers_count` |
| `language` | str | — | GitHub API: linguagem primária |
| `default_branch` | str | — | GitHub API: `default_branch` |
| `created_at` | str | ISO 8601 | GitHub API: `created_at` |
| `status` | str | — | `candidato`, `selecionado` ou `descartado` |
| `etapa` | str | — | Etapa em que o repo foi avaliado ou descartado |
| `motivo` | str | — | Motivo do descarte (`no_actions`, `lt_5_releases`, `lt_50_runs`, …); vazio se selecionado |
| `workflows_total_count` | int | workflows | Total de workflows verificados na seleção |
| `n_releases_window` | int | releases | Releases na janela usadas no filtro |
| `runs_consultados` | int | runs | Runs consultados na seleção |
| `n_runs_valid_window` | int | runs | Runs push válidos na janela (filtro `min_runs_validos`) |
| `contributors` | int | pessoas | Idem `resultados.csv` |
| `age_days` | float | dias | Idem `resultados.csv` |

---

## `data/amostra_ouro/amostra_ouro.csv`

Sorteio completo: 60 repositórios × 5 releases = 300 linhas. Gerado por `scripts/sample_gold.py`
com semente fixa `SEED=42` a partir de `repos_final.csv` (#22).

| Coluna | Tipo | Unidade | Fórmula / Origem |
|---|---|---|---|
| `full_name` | str | — | Um dos 60 repos sorteados |
| `repo_url` | str | URL | `https://github.com/<full_name>` |
| `release_id` | int | — | GitHub API: `id` da release |
| `tag_name` | str | — | GitHub API: `tag_name` |
| `published_at` | str | ISO 8601 | GitHub API: `published_at` |
| `release_url` | str | URL | Página da release no GitHub (`html_url`) |
| `compare_url` | str | URL | Diff com a release anterior (`/compare/tag_ant...tag`); vazio se 1ª da história |

---

## `data/amostra_ouro/labels_<avaliador>.csv`

Uma planilha por avaliador para rotulagem independente (E§6). As releases são as mesmas nos três
arquivos. Gerado por `scripts/sample_gold.py` (#22); preenchido manualmente (#23, #24, #25).

| Coluna | Tipo | Valores válidos | Descrição |
|---|---|---|---|
| `full_name` | str | — | Idem `amostra_ouro.csv` |
| `repo_url` | str | URL | Idem `amostra_ouro.csv` |
| `tipo_projeto` | str | `biblioteca_framework` · `aplicacao_servico` · `ferramenta_cli` · `outro` | Rótulo **por repositório** (preencher só na 1ª linha do repo) |
| `releases_sao_entregas_reais` | str | `sim` · `nao` · `incerto` | Releases do repo representam entregas reais? (rótulo **por repositório**) |
| `release_id` | int | ≥1 | Idem `amostra_ouro.csv` |
| `tag_name` | str | — | Idem `amostra_ouro.csv` |
| `published_at` | str | ISO 8601 | Idem `amostra_ouro.csv` |
| `release_url` | str | URL | Idem `amostra_ouro.csv` |
| `compare_url` | str | URL | Idem `amostra_ouro.csv` |
| `corretiva` | str | `sim` · `nao` | Esta release é corretiva? (rótulo **por release**) |
| `observacoes` | str | — | Texto livre; opcional |

## `data/amostra_ouro/heuristica_amostra.csv`

Saída da heurística de release corretiva sobre as 300 releases da amostra-ouro, gerada por
`scripts/evaluate_heuristic.py` (#28) **só depois** de os três rótulos estarem completos (E§6). Valores
`sim`/`nao`. Uma versão nova em `metricas.heuristica.VERSOES` vira coluna nova e precisa entrar aqui.

| Coluna | Tipo | Valores válidos | Descrição |
|---|---|---|---|
| `release_id` | int | ≥1 | Idem `amostra_ouro.csv`; junta com `item_id` de `consenso.csv` |
| `full_name`, `tag_name` | str | — | Idem `amostra_ouro.csv` |
| `base` | str | — | Tag da release anterior (do `compare_url`); vazio na 1ª release da história |
| `status` | str | `ok` · `404` · `sem_anterior` | Status do `compare/{base}...{tag}` |
| `mensagens_incompletas` | str | `sim` · `nao` | `compare` com 404 ou truncado: a palavra-chave pode faltar por falta de dado |
| `semver_patch` | str | `sim` · `nao` · vazio | Só o patch subiu; vazio se as tags não são comparáveis ou sem anterior |
| `palavra_chave` | str | `sim` · `nao` | `revert`/`hotfix`/`fix` como palavra inteira em algum commit |
| `palavra_chave_ampla` | str | `sim` · `nao` | Também `fixes`, `fixed`, `fixing`, `bugfix`, `reverted`… |
| `n_correcoes` | int | ≥ 0 ou vazio | Commits substantivos de correção (fix/hotfix/bugfix/revert); vazio sem release anterior |
| `n_features` | int | ≥ 0 ou vazio | Commits substantivos de feature (feat/add/support…); vazio sem release anterior |
| `nota_correcao` | str | `sim` · `nao` · vazio | Release notes citam correção; vazio se notas indisponíveis |
| `nota_novidade` | str | `sim` · `nao` · vazio | Release notes citam novidade; vazio se notas indisponíveis |
| `notas_indisponiveis` | str | `sim` · `nao` | Release com anterior cujas release notes deram HTTP 404/410 (removida); só aceito para repositórios em `--permitir-sem-notas` |
| `v1` … `v9` | str | `sim` · `nao` · vazio | Release corretiva segundo cada versão (regras em `avaliacao_heuristica.csv`); vazio = não avaliável (v9 sem release notes) |

## `data/amostra_ouro/avaliacao_heuristica.csv`

Precisão, recall e F1 de cada versão da heurística frente ao consenso (E§6, #28). Positivo = corretiva.

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `versao`, `descricao` | str | — | Versão e regra |
| `n` | int | releases | Releases avaliáveis por esta versão (base de TP/FP/FN/TN, precisão, recall e F1) |
| `n_comum`, `precisao_comum`, `recall_comum`, `f1_comum` | int / float | releases / proporção | Mesmas medidas no subconjunto em que todas as versões são avaliáveis (usado para comparar e escolher) |
| `tp`, `fp`, `fn`, `tn` | int | releases | Matriz de confusão (heurística × consenso) |
| `precisao` | float | proporção | TP / (TP + FP); 0 sem positivos previstos |
| `recall` | float | proporção | TP / (TP + FN) |
| `f1` | float | proporção | 2·P·R / (P + R) |
| `escolhida` | str | `sim` · `nao` | Regra interna do script: v1 se F1 comum ≥ 0,70; senão a de maior F1 comum (empate → menor número). **Não indica validação**: nenhuma versão atingiu F1 ≥ 0,70 |

## `data/amostra_ouro/erros_heuristica.csv`

Falsos positivos e falsos negativos de uma versão da heurística frente ao consenso, gerado por
`scripts/analise_erros_heuristica.py` (#30, bônus) a partir das saídas da #28.

| Coluna | Tipo | Valores válidos | Descrição |
|---|---|---|---|
| `versao` | str | `v1`, `v2`… | Versão analisada (padrão: a escolhida em `avaliacao_heuristica.csv`) |
| `release_id`, `full_name`, `tag_name` | — | — | Idem `amostra_ouro.csv` |
| `base` | str | — | Idem `heuristica_amostra.csv` |
| `tipo_erro` | str | `FP` · `FN` | FP: heurística = corretiva e consenso = não; FN: o contrário |
| `causa_automatica` | str | ver README (#30) | Triagem pelos sinais da versão, uma causa por erro |
| `semver_patch`, `palavra_chave`, `palavra_chave_ampla`, `mensagens_incompletas` | str | `sim` · `nao` (· vazio) | Idem `heuristica_amostra.csv` |
| `release_url`, `compare_url` | str | URL | Idem `amostra_ouro.csv` |
| `causa_manual` | str | — | Anotação do grupo lendo os commits; preservada por `release_id` ao regravar |


## `data/metrics.csv`

Dataset analítico final gerado por `scripts/compute_metrics.py` (#21) a partir de
`outputs/repos_final.csv`. Contém todas as colunas de `repos_final.csv` (copiadas como estão)
mais as variantes calculadas após o refinamento da heurística.

### Colunas herdadas de `repos_final.csv`

Todas as colunas de `repos_final.csv` são copiadas sem alteração. Consulte a tabela
"outputs/resultados.csv e outputs/repos_final.csv" acima para as definições.

### Colunas novas: CFR (b) com heurística v8

| Coluna | Tipo | Unidade | Fórmula / Origem |
|---|---|---|---|
| `cfr_b` | float | proporção | CFR **(b)**: proporção de releases avaliadas seguidas de corretiva em ≤7 dias; `heuristic_version=v8`; `None` se <2 releases na janela ou sem avaliadas (E§5 RQ03b) |
| `cfr_b_class` | str | — | Classificação DORA de CFR (b); vazio se `cfr_b` indefinido |
| `n_releases_avaliadas_cfr_b` | int | releases | Releases na janela publicadas antes de `fim − 7 dias` (fora da zona de censura); denominador do CFR (b) |
| `n_releases_censuradas_cfr_b` | int | releases | Releases nos últimos 7 dias da janela: censuradas, excluídas do denominador (E§5) |
| `n_releases_janela` | int | releases | Total de releases de deploy na janela; `n_avaliadas + n_censuradas` |
| `n_releases_falha_cfr_b` | int | releases | Releases avaliadas marcadas como falha (seguidas de corretiva ≤7 dias) |
| `n_releases_mensagens_incompletas_cfr_b` | int | releases | Releases da janela com `compare` 404 ou truncado (diagnóstico; não entra na invariante) |
| `heuristic_version` | str | — | Versão da heurística usada no CFR (b); final congelada: `v12` |

### Colunas novas: variantes da RQ07

| Coluna | Tipo | Unidade | Fórmula / Origem |
|---|---|---|---|
| `n_releases_deploy_c2` | int | releases | Releases + pré-releases na janela (não-draft, com `published_at`): unidade de deploy da combinação C2 |
| `df_c2` | float | deploys/semana | DF **(C2)**: `n_releases_deploy_c2 / semanas_janela` (conta pré-releases) |
| `df_c2_class` | str | — | Classificação DORA de DF para C2 |
| `n_tags_janela` | int | tags | Tags com `author_date` dentro da janela: unidade de deploy da combinação C3 |
| `n_compare_divergentes` | int | contagem | Releases da janela com `compare` `diverged` (anterior em outra linha de versão; LT pode inflar) |
| `n_compare_truncados` | int | contagem | Releases da janela com `compare` truncado pelo limite da API |
| `df_c3` | float | deploys/semana | DF **(C3)**: `n_tags_janela / semanas_janela` |
| `df_c3_class` | str | — | Classificação DORA de DF para C3 |
| `dora_c1` | str | — | Classificação DORA geral C1 (release · LT(a) · CFR(a) · recovery): mediana floor das 4 notas |
| `dora_c2` | str | — | Classificação DORA geral C2 (release+pré-release · LT(b) · CFR(b) · recovery); vazio se `cfr_b` indefinido |
| `dora_c3` | str | — | Classificação DORA geral C3 (tag · LT(b) · CFR(a) · recovery) |
| `n_metricas_dora_c1`, `n_metricas_dora_c2`, `n_metricas_dora_c3` | int | contagem | Métricas definidas em cada combinação (<4 = parcial) |

---

## Status de validação da heurística de release corretiva (CFR (b))

Os valores de CFR (b) que vierem a entrar no dataset final usam uma heurística **não validada** (nenhuma
versão atingiu F1 ≥ 0,70; ver `docs/refino_heuristica.md`). Regras de uso:

Números da rodada oficial (rótulos commitados nas Issues #23–#25; 300 releases, 85 corretivas). Os papéis
foram definidos na rodada anterior e estão **a rever pelo grupo**: agora a v4 tem F1 maior que a v8.

| Versão (`heuristic_version`) | Papel | Precisão | Recall | F1 | Taxa prevista (referência 28,3%) |
|---|---|---:|---:|---:|---:|
| v8 | estimativa principal **exploratória** | 0,625 | 0,412 | 0,497 | 18,7% |
| v4 | análise de **sensibilidade** | 0,429 | 0,894 | 0,580 | 59,0% |
| v9 | variante experimental, **fora do dataset** (precisa de `body` das releases; n = 295) | 0,627 | 0,573 | 0,599 | 25,4% |

- Todo CFR (b) deve ser lido junto do `heuristic_version` e destes P/R/F1; o F1 é otimista (v8/v9 foram
  desenhadas após a análise de erros, na mesma amostra).
- CFR (b) e CFR (a) medem construtos diferentes e a diferença entre eles inclui o erro de classificação.

## `data/amostra_ouro/concordancia.csv` e `consenso.csv`

Gerados por `scripts/agreement.py` (#26) a partir dos três `labels_<avaliador>.csv` (protocolo em
`data/amostra_ouro/PROTOCOLO_CONSENSO.md`).

| Arquivo | Coluna | Tipo | Descrição |
|---|---|---|---|
| `concordancia.csv` | `dimensao` | str | `tipo_projeto` · `entrega_real` · `corretiva` |
| `concordancia.csv` | `n_itens`, `n_avaliadores` | int | Itens (repositórios ou releases) e avaliadores |
| `concordancia.csv` | `kappa_fleiss` | float | Kappa de Fleiss; vazio se não há variação |
| `concordancia.csv` | `interpretacao` | str | Landis & Koch (1977) |
| `concordancia.csv` | `concordancia_simples` | float | Fração de itens com os três rótulos iguais |
| `consenso.csv` | `dimensao`, `item_id`, `descricao` | str | Item: `full_name` (por repositório) ou `release_id` (corretiva) |
| `consenso.csv` | `GuilhermeVieira05`, `marcosffp`, `ALuiz19` | str | Rótulo de cada avaliador |
| `consenso.csv` | `rotulo_consenso` | str | Rótulo de consenso; vazio se pendente |
| `consenso.csv` | `metodo` | str | `unanimidade` · `maioria` · `reuniao` · `pendente` |
| `consenso.csv` | `justificativa` | str | Decisão da reunião (só `reuniao`) |

## Saídas das análises RQ01–RQ04 (`outputs/analise/`, Issue #35)

Geradas por `python -m analysis.rq01_rq04` a partir de `data/metrics.csv`. O detalhe campo a campo está em `DICIONARIO_DE_DADOS.csv` (arquivos `dora_class.csv`, `dora_class_distribuicao.csv`, `dora_class_por_metrica.csv`, `rq01_rq04_descritiva.csv`, `rq04_censura.csv`, `rq04_censura_resumo.csv`).

| Arquivo | Conteúdo |
|---|---|
| `dora_class.csv` | Classe por métrica e classe geral C1 de cada repositório (`n_metricas` < 4 = parcial, L10) |
| `dora_class_distribuicao.csv` / `dora_class_por_metrica.csv` | Contagem Elite/High/Medium/Low |
| `rq01_rq04_descritiva.csv` | n, mediana, Q1, Q3 e IQR de DF, LT (a)/(b), CFR (a)/(b) e recuperação |
| `rq04_censura.csv` / `rq04_censura_resumo.csv` | Episódios censurados por repositório e no total |
