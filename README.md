# Lab03 — Mineração de Métricas DORA

Pipeline reprodutível que calcula as métricas DORA (deployment frequency, lead time, change failure rate e tempo de recuperação) a partir de dados públicos do GitHub (releases, commits e GitHub Actions).

> **Estado atual (Sprint S01):** o comando único encadeia seleção, funil, coleta (releases, tags, commits entre releases e workflow runs) e métricas DORA, com cache em disco e retomada.

## Pré-requisitos

- Python **3.12** (versão usada no CI)
- Git

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Token do GitHub

O token é lido da variável de ambiente `GITHUB_TOKEN`. **Nunca** o coloque no `config.yaml` nem o commite.

```bash
export GITHUB_TOKEN="seu_token"
```

Alternativamente, crie um arquivo `.env` na raiz (já ignorado pelo Git) com `GITHUB_TOKEN=seu_token`; o comando o carrega sozinho. Uma variável já exportada no terminal tem prioridade sobre o `.env`.

Sem a variável definida, o comando falha com uma mensagem explicando o que fazer.

## Configuração (`config.yaml`)

| Chave | Descrição |
|---|---|
| `github.token_env` | Nome da variável de ambiente que guarda o token (padrão `GITHUB_TOKEN`). |
| `janela.inicio` / `janela.fim` | Janela de observação de 12 meses (`AAAA-MM-DD`, UTC). **Datas provisórias** no `config.yaml` até o professor informar as oficiais (L01); basta editar essas duas linhas. |
| `caminhos.cache` | Pasta do cache local (ignorada pelo Git). |
| `caminhos.saidas` | Pasta das saídas geradas (`funil.csv`, CSVs finais). |

## Execução (comando único)

```bash
python -m pipeline --config config.yaml
```

O comando faz tudo: busca e filtra candidatos até completar `selecao.amostra_alvo` (100) repositórios, coleta os dados de cada um e grava em `outputs/`: `funil.csv`, `funil.md`, `resultados.csv` e `execucao.log`. O funil é regravado a cada 10 repositórios avaliados. A primeira execução leva horas (limite de 5.000 chamadas/hora); o pipeline espera sozinho quando a cota acaba.

**Interrupção e retomada.** Se parar (`Ctrl+C`, rede, rate limit), rode o mesmo comando: as respostas já feitas estão em `cache/` e não são repetidas. O log da 2ª execução mostra `cache_misses: 0` quando tudo já estava em cache. Só respostas 2xx e 404 vão para o cache; erros transitórios (403 de rate limit, 5xx) são refeitos.

**Rate limit e erros.** `X-RateLimit-Remaining/Reset` e `Retry-After` são lidos; com a cota zerada (resposta 200, 403 ou 429) o log mostra `aguardando até <epoch>` e a requisição é repetida. 5xx e erros de rede usam backoff de 1, 2, 4, 8 s (até 5 tentativas).

## Seleção de repositórios e funil (Issue #4)

`pipeline/selection.py` busca candidatos na Search API **fatiada** por faixas de estrelas (e, opcionalmente, linguagem), subdividindo ao meio qualquer fatia com mais de 1.000 resultados. Depois aplica os filtros do mais barato ao mais caro: `actions/workflows.total_count > 0` → ≥ 5 releases na janela → ≥ 50 runs válidos (default branch, `event=push`, buscados mês a mês). A contagem de runs válidos **para ao atingir o mínimo** (`min_runs_validos`), então `n_runs_valid_window` no funil é exato abaixo do mínimo e um piso acima dele (a contagem completa está em `resultados.csv`). A avaliação dos candidatos (ordem determinística por `full_name`, lacuna L17) **para ao selecionar `amostra_alvo` repositórios**; o `funil.md` informa quantos candidatos ficaram sem avaliar. Para quem passa, coleta contribuidores (`per_page=1&anon=true`, última página do `Link`) e idade.

Saídas em `caminhos.saidas`: `funil.csv` (um registro por repositório, com etapa e motivo de descarte) e `funil.md` (resumo gerado dos mesmos registros).

