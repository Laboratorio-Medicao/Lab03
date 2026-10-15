# Auditoria Sprint S02 — Lab03

> Data da auditoria: 2026-10-14  
> Branch auditada: `main` (commit `b70c68b`)  
> Enunciado de referência: `enunciado/03 - Mineração de Métricas DORA.md`

---

## 1. Resumo Executivo

A Sprint S02 tinha como objetivo expandir a amostra para ≥ 300 repositórios, calcular todas as variantes das métricas DORA, produzir dicionário de dados e realizar a rotulagem manual da amostra-ouro. Todos os quatro artefatos principais foram entregues e estão no repositório. A suíte de testes passa com 666 testes e cobertura de 99 % no módulo `metricas/`. O principal ponto em aberto é a heurística de release corretiva, cujo melhor F1 (0,680, versão v9) ficou abaixo do limiar de 0,70 exigido pelo enunciado.

| Requisito S02 | Status |
|---|---|
| ≥ 300 repositórios na amostra final | ✓ 300 repos em `outputs/repos_final.csv` |
| Dataset consolidado (`consolidate_dataset.py`) | ✓ implementado, 10 testes passando |
| Métricas em variantes C1/C2/C3 + CFR(b) (`metrics.csv`) | ✓ 300 repos × 49 colunas |
| Dicionário de dados (`.md` + `.csv` + teste) | ✓ todas as colunas documentadas |
| Rotulagem manual (60 repos × 5 releases) | ✓ arquivo completo |
| Kappa de Fleiss calculado | ✓ (ver artigo — corretiva κ=0,428) |
| Heurística F1 ≥ 0,70 | ✗ melhor F1=0,680 (v9) |
| Artigo — seção de Metodologia | ✓ rascunho completo em `artigo/metodologia.tex` |
| Testes unitários das métricas | ✓ 666 passed, 99 % cov |

---

## 2. Issue #19 — Dataset Final (`consolidate_dataset.py` + `repos_final.csv`)

### Artefatos
- `pipeline/consolidate_dataset.py`
- `outputs/repos_final.csv` (300 linhas + cabeçalho)
- `outputs/resultados.csv` (300 linhas + cabeçalho)
- `tests/test_consolidate_dataset.py` (10 testes)

### Verificação quantitativa

| Arquivo | Repositórios | Status |
|---|---|---|
| `resultados.csv` | 300 | todos `status=concluido` |
| `repos_final.csv` | 300 | sem colunas `status`/`erro` |

O funil documentado em `artigo/metodologia.tex`:

| Etapa | Entram | Saem | Restam |
|---|---|---|---|
| Candidatos avaliados | 2677 | — | 2677 |
| Possui Actions | 2677 | 1219 | 1458 |
| ≥ 5 releases | 1458 | 1038 | 420 |
| ≥ 50 runs válidos | 420 | 120 | 300 |

### Conformidade com o enunciado
- ✓ Critério mínimo de inclusão: 5 releases + 50 workflow runs (E§3)
- ✓ Funil de seleção documentado (E§7)
- ✓ Apenas releases não-rascunho e não-pré-release na definição principal (E§3)
- ✓ Cache e retomada funcionam (pipeline rodou em três sessões por expiração de token)
- ◑ Amostra não é aleatória: primeiros 300 em ordem `full_name`. O enunciado não define aleatorização da amostra final; risco documentado como lacuna L17 na metodologia

### Testes
Todos os 10 testes de `test_consolidate_dataset.py` passam, cobrindo: filtro por status, preservação de ordem, exclusão de colunas internas, soma de censurados e de 404s, campo vazio sem quebra.

---

## 3. Issue #20 — Dicionário de Dados

### Artefatos
- `DICIONARIO_DE_DADOS.csv`
- `DICIONARIO_DE_DADOS.md`
- `tests/test_dicionario.py` (8 testes)

### Verificação
Os testes `test_todas_colunas_documentadas` e `test_labels_avaliadores_documentadas` verificam automaticamente que toda coluna presente nos CSVs de saída tem entrada no dicionário. Os 8 testes passam, cobrindo:

| CSV verificado | Status |
|---|---|
| `outputs/resultados.csv` | ✓ todas colunas documentadas |
| `outputs/repos_final.csv` | ✓ |
| `outputs/funil.csv` | ✓ |
| `data/amostra_ouro/amostra_ouro.csv` | ✓ |
| `data/metrics.csv` (49 colunas) | ✓ |
| `data/amostra_ouro/labels_*.csv` | ✓ |

### Conformidade com o enunciado
- ✓ Cada coluna documentada com nome, tipo, unidade e fórmula/origem (E§7)
- ✓ Teste automatizado garante cobertura contínua ao adicionar novas colunas

