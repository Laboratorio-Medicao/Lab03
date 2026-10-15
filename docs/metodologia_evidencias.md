# Metodologia (Issue #31): mapa de evidências, lacunas e contradições

Rascunho da seção em `artigo/metodologia.tex`. Aqui estão, por requisito do enunciado, a evidência no
repositório e o que falta. Nada foi recalculado nos dados: números vêm dos artefatos listados ou de
contagem direta neles (kappa recalculado de `labels_*.csv` com statsmodels, sem gravar arquivos).

## 1. Requisito → evidência

| Requisito (enunciado) | Evidência | Estado |
|---|---|---|
| RQs e desenho (E§5, E§8) | enunciado; `artigo/introducao.tex` (hipóteses H1–H7) | Escrito; análises RQ01–RQ07 são da S03, não executadas |
| Seleção e funil (E§7) | `outputs/funil.md/.csv`, `config.yaml` | Sustentado: 2677 → 1458 → 420 → 300 |
| Critérios mín. 5 releases / 50 runs (E§3) | `config.yaml` (`min_releases`, `min_runs_validos`) | Do enunciado; interpretação de "run válido" é do grupo (L04) |
| Janela (E§3) | `config.yaml`, `sorteio.json` | **Provisória (L01), pendente do professor** |
| Definições operacionais (E§3, E§5) | `README.md`, `metricas/*.py`, `DICIONARIO_DE_DADOS.md` | Sustentado |
| Coleta, cache, rate limit (E§4, E§7) | `pipeline/http_client.py`, `outputs/execucao.log` | Sustentado; cache não versionado |
| Amostra-ouro, semente fixa (E§6.1) | `sorteio.json` (semente 42, 60×5, sha256 da lista) | Sustentado |
| Rotulagem independente (E§6.2) | `labels_*.csv`, `LEIAME.md`, `rascunho/revisao_*.csv` | **Parcial**: assistida por sugestões compartilhadas |
| Kappa de Fleiss, 3 dimensões (E§6.3) | `concordancia.csv`, recalculado | Sustentado: 0,814 / 0,834 / 0,428 |
| Consenso e desempate (E§6.4) | `PROTOCOLO_CONSENSO.md`, `consenso.csv` | Sustentado; 0 reuniões, 0 pendentes |
| P/R/F1 por versão (E§6.5) | `avaliacao_heuristica.csv`, `docs/refino_heuristica.md` | Sustentado; F1 máx. 0,599 (v9, rodada oficial; 0,680 na rodada anterior) |
| F1 ≥ 0,70 / validação (E§5, E§6) | idem | **Não atendido**: não validada |
| Dicionário de dados (E§7) | `DICIONARIO_DE_DADOS.md/.csv`, `tests/test_dicionario.py` | Sustentado |
| Censura e ausentes (E§3, E§11) | `resultados.csv`, `data_quality.md` | Parcial (ver contradição 2) |

## 2. Contradições e pontos frágeis encontrados

1. **`avaliacao_heuristica.md` desatualizado em relação a `docs/refino_heuristica.md`.** O primeiro (gerado)
   diz "Versão escolhida: v9" e "atualize `HEURISTIC_VERSION`"; o segundo define v8 principal, v4 sensibilidade,
   v9 fora do dataset e status **não validada**. O artigo segue o segundo.
2. **`outputs/data_quality.md` é de uma amostra de 100 repositórios** (`resultados.csv` já tem 300) e
   tem CFR (b) e dicionário em `N/A`. Os números de censura/404 do artigo foram contados direto em
   `resultados.csv` (300); precisam ser regenerados por `scripts.data_quality` para citar o relatório.
2b. **Invariante de lead time falha em 1 repositório** (regeneração do `data_quality` em diretório
   temporário): `agentclientprotocol/agent-client-protocol`, 73 ≠ 74. Causa provável e limites da
   investigação em `docs/auditoria_metodologia.md` §7.
3. **Independência da rotulagem.** `rascunho/revisao_marcosffp.csv` e `revisao_ALuiz19.csv` mostram 0
   sugestões alteradas em `corretiva` (292 aceitas, 8 sem sugestão). Esses arquivos estão fora do Git
   (`rascunho/`), então a afirmação não é reproduzível por terceiros. Não há arquivo equivalente para o
   avaliador GuilhermeVieira05.
4. **Alegação não reproduzível:** `docs/refino_heuristica.md` cita F1 da v9 de ≈ 0,59 a ≈ 0,74 em uma
   divisão por repositório; nenhum script ou arquivo no repositório gera isso. **Não foi usada no artigo.**
5. **Versões v8/v9 não estão no histórico git** (existem só na árvore de trabalho; o `git log` de
   `metricas/heuristica.py` tem apenas v1 e v2–v7). A cronologia "antes/depois da análise de erros" para
   v8/v9 vem do texto de `docs/refino_heuristica.md`, não do histórico.
6. **Janela:** `execucao.log` mostra a coleta em 2026-10-11, depois do fim provisório da janela
   (2026-10-02); consistente, mas dependente de L01.
7. **Possível truncamento na busca:** em `funil.md`, a fatia `stars:1282..1312` tem `total_count` = 1000, igual ao teto da Search API, e consta como não saturada. Pode ter perdido candidatos; não verificado (exigiria API).
8. **Nomes de arquivo de rótulos** divergem entre documentos (`refinamento_s02.md`, divergência 5): fora do escopo.

## 3. Depende do professor (não resolvido aqui)

- Datas oficiais da janela de 12 meses (L01).
- Procedimento quando nenhuma versão atinge F1 ≥ 0,70; aceitabilidade do CFR (b) exploratório; amostra
  independente para validação final.
- Se intervalos de confiança ou outro teste são esperados para P/R/F1 e kappa (não há procedimento definido).
- Corte da amostra quando mais de 300 passam nos filtros (L17) e definição de "popular" (L03): hoje decisão do grupo.
- Idioma e limite de páginas do artigo (L19).

## 4. Decisões provisórias do grupo (marcadas `\prov` no `.tex`)

Piso de 1000 estrelas, exclusão de forks/arquivados, run válido, release contada, release sem commits novos
e commit posterior à release excluídos, CFR (b) com "qualquer release em (R, R+7d]", mediana de
recuperação só de episódios concluídos, v8/v4/v9 como papéis exploratórios.

## 5. Verificações

Fontes lidas: enunciado, `fonte_vdd.md` (lacunas e S02-0xx), `docs/*`, README, `config.yaml`, funil,
data_quality, CSVs de avaliação/consenso/concordância, `sorteio.json`, `LEIAME`, `PROTOCOLO_CONSENSO`,
`rotular.py` e revisões locais. Recalculado: kappa (bate com `concordancia.csv`), contagens de
`consenso.csv` e agregados de `resultados.csv`. Não compilei o `.tex` (sem LaTeX verificado). Sem API,
coleta, commit ou push; rótulos, consenso e datasets não foram modificados.