Decisões do grupo (lacunas do enunciado, configuráveis em `selecao:`): critério de "popular" e faixas de estrelas (L03), run válido (L04), releases contadas (L05), idade = `created_at` até `janela.fim` (L16). A seleção só roda com a janela definida e com `pipeline.http_client` (Issue #11) disponível.

## Coleta de releases (Issue #7)

`pipeline/collect_releases.py` coleta **todas** as releases de cada repositório, **sem corte de data**: as anteriores à janela são necessárias como "release anterior" da 1ª release da janela (`compare/{anterior}...{R}`, RQ02). De cada release guarda `tag_name`, `draft`, `prerelease`, `published_at` e, para uso adiante, `id`, `created_at`, `target_commitish` e `html_url`. A lista sai ordenada por `published_at` (drafts no fim).

- **Cache:** um JSON por repositório em `<cache>/releases/<owner>__<repo>.json` (escrita atômica). Se o arquivo existe, nenhuma chamada é feita. Como não há corte de data, ele continua válido se a janela mudar, **desde que** a coleta tenha rodado depois do fim da janela; se rodou antes, apague o arquivo para trazer as releases publicadas depois.
- **Sem teto:** diferente da Search API e de `actions/runs`, `/releases` não para nas 1.000 mais recentes (conferido em `renovatebot/renovate`, com 122 páginas), então a paginação vai até o fim. Um cache antigo marcado com `"truncado": true` é descartado e a coleta é refeita.
- **Release anterior:** `pares_com_anterior(releases, inicio, fim)` devolve `(anterior, R)` para cada release de deploy da janela (L05); `anterior` pode estar fora da janela e é `None` se R for a primeira da história. `incluir_prerelease=True` gera a variante com pré-releases (RQ07).
- **Branch (L06):** releases não são filtradas pelo default branch (`target_commitish` fica no JSON para análise); registrado como ameaça de construto.

## Execução integrada (Issue #6)

`pipeline/execucao.py` encadeia **seleção → validação da amostra → coleta → métricas → resultados → funil → log** no mesmo comando. Ele só orquestra: seleção/funil vêm da #4; coleta, métricas, `http_client` e cache vêm das Issues #7–#14 e são injetados (`Etapas`, `client`).

- **Amostra:** só repositórios `selecionado` no funil, sem duplicatas (`full_name` sem diferenciar caixa). `selecao.amostra_alvo` (100) não relaxa filtros nem completa a amostra: se passarem menos, o log avisa; se passarem mais, mantém os primeiros na ordem da seleção (critério de corte **não definido**, L17).
- **Erros:** falha em um repositório é registrada (`status=erro` em `resultados.csv` e no log) e a execução segue (política não definida no enunciado).
- **Cache:** se o cliente expõe `estatisticas()`, o log registra o consumo da execução (diferença antes/depois) — útil para comparar a 1ª e a 2ª execução.
- **Saídas** em `caminhos.saidas`: `funil.csv`/`funil.md`, `resultados.csv`, `execucao.log` (append; cada execução tem início e fim datados; o token nunca é logado).
- **Etapas (`pipeline/etapas.py`):** por repositório selecionado, `coletar_repositorio` obtém releases → pares com a release anterior → `compare` paginado → runs mensais (e tags, se `coleta.tags: true`), e `calcular_metricas` produz uma linha de `resultados.csv` (metadados, DF, lead time (a)/(b), CFR (a), recuperação, contadores de exclusão/censura e classificação DORA de referência C1).

## Coleta de tags (Issue #8)

`pipeline/collect_tags.py` coleta **todas** as tags de cada repositório, sem corte de data. Elas são a unidade de deploy da combinação C3 da RQ07. A tag anterior à janela é a base do `compare` da 1ª tag da janela. Tags não trazem data (E§4): a data vem do commit apontado, em `GET /repos/{owner}/{repo}/git/commits/{sha}`.

- **Data da tag:** `commit.author.date`, a mesma regra de "data de um commit" de E§3. `committer.date` também fica no JSON. Cada tag guarda `name`, `sha`, `data`, `author_date` e `committer_date`. A lista sai ordenada por data (desempate por `committer_date` e depois por nome); tags sem data ficam no fim.
- **Custo:** 1 chamada por página de tags + 1 por commit **distinto** (várias tags no mesmo commit custam uma chamada). Como em releases, `/tags` não tem teto de 1.000: a paginação vai até o fim.
- **Commit não encontrado (404/422):** a tag fica com `data = null`, é contada em `sem_data` no JSON, gera aviso no log e fica fora dos pares (política não definida no enunciado).
- **Cache:** um JSON por repositório em `<cache>/tags/<owner>__<repo>.json` (escrita atômica, mesmo formato da Issue #7). Se o arquivo existe, nenhuma chamada é feita.
- **Tag anterior:** `pares_com_anterior(tags, inicio, fim)` devolve `(anterior, T)` para cada tag da janela. `anterior` pode estar fora da janela e é `None` se T for a primeira da história.
- **Escopo:** entram todas as tags, inclusive as que têm release e as que apontam para fora do default branch (como nas releases, L06). Casar tag ↔ release fica para o cálculo das variantes (Issue #21). Ameaça à validade: uma tag criada tarde sobre um commit antigo recebe a data desse commit.

## Coleta de commits entre releases (Issue #9)

`pipeline/collect_commits.py` obtém os commits incluídos em cada release R da janela com `GET /repos/{owner}/{repo}/compare/{anterior}...{R}` (RQ02). A entrada são os pares `(anterior, R)` de `collect_releases.pares_com_anterior`. De cada commit guarda `sha`, `author_date` (`commit.author.date`, E§3), `committer_date`, `message` e `n_parents` (merges, L07).

- **Paginação:** sem paginação o `compare` devolve no máximo 250 commits (E§4). A coleta sempre pagina com `per_page=100`/`page` até reunir `total_commits` (lido da 1ª página) ou até vir uma página vazia. Se a API parar antes do total, a release fica com `"truncado": true` e gera aviso no log.
- **404 (E§11):** tag apagada ou reescrita. A release recebe `status = "404"`, sem commits, gera aviso no log, fica fora do lead time e é contada em `n_releases_ignored_404`. Outros erros HTTP interrompem a coleta do repositório.
- **Compare divergente (L06):** cada release guarda `status_compare` (`ahead`, `behind`, `diverged`, `identical`). `diverged` significa que a release anterior está em outra linha de versão, como um backport publicado entre duas releases da linha principal. Nesse caso o `compare` traz commits a partir do merge-base, que podem ser muito antigos e inflar o lead time. Exemplo real: `cpython v3.11.7...v3.12.1` traz 5.062 commits. Esses casos geram aviso no log, são contados em `n_divergentes` e continuam no cálculo; ficam registrados como ameaça de construto.
- **Sem release anterior:** a primeira release da história recebe `status = "sem_anterior"` (contada em `n_sem_anterior`) e não chama a API.
- **Release sem commits novos:** `status = "ok"` com `commits = []`. A regra de lead time para esse caso (L07) está em [Lead time](#lead-time-issue-10).
- **Cache:** um JSON por repositório em `<cache>/commits/<owner>__<repo>.json`, com um mapa `"base...head" → comparação` (os 404 também ficam nele). Só os pares ausentes vão à API, então mudar a janela reaproveita o que já foi coletado.

## Lead time (Issue #10)

`metricas/lead_time.py` calcula as duas variantes obrigatórias da RQ02 (E§5) a partir das `releases` devolvidas por `collect_commits`. A unidade é **horas** e a data do commit é sempre `commit.author.date` (E§3), nunca `committer.date`.

- **(a) Por release** (`lead_time_release`): `published_at(R) − author_date(commit mais antigo de R)`. O valor do repositório é a mediana entre as releases.
- **(b) Por commit** (`lead_time_commit`): `published_at(R) − author_date(c)` para cada commit c. O valor do repositório é a mediana de **todos** os commits de **todas** as releases, não a mediana das medianas.
- **Exemplo do professor:** `v1.1` publicada em 15/03 com commits de 02/03, 10/03 e 14/03 dá (a) = 13 dias (312 h) e (b) = {13, 5, 1} dias.

`resumo_lead_time` devolve `lt_release_median_h`, `lt_commit_median_h` e as contagens do que ficou fora do cálculo:

| Caso | Tratamento | Contagem |
|---|---|---|
| `compare` com 404 (E§11) | Release ignorada | `n_releases_ignored_404` |
| 1ª release da história, sem anterior (E§5) | Release ignorada | `n_sem_anterior` |
| Release sem commits novos (L07, decisão do grupo) | Release excluída | `n_sem_commits_novos` |
| Commit com data posterior à release (L07, decisão do grupo) | Commit excluído de (a) e (b), com aviso no log | `n_commits_negativos` |
| Commit sem `author_date` / release sem `published_at` | Ignorado | — |
| Commit de merge (L07) | Entra no cálculo como qualquer commit (`n_parents` fica no cache de commits) | — |

Se nenhuma release for avaliável (por exemplo, repo com uma única release), as medianas ficam `None`.

## CFR (a) e tempo de recuperação

`metricas/cfr.py`: `cfr = falhas / (falhas + sucessos)` sobre runs `event=push` (filtro defensivo `so_push`); `classify_conclusion` trata os 9 valores de `conclusion`. `metricas/recovery.py`: por workflow, em ordem de `run_started_at`, o episódio começa na **primeira** falha após um sucesso (falhas seguidas fazem parte dele) e termina no próximo sucesso (`updated_at`); falhas sem sucesso até o fim da janela são **censuradas**: `episodios()` devolve `tempos_h`, `n_episodios` e `n_censurados` (em `resultados.csv`: `n_episodios_censurados` e `prop_episodios_censurados`). Uma falha antes de qualquer sucesso também abre episódio (decisão do grupo).

## Heurística de release corretiva e CFR (b) (Issue #27)

`metricas/heuristica.py` marca uma release S como **corretiva** comparando-a com a release de deploy anterior (a mesma `base` do `compare`) e olhando os commits entre as duas. A versão da regra sai em `heuristic_version`. A validação contra a amostra-ouro e o refino ficam na #28 (versões candidatas em `VERSOES`, ver [Avaliação da heurística](#avaliação-da-heurística-issue-28)). A versão **não tem padrão**: `avaliar`, `classificar_releases` e `resumo_cfr_entrega` exigem `versao` explícita (desconhecida → `ValueError`), e a v9, que lê as release notes (`body`), levanta `DadosAusentesError` se elas não vierem nos itens, em vez de rodar outra regra com o rótulo v9. `HEURISTIC_VERSION` (v1) é só a regra definida antes dos dados.

**Regra v1** (exemplo do professor, E§5: "só muda o patch **e** contém o commit fix"):

| Situação | S é corretiva se |
|---|---|
| Tags SemVer comparáveis | só o *patch* subiu **e** algum commit cita `revert`, `hotfix` ou `fix` |
| Tags não comparáveis (fora de SemVer ou prefixos diferentes) | algum commit cita `revert`, `hotfix` ou `fix` |
| Sem release anterior (1ª da história) | nunca |

- **SemVer:** `MAJOR.MINOR.PATCH[-pre][+build]` com números sem zero à esquerda e prefixo opcional (`v`, `release-`, `pkg@`, `@scope/pkg@`, `pkg-v`). O `v` isolado ou logo após `-`, `_`, `@` ou `/` é só marca de versão (`v2.3.0 → 2.3.1` é comparável). Prefixos diferentes (`a@1.0.0 → b@1.0.1`) indicam pacotes diferentes num monorepo e não são comparáveis. `1.2`, `1.2.3.4`, `release-2020-01` e `2026.10.01` não são SemVer.
- **Só o patch:** mesmo major e minor, patch maior e S sem pré-release. `2.3.0 → 2.3.1-rc1` e `2.3.1-rc1 → 2.3.1` (a final de um RC) não contam.
- **Palavra-chave:** palavra inteira, sem diferenciar caixa, em qualquer parte da mensagem (assunto e corpo). Casa `fix:`, `fix(ui):`, `Revert "..."`, `hotfix`, `bug-fix`, `user/fix-crash`. Não casa `prefix`, `fixture`, `fixes`, `fixed` nem `bugfix`.

`metricas/cfr_entrega.py` calcula o CFR (b) a partir das releases de deploy já marcadas:

- R **falhou** se **qualquer** release de deploy S com `R < S ≤ R + 7 dias` for corretiva (L08). Não precisa ser a próxima, e exatamente 7 d 0 h depois ainda conta.
- R com `published_at + 7 dias > fim da janela` é **censurada** e fica fora do denominador.
- `cfr_b = falhas / avaliadas`. É `None` (indefinido) sem avaliadas ou com **menos de 2 releases de deploy na janela**. Decisão do grupo: a fonte diz "repo com 1 release → indefinido"; contamos na janela porque só as releases da janela podem ser S. Os contadores continuam preenchidos, e `n_releases_avaliadas_cfr_b + n_releases_censuradas_cfr_b = n_releases_janela` (invariante do `data_quality`).

Para calcular por repositório (#21), uma chamada com a saída de `collect_commits` e a janela de `etapas._janela`:

```python
from metricas.cfr_entrega import resumo_cfr_entrega
resumo_cfr_entrega(dados["commits"]["releases"], _janela(inicio, fim))
# {"cfr_b", "n_releases_avaliadas_cfr_b", "n_releases_censuradas_cfr_b", "n_releases_janela",
#  "n_releases_falha_cfr_b", "n_releases_mensagens_incompletas_cfr_b", "heuristic_version"}
```

`n_releases_mensagens_incompletas_cfr_b` é diagnóstico, não entra na invariante. Ele conta as releases da janela cujo `compare` deu 404 ou veio truncado: nelas a palavra-chave pode ter faltado por falta de dado, o que puxa o CFR (b) para baixo. A variante com pré-releases (C2) usa a mesma chamada sobre os pares de `pares_com_anterior(..., incluir_prerelease=True)`.

**Limitações conhecidas** (insumo para a #28 e a #30):
- Backport publicado depois da linha nova (`0.11.0 → 0.10.2`) não é "só patch" em relação à anterior por data.
- CalVer sem zero à esquerda (`2026.10.1`) é lido como SemVer.
- A palavra inteira deixa de fora `fixes`, `fixed` e `bugfix`.
- A saída por release (`classificar_releases`) não tem `release_id`, que o `collect_commits` não guarda. A #28 junta com os rótulos por `(full_name, tag_name)`.

**Independência dos rótulos (E§6):** a heurística não foi calibrada nos rótulos e não é rodada sobre a amostra-ouro antes de os três arquivos `labels_*.csv` passarem no `validar_rotulos`.

## Avaliação da heurística (Issue #28)

`scripts/evaluate_heuristic.py` mede precisão, recall e F1 de cada versão da heurística contra o consenso da amostra-ouro, com `precision_recall_fscore_support` (E§6).

**Pré-requisitos:** os três `labels_<avaliador>.csv` completos e o `consenso.csv` gerado por `scripts.agreement`, sem `pendente`. Os commits de cada release sorteada vêm do cache de commits do pipeline (`cache/commits/`). O que faltar vai à API, o que exige `GITHUB_TOKEN`; sem token, só o cache é usado e uma comparação ausente gera erro.

```
python -m scripts.evaluate_heuristic --config config.yaml
```

- **Guarda de independência:** se algum dos três rótulos (avaliadores de `sorteio.json`) não passar no `validar_rotulos`, o comando sai com código 1 **antes** de aplicar a heurística na amostra-ouro. Ele mostra só o número de pendências por arquivo. Com consenso incompleto, sai com código 2.
- **Gera** em `data/amostra_ouro/`:
  - `heuristica_amostra.csv`: sinais e resultado de cada versão por release;
  - `avaliacao_heuristica.csv`: TP/FP/FN/TN, precisão, recall e F1 por versão;
  - `avaliacao_heuristica.md`: tabela versão → F1 para a Metodologia (#31).
- **Versões candidatas** (`metricas.heuristica.VERSOES`), combinando os dois sinais do enunciado. A palavra ampla aceita também `fixes`, `fixed`, `fixing`, `bugfix`, `reverted`… Em todas, tags não comparáveis usam só a palavra-chave e uma release sem anterior nunca é corretiva.

  | Versão | Regra |
  |---|---|
  | v1 | só patch **e** palavra estrita (definida antes dos dados) |
  | v2 | só patch **ou** palavra estrita |
  | v3 | só palavra estrita |
  | v4 | só patch |
  | v5 | só patch **e** palavra ampla |
  | v6 | só patch **ou** palavra ampla |
  | v7 | só palavra ampla |
  | v8 | commit de correção e nenhum de feature (olha o conteúdo dos commits) |
  | v9 | v8 **ou** release notes com correção e sem novidade (exige `body`; fora do dataset final) |

- **Escolha (regra do script):** a v1, definida antes de ver os dados, só se F1 ≥ 0,70; senão, a de maior F1 (empate → menor número). Como nenhuma versão chegou a 0,70, `escolhida` em `avaliacao_heuristica.csv` é só essa regra interna, **não** validação. Como as versões são comparadas na mesma amostra, sem conjunto de validação separado, o F1 da escolhida tende a ser otimista. O relatório traz todas as versões e o número de corretivas do consenso; isso entra em Ameaças à validade.
- **Status:** nenhuma versão atingiu F1 ≥ 0,70; a heurística é **não validada** e o CFR (b) é exploratório (v8 principal, v4 sensibilidade, v9 fora do dataset). Ver `docs/refino_heuristica.md`.
- **Depois da rodada:** quem calcula o CFR (b) (#21) passa a versão explicitamente; nenhuma versão está validada. Uma versão nova (v8+, desenhada a partir dos erros da #30) entra em `VERSOES` e vira coluna de `heuristica_amostra.csv`, o que exige atualizar o dicionário de dados (o `test_dicionario` cobra).

## Análise de erros da heurística (Issue #30, bônus)

Depois da rodada da #28, `scripts/analise_erros_heuristica.py` detalha os erros de uma versão (padrão: a escolhida em `avaliacao_heuristica.csv`). O resultado alimenta Ameaças à validade (construto) e ideias de novas versões (v8+).

```
python -m scripts.analise_erros_heuristica [--versao vN]
```

- **Lê** em `data/amostra_ouro/`: `heuristica_amostra.csv`, `avaliacao_heuristica.csv` e `consenso.csv`, que precisam existir; os links vêm de `amostra_ouro.csv`. Não lê os arquivos de rótulos. Se a matriz recalculada divergir de `avaliacao_heuristica.csv`, o comando para, porque os arquivos seriam de rodadas diferentes.
- **Gera:**
  - `erros_heuristica.csv`: um FP ou FN por linha, com `causa_automatica` e a coluna `causa_manual` para o grupo anotar lendo os commits (ex.: "fix em docs");
  - `erros_heuristica.md`: matriz de confusão, contagem por causa, comparação entre versões e lista de FP/FN com links. Na comparação, "corrige" conta as releases que uma versão acerta e a analisada erra, e "piora" o contrário. O relatório termina com um resumo para Ameaças à validade.
- **Anotações manuais:** ao rodar de novo, a `causa_manual` é mantida por `release_id`, mesmo trocando de versão. As anotações de releases que deixaram de ser erro saem do CSV, com aviso e contagem; o histórico fica no git.
- **Taxonomia automática** (uma causa por erro, na ordem abaixo). A "palavra" é o sinal que a própria versão usa: estrita em v1–v4, ampla em v5–v7 (`PALAVRA_DA_VERSAO`). v8 e v9 decidem por conteúdo (`VERSOES_DE_CONTEUDO`) e têm causa automática genérica, para anotar em `causa_manual`; o script recusa versões fora desses dois mapas.

  | Tipo | Causa | Quando |
  |---|---|---|
  | FP | `palavra_sem_semver` | tags não comparáveis e palavra-chave |
  | FP | `patch_e_palavra_sem_correcao` | patch e palavra, sem correção real (ex.: `fix` em docs ou CI) |
  | FP | `patch_sem_palavra` | patch bump sem bug (versões que aceitam só patch) |
  | FP | `palavra_sem_patch` | minor/major com palavra (versões OU / só palavra) |
  | FN | `sem_release_anterior` | 1ª release da história |
  | FN | `commits_indisponiveis` | `compare` 404 ou truncado, **e** a palavra mudaria a predição |
  | FN | `palavra_ampla_nao_estrita` | versões estritas: trocar pela palavra ampla (`fixes`, `fixed`…) **corrigiria** o erro |
  | FN | `palavra_sem_patch` | há palavra (estrita ou ampla), mas não é bump de patch (backport, final de RC, minor com correção) |
  | FN | `patch_sem_palavra` | correção num patch sem palavra-chave |
  | FN | `nao_semver_sem_palavra` | tags não comparáveis e sem palavra |
  | FN | `sem_sinal` | nem patch nem palavra |

  `commits_indisponiveis` e `palavra_ampla_nao_estrita` são **contrafactuais**: a regra da versão é reaplicada com o sinal alterado, e a causa só vale se o resultado mudar. A precedência e os contrafactuais foram conferidos só para v1–v7; v8 e v9 não passam por essa taxonomia.

## Testes e cobertura

```bash
pytest
pytest --cov=metricas --cov-report=term-missing --cov-fail-under=80
```

A cobertura mínima é de **80% do módulo `metricas`**. O CI (`.github/workflows/testes.yml`) roda esses testes a cada push.

## Commits devem citar a Issue (`#N`)

Commits sem referência a uma Issue não contam na avaliação. Ative o hook local uma vez após clonar:

```bash
git config core.hooksPath .githooks
```

Com ele, um commit sem `#N` é rejeitado:

```text
feat(pipeline): cria estrutura inicial (#3)   # aceito
ajustes                                       # rejeitado
```

O workflow `.github/workflows/commits.yml` aplica a mesma regra no GitHub, caso o hook não esteja ativo.

## Estrutura do projeto

```text
pipeline/              CLI (python -m pipeline), config, seleção, funil e orquestração (execucao.py)
metricas/              funções de cálculo das métricas DORA (módulo medido pela cobertura)
tests/                 testes automatizados (pytest)
scripts/               utilitários (validação de mensagem de commit)
.githooks/             hook commit-msg que exige #N
.github/workflows/     CI: testes.yml (pytest + cobertura) e commits.yml (#N)
artigo/                artigo (template SBC)
data/                  dados de entrada/intermediários
outputs/               saídas geradas pelo pipeline
config.yaml            configuração (sem segredos)
requirements.txt       dependências fixadas
```

## Amostra-ouro e planilhas de rotulagem (S02, Issue #22)

`scripts/sample_gold.py` sorteia 60 repositórios (semente 42) e 5 releases por repositório, iguais para os três avaliadores, e gera `data/amostra_ouro/labels_A.csv`, `labels_B.csv` e `labels_C.csv` com links das releases. Lê só o cache; não chama a API.

```
python -m scripts.sample_gold --config config.yaml
```

- **Lista:** `data/repos_final.csv` se existir (lista final congelada); senão `outputs/resultados.csv`. Troque com `--repos`.
- **Janela oficial do professor:** edite só `janela.inicio`/`janela.fim` no `config.yaml`, rode `python -m pipeline` (apague o cache de commits/runs se a janela mudou) e rode o comando acima de novo. O sorteio muda com a janela e com a lista; `sorteio.json` registra ambas.
- **Proteção:** se alguma planilha já tiver rótulos, o script aborta para não apagar o trabalho dos avaliadores; `--forcar` sobrescreve.
- **Preenchimento:** tipo do projeto e "releases = entregas reais" vão na primeira linha de cada repositório; "corretiva" em todas. Valores válidos em `data/amostra_ouro/LEIAME.md`.

## Concordância e consenso (S02, Issue #26)

Depois que os três avaliadores commitarem seus `labels_<nome>.csv`:

```
python -m scripts.agreement data/amostra_ouro/labels_marcos.csv \
    data/amostra_ouro/labels_arthur.csv data/amostra_ouro/labels_guilherme.csv
```

Gera em `data/amostra_ouro/`: `concordancia.csv` (kappa de Fleiss por dimensão, com interpretação de Landis & Koch) e `consenso.csv` (rótulo de consenso por item). Unanimidade e maioria 2-1 são automáticas; casos 1-1-1 ficam `pendente` (o comando sai com código 2) até a reunião, quando as decisões vão em `data/amostra_ouro/desempate.csv` (`dimensao,item_id,rotulo,justificativa`) e o comando é rodado de novo. Regras completas em `data/amostra_ouro/PROTOCOLO_CONSENSO.md`.

## Qualidade dos dados e invariantes (S02, Issue #29)

```
python -m scripts.data_quality --config config.yaml [--metricas data/metrics.csv] [--dicionario DICIONARIO_DE_DADOS.csv]
```

Gera `outputs/data_quality.md` e `outputs/data_quality.csv` com: vazios por coluna, duplicatas, datas (commits após a release, sem data), censurados, 404, dias de runs saturados e distribuição por linguagem. As **invariantes** (0 ≤ CFR ≤ 1, lead time ≥ 0, avaliadas + ignoradas/censuradas = releases da janela, colunas no dicionário, somas do funil e amostra final = dataset) saem `OK`, `FALHA` ou `N/A` (coluna/arquivo ainda inexistente, como as colunas do CFR (b) da #21 e o dicionário da #20). Qualquer `FALHA` faz o comando sair com código 1. Os nomes das colunas do CFR (b) esperados estão nas constantes `COL_*` de `scripts/data_quality.py`.
