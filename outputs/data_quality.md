# Qualidade dos dados

Origem: `outputs/resultados.csv` · 100 repositórios. Gerado por `python -m scripts.data_quality`.

Invariantes: **7 OK**, **0 FALHA**, 3 não verificáveis (coluna ou arquivo ausente).

## Invariantes

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| 0 ≤ CFR (a) ≤ 1 | OK | 0 | 100 itens verificados |
| 0 ≤ CFR (b) ≤ 1 | N/A |  | coluna ou arquivo necessário ausente |
| lead time ≥ 0 (lt_release_median_h) | OK | 0 | 100 itens verificados |
| lead time ≥ 0 (lt_commit_median_h) | OK | 0 | 100 itens verificados |
| releases avaliadas + ignoradas = releases da janela (lead time) | OK | 0 | 100 itens verificados |
| releases avaliadas + censuradas = releases da janela (CFR b) | N/A |  | coluna ou arquivo necessário ausente |
| toda coluna do CSV está no dicionário de dados | N/A |  | coluna ou arquivo necessário ausente |
| funil: entram − saem = restam em cada etapa | OK | 0 | 4 itens verificados |
| funil: selecionados + descartados = candidatos avaliados | OK | 0 | 891 itens verificados |
| funil: amostra final = repositórios do dataset | OK | 0 | 100 itens verificados |

## Duplicatas

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| full_name repetido (sem diferenciar caixa) | OK | 0 | 100 únicos |

## Valores vazios

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| language | ALERTA | 2 | 2.0% das linhas vazias |
| rec_median_h | ALERTA | 4 | 4.0% das linhas vazias |
| prop_episodios_censurados | ALERTA | 4 | 4.0% das linhas vazias |
| rec_class | ALERTA | 4 | 4.0% das linhas vazias |
| dora_geral | ALERTA | 4 | 4.0% das linhas vazias |

## Datas

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| commits com data posterior à release (excluídos) | INFO | 135 | 12 de 100 repositórios afetados |
| commits sem author_date ou com data ilegível | INFO | 0 | de 140716 commits no cache |
| commits com author_date depois do fim da janela (2026-10-02) | INFO | 0 |  |

## Censura

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| episódios de falha censurados (RQ04) | INFO | 58 | 58 de 2838 episódios; 35 de 100 repositórios com ao menos um |

## Comparações com 404

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| releases ignoradas por 404 no compare | INFO | 2 | 2 de 100 repositórios afetados |

## Cobertura e exclusões

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| releases sem anterior (1ª da história) | INFO | 31 | 31 de 100 repositórios afetados |
| releases sem commits novos | INFO | 600 | 15 de 100 repositórios afetados |
| dias de runs saturados (teto de 1.000 da API) | INFO | 0 | 0 de 100 repositórios afetados |

## Distribuição por linguagem

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| Python | INFO | 17 | 17.0% |
| Rust | INFO | 16 | 16.0% |
| TypeScript | INFO | 15 | 15.0% |
| Go | INFO | 12 | 12.0% |
| C++ | INFO | 7 | 7.0% |
| JavaScript | INFO | 7 | 7.0% |
| C | INFO | 4 | 4.0% |
| Kotlin | INFO | 4 | 4.0% |
| C# | INFO | 3 | 3.0% |
| (sem linguagem) | INFO | 2 | 2.0% |
| PHP | INFO | 2 | 2.0% |
| Shell | INFO | 2 | 2.0% |
| Swift | INFO | 2 | 2.0% |
| Elixir | INFO | 1 | 1.0% |
| Java | INFO | 1 | 1.0% |
| Nix | INFO | 1 | 1.0% |
| PowerShell | INFO | 1 | 1.0% |
| SQF | INFO | 1 | 1.0% |
| Scala | INFO | 1 | 1.0% |
| Vue | INFO | 1 | 1.0% |