---

## 4. Issue #25 — Rotulagem Manual (`labels_GuilhermeVieira05.csv`)

### Arquivo
`data/amostra_ouro/labels_GuilhermeVieira05.csv`

### Completude

| Campo | Linhas preenchidas | Esperado | Status |
|---|---|---|---|
| `tipo_projeto` | 60 | 60 (1 por repo) | ✓ |
| `releases_sao_entregas_reais` | 60 | 60 (1 por repo) | ✓ |
| `corretiva` | 300 | 300 (5 por repo) | ✓ |

Os demais avaliadores também têm seus arquivos: `labels_ALuiz19.csv` e `labels_marcosffp.csv`.

### Protocolo
Sorteio documentado em `data/amostra_ouro/sorteio.json`: semente 42, 60 repositórios, 5 releases por repositório, SHA-256 do resultado registrado. Protocolo de consenso em `data/amostra_ouro/PROTOCOLO_CONSENSO.md`.

### Concordância (Kappa de Fleiss)
Calculado e reportado em `artigo/metodologia.tex`:

| Dimensão | Itens | κ | Interpretação |
|---|---|---|---|
| Tipo do projeto | 60 | 0,814 | quase perfeita |
| Releases são entregas reais | 60 | 0,834 | quase perfeita |
| Release corretiva | 300 | 0,428 | moderada |

O kappa moderado em `corretiva` é um achado legítimo (critério ambíguo), conforme indicado no enunciado E§6. O artigo discute limitação de independência por uso de sugestões assistidas.

### Conformidade com o enunciado
- ✓ 60 repos sorteados com semente fixa e documentada (E§6.1)
- ✓ Três dimensões rotuladas: tipo, entrega, corretiva (E§6.2)
- ✓ Kappa de Fleiss calculado (E§6.3)
- ✓ Consenso produzido (`consenso.csv`) com protocolo documentado (E§6.4)
- ◑ Rotulagem assistida por sugestões geradas automaticamente — reduz independência (reconhecido no artigo)

---

## 5. Issue #21 — Métricas em Variantes (`scripts/compute_metrics.py` + `data/metrics.csv`)

### Artefatos
- `scripts/compute_metrics.py`
- `data/metrics.csv` (300 repos × 49 colunas)
- `tests/test_compute_metrics.py` (13 testes)

### Colunas adicionais em `metrics.csv` (além das 32 de `resultados.csv`)

| Coluna | Descrição |
|---|---|
| `cfr_b` | CFR(b) proxy de entrega, heurística v8 |
| `cfr_b_class` | Classificação DORA de CFR(b) |
| `n_releases_avaliadas_cfr_b` | Denominador do CFR(b) |
| `n_releases_censuradas_cfr_b` | Releases nos últimos 7 dias (excluídas) |
| `n_releases_janela` | Releases na janela |
| `n_releases_falha_cfr_b` | Releases consideradas falha |
| `n_releases_mensagens_incompletas_cfr_b` | Releases com compare 404/truncado |
| `heuristic_version` | Versão da heurística usada (v8) |
| `n_releases_deploy_c2` | Releases C2 (incluindo pré-releases) |
| `df_c2` | DF variante C2 |
| `df_c2_class` | Classificação DORA de DF(C2) |
| `n_tags_janela` | Tags na janela |
| `df_c3` | DF variante C3 (tags) |
| `df_c3_class` | Classificação DORA de DF(C3) |
| `dora_c1` | Classificação geral C1 (referência) |
| `dora_c2` | Classificação geral C2 (releases+pré-releases, LT(b), CFR(b)) |
| `dora_c3` | Classificação geral C3 (tags, LT(b), CFR(a)) |

### Distribuição das classificações DORA gerais

| Classe | C1 | C2 | C3 |
|---|---|---|---|
| Elite | 26 | 5 | 29 |
| High | 126 | 133 | 132 |
| Medium | 100 | 115 | 91 |
| Low | 25 | 23 | 25 |
| (indefinido) | 23 | 24 | 23 |

### Heurística de release corretiva

| Versão | Precisão | Recall | F1 | Delineamento |
|---|---|---|---|---|
| v1 | 0,362 | 0,720 | 0,482 | antes dos dados |
| v4 | 0,373 | 0,880 | 0,524 | antes da análise de erros |
| v8 | 0,696 | 0,520 | 0,595 | depois da análise de erros |
| v9 | 0,680 | 0,680 | **0,680** | depois da análise de erros |

**Nenhuma versão atingiu F1 ≥ 0,70** (limiar do enunciado E§6.5). O `metrics.csv` usa v8 como estimativa exploratória do CFR(b).

