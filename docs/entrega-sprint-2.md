# Entrega da Sprint 2: Definition of Done (FV §19.2) contra o repositório

> 15/10/2026. Fontes: `enunciado/fonte_vdd.md` (§9.9, §9.12, §9.13, §19.2) e
> `docs/auditoria-sprint-2-independente.md`. Ponto de retomada: `docs/retomada-s02.md`.

| # | Critério (§19.2) | Estado | Evidência |
|---|---|---|---|
| 1 | ≥ 300 repositórios após filtros; funil final | **Atendido** | `outputs/repos_final.csv` (300), `outputs/funil.csv` (2677 → 300); 0 repositórios com < 5 releases ou < 50 runs |
| 2 | Métricas e variantes; censura e 404 contados | **Atendido, com 1 exceção** | `data/metrics.csv`: 299/300 com CFR (b) em v12; `akto-api-security/akto` sem CFR (b) (1.328 `compare` por coletar). Censura: 176/9.062 episódios; 6 releases em 404 |
| 3 | CSV + dicionário completo, com verificação automática | **Atendido** | `DICIONARIO_DE_DADOS.{md,csv}`; `tests/test_dicionario.py` |
| 4 | 60 repositórios, semente fixa, mesmas 5 releases | **Atendido** | `scripts/sample_gold.py` (`SEED=42`); `sorteio.json` com sha256 |
| 5 | 3 arquivos de rótulos independentes, commitados pelos autores | **Atendido nos arquivos; independência não demonstrável pelo Git** | `labels_{GuilhermeVieira05,marcosffp,ALuiz19}.csv`; ressalva descrita no artigo |
| 6 | Fleiss nas 3 dimensões, com interpretação | **Atendido** | `concordancia.csv`: tipo 0,743 (substancial), entrega 0,352 (razoável), corretiva 0,273 (razoável) |
| 7 | Consenso + protocolo de desempate versionado | **Atendido** | `PROTOCOLO_CONSENSO.md`, `consenso.csv` (420 itens, 0 pendentes) |
| 8 | P/R/F1; se < 0,70, refinar e documentar versões | **Atendido (F1 < 0,70, com histórico)** | v1–v12 documentadas; v12: F1 0,722 no desenvolvimento e **0,689 (IC95% 0,563–0,790)** em amostra independente (40 repos, 200 releases). Professor aceitou o CFR (b) como exploratório |
| 9 | Metodologia completa no artigo | **Atendido** | `artigo/metodologia.tex` com funil, janela oficial, definições, tabela v1–v12 e validação independente |
| 10 | Testes/CI verdes; cobertura ≥ 80% | **Atendido localmente** | 742 testes; `metricas/` 99%. CI no GitHub (Python 3.12): conferir a aba Actions |
| 11 | Issues, `#N`, board, individual por integrante | **Parcial** | Commits com `#N` e autoria por integrante verificados; quadro e Issues não são verificáveis sem a API |
| 12 | Revisão pelos três | **Pendente (humano)** | Revisão cruzada do artigo |

## Erros proibidos (§9.12)
Nenhum identificado: rótulos individuais preservados; CFR (a) e CFR (b) em colunas separadas; censurados
mantidos; versões da heurística registradas; kappa reportado (não só % de concordância).

## Exceções que o artigo deve declarar
1. **`akto-api-security/akto`:** sem `cfr_b`, `cfr_b_class` e `dora_c2`/variantes (limite de coleta).
2. **`1bananachicken/MaaNTE`:** repositório removido; v12 rodou com notas vazias (convenção da avaliação).
3. **Heurística abaixo de 0,70** em amostra independente; CFR (b) exploratório.
4. **Classificação geral parcial** em 23 repositórios (sem episódio de recuperação): `n_metricas_dora` < 4.
5. **Amostra** = primeiros 300 em ordem alfabética (ameaça externa já descrita).

## Mudanças desta rodada
v12 como versão final no dataset; correção do corte de DF (12 releases = Medium na janela de 366 dias);
classificação geral parcial com sinalização; `n_compare_divergentes`/`n_compare_truncados`;
`n_sem_commits_novos` passa a incluir releases só com commits posteriores (fecha a invariante do
`data_quality`: 71 verificações, 0 falha); `scripts/recoletar_cache.py`; validação independente e
rotulagem assistida registradas.
