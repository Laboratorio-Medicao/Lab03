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

Sem a variável definida, o comando falha com uma mensagem explicando o que fazer.

## Configuração (`config.yaml`)

| Chave | Descrição |
|---|---|
| `github.token_env` | Nome da variável de ambiente que guarda o token (padrão `GITHUB_TOKEN`). |
| `janela.inicio` / `janela.fim` | Janela de observação de 12 meses (`AAAA-MM-DD`, UTC). **Ainda não definida pelo professor**; enquanto estiver `null` o pipeline apenas avisa. |
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
pipeline/              CLI (python -m pipeline) e leitura do config
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
