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

- **Cache:** um JSON por repositório em `<cache>/releases/<owner>__<repo>.json` (escrita atômica). Se o arquivo existe, nenhuma chamada é feita. Como não há corte de data, ele continua válido se a janela mudar.
- **Teto da API:** o endpoint de releases só pagina até as 1.000 mais recentes. Acima disso a coleta para, marca `"truncado": true` no JSON e avisa no log (as mais antigas ficam de fora).
- **Release anterior:** `pares_com_anterior(releases, inicio, fim)` devolve `(anterior, R)` para cada release de deploy da janela (L05); `anterior` pode estar fora da janela e é `None` se R for a primeira da história. `incluir_prerelease=True` gera a variante com pré-releases (RQ07).
- **Branch (L06):** releases não são filtradas pelo default branch (`target_commitish` fica no JSON para análise); registrado como ameaça de construto.

## Execução integrada (Issue #6)

`pipeline/execucao.py` encadeia **seleção → validação da amostra → coleta → métricas → resultados → funil → log** no mesmo comando. Ele só orquestra: seleção/funil vêm da #4; coleta, métricas, `http_client` e cache vêm das Issues #7–#14 e são injetados (`Etapas`, `client`).

- **Amostra:** só repositórios `selecionado` no funil, sem duplicatas (`full_name` sem diferenciar caixa). `selecao.amostra_alvo` (100) não relaxa filtros nem completa a amostra: se passarem menos, o log avisa; se passarem mais, mantém os primeiros na ordem da seleção (critério de corte **não definido**, L17).
- **Erros:** falha em um repositório é registrada (`status=erro` em `resultados.csv` e no log) e a execução segue (política não definida no enunciado).
- **Cache:** se o cliente expõe `estatisticas()`, o log registra o consumo da execução (diferença antes/depois) — útil para comparar a 1ª e a 2ª execução.
- **Saídas** em `caminhos.saidas`: `funil.csv`/`funil.md`, `resultados.csv`, `execucao.log` (append; cada execução tem início e fim datados; o token nunca é logado).
- **Pendente:** `pipeline.cli.criar_etapas()` devolve `None` até as Issues #7–#10, #13 e #14 entregarem as funções (contrato em `pipeline/execucao.py`); enquanto isso o comando faz só seleção e funil.

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
