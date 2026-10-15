# Qualidade dos dados

Origem: `data/metrics.csv` · 300 repositórios. Gerado por `python -m scripts.data_quality`.

Invariantes: **9 OK**, **0 FALHA**, 1 não verificáveis (coluna ou arquivo ausente).

## Invariantes

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| 0 ≤ CFR (a) ≤ 1 | OK | 0 | 300 itens verificados |
| 0 ≤ CFR (b) ≤ 1 | OK | 0 | 298 itens verificados |
| lead time ≥ 0 (lt_release_median_h) | OK | 0 | 300 itens verificados |
| lead time ≥ 0 (lt_commit_median_h) | OK | 0 | 300 itens verificados |
| releases avaliadas + ignoradas = releases da janela (lead time) | OK | 0 | 300 itens verificados |
| releases avaliadas + censuradas = releases da janela (CFR b) | OK | 0 | 299 itens verificados |
| toda coluna do CSV está no dicionário de dados | N/A |  | coluna ou arquivo necessário ausente |
| funil: entram − saem = restam em cada etapa | OK | 0 | 4 itens verificados |
| funil: selecionados + descartados = candidatos avaliados | OK | 0 | 2677 itens verificados |
| funil: amostra final = repositórios do dataset | OK | 0 | 300 itens verificados |

## Duplicatas

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| full_name repetido (sem diferenciar caixa) | OK | 0 | 300 únicos |

## Valores vazios

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| language | ALERTA | 2 | 0.7% das linhas vazias |
| rec_median_h | ALERTA | 23 | 7.7% das linhas vazias |
| prop_episodios_censurados | ALERTA | 17 | 5.7% das linhas vazias |
| rec_class | ALERTA | 23 | 7.7% das linhas vazias |
| dora_geral | ALERTA | 23 | 7.7% das linhas vazias |
| cfr_b | ALERTA | 2 | 0.7% das linhas vazias |
| cfr_b_class | ALERTA | 2 | 0.7% das linhas vazias |
| n_releases_avaliadas_cfr_b | ALERTA | 1 | 0.3% das linhas vazias |
| n_releases_censuradas_cfr_b | ALERTA | 1 | 0.3% das linhas vazias |
| n_releases_janela | ALERTA | 1 | 0.3% das linhas vazias |
| n_releases_falha_cfr_b | ALERTA | 1 | 0.3% das linhas vazias |
| n_releases_mensagens_incompletas_cfr_b | ALERTA | 1 | 0.3% das linhas vazias |
| heuristic_version | ALERTA | 1 | 0.3% das linhas vazias |
| n_releases_deploy_c2 | ALERTA | 1 | 0.3% das linhas vazias |
| df_c2 | ALERTA | 1 | 0.3% das linhas vazias |
| df_c2_class | ALERTA | 1 | 0.3% das linhas vazias |
| n_tags_janela | ALERTA | 1 | 0.3% das linhas vazias |
| df_c3 | ALERTA | 1 | 0.3% das linhas vazias |
| df_c3_class | ALERTA | 1 | 0.3% das linhas vazias |
| n_compare_divergentes | ALERTA | 1 | 0.3% das linhas vazias |
| n_compare_truncados | ALERTA | 1 | 0.3% das linhas vazias |
| dora_c1 | ALERTA | 1 | 0.3% das linhas vazias |
| dora_c2 | ALERTA | 1 | 0.3% das linhas vazias |
| dora_c3 | ALERTA | 1 | 0.3% das linhas vazias |
| n_metricas_dora_c1 | ALERTA | 1 | 0.3% das linhas vazias |
| n_metricas_dora_c2 | ALERTA | 1 | 0.3% das linhas vazias |
| n_metricas_dora_c3 | ALERTA | 1 | 0.3% das linhas vazias |

## Datas

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| commits com data posterior à release (excluídos) | INFO | 381 | 32 de 300 repositórios afetados |
| commits sem author_date ou com data ilegível | INFO | 0 | de 346044 commits no cache |
| commits com author_date depois do fim da janela (2026-10-02) | INFO | 0 |  |

## Censura

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| episódios de falha censurados (RQ04) | INFO | 176 | 176 de 9062 episódios; 105 de 300 repositórios com ao menos um |
| releases censuradas no CFR (b) (últimos 7 dias) | INFO | 397 |  |

## Comparações com 404

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| releases ignoradas por 404 no compare | INFO | 6 | 5 de 300 repositórios afetados |

## Cobertura e exclusões

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| releases sem anterior (1ª da história) | INFO | 93 | 93 de 300 repositórios afetados |
| releases sem commits novos | INFO | 1686 | 51 de 300 repositórios afetados |
| dias de runs saturados (teto de 1.000 da API) | INFO | 0 | 0 de 300 repositórios afetados |

## Distribuição por linguagem

| Verificação | Status | Valor | Detalhe |
|---|---|---:|---|
| TypeScript | INFO | 67 | 22.3% |
| Python | INFO | 54 | 18.0% |
| Go | INFO | 41 | 13.7% |
| Rust | INFO | 30 | 10.0% |
| C++ | INFO | 21 | 7.0% |
| JavaScript | INFO | 18 | 6.0% |
| Java | INFO | 12 | 4.0% |
| Kotlin | INFO | 9 | 3.0% |
| C | INFO | 8 | 2.7% |
| C# | INFO | 7 | 2.3% |
| Swift | INFO | 6 | 2.0% |
| HTML | INFO | 4 | 1.3% |
| PHP | INFO | 4 | 1.3% |
| Scala | INFO | 4 | 1.3% |
| Shell | INFO | 3 | 1.0% |
| (sem linguagem) | INFO | 2 | 0.7% |
| Elixir | INFO | 2 | 0.7% |
| Ruby | INFO | 2 | 0.7% |
| Dart | INFO | 1 | 0.3% |
| Nix | INFO | 1 | 0.3% |
| PowerShell | INFO | 1 | 0.3% |
| SQF | INFO | 1 | 0.3% |
| Vala | INFO | 1 | 0.3% |
| Vue | INFO | 1 | 0.3% |
