# Lab03 — Mineração de Métricas DORA

Pipeline reprodutível que calcula as métricas DORA (deployment frequency, lead time, change failure rate e tempo de recuperação) a partir de dados públicos do GitHub (releases, commits e GitHub Actions).

> **Estado atual (Sprint S01):** esqueleto do projeto, configuração, comando único, CI e hook de commit. As etapas de seleção, coleta e cálculo entram nas demais Issues da S01 e serão encadeadas no mesmo comando.

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

## Seleção de repositórios e funil (Issue #4)

`pipeline/selection.py` busca candidatos na Search API **fatiada** por faixas de estrelas (e, opcionalmente, linguagem), subdividindo ao meio qualquer fatia com mais de 1.000 resultados. Depois aplica os filtros do mais barato ao mais caro: `actions/workflows.total_count > 0` → ≥ 5 releases na janela → ≥ 50 runs válidos (default branch, `event=push`, buscados mês a mês). Para quem passa, coleta contribuidores (`per_page=1&anon=true`, última página do `Link`) e idade.

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
- **Pendente:** `pipeline.cli.criar_etapas()` devolve `None` até as Issues #7–#10, #13 e #14 entregarem as funções (contrato em `pipeline/execucao.py`); enquanto isso o comando faz só seleção e funil.

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