### Conformidade com o enunciado
- ✓ C1: release, LT(a), CFR(a) — combinação de referência (E§5 RQ07)
- ✓ C2: release+pré-release, LT(b), CFR(b) (E§5 RQ07)
- ✓ C3: tag, LT(b), CFR(a) (E§5 RQ07)
- ✓ Classificação DORA com cortes fixos do enunciado (E§5 RQ07 tabela)
- ✓ CFR(b): janela de 7 dias, censura nos últimos 7 dias (E§5 RQ03b)
- ✗ F1 da heurística < 0,70 — enunciado pede refinamento até atingir o limiar (E§6.5)
- ◑ v8/v9 desenhadas após análise dos erros na mesma amostra → F1 otimista (documentado como ameaça à validade no artigo)

---

## 6. Testes e Cobertura

```
Suíte completa: 666 passed (uv run pytest tests/)
Cobertura de metricas/: 99 % (1 linha faltando em recovery.py:26)

Módulo                 Stmts  Miss  Cover
-----------------------------------------
metricas/__init__.py       0     0   100%
metricas/cfr.py           13     0   100%
metricas/cfr_entrega.py   25     0   100%
metricas/dora.py          81     0   100%
metricas/heuristica.py   101     0   100%
metricas/lead_time.py     50     0   100%
metricas/recovery.py      32     1    97%
-----------------------------------------
TOTAL                    302     1    99%
```

Cobertura do enunciado: **≥ 80 % exigido (E§7) — 99 % obtido.**

---

## 7. Artigo — Seção de Metodologia (`artigo/metodologia.tex`)

A seção de metodologia está escrita e cobre:
- Questões de pesquisa e desenho do estudo
- Seleção e funil (com tabela de números reais)
- Janela temporal (provisória, pendente confirmação do professor)
- Definições operacionais de todas as métricas
- Procedimento de coleta, cache, limitações da API
- Rotulagem manual e sugestões assistidas
- Concordância entre avaliadores (kappa de Fleiss)
- Heurística: versões, F1 e status de validação
- Dados ausentes, censura e ameaças à validade

Itens marcados como `\pend{...}` (pendentes do professor):
1. Janela temporal oficial (datas declaradas como provisórias no `config.yaml`)
2. Se a fatia `stars:1282..1312` com 1000 resultados foi truncada
3. Se rotulagem assistida é metodologicamente aceitável para validação

---

## 8. Gaps e Pendências para S03

### Bloqueios técnicos
| Item | Detalhe |
|---|---|
| Heurística F1 < 0,70 | Melhor resultado: v9 com F1=0,680. Enunciado pede refinamento. A v9 usa release notes (campo `body`) que não estão no cache atual. |
| Janela temporal | Datas provisórias em `config.yaml`; se o professor alterar, coleta e sorteio precisam ser refeitos |

### Análises que pertencem a S03 (não estão em S02)
- Análise estatística das RQ01–RQ04 (mediana, IQR, classificação DORA)
- Correlação de Spearman entre DF e CFR — RQ05
- Kruskal-Wallis / Mann-Whitney por subgrupos — RQ06
- Correção de Holm para comparações múltiplas — RQ06
- Análise de sensibilidade C1 × C2 × C3 (% mudança de classe, kappa de Cohen ponderado) — RQ07
- RQ08 bônus (rework rate ou evolução temporal)

---

## 9. Conformidade Geral com o Enunciado (S02)

| Requisito | Referência | Status |
|---|---|---|
| Amostra ≥ 300 repositórios | E§10 S02 | ✓ |
| Métricas em todas as variantes obrigatórias | E§5 RQ07 | ✓ |
| Dataset em CSV com dicionário de dados | E§10 S02 | ✓ |
| Dicionário de dados com nome, tipo, unidade, fórmula | E§7 | ✓ |
| Amostra-ouro: 60 repos sorteados, semente documentada | E§6.1 | ✓ |
| Rotulagem independente por 3 avaliadores | E§6.2 | ◑ (sugestões reduzem independência) |
| Kappa de Fleiss calculado | E§6.3 | ✓ |
| Consenso com protocolo documentado | E§6.4 | ✓ |
| Heurística validada com F1 ≥ 0,70 | E§6.5 | ✗ (melhor F1=0,680) |
| Testes com cobertura ≥ 80 % do módulo `metricas/` | E§7 | ✓ (99 %) |
| CI do grupo rodando os testes | E§7 | ✓ (.github/workflows/testes.yml) |
| Artigo — seção de metodologia | E§10 S02 | ✓ rascunho completo |
| Issues com assignee e referência a número | E§10 | ✓ (verificado nos commits) |
