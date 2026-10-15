# Auditoria independente da Sprint 2 (Lab03S02)

> Auditoria técnica, somente leitura, de 15/10. Substitui a auditoria interna anterior do grupo (`auditoria-sprint-2.md`, de 14/10), removida a pedido; ela permanece no histórico do Git.

## 1. Identificação da auditoria

| Item | Valor |
|---|---|
| Data | 2026-10-15 |
| Branch / commit | `main-2` / `966c088` (merge do PR #72; contém `b7ab06f`, v10) |
| Estado inicial | `git status` limpo; 59 commits; sem alterações preexistentes |
| Fontes oficiais | `enunciado/03 - Mineração de Métricas DORA.md` (E§1–E§12, lido integralmente); `enunciado/fonte_vdd.md` (FV; §0, §4, §5, §6, §9, §17.2, §18 T6–T12 lidos; demais seções fora do escopo da S02) |
| Documentos do grupo lidos | `README.md`, `DICIONARIO_DE_DADOS.{md,csv}`, `artigo/metodologia.tex`, `docs/*.md`, `data/amostra_ouro/*` |
| Precedência aplicada | enunciado > FV > decisões do grupo; código/documentação/CSV tratados como alegações a verificar |

**Comandos executados** (todos sem rede e sem escrita no repositório; `cache`, `.coverage` e venv ficaram no diretório temporário da sessão):

1. `git status`, `git log`, `git diff 4c4d583 b7ab06f`, `git log -S`/`-p` (varredura de tokens), contagens por autor.
2. `pytest -q -p no:cacheprovider --cov=metricas --cov-report=term-missing` num venv isolado (Python 3.14.5; `requirements.txt` instalado do PyPI): **681 passed**, cobertura de `metricas/` **99%**.
3. Recálculo independente (script próprio, métricas reimplementadas sem importar `metricas.*`; somente leitura do cache HTTP bruto de `~/Developer/Lab03/cache`): DF, LT (a)/(b), CFR (a), recuperação, episódios, censura, 404 e CFR (b) (sinalizadores da v8 vindos da heurística do projeto, contagem própria).
4. Verificações estatísticas e de consistência em `data/metrics.csv`, `outputs/*.csv`, `data/amostra_ouro/*.csv` (kappa de Fleiss por fórmula direta, consenso, P/R/F1, sorteio com `random.Random(42)`).
5. Casos mínimos com resposta conhecida executados nas funções reais (seção 5 deste relatório).

**Limitações.** (i) Sem API do GitHub: Issues, Projects, CI e a Search API não foram consultados. (ii) O cache bruto local cobre 99 dos 300 repositórios; para os outros 201 a conferência foi só de consistência interna. (iii) Testes rodaram em Python 3.14, o CI usa 3.12. (iv) A execução ponta a ponta do pipeline (rede/token) não foi feita. (v) Quando o comportamento humano (independência da rotulagem) não é observável por artefatos, foi classificado como **não comprovado**.

**Preservação.** Nenhum código, teste, CSV, cache, artigo ou dicionário foi alterado; `git status` permanece limpo exceto por este relatório.

## 2. Resumo executivo

- **Requisitos identificados:** 44 (obrigatórios, derivados e lacunas relevantes à S02).
- **Estados:** 28 conformes · 7 parcialmente conformes · 3 não conformes · 4 não comprovados · 2 pendentes de definição.
- **Achados:** 14 — críticos 0 · altos 3 · médios 9 · baixos 2.
- **O que está sólido:** a amostra (300), o funil, as métricas DF/LT/CFR(a)/recuperação, a censura e a classificação DORA. Nos 99 repositórios reprocessáveis, **0 divergências** entre o dataset e o recálculo independente em 13 colunas; kappa, consenso e P/R/F1 foram recalculados e conferem; o sorteio da amostra-ouro é reproduzível.
- **Bloqueios:** (1) o CFR (b) do dataset usa a v8 (F1 0,497), não a versão final avaliada, e a heurística não atinge F1 0,70 (S2-001); (2) a independência da rotulagem não é demonstrável (S2-002); (3) o F1 é medido na mesma amostra que desenhou a heurística (S2-003).
- **Veredito curto:** com as evidências atuais, a Sprint 2 **não deve ser dada como concluída**. A entrega mecânica (dados, scripts, rótulos, kappa, consenso, P/R/F1) está feita; faltam decisão e recálculo do CFR (b), sincronização do artigo e uma validação não circular. Nenhum problema exige refazer a coleta completa.

## 3. Matriz de requisitos

| ID | Requisito | Fonte oficial | Evidência no projeto | Estado | Severidade | Correção necessária |
|---|---|---|---|---|---|---|
| R01 | [OBR] Amostra final ≥ 300 repositórios após os filtros | E§2, E§10; FV S02-001 | `data/metrics.csv`, `outputs/repos_final.csv`, `outputs/resultados.csv`: 300 linhas, mesmo conjunto e mesma ordem; 0 duplicatas (inclusive sem diferenciar caixa); `funil.csv` tem 300 `selecionado` = dataset | **CONFORME** | — | — |
| R02 | [OBR] Funil de seleção gerado automaticamente, com contagens e motivos de descarte | E§7; FV S01-007 | `outputs/funil.csv` (2677 avaliados): 1219 `no_actions` + 1038 `lt_5_releases` + 120 `lt_50_runs` + 300 `selecionado`; 2677−1219=1458; −1038=420; −120=300 (fecha). Totais da Search API (60.143/60.142; 57.465 não avaliados) só constam em `funil.md` e exigem a API: não reproduzidos | **CONFORME** | — | — |
| R03 | [OBR] Critério mínimo: ≥ 5 releases e ≥ 50 runs válidos na janela | E§3; FV TRV-008 | No dataset: 0 repositórios com `n_releases_janela` < 5 e 0 com `n_runs_sucesso`+`n_runs_falha` < 50 | **CONFORME** | — | — |
| R04 | [OBR] Janela de 12 meses fixada pelo professor (02/10/2025–02/10/2026) aplicada de ponta a ponta | E§3; FV TRV-001, L01 | Datas aplicadas em `config.yaml`, `sorteio.json`, cálculo e coleta. Porém `config.yaml` e `artigo/metodologia.tex:55-57` ainda a chamam de provisória/`\pend`; fim inclusivo (23:59:59) faz a janela ter 366 dias (52,29 semanas) | **PARCIALMENTE CONFORME** | BAIXA | Atualizar `config.yaml`, README e artigo para 'oficial'; decidir/registrar 365×366 dias (ver S2-007) |
| R05 | [OBR] Coleta completa dos 300 com cache e retomada | E§10, E§11; FV S02-002 | Só documental (`outputs/execucao.log`, `funil.md`). O cache bruto dos 300 não está nesta máquina: só 99 repositórios foram reprocessáveis; a retomada não foi exercitada | **NÃO COMPROVADO** | MÉDIA | Preservar/compartilhar o cache bruto (ou hash + instruções) para permitir reprocessamento dos 300 (S2-012) |
| R06 | [OBR] Deployment frequency (RQ01) e sua classificação | E§5 RQ01/RQ07; FV §5.1 | Fórmula correta (`metricas/dora.py:44-62`); recálculo independente = CSV em 99/99; testes de fronteira. Defeito: 11 repositórios com exatamente 12 releases (cadência mensal) saem `Low` em vez de `Medium` (janela de 366 dias × corte '1/mês' calculado para 365) | **PARCIALMENTE CONFORME** | MÉDIA | Alinhar denominador e corte (usar 365 dias/52,14 sem ou com corte derivado da mesma janela) e recalcular `df_class`, `df_c2_class`, `df_c3_class` (S2-007) |
| R07 | [OBR] Lead time (a) por release | E§5 RQ02; FV §5.2 | `metricas/lead_time.py:60-63`; recálculo independente = CSV em 99/99; exemplo `v1.1` → 312 h (13 d) | **CONFORME** | — | — |
| R08 | [OBR] Lead time (b) por commit (mediana de todos os commits) | E§5 RQ02; FV §5.2 | `metricas/lead_time.py:78-81`; recálculo independente = CSV em 99/99; exemplo → {13, 5, 1} d | **CONFORME** | — | — |
| R09 | [OBR] CFR (a) — proxy de CI, todos os workflows juntos | E§5 RQ03a; FV §5.3a | `metricas/cfr.py:38-48`; recálculo independente = CSV em 99/99 (sucessos, falhas e taxa) | **CONFORME** | — | — |
| R10 | [OBR] CFR (b) implementado, integrado e persistido, com censura dos últimos 7 dias e janela de 7 dias inclusiva | E§5 RQ03b; FV §5.3b, S02-013 | `metricas/cfr_entrega.py:43-57`; 7d0h → falha, 7d+1s → não falha; censura contada; `n_avaliadas`+`n_censuradas`=`n_janela` em 300/300; recálculo independente (flags v8) = CSV em 99/99; coluna presente em `data/metrics.csv` | **CONFORME** | — | — |
| R11 | [OBR] Se F1 < 0,70, refinar e reavaliar a heurística | E§6.5; FV S02-015 | 10 versões (v1–v10) avaliadas contra o consenso; F1 final 0,6456 (v10). Refino foi feito na mesma amostra em que se avalia (ver R31) | **CONFORME** | — | — |
| R12 | [DER] CFR (b) do dataset calculado com a versão final da heurística | FV §9.13 ('Congelar a versão final… e recalcular CFR(b)'); `docs/refinamento_s02.md` #21 | `scripts/compute_metrics.py:31` fixa `v8`; `data/metrics.csv`: `heuristic_version=v8` em 300/300. v8 tem F1 0,4965 (6º de 10); v10 (escolhida) 0,6456. Constantes divergentes: `heuristica.py:39`=v1, `compute_metrics`=v8, `avaliacao_heuristica.csv`=v10 | **NÃO CONFORME** | ALTA | Decidir a versão final e recalcular `metrics.csv` (ver S2-001) |
| R13 | [OBR] Tempo de recuperação (RQ04) por workflow, mediana, censura | E§5 RQ04; FV §5.4 | `metricas/recovery.py:34-58`; recálculo independente = CSV em 99/99 (mediana, episódios, censurados); exemplo 1h20 → 1,3333 h; `cancelled` não encerra episódio; workflows isolados | **CONFORME** | — | — |
| R14 | [OBR] Casos censurados e releases ignoradas por 404 registrados e contados | E§3, E§11; FV S02-006 | Colunas `n_episodios_censurados`, `prop_episodios_censurados`, `n_releases_censuradas_cfr_b`, `n_releases_ignored_404`: 176/9062 episódios censurados; 418 releases censuradas no CFR (b); 6 releases 404 (5 repositórios) | **CONFORME** | — | — |
| R15 | [OBR] Classificação DORA por métrica e geral (tabela fixa; mediana com floor) | E§5 RQ07; FV TRV-015, §5.5 | 0 divergências em 300 linhas entre as colunas `*_class`/`dora_geral` e `metricas.dora`; fronteiras e (4,3,3,1)→High testadas e reproduzidas; ressalva de R06 | **CONFORME** | — | — |
| R16 | Regra para classificação geral quando uma métrica é indefinida | FV L10 (lacuna) | 23 repositórios (7,7%) sem `rec_median_h`/`dora_geral`/`dora_c1`/`dora_c3`; 24 sem `dora_c2`. Código deixa vazio (decisão do grupo, documentada). Sem regra do professor | **PENDENTE DE DEFINIÇÃO** | MÉDIA | Consultar o professor; documentar a regra no README/artigo e tratá-la no RQ07 (S2-010) |
| R17 | [DER] Colunas das variantes da RQ07 (release+pré-release; tag) no dataset | E§5 RQ07; FV S02-004 | `df_c2`, `df_c3`, `*_class`, `dora_c1/c2/c3`, `n_releases_deploy_c2`, `n_tags_janela` presentes; herdam v8 (C2) e o defeito de R06 | **CONFORME** | — | — |
| R18 | [OBR] Dataset `.csv` com as métricas por repositório | E§10; FV S02-003 | `data/metrics.csv`: 300×49; 0 `NaN`/`inf`/'None'; vazios só onde documentado (23 `rec_*`, 17 `prop_*`, 2 `language`, 1 `cfr_b`) | **CONFORME** | — | — |
| R19 | [OBR] Dicionário: nome, tipo, unidade e fórmula/origem para cada coluna dos CSVs finais | E§7, E§10; FV S02-005, T10 | Todas as 49 colunas de `metrics.csv` documentadas; `test_dicionario` passa. Mas: 5 entradas de colunas que não existem mais (`notas_indisponiveis`, `n_comum`, `precisao_comum`, `recall_comum`, `f1_comum`) e 4 CSVs gerados sem entrada (`data_quality.csv`, `*_2eval.csv`, snapshot do Kanban) | **PARCIALMENTE CONFORME** | BAIXA | Remover entradas obsoletas; cobrir ou declarar fora de escopo os 4 CSVs (S2-013) |
| R20 | [DER] Dataset reproduzível a partir do pipeline e dos artefatos preservados | FV §13 | `compute_metrics` roda só do cache (sem HTTP) e reproduz o CSV nos 99 repositórios disponíveis; cache não versionado; README ainda descreve amostra de 100 e `data/repos_final.csv` | **PARCIALMENTE CONFORME** | MÉDIA | Documentar como obter o cache; corrigir README (S2-012) |
| R21 | [DER] Relatório de qualidade dos dados atualizado para a amostra de 300 | `docs/refinamento_s02.md` #21 (aceite), FV D1 | `outputs/data_quality.md` ainda é de 100 repositórios, com 3 invariantes `N/A` (CFR (b), soma de censuradas, dicionário) | **NÃO CONFORME** | MÉDIA | Rodar `python -m scripts.data_quality --metricas data/metrics.csv` e commitar (S2-008) |
| R22 | [OBR] Sorteio de 60 repositórios com semente fixa documentada no código | E§6.1; FV S02-007 | `scripts/sample_gold.py:50` `SEED=42`; `random.Random(42).sample(sorted(repos),60)` sobre `resultados.csv` reproduz exatamente os 60 de `amostra_ouro.csv`; `sha256` de `resultados.csv` confere com `sorteio.json` | **CONFORME** | — | — |
| R23 | [DER] 5 releases por repositório, as mesmas para os três avaliadores | E§6 (consequência); FV S02-010 | 300 `release_id` idênticos e na mesma ordem nos 3 arquivos; 5 por repositório em 60/60 | **CONFORME** | — | — |
| R24 | [OBR] Três arquivos de rótulos, um por integrante, commitados pelo próprio autor com `#N` | E§10; FV S02-018 | `labels_GuilhermeVieira05.csv` (ee6275b, #25, Guilherme), `labels_marcosffp.csv` (6a4a67a, #23, Marcos), `labels_ALuiz19.csv` (895d6c0, #24, ALuiz19); 3 hashes distintos | **CONFORME** | — | — |
| R25 | [OBR] Rotulagem independente: sem consultar os demais e sem ver a saída da heurística | E§6.2; FV §9.12 (1) | Não demonstrável pelo Git. Contra-indícios documentados pelo grupo: rodada anterior com 'sugestões' compartilhadas (97,7% entre dois avaliadores; 292/292 = sugestão); no commitado, concordância 82,0% (ALuiz19×marcosffp) vs 56,0–63,3% com Guilherme; ALuiz19 implementou a heurística (fd2b384) e rotulou; Marcos alterou a heurística (e0e456f, 21:18) 41 min antes de commitar seus rótulos (6a4a67a, 21:59); 2 avaliadores rotularam repositório removido sem acesso | **NÃO COMPROVADO** | ALTA | Decisão do professor sobre rotulagem assistida; se exigido, re-rotular cegamente uma subamostra (ver S2-002) |
| R26 | [OBR] Kappa de Fleiss nas 3 dimensões, sobre os rótulos originais | E§6.3; FV S02-011 | Recalculado com fórmula própria (sem statsmodels) a partir dos 3 `labels_*.csv`: 0,7429 / 0,3516 / 0,2728 = `concordancia.csv`; `scripts/agreement.py:68-80` usa `aggregate_raters`+`fleiss_kappa`; κ=1 em concordância perfeita | **CONFORME** | — | — |
| R27 | [OBR] Consenso com protocolo de desempate versionado, rastreável aos 3 rótulos | E§6.4; FV S02-012 | `PROTOCOLO_CONSENSO.md`; `consenso.csv`: 420 itens (60+60+300), 3 rótulos + `metodo` por linha; regra recomputada: 420/420 coerentes; 0 pendentes; 85 corretivas; rótulos individuais intactos (arquivos próprios) | **CONFORME** | — | — |
| R28 | [OBR] Precisão, recall e F1 da heurística contra o consenso | E§6.5; FV S02-014 | Recalculado de `heuristica_amostra.csv`×`consenso.csv`: TP/FP/FN/TN, P, R e F1 das 10 versões = `avaliacao_heuristica.csv`; exemplo do professor 40/30/50 → 0,75/0,60/0,667 | **CONFORME** | — | — |
| R29 | [OBR] Cada versão testada e seu F1 documentados no artigo | E§6.5; FV S02-015, T12 | `artigo/metodologia.tex:194-203` lista v1–v9 (sem v10) com números que não batem com `avaliacao_heuristica.csv` (ex.: v1 F1 0,539 vs 0,557; v9 n=295 vs 300) | **PARCIALMENTE CONFORME** | MÉDIA | Regenerar a tabela do artigo a partir do CSV atual e incluir v10 (S2-004) |
| R30 | [OBR] Heurística 'validada' contra a amostra rotulada (condição para usar CFR (b)) | E§5 RQ03b; FV S02-016 | F1 máximo 0,6456 < 0,70. Nem o enunciado nem a FV dizem como proceder (o próprio `refino_heuristica.md` registra a lacuna); FV aceite admite 'F1 ≥ 0,70 **ou** histórico documentado' | **PENDENTE DE DEFINIÇÃO** | ALTA | Perguntar ao professor se CFR (b) exploratório é aceitável (S2-001) |
| R31 | [DER] Validação sem vazamento entre amostra de desenho e de avaliação | FV §9.11 (overfitting) | v8–v10 desenhadas depois da análise de erros (8fc43b4) e avaliadas nos mesmos 300 itens, escolha entre 10 versões; sem amostra de validação. Reconhecido em `docs/refino_heuristica.md` | **NÃO CONFORME** | ALTA | Validar a versão congelada em amostra nova (ver S2-003) |
| R32 | [OBR] Tipo do projeto rotulado para a RQ06 | E§6; FV §3.2 | `consenso.csv` dimensão `tipo_projeto`: 60 itens, 44 unanimidade + 16 maioria, 0 pendentes | **CONFORME** | — | — |
| R33 | [OBR] Metodologia completa: fonte, funil, janela, definições/variantes, protocolo de validação | E§8, E§10; FV S02-017 | `artigo/metodologia.tex` cobre todos os itens, com ressalvas honestas (`\pend`, `\prov`). Defasado: sem v10, sem `metrics.csv` (diz que CFR (b) 'não está' no arquivo de métricas, `:86-87`), tabela de F1 divergente; só fragmentos `.tex` (sem documento principal/SBC/.bib) | **PARCIALMENTE CONFORME** | MÉDIA | Sincronizar com os artefatos (S2-004); montar documento SBC antes da entrega final (S2-004) |
| R34 | [OBR] Tabela do funil na Metodologia | E§7, E§8; FV §9.8 | `metodologia.tex:35-44` = `funil.csv` (2677/1219/1038/120/300) | **CONFORME** | — | — |
| R35 | [OBR] Testes automatizados das métricas com fixtures e casos de borda | E§7; FV S01-020/021 | `pytest`: 681 passed; casos de borda nomeados: release sem commits novos, falha nunca recuperada, 1 release, `cancelled` | **CONFORME** | — | — |
| R36 | [OBR] Cobertura ≥ 80% do módulo de métricas | E§7; FV S01-022 | `--cov=metricas`: 99% (313 stmts, 1 não coberta: `recovery.py:26`) | **CONFORME** | — | — |
| R37 | [OBR] CI do grupo executando os testes a cada push | E§7; FV S01-023 | `.github/workflows/testes.yml` conforme o modelo (py3.12, `--cov-fail-under=80`). Execução verde não verificável localmente; testes rodaram em Python 3.14.5, não 3.12 | **NÃO COMPROVADO** | BAIXA | Conferir a aba Actions (último run verde no commit auditado) |
| R38 | [OBR] Comando único e token por variável de ambiente | E§7; FV S01-002/003 | `python -m pipeline --config` existe (`--help` OK); token via `GITHUB_TOKEN`; não executado de ponta a ponta (exige rede/token). README com trechos desatualizados (S2-005) | **PARCIALMENTE CONFORME** | BAIXA | Teste de 'máquina limpa' do README (FV §13.1) |
| R39 | [OBR] Sem bibliotecas prontas de acesso à API do GitHub | E§4, E§10; FV TRV-011 | `requirements.txt`: PyYAML, requests, pytest, pytest-cov, statsmodels, scikit-learn; cliente HTTP próprio (`pipeline/http_client.py`) | **CONFORME** | — | — |
| R40 | [OBR] Token nunca versionado | E§7; FV S01-003 | Varredura na árvore de trabalho (`ghp_`, `github_pat_`, `gho_`) e em todo o histórico (`ghp_`): 0 ocorrências; `.gitignore` cobre `.env*`/`*.token`/`cache/` | **CONFORME** | — | — |
| R41 | [OBR] Commits referenciam o nº da Issue | E§10; FV S01-029, AVL-004 | 59 commits: 0 não-merge sem `#N`; 0 merges sem `#N` | **CONFORME** | — | — |
| R42 | [OBR] Cada integrante com artefato de código na sprint | E§10; FV S01-028, AVL-002 | Guilherme: #19, #20, #21; Marcos: #22, #26, #29; ALuiz19: #27, #28, #30 (autor por `git log`) | **CONFORME** | — | — |
| R43 | [OBR] GitHub Projects com WIP, Assignees e evolução semanal | E§10; FV S01-030 | Sem acesso ao Projects/Issues nesta auditoria (sem API); só o snapshot do Kanban de 2026-10-06 | **NÃO COMPROVADO** | BAIXA | Verificar no quadro |
| R44 | [OBR] Definições comuns: default branch, `event=push`, tabela de `conclusion`, deploy = release não-draft/não-pré, `author.date` | E§3; FV TRV-003..007 | Testes específicos + recálculo independente (CFR (a), recuperação, DF, LT) coerentes em 99/99; `compare` paginado e 404 tratado | **CONFORME** | — | — |

## 4. Auditoria das métricas DORA

Cada item abaixo foi rastreado até o código, os testes e o CSV. "Recálculo" = reimplementação independente sobre o cache HTTP bruto de **99** repositórios (os demais 201 não têm cache nesta máquina).

### 4.1 Deployment frequency (RQ01)
- **Definição:** releases publicadas na janela ÷ semanas da janela (E§5 RQ01).
- **Implementação:** `metricas/dora.py:44-62` — conta `draft=false`, `prerelease=false`, `published_at` ∈ [início, fim] inclusivos; semanas = (fim−início)/7 d. Chamada em `pipeline/etapas.py:64`.
- **Recálculo:** 99/99 iguais. Caso `52 releases / 365 d = 0,9973` reproduzido.
- **Presença/dicionário:** `deployment_frequency` em `metrics.csv`; dicionário coerente.
- **Problema:** janela de 366 dias (fim 23:59:59 do último dia) × corte '1/mês' de 365 dias → 11 repositórios com 12 releases `Low` (S2-007). O artigo/dicionário descrevem 'semanas da janela' sem declarar 52,29.
- **Estado:** PARCIALMENTE CONFORME.

### 4.2 Lead time (a) e (b)
- **Implementação:** `metricas/lead_time.py` — (a) `max` dos lead times (commit mais antigo) por release, mediana; (b) mediana de todos os commits de todas as releases (não é mediana de medianas); `author_date`, não `committer_date`.
- **Decisões do grupo (FV L07), documentadas e contadas:** release sem commits novos (1.685 releases; 11,5% de 14.641 na janela) e commits posteriores à release (381 em 32 repositórios) excluídos.
- **Recálculo:** (a) e (b) 99/99 iguais; `n_releases_ignored_404`, `n_sem_anterior`, `n_releases_avaliadas` 99/99. Exemplo `v1.1`: (a)=312 h (13 d); (b)={13, 5, 1} d.
- **Risco:** 13,8% das comparações dos 99 repositórios são `diverged` (backports); não persistido (S2-011).
- **Estado:** CONFORME (R07, R08), com risco registrado.

### 4.3 CFR (a)
- **Implementação:** `metricas/cfr.py:38-48`; `event=push` por filtro defensivo; denominador 0 → `None`.
- **Recálculo:** 99/99 (sucessos, falhas, taxa). `cancelled`, `skipped`, `neutral`, `action_required`, `stale` e vazio ignorados (teste parametrizado).
- **Estado:** CONFORME. O artigo discute falha de pipeline ≠ falha em produção como ameaça de construto.

### 4.4 CFR (b)
- **Implementação:** `metricas/cfr_entrega.py:43-57` — falha se existe corretiva em (R, R+7d]; qualquer release, não só a próxima (L08); censura quando R+7d > fim; indefinido com < 2 releases.
- **Casos reproduzidos:** `v2.3.0→v2.3.1` + `fix` → corretiva; `v2.4.0→v2.5.0` → não; corretiva a 7d0h → falha, a 7d+1s → não; release a 5 dias do fim → censurada e fora do denominador.
- **Recálculo:** 99/99 iguais (contagem própria sobre os sinalizadores da v8).
- **Integração:** `compute_metrics` → `data/metrics.csv` (`cfr_b`, 5 contadores, `heuristic_version`). `outputs/resultados.csv` **não** tem CFR (b) por desenho.
- **Problema:** versão da heurística (S2-001).
- **Estado:** cálculo CONFORME (R10); versão NÃO CONFORME (R12).

### 4.5 Tempo de recuperação
- **Implementação:** `metricas/recovery.py:34-58` — por `workflow_id`, ordenado por `run_started_at`; episódio da 1ª falha ao próximo sucesso; `updated_at` do sucesso; falha sem sucesso → censurada; falha antes de qualquer sucesso também abre episódio (decisão do grupo, L09).
- **Recálculo:** mediana, `n_episodios`, `n_censurados` 99/99. Exemplo 09:00…11:20 → 1,3333 h; com `cancelled` no meio, inalterado.
- **Natureza de proxy:** o artigo e o README declaram que CI não é produção.
- **Dados:** 9.062 episódios; 176 censurados em 105 repositórios; 23 repositórios sem mediana (S2-010).
- **Estado:** CONFORME.

### 4.6 Classificação DORA
- **Implementação:** `metricas/dora.py:65-130`; cortes do enunciado; `classify_overall` mediana com `floor`.
- **Verificação:** 300/300 linhas coerentes (`df`, `lt`, `cfr`, `rec`, `cfr_b`, `df_c2`, `df_c3`, `dora_geral`). Fronteiras reproduzidas: DF 7→Elite, 6,99→High, 1→High; LT 24→High, 168→Medium, 720→Low; CFR .15/.30/.45/.4501; REC 1→High, 24→Medium, 168→Low; (4,3,3,1)→High.
- **Estado:** CONFORME, ressalvado S2-007.

## 5. Dataset, dicionário e recálculo independente

| Verificação | Resultado |
|---|---|
| Linhas / colunas / duplicatas | 300 / 49 / 0 |
| `NaN`, `inf`, 'None' | 0 |
| Vazios | `rec_median_h`, `rec_class`, `dora_geral`, `dora_c1`, `dora_c3`: 23; `dora_c2`: 24; `prop_episodios_censurados`: 17; `cfr_b`/`cfr_b_class`: 1; `language`: 2 |
| `n_avaliadas_cfr_b + n_censuradas_cfr_b = n_releases_janela` | 300/300 |
| `n_releases_janela` ≥ 5; runs válidos ≥ 50 | 0 violações |
| `n_runs_dias_saturados` | 0 em 300 |
| `heuristic_version` | `v8` em 300/300 |
| Mesmo conjunto/ordem em `metrics`, `repos_final`, `resultados`, `funil.selecionado` | sim |
| Classes × valores numéricos | 0 divergências |
| Colunas de `metrics.csv` sem entrada no dicionário | 0 (49/49) |
| Recálculo independente vs CSV (99 repositórios, 13 colunas) | 0 divergências |

**Casos mínimos com resposta conhecida (funções reais):** DF 52/365 d = 0,9973; LT(a) 312 h; LT(b) {13, 5, 1} d; CFR (b) 7d0h/7d+1s; censura de 7 dias; recuperação 1h20 = 1,3333 h e falha nunca recuperada = 1 censurado; classificação nas fronteiras; Fleiss com concordância perfeita = 1,0; P/R/F1 do exemplo do professor = 0,75 / 0,60 / 0,667.

## 6. Auditoria da validação manual

| Aspecto | Resultado verificado | Estado |
|---|---|---|
| Sorteio | `random.Random(42).sample(sorted(repos), 60)` sobre `resultados.csv` = os 60 de `amostra_ouro.csv`; `sha256` da lista confere com `sorteio.json`; 60 ⊂ `repos_final` | Reproduzido |
| Releases | 5 por repositório (300), mesmos `release_id` e ordem nos 3 arquivos | Reproduzido |
| Arquivos | 3 `labels_*.csv`, distintos, cada um commitado pelo próprio autor com `#N` | Conforme |
| Independência | Não observável; ver S2-002 | **Não comprovada** |
| Concordância (3 avaliadores) | κ de Fleiss: tipo 0,7429 (substancial), entrega real 0,3516 (razoável), corretiva 0,2728 (razoável); concordância simples 0,733 / 0,917 / 0,507; recalculado por fórmula direta | Conforme |
| Leitura do κ | `entrega_real`: 57–58 'sim' em 60 por avaliador → efeito de prevalência (κ baixo com 91,7% de acordo), já descrito no artigo | Ok |
| Consenso | maioria simples; 1-1-1 → reunião (`desempate.csv`, inexistente porque não houve); 420 itens: corretiva 152 unanimidade + 148 maioria, tipo 44+16, entrega 55+5; 0 pendentes; 85 corretivas | Conforme |
| P/R/F1 | 10 versões recalculadas = CSV; v10: TP 51, FP 22, FN 34, TN 193 → P 0,6986, R 0,6000, F1 0,6456 | Conforme |
| Versões | v1 definida antes dos dados; v2–v7 no mesmo commit do avaliador (360adc7); v8–v10 após análise de erros | Documentado; F1 otimista (S2-003) |
| Releases sem anterior | 5 das 300 são a primeira da história; a heurística nunca as marca e o consenso também não (0 'sim' entre elas): sem efeito no F1 | Observação |

**Comprovado:** sorteio, igualdade das releases, autoria dos arquivos, κ, consenso, P/R/F1. **Depende de registros ausentes:** independência dos avaliadores; origem das 'sugestões' da primeira rodada; proveniência do dado do repositório removido (S2-006).

## 7. Auditoria do artigo e da Metodologia

Todas as subseções exigidas existem. O texto é cuidadoso em declarar limitações (`\pend`, `\prov`). Divergências com a execução real:

| Procedimento descrito | Execução/artefato | Achado |
|---|---|---|
| 'CFR (b) não está no arquivo de métricas atual' (`:86-87`) | Está em `data/metrics.csv` (#21, 14/10 21:42) | S2-004 |
| Tabela v1–v9, n=295 para v9, melhor F1 0,599 | `avaliacao_heuristica.csv`: v1–v10, n=300, melhor F1 0,6456 (v10) | S2-004 |
| 'nove versões' | dez versões | S2-004 |
| v1 F1 0,539 | 0,557 no CSV (predições do repositório removido mudaram) | S2-006 |
| Janela 'provisória' (`\pend`) | Janela aprovada | S2-014 |
| 57.465 candidatos não avaliados; 60.143 resultados | Só em `funil.md`; não reproduzível sem API | R02 |
| 'Cada avaliador preencheu em arquivo próprio' | Verdadeiro nos arquivos; independência não demonstrada e declarada como tal | S2-002 |
| `stars:1282..1312` com 1.000 resultados marcado `\pend` 'truncado?' | `total_count`=1000 não excede o teto (`selection.py:174` testa `> 1000`); sem truncamento | Pode ser removido |

Não há afirmação de resultado estatístico das RQs (corretamente adiado para a S03). Procedimentos **planejados**: IC/bootstrap, amostra de validação separada, template SBC; **executados e comprovados**: seleção, coleta, métricas, sorteio, rótulos, κ, consenso, P/R/F1.

## 8. Testes e execução

| Comando | Resultado |
|---|---|
| `pytest -q -p no:cacheprovider --cov=metricas --cov-report=term-missing` | 681 passed em ~9 s; cobertura 99% (`recovery.py:26`) |
| Recálculo independente (99 repositórios) | 0 divergências |
| Casos mínimos | todos conferem (seção 5) |

**O que os testes protegem bem:** exemplos do professor (v1.1, v2.3.0→v2.3.1, 1h20), fronteiras de classificação, 7 dias inclusivos, censura, `cancelled`, workflows independentes, invariante `avaliadas + censuradas = janela` (propriedade).

**Lacunas:** (i) `test_compute_metrics::test_cfr_b_usa_versao_v8` **fixa** a versão v8 como esperada, blindando S2-001; (ii) nenhum teste exercita a janela de 366 dias contra o corte de 12 releases (S2-007); (iii) testes de 'notas ausentes/HTTP ≠ 200' removidos em b7ab06f (S2-006); (iv) `test_dicionario` é unidirecional (S2-013); (v) CI não verificado.

## 9. Achados detalhados

### S2-001 — CFR (b) do dataset usa v8; versão avaliada como melhor é v10; heurística sem 'validação' formal
- **Severidade:** ALTA
- **Requisitos afetados:** R12, R30
- **Evidência e localização:** `scripts/compute_metrics.py:31` (`VERSAO_HEURISTICA = "v8"`), `:105`; `data/metrics.csv` coluna `heuristic_version`=v8 em 300/300; `data/amostra_ouro/avaliacao_heuristica.csv`: v8 F1 0,4965 (6º de 10), v10 0,6456; `avaliacao_heuristica.md` ('atualize `HEURISTIC_VERSION` e recalcule o CFR (b)'); `metricas/heuristica.py:39` v1; `pipeline/collect_releases.py:32` (`CAMPOS` sem `body`); `FV §9.13`.
- **Explicação técnica:** v8 prevê 18,7% de releases corretivas contra 28,3% do consenso (56/300 vs 85/300), logo subestima o CFR (b); v10 e v9 exigem `body`, que o pipeline descarta ao normalizar as releases, e `collect_commits` não repassa `body` a `classificar_releases`. Três constantes diferentes (v1, v8, v10) convivem.
- **Consequência:** `cfr_b`, `cfr_b_class`, `dora_c2` e, adiante, RQ03b, RQ05b e RQ07 herdam um estimador que o grupo já sabe ser inferior e viesado. Impede declarar o item do checklist 'versão final congelada'.
- **Correção recomendada:** (1) Decidir com o professor se CFR (b) exploratório é aceitável (R30) e qual versão é a final. (2) Se v9/v10: o cache HTTP bruto das páginas de `/releases` **já contém `body`** (verificado: 3.182 caracteres numa release); basta reprocessar do cache bruto de quem coletou, sem nova coleta, passando `body` até `classificar_releases`. (3) Passar a versão por configuração, não por constante, e recalcular `metrics.csv`.
- **Critério de aceite:** `heuristic_version` única em `metrics.csv`, igual à declarada em `avaliacao_heuristica.*`, README, dicionário e artigo; `test_compute_metrics` cobre a versão final; `data_quality` com invariantes de CFR (b) `OK`.

### S2-002 — Independência da rotulagem não comprovada
- **Severidade:** ALTA
- **Requisitos afetados:** R25
- **Evidência e localização:** `artigo/metodologia.tex:111-131`; `docs/auditoria_metodologia.md` §2.1; `git log` (fd2b384 14/10 01:43 ALuiz19 heurística; 895d6c0 14/10 21:46 ALuiz19 rótulos; e0e456f 14/10 21:18 Marcos altera heurística; 6a4a67a 14/10 21:59 Marcos rótulos); concordância em `corretiva` recalculada: 0,820 / 0,633 / 0,560.
- **Explicação técnica:** O Git registra quando o arquivo foi commitado, não quando foi preenchido. A única rodada rotulada com sugestões compartilhadas ficou fora do repositório; o enunciado exige rotular 'sem consultar os demais e sem ver a saída da heurística'. Dois avaliadores conheciam o desenho da heurística (a escreveram/alteraram) e rotularam depois. A concordância assimétrica (par mais próximo pesa mais no 2-a-1) é compatível com orientação comum, mas não a prova.
- **Consequência:** κ de Fleiss, consenso e F1 não podem ser lidos como três julgamentos independentes. O consenso (28,3% corretivas) é a referência de todo o F1.
- **Correção recomendada:** Levar a decisão ao professor (já marcado como `\pend`). Se exigido: sortear uma subamostra (p.ex. 20 repositórios × 5 releases), cada avaliador rotula isolado, sem sugestões e sem acesso às regras, com entrega por commit/Issue e hash antes da reunião.
- **Critério de aceite:** Protocolo de rotulagem cega registrado, três arquivos novos commitados antes de qualquer consenso, κ recalculado e comparado ao atual.

### S2-003 — F1 otimista: versões desenhadas e escolhidas na própria amostra de avaliação
- **Severidade:** ALTA
- **Requisitos afetados:** R31, R30
- **Evidência e localização:** `docs/refino_heuristica.md` (Riscos 1); `artigo/metodologia.tex:178-181, 238-241`; `data/amostra_ouro/erros_heuristica.*` (análise de erros, 8fc43b4) anterior a v8–v10.
- **Explicação técnica:** v8, v9 e v10 usam contagens e *release notes* ajustadas após ver os erros em 300 releases; a v10 é a de maior F1 entre 10 candidatas na mesma amostra, sem conjunto separado. O F1 de 0,6456 é limite superior.
- **Consequência:** Qualquer F1 ≥ 0,70 numa nova rodada sobre a mesma amostra seria ainda menos informativo; hoje nem 'validada' nem 'refutada' podem ser afirmadas com segurança.
- **Correção recomendada:** Congelar a versão; sortear repositórios da amostra final **fora** dos 60 (semente distinta, registrada), rotular com protocolo cego (S2-002) e avaliar uma única vez; reportar intervalo (ex.: bootstrap).
- **Critério de aceite:** F1 da versão congelada numa amostra disjunta, com semente, n e intervalo no artigo.

### S2-004 — Artigo defasado em relação aos artefatos
- **Severidade:** MÉDIA
- **Requisitos afetados:** R29, R33
- **Evidência e localização:** `artigo/metodologia.tex:86-87` ('CFR (b) não está no arquivo de métricas'), `:183-185` (n=295; 'nove versões'), `:194-203` (v1 F1 0,539, v9 n=295, sem v10), `:210-211` ('melhor F1 0,599'); `data/amostra_ouro/avaliacao_heuristica.csv` (n=300 em todas; v1 0,557; v10 0,6456).
- **Explicação técnica:** A tabela cita `avaliacao_heuristica.csv` como fonte, mas foi escrita para uma rodada anterior (subconjunto de 295). A rodada commitada em b7ab06f muda predições das 5 releases do repositório removido.
- **Consequência:** A Metodologia descreve uma execução que não é a dos arquivos entregues; viola 'documentar cada versão e seu F1'.
- **Correção recomendada:** Regenerar a tabela e os números do texto a partir do CSV; mencionar `data/metrics.csv` e a versão usada no CFR (b).
- **Critério de aceite:** Todo número do artigo reproduzível por `avaliacao_heuristica.csv`/`concordancia.csv`/`metrics.csv`.

### S2-005 — Documentação auxiliar contraditória entre si
- **Severidade:** MÉDIA
- **Requisitos afetados:** R38, R12
- **Evidência e localização:** `docs/refino_heuristica.md` (v10 'fora do dataset', `--permitir-sem-notas`, n=295); `data/amostra_ouro/avaliacao_heuristica.md` ('v10 escolhida'); `README.md:45` (amostra_alvo 100), `:192-196` (só v8/v9; 'v9 fora do dataset'), `:280` (`data/repos_final.csv`, inexistente); `DICIONARIO_DE_DADOS.md` (heuristic_version 'v8 na geração inicial').
- **Explicação técnica:** Quatro documentos dão quatro versões 'principais' (v8, v9, v10, v4). A flag `--permitir-sem-notas` citada não existe mais em `scripts/evaluate_heuristic.py`.
- **Consequência:** Quem replica (entrega final) não consegue saber qual é o procedimento vigente.
- **Correção recomendada:** Um único documento de referência para a decisão da versão; README e dicionário apontam para ele.
- **Critério de aceite:** Sem contradições entre README, dicionário, `docs/` e artefatos gerados.

### S2-006 — Salvaguardas da avaliação removidas no commit da v10
- **Severidade:** MÉDIA
- **Requisitos afetados:** R28, R20
- **Evidência e localização:** `git diff 4c4d583 b7ab06f -- scripts/evaluate_heuristic.py tests/test_evaluate_heuristic.py`; `data/amostra_ouro/heuristica_amostra.csv` linhas de `1bananachicken/MaaNTE`.
- **Explicação técnica:** O commit b7ab06f removeu o tratamento explícito de release sem notas (HTTP 404/410 → não avaliável), o erro para HTTP ≠ 200, a flag `--permitir-sem-notas`, a medida em subconjunto comum e testes correspondentes (117 linhas alteradas em `test_evaluate_heuristic.py`). As 5 releases do repositório removido passaram de `404`/sem commits para `ok` com commits e notas: a rodada usou um cache que ainda tinha o dado, que ninguém mais possui.
- **Consequência:** Resultados mudaram (ex.: v1 TP 63→66) sem que o dado de origem seja versionado ou reproduzível; a v9/v10 deixa de falhar em silêncio quando faltam notas.
- **Correção recomendada:** Restaurar as salvaguardas (ou justificar a remoção) e registrar a proveniência do dado do repositório removido (hash do cache ou extrato versionado das 5 releases).
- **Critério de aceite:** Testes de 'notas ausentes' e 'HTTP ≠ 200' de volta; a avaliação reproduz o CSV a partir de um extrato versionado.

### S2-007 — Janela de 366 dias × corte '1 por mês' de 365: 11 repositórios com 12 releases saem `Low`
- **Severidade:** MÉDIA
- **Requisitos afetados:** R06
- **Evidência e localização:** `metricas/dora.py:26` (`DF_UM_POR_MES = 84/365`), `:52-55`; `pipeline/etapas.py:47-52` (fim 23:59:59); `data/metrics.csv`: 11 repositórios com `n_releases_janela=12`, todos `df_class=Low`.
- **Explicação técnica:** Com 52,2857 semanas, 12 releases dão 0,2295 < 0,2301 (corte para 365 dias). Um repositório que publica uma release por mês cai em `Low`, contrariando '≥ 1 por mês → Medium' (E§5 RQ07). Com 365 dias exatos, os mesmos 11 seriam `Medium`.
- **Consequência:** 11 de 300 (3,7%) com `df_class` (e C2/C3 afins) errado; `dora_geral` não muda em nenhum (testado), mas RQ01/RQ07 por categoria mudam.
- **Correção recomendada:** Usar a mesma duração nos dois lados (ex.: janela [início, fim) de 365 dias ou corte derivado de `(fim−início)`), documentar e recalcular `df_*_class`.
- **Critério de aceite:** 12 releases na janela → `Medium`; teste de fronteira cobrindo o caso; 0 repositórios mudando por 365 vs 366.

### S2-008 — Relatório de qualidade dos dados é de 100 repositórios
- **Severidade:** MÉDIA
- **Requisitos afetados:** R21
- **Evidência e localização:** `outputs/data_quality.md` ('· 100 repositórios'; 3 invariantes `N/A`).
- **Explicação técnica:** O arquivo não foi regenerado após #19/#21; o critério de aceite da #21 exige invariantes de CFR (b) em `OK`.
- **Consequência:** O artefato que deveria atestar integridade dos 300 não atesta nada sobre CFR (b) nem sobre o dicionário.
- **Correção recomendada:** `python -m scripts.data_quality --metricas data/metrics.csv` e commit.
- **Critério de aceite:** 0 `FALHA`, 0 `N/A` nas invariantes de CFR (b) e dicionário.

### S2-009 — Amostra = primeiros 300 que passam, em ordem alfabética de `full_name`
- **Severidade:** MÉDIA
- **Requisitos afetados:** R01 (validade)
- **Evidência e localização:** `outputs/funil.md` ('ordem determinística por `full_name`'); distribuição de iniciais em `data/metrics.csv`: 251 de 300 começam com `a`, 49 com dígito; 57.465 candidatos não avaliados.
- **Explicação técnica:** Critério de corte não aleatório e correlacionado a nomes de organizações. O enunciado não exige aleatoriedade, e o artigo já a declara como ameaça externa.
- **Consequência:** Generalização para 'repositórios populares' enfraquecida; todas as RQs herdam.
- **Correção recomendada:** Se houver orçamento de API: avaliar uma amostra aleatória com semente da população de 60.142. Caso contrário, manter e reforçar a ameaça com a distribuição de iniciais.
- **Critério de aceite:** Amostra com semente documentada ou ameaça quantificada no artigo.

### S2-010 — 23 repositórios (7,7%) sem classificação geral
- **Severidade:** MÉDIA
- **Requisitos afetados:** R16
- **Evidência e localização:** `data/metrics.csv`: `dora_geral` vazio em 23 (sem episódio concluído de recuperação); `scripts/compute_metrics.py:163-181`.
- **Explicação técnica:** Sem regra da FV (L10). O código deixa vazio; o enunciado não prevê.
- **Consequência:** Perda de 7,7% da amostra na RQ07 e nas tabelas por categoria.
- **Correção recomendada:** Decisão do professor ou regra do grupo documentada (p.ex. classificar com as métricas disponíveis e sinalizar).
- **Critério de aceite:** Regra escrita no README/artigo e aplicada no dataset.

### S2-011 — Divergência e truncamento do `compare` calculados, mas não persistidos
- **Severidade:** MÉDIA
- **Requisitos afetados:** R07, R08
- **Evidência e localização:** `pipeline/collect_commits.py:172-173` (`n_truncadas`, `n_divergentes`); ausentes das colunas de `resultados.csv`/`metrics.csv`; nos 99 repositórios reprocessáveis: 620 de 4.507 comparações `diverged` (13,8%), 0 truncadas.
- **Explicação técnica:** `diverged` indica anterior em outra linha de versão; o lead time pode inflar (documentado na docstring e no artigo, mas não mensurável por repositório).
- **Consequência:** Não é possível filtrar/sensibilizar LT por esse risco nas RQs; outliers (ex.: `actions/runner-images`) ficam sem explicação no dataset.
- **Correção recomendada:** Persistir `n_compare_divergentes` e `n_compare_truncados` e documentá-los.
- **Critério de aceite:** Colunas no CSV e no dicionário; contagem total reportada no artigo.

### S2-012 — Cache bruto não versionado e só 99/300 reprocessáveis
- **Severidade:** MÉDIA
- **Requisitos afetados:** R05, R20
- **Evidência e localização:** `.gitignore` (`cache/`); `~/Developer/Lab03/cache` com 100 repositórios; `artigo/metodologia.tex:100-102`.
- **Explicação técnica:** A reprodução dos 300 depende de máquina específica; o replicador da entrega final parte do README.
- **Consequência:** Somente 33% do dataset foi recalculado de forma independente nesta auditoria; o restante confia no pipeline.
- **Correção recomendada:** Publicar o cache compactado (release/Drive) com hash, ou extrato mínimo (releases+compare+runs reduzidos) versionado.
- **Critério de aceite:** Reprocessamento dos 300 por terceiro reproduz `metrics.csv` byte a byte.

### S2-013 — Dicionário com entradas obsoletas e CSVs sem entrada
- **Severidade:** BAIXA
- **Requisitos afetados:** R19
- **Evidência e localização:** `DICIONARIO_DE_DADOS.csv`: `notas_indisponiveis` (heuristica_amostra); `n_comum`, `precisao_comum`, `recall_comum`, `f1_comum` (avaliacao_heuristica); sem entrada: `outputs/data_quality.csv`, `data/amostra_ouro/{consenso,concordancia}_2eval.csv`, `data/kanban-snapshots/*.csv`.
- **Explicação técnica:** `test_dicionario` só cobra coluna sem entrada, não entrada sem coluna.
- **Consequência:** Dicionário não espelha os arquivos entregues.
- **Correção recomendada:** Remover as 5 entradas; documentar ou excluir do escopo os 4 arquivos; ampliar o teste para bidirecional.
- **Critério de aceite:** Conjuntos de colunas = conjuntos de entradas, por arquivo.

### S2-014 — Documentos ainda chamam a janela de 'provisória'; artigo sem documento principal
- **Severidade:** BAIXA
- **Requisitos afetados:** R04, R33
- **Evidência e localização:** `config.yaml` (comentário 'DATAS PROVISÓRIAS'); `artigo/metodologia.tex:55-57`, `\pend`; `artigo/` só com `.tex` de seção; `pipeline.log` (807 KB) versionado na raiz.
- **Explicação técnica:** A janela foi aprovada pelo professor (informação do grupo nesta auditoria); os textos não foram atualizados.
- **Consequência:** Ruído e risco de reabrir uma decisão fechada.
- **Correção recomendada:** Atualizar os textos; mover/ignorar `pipeline.log`.
- **Critério de aceite:** Nenhum 'provisória' referente à janela; `pipeline.log` fora do Git.

## 10. Plano de correção priorizado

| # | Ação | Depende de | Nova coleta? | Como comprovar |
|---|---|---|---|---|
| **1. Bloqueios** | | | | |
| 1.1 | Perguntar ao professor: (a) CFR (b) com F1 < 0,70 é aceitável como exploratório? (b) rotulagem assistida é aceita? (c) regra de classificação geral com métrica indefinida (L10) | — | Não | Resposta registrada no README/artigo |
| 1.2 | Fixar a versão final da heurística e recalcular `metrics.csv` (S2-001) | 1.1; `body` das releases | **Não**, se o cache HTTP bruto de quem coletou estiver preservado (já contém `body`); só reprocessar | `heuristic_version` único e igual em todos os artefatos |
| **2. Cálculo e integração** | | | | |
| 2.1 | Corrigir denominador/corte de DF e recalcular `df_*_class` (S2-007) | — | Não | 12 releases → Medium; 0 mudanças 365×366 |
| 2.2 | Persistir `n_compare_divergentes`/`n_compare_truncados` (S2-011) | cache | Não | Colunas + dicionário |
| 2.3 | Restaurar salvaguardas de `evaluate_heuristic` e testes (S2-006) | — | Não | Testes verdes |
| **3. Dados e validação** | | | | |
| 3.1 | Amostra de validação disjunta com rotulagem cega e semente (S2-002/003) | 1.1 | Parcial: ~20 repositórios × 5 releases (rotulagem; a coleta de releases/compare já existe para os 300) | κ e F1 na amostra nova, com intervalo |
| 3.2 | Regenerar `data_quality.*` para 300 (S2-008) | 1.2 | Não | 0 FALHA, 0 N/A |
| 3.3 | Preservar/compartilhar o cache bruto ou extrato versionado (S2-012) | — | Não | Reprocessamento por terceiro |
| **4. Documentação e artigo** | | | | |
| 4.1 | Sincronizar tabela, números e CFR (b)/`metrics.csv` no artigo (S2-004) | 1.2, 3.1 | Não | Números reproduzíveis |
| 4.2 | Unificar README/`docs/`/dicionário (S2-005, S2-013, S2-014) | 1.2 | Não | Sem contradições |
| **5. Não bloqueantes** | | | | |
| 5.1 | Avaliar amostra aleatória com semente (S2-009) | orçamento de API | Sim (opcional) | Ameaça quantificada ou amostra nova |
| 5.2 | Conferir CI e Projects (R37, R43) | acesso ao GitHub | Não | Print/URL do run verde; quadro atualizado |

Nenhuma ação exige refazer a coleta completa dos 300 repositórios.

## 11. Veredito final

- **A Sprint 2 está concluída?** Não, com as evidências atuais. Os entregáveis mecânicos existem e conferem; as pendências são de decisão, sincronização e validade.
- **Requisitos que impedem a conclusão:** R12 (CFR (b) com a versão final), R25 (independência da rotulagem, não comprovada), R31 (validação sem vazamento) e, em decisão do professor, R30 e R16. R29/R33 (artigo defasado) e R21 (qualidade dos dados) precisam ser fechados.
- **Os resultados atuais podem ser usados com confiança?** **Sim** para DF, LT (a)/(b), CFR (a), recuperação, censura e classificações por métrica (com a correção de S2-007). **Não ainda** para CFR (b), `dora_c2` e qualquer inferência que dependa do consenso de `corretiva`: a v8 subestima e a referência não é demonstravelmente independente.
- **O que corrigir primeiro:** 1.1 (decisões do professor) → 1.2 (versão final e recálculo) → 3.1 (validação disjunta) → 4.1 (artigo).
- **Refazer a coleta completa?** Não. Recalcular `metrics.csv` a partir do cache bruto preservado; rotular uma amostra nova de ~20 repositórios.
- **Não comprovável com o que foi fornecido:** independência da rotulagem; execução verde do CI; estado de Issues e do Projects; execução limpa do README; dados dos 201 repositórios sem cache local; totais da Search API (60.143/57.465).
- **Repetir após as correções:** recálculo independente sobre o maior número possível de repositórios; kappa/consenso/P-R-F1 a partir dos arquivos originais; coerência número a número entre artigo, README, dicionário e CSV; `pytest --cov` e CI.
