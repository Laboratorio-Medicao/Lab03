# Ponto de retomada da Sprint 2 (15/10, 17h)

Estado: código, testes (742 passam), dicionário, README, `config.yaml` e artigo sincronizados com a v12.
Nada foi commitado.

## Pendências (nesta ordem)
1. **Completar o cache de `akto-api-security/akto`** (falta um `compare`; falhou por colisão de escrita
   entre processos paralelos que compartilhavam `cache/*.tmp`). Rodar **um processo só**:
   `GITHUB_TOKEN=... python -m scripts.recoletar_cache --repos <csv com akto>` (apague antes qualquer
   `cache/*.json` corrompido; o cache HTTP bruto é `cache/<sha256>.json`).
2. **`1bananachicken/MaaNTE`** (repositório removido): o JSON de releases veio do cache antigo, sem `body`;
   a v12 exige o `body`. Recuperar as notas do cache da amostra-ouro (quem rotulou tem) ou documentar a
   exclusão desse repositório do CFR (b).
3. Rodar `python -m scripts.compute_metrics --versao v12` (saída em `data/metrics.csv`; hoje 298/300 OK,
   2 linhas vazias: akto e MaaNTE) e `python -m scripts.data_quality --metricas data/metrics.csv`.
4. Investigar a única falha do data_quality: `agentclientprotocol/agent-client-protocol` (73 != 74 na
   invariante avaliadas + ignoradas = janela).
5. Rodar `pytest`, commitar com `#N` (inclui `experimental/`, `data/validacao_independente/`, scripts novos).
6. **Revogar os tokens do GitHub** colados na conversa.

## Cache
`~/Developer/Lab03/cache` (commits/ e tags/) é compartilhado; `cache/releases/` da cópia de trabalho
tem as 300 releases (com `body`). `cache/commits` e `cache/tags` são links para o cache acima.

## Atualização (18h45)
- `n_sem_commits_novos` agora conta também releases só com commits posteriores à release (fecha a
  invariante avaliadas+ignoradas=janela). Regra em `metricas/lead_time.py`; `agentclientprotocol/
  agent-client-protocol` corrigido à mão (12 → 13) em `resultados.csv`, `repos_final.csv` e `metrics.csv`
  porque o cache de runs não está nesta máquina para regenerar. `data_quality`: 71 verificações, 0 falha.
- MaaNTE: não há `body` em nenhum cache local; fica sem CFR (b) (colunas extras vazias) e documentado.
- akto: coleta em andamento (`scripts.recoletar_cache`); depois rodar `compute_metrics --versao v12`.

## Decisão (15/10, 19h): 300/300 em v12
- `1bananachicken/MaaNTE` (repositório removido, 404 nas notas): para o CFR (b) com a v12 as notas são
  tratadas como **vazias** (`body = ""`), a mesma convenção da avaliação (`coletar_notas`: 404/410 → vazio).
  Limitação a declarar no artigo: a v12 roda nesse repositório sem as release notes (só mensagens de commit
  e SemVer); o cache de releases é local (`cache/releases/1bananachicken__maante.json`, campo
  `body_vazio_por_repo_removido`).
- `akto`: coleta incremental em andamento (~1.328 releases, ~2 compares/min); o script de fechamento
  (`scratchpad/fim.sh`) roda `compute_metrics --versao v12`, `data_quality` e `pytest` quando ela acabar.
