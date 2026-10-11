# Rotulagem da amostra-ouro

Cada avaliador (GuilhermeVieira05, marcosffp, ALuiz19) preenche **somente o seu arquivo** `labels_<avaliador>.csv`,
sem consultar os demais e sem ver a saída da heurística de release corretiva. As releases são as
mesmas nos três arquivos.

## Colunas a preencher

| Coluna | Onde preencher | Valores válidos |
|---|---|---|
| `tipo_projeto` | primeira linha de cada repositório | `biblioteca_framework` · `aplicacao_servico` · `ferramenta_cli` · `outro` |
| `releases_sao_entregas_reais` | primeira linha de cada repositório | `sim` · `nao` · `incerto` |
| `corretiva` | todas as linhas (uma por release) | `sim` · `nao` |
| `observacoes` | opcional | texto livre |

- `release_url`: página da release (leia as *release notes*).
- `compare_url`: lista de commits entre a release anterior e esta (vazia na primeira release da história).
- Não altere nem reordene as demais colunas: a consolidação do kappa casa as linhas por `release_id`.
- Commite o arquivo preenchido com `#N` da sua Issue de rotulagem.

Sorteio: semente `42`, 60 repositórios, 5 releases por repositório
(ver `sorteio.json`). Gerado por `python -m scripts.sample_gold`.
