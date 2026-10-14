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
| `deployment_frequency` | float | deploys/dia | DF = `n_releases_deploy_total / duração_janela_dias` |
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
| `dora_geral` | str | — | Pior nota entre as 4 métricas; vazio se qualquer uma indefinida (L10) |

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
| `v1` … `v7` | str | `sim` · `nao` | Release corretiva segundo cada versão (regras em `avaliacao_heuristica.csv`) |

## `data/amostra_ouro/avaliacao_heuristica.csv`

Precisão, recall e F1 de cada versão da heurística frente ao consenso (E§6, #28). Positivo = corretiva.

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `versao`, `descricao` | str | — | Versão e regra |
| `n` | int | releases | Releases avaliadas |
| `tp`, `fp`, `fn`, `tn` | int | releases | Matriz de confusão (heurística × consenso) |
| `precisao` | float | proporção | TP / (TP + FP); 0 sem positivos previstos |
| `recall` | float | proporção | TP / (TP + FN) |
| `f1` | float | proporção | 2·P·R / (P + R) |
| `escolhida` | str | `sim` · `nao` | v1 se F1 ≥ 0,70; senão a de maior F1 (empate → menor número) |
