# FONTE DA VERDADE — LAB03 MINERAÇÃO DE MÉTRICAS DORA

> **Disciplina:** Laboratório de Experimentação de Software — Eng. de Software, PUC Minas (6º período, noite) · **Professor:** Danilo Maia
> **Valor:** 20 pontos (+1 bônus pela RQ 08) · **Grupo:** trio (3 integrantes — o material fala em "cada um dos três integrantes")
> **Como usar este documento:** ele é um manual de execução. Leia a §0 (legenda), depois siga as sprints na ordem. Nada aqui substitui o enunciado do professor; quando houver conflito, o enunciado vence.

---

# 0. LEGENDA, CÓDIGOS DE ORIGEM E REGRAS DE LEITURA

### 0.1 As quatro categorias (nunca misturar)

| Tag | Significado |
|---|---|
| **[OBRIGATÓRIO — PROFESSOR]** | Está escrito no enunciado. Não cumprir custa nota. |
| **[DERIVADO — NECESSÁRIO PARA CUMPRIR]** | Não está escrito assim, mas é consequência inevitável de um requisito explícito. Tratar como obrigatório. |
| **[RECOMENDAÇÃO]** | Boa prática. Não foi exigida. Inclui as "divisões sugeridas" do professor, que ele próprio chama de *sugeridas*. |
| **[DIFERENCIAL]** | Extra para elevar a qualidade. Só depois de 100% do obrigatório. |

### 0.2 Marcadores de alerta

| Marcador | Uso |
|---|---|
| ⚠️ **NÃO DEFINIDO NO MATERIAL — NÃO ASSUMIR.** | Lacuna do enunciado. Está catalogada na §0.5 (código `Lxx`). O grupo deve **perguntar ao professor** ou, se não houver resposta, **escolher uma regra, documentá-la no README/artigo e aplicá-la de forma consistente**. |
| 🔎 **INFERÊNCIA NECESSÁRIA** | Interpretação que fiz porque o texto admite mais de uma leitura. Explico o porquê. |
| 💡 **RECOMENDAÇÃO** | Idem tag [RECOMENDAÇÃO]. |
| ⭐ **DIFERENCIAL** | Idem tag [DIFERENCIAL]. |

### 0.3 Códigos de origem (como cada item foi rastreado)

| Código | Fonte | Papel |
|---|---|---|
| **E§n** | `03 - Mineração de Métricas DORA.md` (enunciado do LAB03), seção *n* (1 Contexto · 2 Visão geral · 3 Definições operacionais · 4 Coleta/endpoints · 5 RQs · 6 Validação manual · 7 Engenharia · 8 Artigo · 9 Replicação · 10 Processo/sprints/avaliação · 11 FAQ · 12 Glossário/referências) | **Fonte primária e autoridade máxima** |
| **A5-sNNN** | `Aula 5 (4).pdf` — "Product, Process and Resource Attributes", slide *NNN*/122 (a parte DORA está nos slides 104–113) | Apoio conceitual. Não define requisitos do LAB03. |
| **TF-sNN** | `trab-final-pdf (4).pdf` — "Análise de Dados Aplicada à Experimentação em ES — Trabalho Final — Grupo 1" (98 slides) | Apoio geral de estatística/visualização. **Não é enunciado do LAB03.** |

### 0.4 Auditoria dos materiais (o que cada arquivo realmente contém)

| Arquivo | O que é | Uso nesta Fonte da Verdade |
|---|---|---|
| Enunciado `.md` | Documento completo do LAB03 (12 seções) | 100% dos requisitos |
| Aula 5 (122 slides) | Aula sobre atributos de produto/processo/recurso; slides 104–113 trazem DORA: fórmulas simples, faixas **qualitativas** (Elite/Alto/Médio/Baixo) e a tese "velocidade e estabilidade não são opostas" | Contexto para Introdução/Discussão. **Divergências com o enunciado** abaixo. |
| Trabalho Final Grupo 1 (98 slides) | Material de outra disciplina/atividade sobre etapas de experimentação, ferramentas de análise, estatística descritiva, testes, regressão e tipos de gráfico | Só como referência de boas práticas (mediana/IQR, tamanho de efeito, correção de múltiplos testes, gráficos). Tudo que sair daí é [RECOMENDAÇÃO]. |

**Divergências detectadas entre apoio e enunciado (o enunciado vence):**

| Tema | Aula 5 | Enunciado LAB03 | Decisão |
|---|---|---|---|
| Tempo de recuperação | **MTTR = média** dos tempos (A5-s112) | Mediana dos episódios; "tempo de recuperação" (E§1, E§5 RQ04) | Usar **mediana** |
| Faixas DORA | Qualitativas ("minutos a horas", "semanal a mensal"…) (A5-s113) | **Cortes numéricos fixos** (E§5 RQ07) | Usar a **tabela fixa do enunciado** |
| CFR | `N_falhas/N_deploys` (A5-s111) | Duas variantes obrigatórias (a) CI e (b) entrega | Seguir o enunciado |

### 0.5 Registro de lacunas (⚠️ NÃO DEFINIDO NO MATERIAL — NÃO ASSUMIR)

Estas são as decisões que o enunciado **não** toma. Cada uma deve virar uma linha na seção "Decisões do grupo" do README (§13) e, quando relevante, na Metodologia do artigo. **Ação padrão:** perguntar ao professor; sem resposta, decidir, documentar e testar.

| ID | Lacuna | Onde pega | Resolução sugerida (marcada como 💡) |
|---|---|---|---|
| L01 | **Datas exatas da janela de 12 meses.** O professor as fixa "na abertura do Lab03S01" (E§3) — não estão no material fornecido | Toda a coleta | Obter com o professor; gravar em `config.yaml`. Nunca "hardcodar". |
| L02 | **Datas/prazos** de S01, S02, S03 e entrega final ("conforme cronograma da disciplina", E§10) | Roadmap | Usar "Etapa 1, 2…" (§21) até receber as datas. |
| L03 | **O que é "popular"**: limite de estrelas, linguagem, exclusão de forks/arquivados/templates, mínimo de contribuidores. `stars:>1000` aparece só como *exemplo* de endpoint (E§4) | Seleção | 💡 Definir e documentar (ex.: `stars:>1000`, não-fork, não-arquivado). |
| L04 | **O que são "workflow runs válidos"** para o mínimo de 50 (E§3) | Funil | 🔎 Interpretação mais coerente: runs no default branch, `event=push`, criados na janela **e** com `conclusion` ∈ {success, failure, timed_out, startup_failure}. Justificativa: E§3 diz que os demais "não entram em nenhum cálculo". |
| L05 | **Quais releases contam** para o mínimo de 5 | Funil | 🔎 Releases com `draft=false` **e** `prerelease=false` e `published_at` na janela, pois essa é a definição principal de deploy (E§3). |
| L06 | Se releases devem ser filtradas pelo default branch (`target_commitish`) — E§3 diz "considere apenas o default branch" sem dizer a quais dados se aplica | Releases, compare | 💡 Aplicar o default branch aos **workflow runs** (explícito em E§3) e documentar que releases/compare não foram filtrados por branch (ameaça de construto). |
| L07 | **Lead time — casos não definidos:** commit com data **posterior** à release (valor negativo); commits de merge; release **sem commits novos** (E§7 manda testar, mas não diz o resultado) | RQ02 | 💡 Release sem commits novos → excluída do cálculo de lead time e contada; negativos → sinalizar e registrar contagem. |
| L08 | **CFR(b):** "seguida em até 7 dias por release corretiva" — só a **próxima** release ou **qualquer** release no intervalo? Pré-release pode ser corretiva? | RQ03b | 🔎 Qualquer release de deploy (definição principal) em (R, R+7d] que seja corretiva. Documentar e testar. |
| L09 | **RQ04:** (i) como o episódio **censurado** entra na mediana; (ii) run inicial com falha **sem sucesso anterior**; (iii) repositório **sem nenhum episódio**; (iv) qual campo ordena os runs | RQ04 | 💡 Mediana dos episódios **concluídos** + proporção de censurados reportada; sensibilidade opcional usando o fim da janela como limite inferior (⭐). Ordenar por `run_started_at`. |
| L10 | **Classificação geral quando uma métrica é indefinida** (sem episódios, CFR(b) sem releases avaliáveis) | RQ07, classificação | 💡 Documentar regra (ex.: classificar só com as métricas disponíveis e sinalizar, ou excluir do RQ07). |
| L11 | **Conversão de "≥ 1 por mês"** (deployment frequency) para releases/semana | Classificação DF | 🔎 1 mês ≈ 52,14/12 ≈ 4,345 semanas ⇒ 1 por mês ≈ **0,230 release/semana**. Documentar. |
| L12 | **RQ06:** o que são "as quatro métricas" dado que RQ02 e RQ03 têm duas variantes; tamanho mínimo de subgrupo; linguagens com muitos níveis; tamanho da família de testes para Holm | RQ06 | 💡 Rodar as variantes de referência (C1: LT(a), CFR(a)) como as "quatro métricas"; agrupar linguagens raras em "Outras"; Holm sobre **todos** os testes realmente executados. |
| L13 | **RQ07:** qual definição de tempo de recuperação em cada combinação (a tabela de exemplo só varia unidade de deploy, lead time e CFR); as combinações C1–C3 são *exemplo* | RQ07 | 🔎 Recuperação inalterada entre combinações. C1–C3 são o ponto de partida recomendado, mas basta haver ≥ 3 combinações. |
| L14 | **Pesos da "parcela individual"** e **limite de WIP** exigido no GitHub Projects | Avaliação | 💡 Definir WIP (ex.: máx. 2 cartões "In progress" por pessoa) e escrever no README do Project. |
| L15 | **Quem escolhe os 30 repositórios** da replicação e como o professor sorteia/avisa o grupo; **prazo** para abrir/responder Issues | Entrega final | Perguntar ao professor. 💡 Se couber ao replicador, sortear com semente fixa. |
| L16 | **Idade do repositório**: qual campo (`created_at`?) e referência temporal (hoje? início da janela?) | RQ06 | 🔎 `created_at` até a data de início ou fim da janela; documentar qual. |
| L17 | Se a amostra de **100** (S01) precisa ser subconjunto da de **≥ 300** (S02) e se os 100 devem *passar* nos filtros | S01/S02 | 💡 Sim para ambos (reaproveita cache e evita retrabalho). |
| L18 | **Fuso horário** e **re-execuções** (`run_attempt`) de workflow runs | Datas | 💡 Trabalhar em UTC (padrão da API) e documentar. |
| L19 | **Idioma do artigo** e número de páginas das referências (E§8 só diz "máx. 10 páginas") | Artigo | Perguntar. Assumir ≤ 10 páginas totais. |
| L20 | **Em qual sprint o bônus RQ08 pontua** | Nota | Perguntar. Sugestão do professor: C faz RQ08 na S03. |
| L21 | **Nº de tentativas máximo do backoff** ("até um limite de tentativas", E§7) | Engenharia | 💡 Ex.: 5–6 tentativas (1 s, 2 s, 4 s, 8 s, 16 s, 32 s). |
| L22 | **Formato exato** dos CSVs finais (quantos arquivos, quais nomes) — E§7 só fala em "CSVs finais" e dicionário | Dataset | Proposta em §6. |

---

# 1. OBJETIVO DO LABORATÓRIO

**Objetivo declarado (E§1):** *minerar* as métricas DORA — calculá-las automaticamente a partir de dados públicos de **repositórios open-source reais que usam CI/CD com GitHub Actions**.

**O problema central (E§1):** o GitHub **não registra** deploys nem falhas em produção. Tudo que o grupo calcula é **proxy**:

| Conceito DORA | Proxy neste laboratório |
|---|---|
| Deploy em produção | Release publicada (`draft=false`) |
| Commit chegando à produção | `commit.author.date` → `release.published_at` |
| Falha em produção | (a) workflow run com falha; (b) release seguida de release corretiva em ≤ 7 dias |
| Recuperação | Do início da 1ª falha até o fim do próximo run bem-sucedido do mesmo workflow |

**A pergunta que o laboratório quer que o grupo responda não é só "qual é o valor?" mas também "o quanto podemos confiar nele?"** (E§1). Por isso há **duas camadas de validação obrigatórias**:

1. **Validação manual** (amostra-ouro de 60 repositórios, E§6) — compara critérios automáticos com julgamento humano.
2. **Análise de sensibilidade** (RQ07) — mede o quanto a classificação DORA muda quando a definição muda.

**Resultado final:** um **pipeline reprodutível** (executável por outro grupo só com o README), um **dataset** com dicionário, **análises** das RQ01–RQ07 (+ bônus RQ08), um **artigo SBC ≤ 10 páginas** escrito aos poucos, e uma **replicação cruzada** do pipeline de outro grupo.

**Leitura recomendada pelo professor antes de começar (≈ 20 min, E§1):** [DORA four keys](https://dora.dev/guides/dora-metrics-four-keys/) e [DORA Quick Check](https://dora.dev/quickcheck/). Marcar como [RECOMENDAÇÃO — PROFESSOR].

---

# 2. FONTE E REGRAS DE AUTORIDADE

1. **Autoridade máxima:** E§1–E§12 (o enunciado).
2. **Apoio:** A5 e TF. Servem para entender e para boas práticas, **jamais** para alterar uma definição do enunciado (ver divergências na §0.4).
3. **O que não está no material:** ⚠️ NÃO DEFINIDO NO MATERIAL — NÃO ASSUMIR. Vai para a tabela de lacunas (§0.5).
4. **Definições operacionais são comuns a toda a turma** (E§3): não podem ser alteradas "por conveniência", senão a replicação cruzada e a comparação entre grupos quebram.
5. **Correção é feita a partir do GitHub Projects** e **commits sem referência ao número da Issue não são considerados** (E§10). Isso rege tudo o que o grupo faz no repositório.
6. **Proibição técnica:** bibliotecas de terceiros que consultem a API do GitHub (ex.: PyGithub) são proibidas. Pandas/SciPy/statsmodels/scikit-learn/pymannkendall são permitidas (E§4, E§10).

---

# 3. VISÃO GERAL DAS SPRINTS

### 3.1 Mapa geral

| Sprint | Objetivo | Entrega principal | Resultado esperado | Pontos | Seção do artigo |
|---|---|---|---|---|---|
| **S01** (Lab03S01) | Provar que o pipeline de coleta funciona e é robusto | Pipeline para **100 repositórios** + testes + CI | Dados brutos em cache; funil gerado; funções de métrica testadas; CI verde | 5 | **Introdução + hipóteses** (uma por RQ, antes de ver dados) |
| **S02** (Lab03S02) | Ter a amostra completa, as métricas e saber o quanto confiar nas heurísticas | **≥ 300 repositórios** pós-filtro; métricas em todas as variantes obrigatórias; CSV + dicionário; validação manual (60 repos) | Dataset final; kappa de Fleiss (3 dimensões); P/R/F1 da heurística corretiva (≥ 0,70 ou refinada e documentada) | 5 | **Metodologia** completa |
| **S03** (Lab03S03) | Responder as RQs | Análise **RQ01–RQ07** (+ RQ08 bônus) em notebooks/scripts reexecutáveis a partir do CSV | Tabelas e gráficos com mediana/IQR e classificação DORA; Spearman; testes com Holm e tamanho de efeito; sensibilidade | 5 | **Resultados + Discussão** |
| **Final** | Provar reprodutibilidade e fechar o artigo | **Replicação** de outro grupo (30 repos) + **resposta às Issues** recebidas + **artigo completo** | Relato de replicação; Issues abertas/respondidas; artigo ≤ 10 p. | 5 (2 + 1 + 2) | **Ameaças à validade + Replicação** + revisão geral |

**Bônus:** RQ08 (+1 ponto). **Desconto:** até **10% da nota da sprint** por uso insuficiente do GitHub Projects (WIP não respeitado, Issues sem Assignee, cartões desatualizados, ausência de evolução semanal) — E§10.

### 3.2 Dependência entre as sprints (fluxo real)

```
        ┌────────────────────────── (artigo escrito aos poucos) ──────────────────────────┐
        │                                                                                  │
S01  ─────────────►  S02  ─────────────────►  S03  ─────────────────►  FINAL
pipeline p/ 100      amostra ≥300 +            RQ01–RQ07 (+RQ08)       replicação (30 repos) do OUTRO grupo
repos + testes+CI    métricas + CSV +          sobre o CSV             + Issues respondidas
+ INTRODUÇÃO         dicionário +              + RESULTADOS/DISCUSSÃO  + AMEAÇAS + REPLICAÇÃO + revisão
(hipóteses ANTES     VALIDAÇÃO MANUAL
dos dados)           + METODOLOGIA
        │                │                          │                        │
        └─ funções de    └─ rótulo "tipo do        └─ RQ07 precisa das      └─ o pipeline do grupo precisa estar
           métrica e       projeto" alimenta RQ06     variantes (pré-release/   100% documentado ANTES de outro grupo
           cache são       └─ heurística validada      tag) coletadas até S02    executá-lo
           reutilizados       sustenta RQ03(b)
```

**Dependências críticas que o enunciado só sugere (⚠️ ler com atenção):**
- A **heurística corretiva** (S02, validada na amostra-ouro) alimenta o **CFR(b)** e o **bônus RQ08** → ambos ficam travados até S02 terminar.
- O **tipo de projeto** só existe para os **60 repositórios rotulados** (E§6: "o tipo do projeto rotulado aqui é usado na RQ 06"). Se o grupo escolher "tipo do projeto" como fator na RQ06, o *n* daquele teste é ≤ 60. 🔎 Isso é uma consequência direta do texto, não uma regra nova.
- Os dados de **pré-release e tags** (para RQ07) precisam ser coletados **antes** de S03, senão a RQ07 trava (a coleta de tags já está prevista na S01, E§10).

---

# 4. MAPA COMPLETO DE REQUISITOS (MATRIZ REQUISITO → EVIDÊNCIA)

**Convenção de obrigatoriedade:** `OBR` = [OBRIGATÓRIO — PROFESSOR] · `DER` = [DERIVADO — NECESSÁRIO PARA CUMPRIR] · `REC` = [RECOMENDAÇÃO] · `DIF` = [DIFERENCIAL].
**Prefixos:** `TRV` = transversal (vale em todas as sprints) · `S01`/`S02`/`S03` · `SF` = entrega final.

### 4.1 Definições operacionais e restrições transversais (TRV)

| ID | Requisito | Origem | Obrig. | Sprint | Artefato | Evidência de conclusão |
|---|---|---|---|---|---|---|
| TRV-001 | Janela de observação de 12 meses, datas fixadas pelo professor na abertura da S01 (⚠️ L01) | E§3 | OBR | S01→Final | `config.yaml` com `window_start`/`window_end` | Config versionada; datas citadas na Metodologia |
| TRV-002 | Só entram releases publicadas e workflow runs **criados dentro da janela** | E§3 | OBR | S01→Final | Filtros no coletor e no cálculo | Teste unitário de filtro + coluna `in_window` |
| TRV-003 | Considerar apenas o **default branch** (`default_branch` da API) | E§3 | OBR | S01→Final | Coletor de runs com `branch=<default_branch>` | Metadado `default_branch` por repo; requests logadas |
| TRV-004 | **Deploy = release publicada** (`draft=false`); pré-releases e tags sem release ficam fora da definição principal e viram **variantes** na RQ07 | E§3 | OBR | S01→S03 | Flag `is_prerelease`, `is_draft` por release; coleta de tags | CSV de releases com flags; teste de filtro |
| TRV-005 | Data de commit = `commit.author.date`; rebase/squash distorcem → registrar como ameaça à validade | E§3 | OBR | S01 (código) / Final (ameaça) | Função de lead time usando `author.date`; parágrafo de ameaça | Teste usando `author.date`; seção de Ameaças |
| TRV-006 | Runs de CI considerados: **default branch + `event=push`** (agendados/manuais fora) | E§3 | OBR | S01→Final | Query `event=push` + filtro defensivo | Teste de filtro com `schedule` ignorado |
| TRV-007 | Classificação de `conclusion`: `success`=sucesso; `failure`,`timed_out`,`startup_failure`=falha; `cancelled`,`skipped`,`neutral`,`action_required`,`stale`, vazio=**ignorar** | E§3 | OBR | S01 | Função `classify_conclusion` | Teste parametrizado cobrindo os 9 valores |
| TRV-008 | Inclusão mínima: **≥ 5 releases** e **≥ 50 workflow runs válidos** na janela; abaixo → descartado e contabilizado no funil | E§3, E§7 | OBR | S01→S02 | Etapa de filtro + funil | `funil.csv` com contagens e motivo |
| TRV-009 | **Censura:** caso sem evento final **não é descartado**; é registrado como censurado e o grupo informa **quantos** | E§3 | OBR | S01→S03 | Campos `censored`/`n_censored` | CSV com coluna de censura; números no artigo |
| TRV-010 | Reportar **mediana e IQR** (não média/desvio-padrão) em **todas** as RQs | E§5 | OBR | S03 | Tabelas/gráficos com mediana (Q1–Q3) | Tabelas do artigo; scripts de análise |
| TRV-011 | Coleta por **script próprio** via REST e/ou GraphQL; **proibido** PyGithub e afins; permitidas pandas/SciPy/statsmodels/sklearn/pymannkendall | E§4, E§10 | OBR | S01→Final | Cliente HTTP próprio (`requests`/`httpx`/`urllib`) | `requirements.txt` sem biblioteca de acesso à API do GitHub |
| TRV-012 | Respeitar tetos: Search ≤ 1.000/consulta (fatiar); `compare` ≤ 250 commits sem paginação (paginar); `actions/runs` ≤ 1.000/consulta (dividir em meses e **conferir** se algum mês atingiu o teto) | E§4 | OBR | S01 | Fatiamento de busca; paginação do compare; divisão mensal de runs | Teste/log mostrando fatiamento e alerta de teto |
| TRV-013 | `actions/workflows` com `total_count=0` ⇒ descartar **antes** de gastar chamadas | E§4 | OBR | S01 | Filtro precoce no funil | Linha "sem Actions" no funil |
| TRV-014 | Paginação seguindo o cabeçalho `Link rel="next"` até o fim | E§4 | OBR | S01 | Helper de paginação | Teste com resposta mockada de 3 páginas |
| TRV-015 | Tabela fixa de classificação DORA (4 métricas × 4 faixas) e regra geral (4/3/2/1, mediana, **arredondada para baixo**) | E§5 RQ07 | OBR | S01 (função)/S03 | Função `classify_*` e `classify_overall` | Testes de fronteira; exemplo (4,3,3,1)→High |

### 4.2 Coleta e engenharia do pipeline

| ID | Requisito | Origem | Obrig. | Sprint | Artefato | Evidência de conclusão |
|---|---|---|---|---|---|---|
| S01-001 | Estrutura de repositório do grupo (código, `tests/`, `.github/workflows/`, `README`, `requirements.txt`, `config.yaml`) | E§7 (implícito) | DER | S01 | Esqueleto do repo | Árvore de diretórios no `main` |
| S01-002 | **Execução com um único comando** a partir do README (ex.: `python -m pipeline --config config.yaml`) | E§7 | OBR | S01 | `__main__`/CLI + README | Execução limpa em máquina nova seguindo só o README |
| S01-003 | Token lido de variável de ambiente (ex.: `GITHUB_TOKEN`) e **nunca commitado** | E§7 | OBR | S01 | Leitura via `os.environ`; `.gitignore` | Varredura do histórico sem token; erro claro se variável ausente |
| S01-004 | Seleção de candidatos pela Search API com **fatiamento** (faixas de estrelas e/ou linguagem) | E§4 | OBR | S01 | `selection.py` | Log de faixas consultadas; nº candidatos > 1.000 se necessário |
| S01-005 | Descartar repos sem Actions (`total_count=0`) | E§4 | OBR | S01 | `selection.py` | Etapa do funil |
| S01-006 | Aplicar mínimos (≥ 5 releases e ≥ 50 runs válidos na janela) | E§3 | OBR | S01 | `selection.py` | Etapas do funil |
| S01-007 | **Funil de seleção gerado automaticamente** (nº por etapa + motivo de descarte), com exemplo "4.000 → 2.900 → 610 → 350" | E§7, E§3 | OBR | S01 (100 repos) / S02 (final) | `outputs/funil.csv` (+ `.md`) | Arquivo gerado pelo pipeline, sem edição manual |
| S01-008 | Coleta de **metadados**: estrelas, linguagem, nº de contribuidores, idade, `default_branch` | E§10 (A), E§5 RQ06, E§4 dica | OBR | S01 | `collect_metadata` | Colunas no CSV; contributors via `per_page=1&anon=true` e `Link` |
| S01-009 | Coleta de **releases** (`draft`, `prerelease`, `published_at`, `tag_name`) | E§4, E§10 | OBR | S01 | `collect_releases` | JSON em cache por repo |
| S01-010 | Coletar também releases **anteriores à janela** (necessárias como "release anterior" da 1ª release da janela) | E§5 RQ02 | DER | S01 | `collect_releases` sem corte de data | Teste: 1ª release da janela tem `previous_release` fora da janela |
| S01-011 | Coleta de **tags** (variante RQ07), usando a data do commit apontado pela tag | E§4, E§10 | OBR | S01 | `collect_tags` | JSON/CSV de tags com data |
| S01-012 | Coleta de **commits entre releases** via `compare/{base}...{head}` **com paginação** (`per_page`/`page`) | E§4, E§10 | OBR | S01 | `collect_commits` | Teste com compare > 250 commits (mock) |
| S01-013 | Em caso de **404** no `compare`: registrar, ignorar a release no lead time e **contar** quantas foram ignoradas | E§11 | OBR | S01 | Tratamento de 404 + contador | Coluna `n_releases_ignored_404`; teste do caminho 404 |
| S01-014 | Coleta de **workflow runs** (`branch`, `event=push`, `created=`) **dividindo a janela por mês** e conferindo teto de 1.000 | E§4, E§10 | OBR | S01 | `collect_runs` | Log por mês com contagem; alerta se = 1.000 |
| S01-015 | **Cache local** (JSON por repo+endpoint ou SQLite) | E§7 | OBR | S01 | `cache/` ou `cache.sqlite` | 2ª execução faz 0 chamadas já cacheadas |
| S01-016 | **Retomada** após interrupção (rate limit, rede, `Ctrl+C`) sem repetir chamadas | E§7 | OBR | S01 | Cache + marcação de progresso | Teste: interromper e reexecutar continua do ponto |
| S01-017 | Ler `X-RateLimit-Remaining`/`X-RateLimit-Reset` e **esperar automaticamente** | E§7, E§4 | OBR | S01 | `RateLimiter` | Log "aguardando até <epoch>"; teste com cabeçalho mockado |
| S01-018 | **Backoff exponencial** (1 s, 2 s, 4 s, 8 s…) para 5xx, com limite de tentativas (⚠️ L21) | E§7 | OBR | S01 | `retry_with_backoff` | Teste com sequência 500,500,200 e verificação de esperas |
| S01-019 | Pipeline base funcionando para **100 repositórios** (seleção+funil, releases, commits entre releases, runs) | E§10 | OBR | S01 | Execução completa | Cache/CSV de 100 repos + log de execução |
| S01-020 | **Testes unitários** (pytest) das funções de cálculo (lead time, CFR, recuperação, classificação DORA) com **fixtures** feitas à mão | E§7, E§10 | OBR | S01 | `tests/test_*.py` | `pytest` verde; fixtures baseadas nos exemplos da E§5 |
| S01-021 | Casos de borda: release sem commits novos; falha nunca recuperada (censurada); repo com 1 release; execuções `cancelled` ignoradas | E§7 | OBR | S01 | Testes dedicados | Nomes de teste/saída `-v` mostrando os 4 casos |
| S01-022 | Cobertura **≥ 80% do módulo de métricas** (`pytest --cov=metricas --cov-report=term-missing`) | E§7 | OBR | S01 | Módulo `metricas` + config de cobertura | Relatório de cobertura ≥ 80% |
| S01-023 | **CI do grupo** rodando os testes no GitHub Actions a cada push (modelo `testes.yml` fornecido) | E§7 | OBR | S01 | `.github/workflows/testes.yml` | Badge/aba Actions com execução verde |
| S01-024 | `requirements.txt` e versão de Python fixados (o modelo de CI usa Python 3.12 e `pip install -r requirements.txt`) | E§7 (modelo CI) | DER | S01 | `requirements.txt` | CI instala sem erro |
| S01-025 | Função de **deployment frequency** (releases / semanas da janela) testada | E§5 RQ01, E§7 | DER | S01 | `metricas.deployment_frequency` | Testes (§12). ⚠️ A divisão sugerida não atribui DF nem classificação a ninguém — decidir dono |
| S01-026 | **Artigo — Introdução com hipótese informal por RQ**, escrita **antes** de ver os dados | E§2, E§8, E§10 | OBR | S01 | `artigo/` (LaTeX SBC) | PDF/`.tex` com 1 hipótese por RQ; commit datado antes das análises |
| S01-027 | Issues por componente, testáveis isoladamente antes de integrar | E§10 | REC (sugestão do professor) → DER p/ GH | S01 | Issues no Projects | Issues #n fechadas por commits |
| S01-028 | Cada integrante é **Assignee de ≥ 1 Issue com artefato de código** commitado (não só escrita) | E§10 | OBR | S01 | Issues + commits | Lista por integrante (§14.5) |
| S01-029 | Commits **referenciando o nº da Issue** (`#N`) | E§10 | OBR | S01→Final | Mensagens de commit | `git log` com `#N` em 100% dos commits relevantes |
| S01-030 | GitHub Projects com WIP respeitado, Assignees, cartões atualizados, **evolução semanal** | E§10 | OBR | S01→Final | Board | Prints/histórico semanal (§14.6) |

### 4.3 Sprint 02 — amostra completa, métricas, validação

| ID | Requisito | Origem | Obrig. | Sprint | Artefato | Evidência |
|---|---|---|---|---|---|---|
| S02-001 | Amostra final **≥ 300 repositórios após os filtros** | E§2, E§10 | OBR | S02 | `repos_final.csv` | `len(df) ≥ 300`; funil final |
| S02-002 | Coleta completa dos 300+ (rodando em segundo plano, com cache/retomada) | E§10, E§11 | OBR | S02 | Cache completo | Cache + log de execução |
| S02-003 | Métricas em **todas as variantes obrigatórias**: DF; lead time (a) e (b); CFR (a) e (b); tempo de recuperação; classificação DORA | E§5, E§10 | OBR | S02 | `metrics.csv` | Colunas preenchidas; testes verdes |
| S02-004 | Dados das **variantes da RQ07** (release+pré-release; tag) disponíveis no dataset | E§5 RQ07 | DER | S02 | Colunas por combinação | Colunas C1/C2/C3 (ou as escolhidas) |
| S02-005 | **Dataset em `.csv`** + **dicionário de dados** (nome, tipo, unidade, fórmula/origem) para **cada coluna dos CSVs finais** | E§7, E§10 | OBR | S02 | `data/*.csv`, `DICIONARIO_DE_DADOS.md/.csv` | Toda coluna tem entrada; verificação automática (⭐ D2) |
| S02-006 | Contar e informar **casos censurados** e **releases ignoradas por 404** | E§3, E§11 | OBR | S02 | Colunas/resumo | Números na Metodologia |
| S02-007 | **Sortear 60 repositórios** da amostra final com **semente fixa documentada no código** (ex.: `df.sample(n=60, random_state=42)`) | E§6 | OBR | S02 | `scripts/sample_gold.py` | Mesmo sorteio ao reexecutar |
| S02-008 | **Rotulagem independente** por cada um dos 3 integrantes, sem consultar os demais e **sem ver a saída da heurística**: (i) tipo do projeto (biblioteca/framework, aplicação/serviço, CLI, outro); (ii) releases = entregas reais (sim/não/incerto); (iii) **5 releases sorteadas** por repo: corretiva (sim/não) | E§6 | OBR | S02 | 3 planilhas/CSVs de rótulos | 3 arquivos commitados, um por integrante |
| S02-009 | Planilha gerada automaticamente com **links diretos** para a página da release | E§6 (dica) | REC (dica do professor) | S02 | Script gerador | Planilha com coluna de URL |
| S02-010 | As 5 releases por repo devem ser **as mesmas** para os três avaliadores (necessário para o kappa) | E§6 (consequência) | DER | S02 | Script gerador com semente | Planilhas com mesmos `release_id` |
| S02-011 | **Kappa de Fleiss** nas 3 dimensões (`aggregate_raters` + `fleiss_kappa`) | E§6 | OBR | S02 | `agreement.py` / notebook | Valores de κ + interpretação Landis & Koch |
| S02-012 | **Consenso** e **protocolo de desempate registrado no repositório** (ex.: maioria simples; 1-1-1 decidido em reunião) | E§6 | OBR | S02 | `PROTOCOLO_CONSENSO.md` + `consenso.csv` | Arquivo versionado |
| S02-013 | **Heurística automática** de release corretiva implementada (CFR b); regra livre (ex.: só *patch* mudou e/ou `revert`/`hotfix`/`fix` nos commits) | E§5 RQ03b | OBR | S02 | `heuristica.py` | Código + testes |
| S02-014 | **Precisão, recall e F1** da heurística vs consenso (`precision_recall_fscore_support`) | E§6 | OBR | S02 | Notebook/script | Tabela P/R/F1 |
| S02-015 | Se **F1 < 0,70**: refinar e reavaliar; **documentar cada versão testada e seu F1** no artigo | E§6 | OBR | S02 | Histórico de versões da heurística | Tabela "versão → F1" no artigo |
| S02-016 | Heurística **validada** contra a amostra rotulada (condição para usar CFR b) | E§5 RQ03b | OBR | S02 | Relatório de validação | F1 final registrado |
| S02-017 | **Artigo — Metodologia completa:** fonte de dados, funil, janela, definições operacionais e variantes, protocolo de validação manual | E§8, E§10 | OBR | S02 | `artigo/` | Seção revisada |
| S02-018 | Cada integrante com sua **Issue de rotulagem** e **arquivo de rótulos commitado** | E§10 | OBR | S02 | 3 Issues + 3 arquivos | Issues fechadas com commits `#N` |
| S02-019 | Congelar a lista final **antes** de sortear a amostra-ouro (senão o sorteio muda) | E§6 (consequência) | DER | S02 | `repos_final.csv` versionado | Hash/commit do arquivo citado |

### 4.4 Sprint 03 — análises

| ID | Requisito | Origem | Obrig. | Sprint | Artefato | Evidência |
|---|---|---|---|---|---|---|
| S03-001 | **RQ01:** DF em releases/semana, mediana e IQR | E§5 | OBR | S03 | `rq01.ipynb/py` | Tabela + gráfico |
| S03-002 | **RQ02:** lead time (a) por release e (b) por commit; mediana e IQR; explicar por que divergem | E§5 | OBR | S03 | `rq02` | Tabela + parágrafo explicativo |
| S03-003 | **RQ03:** CFR (a) CI e (b) entrega; discutir falha de pipeline ≠ falha em produção | E§5 | OBR | S03 | `rq03` | Tabela + discussão |
| S03-004 | **RQ04:** tempo de recuperação em horas; proporção de episódios **censurados por repositório** | E§5 | OBR | S03 | `rq04` | Tabela + proporção de censura |
| S03-005 | **Classificação DORA de referência (C1)** por repositório | E§10 | OBR | S03 | `dora_class.csv` | Distribuição Elite/High/Medium/Low |
| S03-006 | **RQ05:** Spearman entre DF e CFR, **separado** para (a) e (b); reportar ρ, p e n; dispersão (escala log se necessário); discutir tese DORA e "correlação ≠ causalidade" | E§5 | OBR | S03 | `rq05` | ρ,p,n por variante + scatter |
| S03-007 | **RQ06:** ≥ 3 fatores; Kruskal-Wallis (≥ 3 grupos) ou Mann-Whitney (2 grupos) por fator×métrica | E§5 | OBR | S03 | `rq06` | Tabela de testes |
| S03-008 | **RQ06:** correção de **Holm** (`multipletests(method='holm')`) | E§5 | OBR | S03 | `rq06` | p ajustados na tabela |
| S03-009 | **RQ06:** tamanho de efeito — ε² = H/(n−1) (KW); Cliff's δ = 2·U₁/(n₁·n₂) − 1 (2 grupos) | E§5 | OBR | S03 | `rq06` | Colunas ε²/δ + interpretação |
| S03-010 | **RQ07:** ≥ 3 combinações de definições; classificação por combinação; para cada **par**: % que mudou de categoria e **kappa de Cohen ponderado linear** | E§5 | OBR | S03 | `rq07` | Tabela por par + matriz de transição |
| S03-011 | **RQ07:** discutir se as conclusões das RQ01–06 são **robustas** | E§5 | OBR | S03 | Discussão | Parágrafo no artigo |
| S03-012 | **RQ08 (bônus +1):** escolher **uma** opção — rework rate **ou** evolução temporal (Mann-Kendall por trimestre, proporção de repos com tendência significativa em cada direção) | E§5 | OBR p/ ganhar o bônus (opcional) | S03 | `rq08` | Resultado + discussão |
| S03-013 | **Cada análise = notebook ou script próprio, reexecutável a partir do CSV** | E§10 | OBR | S03 | `analysis/` | Reexecução do zero reproduz tabelas |
| S03-014 | Resultados com mediana, IQR e classificação DORA em **tabelas e gráficos** | E§8 | OBR | S03 | Figuras/tabelas | Artefatos no artigo |
| S03-015 | **Artigo — Resultados e Discussão** (hipóteses vs. resultados; o que surpreendeu e por quê) | E§8, E§10 | OBR | S03 | `artigo/` | Seções revisadas |

### 4.5 Entrega final

| ID | Requisito | Origem | Obrig. | Sprint | Artefato | Evidência |
|---|---|---|---|---|---|---|
| SF-001 | **Executar o pipeline do outro grupo usando apenas o README**, sobre **subamostra de 30 repositórios** do dataset original, **sem pedir ajuda** | E§9 | OBR | Final | Log de execução | Log com comandos, versões, erros |
| SF-002 | Se travar, **registrar o travamento como resultado** | E§9 | OBR | Final | Seção de replicação | Descrição no artigo |
| SF-003 | **Comparar** com o CSV original: **diferença relativa por métrica** e **% de repositórios com a mesma classificação DORA** | E§9 | OBR | Final | `replicacao/compara.py` + tabela | Tabela de diferenças |
| SF-004 | **Explicar** as pequenas diferenças (repos continuam recebendo commits; datas de coleta diferem) | E§9 | OBR | Final | Texto | Parágrafo |
| SF-005 | **Abrir Issues no repo do grupo autor** para cada problema (falha de execução, doc faltante, divergência), com **evidências** (comando, erro, esperado × obtido) | E§9 | OBR | Final | Issues no repo do outro grupo | Links das Issues |
| SF-006 | Registrar na seção **"Replicação cruzada"** do artigo: reprodutível? o que impediu/dificultou? | E§8, E§9 | OBR | Final | Seção | Texto revisado |
| SF-007 | **Responder cada Issue recebida** até o prazo final: **corrigir o pipeline ou justificar** a não correção | E§9 | OBR | Final | Comentários/commits `#N` | Todas as Issues com resposta |
| SF-008 | Issues recebidas **adicionadas ao próprio GitHub Projects** | E§9 | OBR | Final | Cartões | Board atualizado |
| SF-009 | **Ameaças à validade** nas 4 categorias (construto, interna, externa, conclusão), cada uma **apoiada** em resultados da validação manual e da sensibilidade | E§8 | OBR | Final | Seção | Texto com números |
| SF-010 | Artigo **completo e revisado**: template SBC, **≤ 10 páginas**, 7 itens (Intro, Metodologia, Resultados, Discussão, Ameaças, Replicação, link) | E§8 | OBR | Final | PDF | PDF ≤ 10 p. |
| SF-011 | **Link do repositório/GitHub Projects** preenchido (o enunciado traz `<preencher>`) | E§8 | DER | Final | Seção | Link funcional |
| SF-012 | Revisão final **pelos três** | E§10 | OBR | Final | Commits de revisão | Histórico |
| SF-013 | Cada integrante Assignee de ≥ 1 Issue **com artefato de código** também na entrega final | E§10 | OBR | Final | Issues + commits | Lista por integrante |
| SF-014 | Pipeline aceita **lista de repositórios como entrada** (para rodar nos 30 do replicador) | E§9 (consequência) | DER | S03→Final | Opção `--repos-file`/config | Execução com 30 repos |
| SF-015 | **README validado** por teste interno ("máquina limpa") **antes** de o outro grupo executar | E§7, E§9 | DER | S03 | Checklist de reprodutibilidade (§13) | Registro do teste |
| SF-016 | O dataset original (CSV) e o dicionário estão **no repositório** para o replicador comparar | E§7, E§9 | DER | S02/S03 | `data/` versionado | Arquivos no `main` |
| SF-017 | O papel do replicador exige **artefato de código** por integrante: ex. A entrega o script/log de execução da replicação | E§10 | DER | Final | `replicacao/` | Commits `#N` do integrante A |

### 4.6 Avaliação e processo

| ID | Requisito | Origem | Obrig. | Sprint | Evidência |
|---|---|---|---|---|---|
| AVL-001 | Pontuação: S01=5, S02=5, S03=5, Final=5 (replicação 2 + Issues 1 + artigo 2); total 20 (+1 bônus) | E§10 | OBR | — | Tabela §3.1 |
| AVL-002 | **Sem commits atribuíveis** a um integrante numa sprint ⇒ **zera a parcela individual** dele naquela sprint | E§10 | OBR | Todas | Commits por autor/sprint |
| AVL-003 | **Desconto de até 10%** da nota da sprint por GitHub Projects mal usado | E§10 | OBR | Todas | Board |
| AVL-004 | **Commits sem `#Issue` não serão considerados** | E§10 | OBR | Todas | `git log` |
| AVL-005 | A correção parte do **GitHub Projects** | E§10 | OBR | Todas | Board organizado |
| AVL-006 | Outras linguagens são aceitas, desde que haja **comando único** no README e **equivalente de testes com cobertura** | E§11 | OBR (condição) | S01 | README + CI |

---

# 5. DEFINIÇÕES OPERACIONAIS — FONTE ÚNICA

> **Regra:** estas definições vêm do enunciado e valem para toda a turma. **Não alterar, não simplificar.** Onde há lacuna, está marcada com ⚠️/🔎.

### 5.0 Regras comuns a todas as métricas

| Item | Regra | Origem |
|---|---|---|
| Janela | 12 meses; datas fixadas pelo professor (⚠️ L01). Releases: `published_at` na janela. Runs: `created_at` na janela | E§3 |
| Branch | Somente `default_branch` (aplicado explicitamente aos runs; ⚠️ L06 para releases/compare) | E§3 |
| Unidade de deploy (principal) | Release com `draft=false`. Excluir `prerelease=true` e tags sem release (viram variantes na RQ07) | E§3 |
| Data de commit | `commit.author.date` | E§3 |
| Data de release | `published_at` (E§3 usa `release.published_at` como exemplo de definição operacional) | E§3 |
| Runs considerados | `event=push`, default branch, na janela | E§3 |
| `conclusion` | Tabela de 3 grupos (sucesso / falha / ignorar) — ver TRV-007 | E§3 |
| Estatística descritiva | **Mediana e IQR**; **nunca** média e desvio-padrão como resultado | E§5 |
| Unidade de análise | O **repositório** (cada métrica produz 1 valor por repo, via mediana quando agrega muitos eventos) | E§5 |
| Censura | Registrar como censurado e **informar quantos**; nunca descartar | E§3 |
| Unidade temporal no dataset | 🔎 **Horas** (E§3 dá "diferença, em horas" como exemplo de definição operacional; RQ04 exige horas). Classificação usa limites em dias/semanas ⇒ converter corretamente (1 dia = 24 h; 1 semana = 168 h; 30 dias = 720 h) | E§3, E§5 |

---

### 5.1 Deployment Frequency (RQ01)

| Campo | Definição |
|---|---|
| **Conceito** | Com que frequência a equipe coloca mudanças em produção (E§1) |
| **Proxy** | Release publicada |
| **Fórmula** | `DF = nº de releases publicadas na janela ÷ nº de semanas da janela` (≈ 52,1 semanas) |
| **Unidade** | releases/semana |
| **Dados** | Lista de releases com `draft`, `prerelease`, `published_at` |
| **Filtros** | `draft=false`, `prerelease=false` (definição principal), `published_at` ∈ janela |
| **Janela** | 12 meses. 🔎 Usar `(window_end − window_start)/7` em vez de fixar 52,1 (o enunciado diz "≈ 52,1"); documentar |
| **Exceções** | Releases fora da janela, drafts, pré-releases |
| **Censura** | Não se aplica |
| **Casos de borda** | 0 releases (não ocorre pós-filtro, mas a função deve lidar); release exatamente no limite da janela (definir inclusivo/exclusivo e testar) |
| **Exemplo do professor** | NÃO HÁ exemplo numérico para DF no enunciado. ⚠️ Fabricar um é [RECOMENDAÇÃO]: 52 releases em 52,14 semanas ≈ 0,997/sem |
| **Teste que deve existir** | `DF(52 releases, 365 dias)` ≈ 0,997; ignora draft e pré-release; ignora fora da janela |
| **Risco de interpretação** | Contar pré-releases/tags na definição principal; dividir por 12 (meses) em vez de semanas; esquecer que "≥ 1 por mês" precisa de conversão (⚠️ L11) |

### 5.2 Lead time for changes (RQ02) — duas variantes obrigatórias

| Campo | Definição |
|---|---|
| **Conceito** | Tempo de uma mudança do commit até estar em produção |
| **Proxy** | `release.published_at − commit.author.date` |
| **Dados** | Releases (incl. **anterior à janela**), commits do `compare/{anterior}...{R}` (com paginação) |
| **Regra de montagem** | Para cada release **R da janela**: comparar com a release **imediatamente anterior** (que pode estar **fora** da janela). **Se não existe release anterior** (primeira release da história do repo), **ignorar R** |
| **(a) Por release** | `LT(R) = data(R) − data(commit mais antigo incluído em R)`. Valor do repo = **mediana** entre suas releases |
| **(b) Por commit** | Cada commit c em R: `LT(c) = data(R) − data(c)`. Valor do repo = **mediana de todos os commits de todas as releases** (não é mediana de medianas) |
| **Unidade** | horas (apresentar dias quando fizer sentido) |
| **Exemplo do professor** | `v1.1` publicada em 15/03; commits em 02/03, 10/03, 14/03. **(a)** 15/03 − 02/03 = **13 dias**. **(b)** 13, 5 e 1 dias; esses 3 valores se somam aos das outras releases antes de calcular a mediana |
| **Casos de borda** | Release sem commits novos (⚠️ L07: resultado não definido; E§7 manda testar); repo com 1 release; `compare` 404 (ignorar e contar — E§11); compare > 250 commits (paginar); commit com data posterior à release (⚠️ L07); a primeira release da janela usa a anterior fora da janela |
| **Teste que deve existir** | Exemplo `v1.1` ⇒ 13 dias (a) e {13,5,1} (b); divergência (a)×(b) com commit "esquecido"; 404; 1 release; sem commits novos |
| **Risco de interpretação** | Usar `committer.date`; tirar mediana das medianas em (b); descartar releases cujo "anterior" está fora da janela (**errado**); esquecer paginação do compare; usar tag em vez de release |
| **Pista do professor** | Um commit antigo "esquecido" numa release explode (a) e quase não afeta (b) — **o artigo deve explicar a divergência** |

### 5.3 Change Failure Rate (RQ03) — duas variantes obrigatórias

#### (a) Proxy de CI

| Campo | Definição |
|---|---|
| **Fórmula** | `CFR(a) = nº runs com falha ÷ (nº falhas + nº sucessos)` |
| **Falha** | `failure`, `timed_out`, `startup_failure` |
| **Sucesso** | `success` |
| **Ignorar** | `cancelled`, `skipped`, `neutral`, `action_required`, `stale`, vazio |
| **Filtros** | default branch, `event=push`, `created_at` na janela; **todos os workflows juntos** (FAQ, E§11) |
| **Unidade** | proporção (0–1) ou % |
| **Casos de borda** | Denominador 0 (todos ignorados); runs `schedule`; runs em outro branch; runs fora da janela |
| **Teste** | Mistura com `cancelled`/`skipped` (não entram); denominador 0 não gera exceção não-tratada |
| **Risco** | Tratar `cancelled` como falha; usar média por workflow em vez do agregado; **confundir falha de pipeline com falha em produção** — o artigo precisa **discutir essa diferença** |

#### (b) Proxy de entrega

| Campo | Definição |
|---|---|
| **Fórmula** | `CFR(b) = nº de releases que falharam ÷ nº de releases avaliadas` |
| **Release R falha** | se for **seguida, em até 7 dias**, por uma **release corretiva** (🔎 L08: qualquer release de deploy em (R, R+7d] que seja corretiva) |
| **Release corretiva** | aquela cujo **objetivo principal é corrigir um defeito recente**. **O grupo define a heurística automática**; exemplos do professor: (i) muda apenas o *patch* de SemVer (`2.3.0 → 2.3.1`); e/ou (ii) há commits com `revert`, `hotfix` ou `fix` na mensagem entre as duas releases |
| **Validação** | A heurística **precisa** ser validada contra a amostra rotulada (E§6) |
| **Censura** | Releases publicadas nos **últimos 7 dias da janela** **não podem ser avaliadas** e **ficam fora do denominador** (e devem ser contadas/informadas) |
| **Exemplo do professor** | `v2.3.0` (10/05) → `v2.3.1` (12/05), só muda *patch* e contém `fix: crash ao abrir arquivo` ⇒ `v2.3.0` **falhou**. `v2.4.0` (01/06) → `v2.5.0` (20/06) ⇒ **não falhou** |
| **Casos de borda** | Exatamente 7 dias ("em até" ⇒ inclui; 🔎 testar 7d0h e 7d1h); release nos últimos 7 dias; só 1 release; tag fora de SemVer (`release-2020-01`); `v` prefix; sufixos `-rc1`; "fix" como substring de "prefix"/"fixture" (💡 usar palavra inteira) |
| **Testes** | Os 2 exemplos acima; fronteira de 7 dias; censura; 1 release; não-SemVer |
| **Risco** | Avaliar releases nos 7 últimos dias; contar a **corretiva** como "falha" por si só (falha é a release **anterior**); heurística não validada |

### 5.4 Tempo de recuperação (RQ04)

| Campo | Definição |
|---|---|
| **Conceito** | Quanto tempo leva para se recuperar de uma falha (antigo MTTR; "failed deployment recovery time" desde 2023, E§1) |
| **Dados** | Workflow runs: `workflow_id`/nome, `conclusion`, `run_started_at`, `updated_at` |
| **Agrupamento** | **Por workflow** (um mesmo workflow no default branch); só depois agrega pela mediana (E§11) |
| **Episódio de falha** | **Começa** na **primeira falha após um sucesso** e **termina** na **próxima execução bem-sucedida do mesmo workflow** |
| **Cálculo** | `recovery = updated_at(run bem-sucedido) − run_started_at(1ª falha do episódio)` |
| **Valor do repositório** | **Mediana** de todos os episódios de todos os workflows |
| **Unidade** | horas |
| **Censura** | Episódio que **nunca termina na janela** é **censurado**; reportar a **proporção de episódios censurados por repositório** (⚠️ L09: como entra na mediana) |
| **Ignorados** | `cancelled`, `skipped`, `neutral`, `action_required`, `stale`, vazio **não entram** (nem encerram nem iniciam episódio) |
| **Exemplo do professor** | Workflow `CI`, `main`: 09:00 success · 10:00 failure (início) · 10:30 failure (mesmo episódio) · 11:15 success (terminou 11:20) ⇒ 11:20 − 10:00 = **1h20** |
| **Casos de borda** | Falha nunca recuperada (**obrigatório testar**); `cancelled` no meio (**obrigatório testar**); falha inicial sem sucesso anterior (⚠️ L09); vários workflows intercalados; repo sem falhas (nenhum episódio) |
| **Teste que deve existir** | Exemplo 1h20 (= 1,333… h); censura; `cancelled` ignorado; 2 workflows independentes |
| **Risco** | Usar `created_at` em vez de `run_started_at`; usar o início do run de sucesso (e não `updated_at`); **misturar workflows** (sucesso do lint encerrando falha do teste); descartar censurados |

### 5.5 Classificação DORA (tabela fixa) — E§5 RQ07

| Métrica | Elite | High | Medium | Low |
|---|---|---|---|---|
| Deployment frequency | ≥ 7 /semana | ≥ 1 e < 7 /semana | ≥ 1 /mês e < 1 /semana | < 1 /mês |
| Lead time (mediana) | < 1 dia | 1 dia a < 1 semana | 1 semana a < 30 dias | ≥ 30 dias |
| CFR | ≤ 15% | > 15% e ≤ 30% | > 30% e ≤ 45% | > 45% |
| Tempo de recuperação (mediana) | < 1 hora | 1 hora a < 1 dia | 1 dia a < 1 semana | ≥ 1 semana |

**Fronteiras exatas (testar todas):** DF `7.0`→Elite, `6.99`→High, `1.0`→High; LT `24 h`→High, `168 h`→Medium, `720 h`→Low; CFR `0.15`→Elite, `0.30`→High, `0.45`→Medium, `0.4501`→Low; Recuperação `1 h`→High, `24 h`→Medium, `168 h`→Low. (⚠️ L11 para o "1 por mês".)

**Classificação geral:** Elite=4, High=3, Medium=2, Low=1 em cada uma das 4 métricas. **Categoria geral = mediana dos 4 valores, arredondada para baixo.**
- Exemplo do professor: (4,3,3,1) ⇒ mediana 3 ⇒ **High**.
- 🔎 Como são 4 valores, a mediana é a média dos dois centrais; o *floor* trata o `.5`. Ex. derivados: (4,3,2,1) ⇒ 2,5 ⇒ **Medium**; (4,4,3,1) ⇒ 3,5 ⇒ **High**; (4,4,1,1) ⇒ 2,5 ⇒ **Medium**.
- ⚠️ L10: métrica indefinida.

> **Atenção:** "tabela de referência adaptada" — **é a tabela da disciplina**, não a oficial do DORA (E§5). Não substituir por faixas do relatório DORA nem pelas qualitativas da Aula 5.

### 5.6 RQ05 — Spearman

| Campo | Definição |
|---|---|
| **Métrica** | ρ de Spearman entre **DF (RQ01)** e **CFR (RQ03)**, **separadamente** para (a) e (b) |
| **Ferramenta** | `scipy.stats.spearmanr`; reportar **ρ, p-valor e n** |
| **Por que Spearman** | Não exige normalidade nem linearidade; usa ranks |
| **Gráfico** | Dispersão, **eixo log se os valores variarem muito** |
| **Discutir** | DORA diz que velocidade e estabilidade **não** são trade-off — os dados confirmam ou contradizem? **Correlação ≠ causalidade** |
| **Borda** | `n` diferente entre (a) e (b) (CFR(b) pode ser indefinido); empates; variável constante ⇒ ρ = NaN |
| **Risco** | Interpretar sinal invertido (CFR alto = pior); concluir causalidade; esquecer de reportar `n` |

### 5.7 RQ06 — comparação entre subgrupos

| Campo | Definição |
|---|---|
| **Fatores (≥ 3)** | escolher entre: linguagem principal; popularidade (quartis de estrelas); nº de contribuidores (quartis); idade (quartis); tipo do projeto (manual, E§6) |
| **Métricas** | RQ01 a RQ04 (⚠️ L12 sobre variantes) |
| **Teste** | **Kruskal-Wallis** (≥ 3 grupos); **Mann-Whitney** se o fator tem **2** grupos |
| **Correção** | **Holm**, `statsmodels…multipletests(method='holm')` — com 3 fatores × 4 métricas são **≥ 12 testes** |
| **Tamanho de efeito** | **KW:** `ε² = H / (n − 1)` (0 a 1). **2 grupos:** `δ = 2·U₁/(n₁·n₂) − 1`, onde `U₁` é a estatística de `mannwhitneyu(x, y)`; |δ| < 0,147 desprezível; < 0,33 pequeno; < 0,474 médio; ≥ 0,474 grande (Romano et al., 2006) |
| **Borda** | Subgrupos muito pequenos; categorias vazias; tipo do projeto só nos 60 rotulados; sinal de δ depende da ordem `(x, y)` |
| **Risco** | Esquecer Holm; reportar só p; aplicar KW a 2 grupos; ε² com `n` errado |

### 5.8 RQ07 — sensibilidade

| Campo | Definição |
|---|---|
| **Combinações** | ≥ **3** (exemplo: C1 = release/LT(a)/CFR(a); C2 = release+pré-release/LT(b)/CFR(b); C3 = tag/LT(b)/CFR(a)) |
| **Passos** | Classificar cada repo em cada combinação (E/H/M/L); para cada **par** (C1×C2, C1×C3, C2×C3): **% que mudou de categoria** e **kappa de Cohen ponderado linear** (`cohen_kappa_score(..., weights='linear')`) |
| **Discussão** | As conclusões das RQ01–06 são **robustas** ou dependem de escolha arbitrária? |
| **Armadilha técnica 🔎** | Passar rótulos **texto** ("Elite", "High"…) ao sklearn ordena **alfabeticamente** e **quebra a ponderação linear**. Codificar como inteiros 1–4 (Low=1…Elite=4) |
| **Borda** | Repos indefinidos em alguma combinação; tags sem data (usar data do commit apontado) |

### 5.9 RQ08 — bônus (+1)

Escolher **uma** opção (E§5):

| Opção | Definição | Discussão obrigatória |
|---|---|---|
| **Rework rate** | `nº de releases corretivas (heurística da RQ03b) ÷ nº total de releases` | Em que difere do CFR(b) |
| **Evolução temporal** | Métricas DORA **por trimestre**; **Mann-Kendall** (`pymannkendall`) por repo; proporção de repos com tendência **significativa** em cada direção | Reportar as duas proporções (melhora/piora) |

---

# 6. DATASET E DICIONÁRIO DE DADOS

> ⚠️ L22: o enunciado exige "CSVs finais" com dicionário, mas **não define quais arquivos nem colunas**. O desenho abaixo é **[DERIVADO]** (cada coluna existe porque alguma definição precisa dela) e a **organização em arquivos é [RECOMENDAÇÃO]**.

### 6.1 Camadas de dados

| Camada | Conteúdo | Observação |
|---|---|---|
| **Cache bruto** | Resposta JSON da API por repo+endpoint (ou SQLite) | Obrigatório (E§7). Não precisa ir ao Git se for enorme; se não for versionado, o README deve dizer como regenerar |
| **CSVs finais** | `repos.csv` (1 linha por repo), `releases.csv`, `episodes.csv`, etc. | Obrigatório pelo menos o CSV por repositório com métricas (E§10) |
| **Rótulos** | 3 arquivos independentes + `consenso.csv` | Obrigatório (E§6, E§10) |
| **Resultados estatísticos** | Tabelas por RQ | Gerados a partir do CSV (E§10) |

### 6.2 Mapa de campos

| Campo | Origem | Tipo | Unidade | Obrig. | Utilização |
|---|---|---|---|---|---|
| `full_name` | Search/`repos` | str | — | DER | Identificador |
| `stars` (`stargazers_count`) | Search/`repos` | int | estrelas | OBR | Popularidade (RQ06, quartis) |
| `language` | Search/`repos` | str | — | OBR | Fator RQ06 |
| `created_at` | `repos` | datetime UTC | — | DER | Idade (⚠️ L16) |
| `age_days` | calculada | float | dias | DER | Fator RQ06 |
| `contributors` | `contributors?per_page=1&anon=true` + `Link` | int | pessoas | OBR | Fator RQ06 (quartis) |
| `default_branch` | `repos` | str | — | OBR | Filtro de runs |
| `workflows_total_count` | `actions/workflows` | int | — | OBR | Funil |
| `n_releases_window` | releases | int | releases | OBR | Funil (≥ 5), DF |
| `n_runs_valid_window` | runs | int | runs | OBR | Funil (≥ 50) |
| `release.tag_name`, `draft`, `prerelease`, `published_at` | `releases` | str/bool/datetime | — | OBR | Deploy, DF, LT, CFR(b) |
| `tag.name`, `tag.commit_sha`, `tag.commit_date` | `tags` + commit | str/datetime | — | OBR | Variante tag (RQ07) |
| `commit.sha`, `commit.author.date`, `commit.message` | `compare` | str/datetime/str | — | OBR | LT(a)(b); heurística |
| `run.id`, `workflow_id`, `name`, `event`, `head_branch`, `conclusion`, `created_at`, `run_started_at`, `updated_at` | `actions/runs` | mix | — | OBR | CFR(a), RQ04 |
| `df_per_week` | calculada | float | releases/sem | OBR | RQ01 |
| `lt_release_median_h` | calculada | float | horas | OBR | RQ02(a) |
| `lt_commit_median_h` | calculada | float | horas | OBR | RQ02(b) |
| `cfr_ci` | calculada | float | proporção | OBR | RQ03(a) |
| `cfr_release` | calculada | float | proporção | OBR | RQ03(b) |
| `n_releases_evaluated_cfr_b`, `n_releases_censored_cfr_b` | calculadas | int | releases | OBR (censura) | Denominador / censura |
| `recovery_median_h` | calculada | float | horas | OBR | RQ04 |
| `n_episodes`, `n_episodes_censored`, `prop_episodes_censored` | calculadas | int/float | episódios/proporção | OBR | RQ04 / censura |
| `n_releases_ignored_404` | calculada | int | releases | OBR | FAQ E§11 |
| `class_df`, `class_lt`, `class_cfr`, `class_rec`, `class_overall` | calculadas | cat | — | OBR | Classificação (RQ07) |
| `class_overall_C1/C2/C3` | calculadas | cat | — | OBR (≥ 3 comb.) | RQ07 |
| `gold_sample` (bool), `seed` | sorteio | bool/int | — | DER | Reprodutibilidade |
| `label_type_{A,B,C}`, `label_real_delivery_{A,B,C}` | rótulos | cat | — | OBR | Fleiss; tipo para RQ06 |
| `label_corrective_{A,B,C}` por `release_id` | rótulos | bool | — | OBR | Fleiss; P/R/F1 |
| `consensus_type`, `consensus_real_delivery`, `consensus_corrective` | consenso | cat/bool | — | OBR | Referência P/R/F1; RQ06 |
| `heuristic_corrective` (+ `heuristic_version`) | heurística | bool/str | — | OBR | P/R/F1 |
| Resultados estatísticos (ρ, p, n; H, p, p_holm, ε²; U, δ; κ ponderado; % mudança) | análises | float | — | OBR | Artigo |

### 6.3 Dicionário de dados (exigência E§7)

**Requisito:** cada coluna de cada CSV final com **nome, tipo, unidade (horas? dias? %?) e fórmula ou origem na API**. Formato 💡 sugerido (`DICIONARIO_DE_DADOS.md` ou `.csv`):

| coluna | arquivo | tipo | unidade | fórmula / origem na API | observações (nulos, censura) |
|---|---|---|---|---|---|
| `df_per_week` | `repos.csv` | float | releases/semana | `n_releases_window / ((window_end − window_start)/7)`; releases de `GET /repos/{o}/{r}/releases` com `draft=false`, `prerelease=false` | — |
| `lt_release_median_h` | `repos.csv` | float | horas | mediana por release de `published_at(R) − min(commit.author.date)` do `compare` | NaN se nenhuma release avaliável |
| `recovery_median_h` | `repos.csv` | float | horas | mediana de `updated_at(sucesso) − run_started_at(1ª falha)` por workflow | Só episódios concluídos (⚠️ L09) |
| … | … | … | … | … | … |

💡 **Verificação automática** (⭐ D2): script que falha se alguma coluna do CSV não estiver no dicionário.

---

# 7. AS QUESTÕES DE PESQUISA (RQs)

### 7.1 Matriz das RQs

| RQ | Pergunta | Dados necessários | Cálculo | Estatística | Gráfico | Resultado esperado | Sprint |
|---|---|---|---|---|---|---|---|
| RQ01 | Qual a frequência de deploys dos repos populares com CI/CD? | releases na janela | DF = releases/semanas | Mediana, IQR | Histograma/boxplot (💡) em escala log | Distribuição de DF + classe DORA | S03 (cálculo em S02) |
| RQ02 | Qual o tempo entre commit e deploy? | releases + commits do compare | LT (a) por release; (b) por commit | Mediana, IQR | Boxplot (a) vs (b), escala log (💡) | Valores por repo + explicação da divergência | S03 |
| RQ03 | Qual a taxa de falha? | runs; releases + heurística | CFR (a) CI; (b) entrega (7 dias) | Mediana, IQR | Boxplot/histograma (💡) | CFR (a) e (b) + discussão pipeline ≠ produção | S03 |
| RQ04 | Qual o tempo de recuperação? | runs por workflow | Episódios; `updated_at − run_started_at` | Mediana, IQR; % censura | Boxplot/ECDF (💡) | Recuperação mediana + proporção censurada | S03 |
| RQ05 | Maior DF ⇒ maior ou menor CFR? | DF (RQ01), CFR (RQ03 a e b) | Spearman por variante | ρ, p, n | **Dispersão** (log se preciso) | ρ por variante + discussão da tese DORA | S03 |
| RQ06 | Que características associam-se a melhor desempenho? | RQ01–04 + fatores (≥ 3) | Grupos por fator; testes | KW/MW + Holm + ε²/δ | 💡 Boxplot por grupo | Tabela de testes com ajuste e efeito | S03 |
| RQ07 | Quanto a classificação depende da definição? | Métricas por combinação (≥ 3) | Classificação por combinação | % mudança; κ ponderado linear por par | 💡 Matriz de transição/heatmap | Quadro de robustez | S03 |
| RQ08 (bônus) | Rework rate **ou** evolução temporal | heurística; métricas trimestrais | Proporção; Mann-Kendall | — / Mann-Kendall | 💡 Barras/linhas | Resultado + discussão | S03 (opcional) |

> Gráficos explicitamente exigidos: **RQ05 → dispersão** (E§5). Os demais são exigidos como "tabelas e gráficos" em geral (E§8); a escolha do tipo é do grupo (💡 apoio: TF-s37–38 histograma, TF-s39–40 boxplot, TF-s41–42 violino, TF-s45–46 dispersão, TF-s49–50 e s59–60 heatmap).

### 7.2 Detalhamento por RQ

#### RQ01 — Frequência de deploys
- **Entrada:** `published_at`, `draft`, `prerelease`, janela.
- **Processamento:** contar releases de deploy na janela ÷ semanas.
- **Saída:** `df_per_week` por repo; mediana e IQR da amostra; classe DORA da métrica.
- **Estatística:** descritiva (mediana/IQR).
- **Visualização:** 💡 histograma ou boxplot, eixo log.
- **Interpretação:** ritmo de publicação de releases dos projetos populares.
- **Limitações:** release ≠ deploy; biblioteca que publica mensalmente não "deploya" nada (E§1); não permite afirmar frequência de **produção**.

#### RQ02 — Lead time
- **Entrada:** releases (inclusive anterior à janela), commits entre releases com `author.date`.
- **Processamento:** (a) `R − commit mais antigo` → mediana por repo; (b) todos os commits de todas as releases → mediana por repo.
- **Saída:** `lt_release_median_h`, `lt_commit_median_h`; releases ignoradas (1ª da história, 404, sem commits).
- **Estatística:** mediana/IQR.
- **Visualização:** 💡 boxplot pareado (a)×(b), escala log.
- **Interpretação:** latência entre escrita da mudança e publicação.
- **Limitações:** `author.date` ≠ momento de integração; rebase/squash distorcem (ameaça de validade obrigatória); (a) sensível a 1 commit antigo.

#### RQ03 — CFR
- **Entrada:** runs (CFR a); releases + heurística + commits (CFR b).
- **Processamento:** (a) falhas ÷ (falhas+sucessos); (b) releases falhas ÷ avaliadas, excluindo os últimos 7 dias.
- **Saída:** `cfr_ci`, `cfr_release`, nº avaliadas e censuradas.
- **Estatística:** mediana/IQR.
- **Visualização:** 💡 boxplot (a)×(b).
- **Interpretação:** (a) estabilidade do pipeline; (b) proxy de instabilidade das entregas.
- **Limitações:** (a) **não é** falha em produção; (b) depende da heurística (F1 da validação manual); não mede incidentes reais.

#### RQ04 — Recuperação
- **Entrada:** runs por workflow, ordenados.
- **Processamento:** episódios por workflow; mediana por repo; proporção de censura.
- **Saída:** `recovery_median_h`, `n_episodes`, `prop_episodes_censored`.
- **Estatística:** mediana/IQR + proporção censurada.
- **Visualização:** 💡 boxplot/ECDF, escala log.
- **Interpretação:** rapidez em voltar a "verde" no CI.
- **Limitações:** recuperação de **CI** ≠ recuperação de produção; censura enviesa se descartada (E§3).

#### RQ05 — Spearman
- **Entrada:** `df_per_week`, `cfr_ci`, `cfr_release`.
- **Processamento:** `spearmanr` por variante, descartando NaN **e registrando n**.
- **Saída:** ρ, p, n por variante.
- **Estatística:** Spearman.
- **Visualização:** dispersão (log se necessário) — **exigida**.
- **Interpretação:** ρ < 0 compatível com "velocidade e estabilidade andam juntas"; ρ ≈ 0 ou > 0 contradiz/não sustenta.
- **Limitações:** **não** concluir causalidade; ρ mede associação monotônica, não magnitude de efeito prático.

#### RQ06 — Fatores
- **Entrada:** métricas + ≥ 3 fatores; grupos por quartis para fatores numéricos.
- **Processamento:** KW (≥ 3 grupos)/MW (2 grupos) por fator×métrica; Holm; ε² ou δ.
- **Saída:** tabela (fator, métrica, estatística, p, p_holm, efeito, interpretação).
- **Estatística:** KW/MW + Holm + ε²/Cliff.
- **Visualização:** 💡 boxplot/violino por grupo.
- **Interpretação:** quais características estão **associadas** a melhor desempenho.
- **Limitações:** observacional; **tipo do projeto** só nos 60 rotulados; muitos testes ⇒ risco de falso positivo (por isso Holm); p pequeno ≠ efeito grande.

#### RQ07 — Sensibilidade
- **Entrada:** métricas por combinação (≥ 3).
- **Processamento:** classificar (§5.5); para cada par: % mudança e κ ponderado linear (rótulos como inteiros).
- **Saída:** tabela por par + 💡 matriz de transição.
- **Estatística:** % e kappa de Cohen ponderado.
- **Visualização:** 💡 heatmap de transição.
- **Interpretação:** o quanto "ser Elite/High/…" depende da definição escolhida.
- **Limitações:** a tabela de cortes é **adaptada** (da disciplina), não oficial; kappa alto não prova que a definição é "correta".

#### RQ08 — Bônus
- **Rework rate:** proporção de releases corretivas; discutir diferença para CFR(b). **Evolução temporal:** métricas por trimestre + Mann-Kendall por repo.
- **Limitações:** a heurística de corretiva herda seus erros (F1); trimestres com poucas releases dão séries curtas (Mann-Kendall perde poder).

---

# 8. SPRINT 01 (Lab03S01) — PIPELINE DE COLETA, TESTES E CI · 5 pontos

## 8.1 Objetivo da sprint (em linguagem simples)

Construir o **motor** do laboratório: um pipeline que, com **um comando**, escolhe repositórios, coleta os dados da API do GitHub **sem estourar o rate limit**, **guarda tudo em disco** para poder retomar, e tem as **funções de cálculo das métricas testadas** com CI rodando. Em paralelo, escrever a **Introdução com uma hipótese informal por RQ — antes de ver dados**. Não é a sprint de responder as RQs; é a sprint de provar que o grupo **consegue coletar de forma confiável**.

## 8.2 O que é obrigatório (lista completa de entregas)

1. [OBR] Pipeline de coleta base **funcionando para 100 repositórios** (E§10).
2. [OBR] **Seleção + funil registrado** (E§10, E§7).
3. [OBR] Coleta de **releases**, **commits entre releases** e **workflow runs do default branch na janela** (E§10).
4. [OBR] **Cache/retomada** e **tratamento de rate limit** (E§10, E§7).
5. [OBR] **Testes unitários** das funções de cálculo, **com fixtures**, e **CI do grupo rodando os testes** (E§10, E§7).
6. [OBR] **Cobertura ≥ 80% do módulo de métricas** (E§7).
7. [OBR] **Artigo: Introdução com hipóteses informais** para cada RQ (E§10, E§8).
8. [OBR] Cada integrante **Assignee de ≥ 1 Issue com artefato de código** commitado (E§10).
9. [OBR] Commits com `#Issue`; GitHub Projects bem usado (E§10).
10. [OBR] Execução por **comando único** documentada no README; token em variável de ambiente (E§7).

## 8.3 O que precisa ser implementado (componentes técnicos)

| # | Componente | Responsabilidade | Tag |
|---|---|---|---|
| 1 | `config.yaml` + leitor de config | Janela, limiares, sementes, diretórios, parâmetros de busca | DER |
| 2 | `http_client` (próprio) | Requisições autenticadas, leitura de cabeçalhos, retry/backoff, rate limit, `Link rel=next` | OBR |
| 3 | `cache` | Persistência (JSON por repo+endpoint ou SQLite); chave determinística; escrita atômica | OBR |
| 4 | `selection` | Busca por faixas de estrelas/linguagem; remove sem Actions; aplica mínimos; escreve funil | OBR |
| 5 | `collect_metadata` | Estrelas, linguagem, `created_at`, `default_branch`, contribuidores (`per_page=1&anon=true` → última página no `Link`) | OBR |
| 6 | `collect_releases` | Todas as releases (inclusive anteriores à janela) com `draft`, `prerelease`, `published_at`, `tag_name` | OBR/DER |
| 7 | `collect_tags` | Tags + data do commit apontado | OBR |
| 8 | `collect_commits` | `compare/{prev}...{R}` paginado; 404 registrado | OBR |
| 9 | `collect_runs` | `actions/runs?branch=&event=push&created=` fatiado por mês; alerta de teto 1.000 | OBR |
| 10 | `metricas/` (módulo) | `deployment_frequency`, `lead_time_release`, `lead_time_commit`, `cfr_ci`, `recovery_episodes`, `classify_*`, `classify_overall`, `classify_conclusion` | OBR (módulo medido na cobertura) |
| 11 | `pipeline/__main__` | Orquestra tudo com 1 comando | OBR |
| 12 | `.github/workflows/testes.yml` | CI (pytest + cobertura ≥ 80%) | OBR |
| 13 | `tests/` com fixtures | Dados construídos à mão (§12) | OBR |

> ⚠️ **Gap do enunciado:** a divisão sugerida (A/B/C) atribui lead time ao B e CFR(a)+recuperação ao C, mas **não atribui `deployment_frequency` nem `classify_*`** a ninguém — e o E§7 exige testes de **classificação DORA**. 💡 Atribuir ao integrante A (que tem a menor carga de funções de métrica).

## 8.4 Funil de seleção (exigência E§7 — detalhamento completo)

| Etapa | Regra | Código responsável | Qtde esperada/observada | Motivo de exclusão | Arquivo de registro |
|---|---|---|---|---|---|
| 0. Candidatos | Search API (`stars:>…`, fatiada por faixas/linguagem; ≤ 1.000/consulta) | `selection.search_candidates` | Exemplo do professor: 4.000 (⚠️ L03: critério de "popular") | — | `outputs/funil.csv` |
| 1. Possui Actions | `actions/workflows.total_count > 0` | `selection.filter_actions` | Ex.: 2.900 | `no_actions` | idem |
| 2. Releases mínimas | ≥ 5 releases de deploy na janela (⚠️ L05) | `selection.filter_releases` | — | `lt_5_releases` | idem |
| 3. Runs mínimos | ≥ 50 runs válidos no default branch/push/janela (⚠️ L04) | `selection.filter_runs` | Ex. (2+3 juntos): 610 | `lt_50_runs` | idem |
| 4. Demais critérios | Os que o grupo definir (ex.: não-fork, não-arquivado — ⚠️ L03) | `selection.filter_other` | — | `excluded_<criterio>` | idem |
| 5. Amostra final | Repos que sobraram (S01: ≥ 100; S02: ≥ 300) | `selection.finalize` | Ex.: 350 | — | `repos_final.csv` |

**Regras de ouro do funil:** (i) gerado **automaticamente** pelo pipeline (nada digitado à mão); (ii) cada descarte tem **um motivo único e contado**; (iii) a ordem das etapas **baratas primeiro** (descartar `total_count=0` antes de chamar releases/runs — E§4); (iv) a soma `entram − saem = restam` em cada etapa (💡 validar por teste).

## 8.5 O que precisa ser coletado

| Dado | Endpoint | Cuidado (E§4) | Cache |
|---|---|---|---|
| Candidatos | `GET /search/repositories?q=stars:>1000` | ≤ 1.000 resultados/consulta → fatiar | por faixa |
| Workflows | `GET /repos/{o}/{r}/actions/workflows` | `total_count=0` → descartar | por repo |
| Metadados | `GET /repos/{o}/{r}` + contributors | `per_page=1&anon=true` e ler `Link` | por repo |
| Releases | `GET /repos/{o}/{r}/releases` | `draft`, `prerelease`, `published_at`, `tag_name`; paginar | por repo |
| Tags | `GET /repos/{o}/{r}/tags` | Sem data → usar a do commit apontado | por repo |
| Commits entre releases | `GET /repos/{o}/{r}/compare/{base}...{head}` | ≤ 250 sem paginação; 404 possível | por par |
| Workflow runs | `GET /repos/{o}/{r}/actions/runs?branch=…&event=push&created=AAAA-MM-DD..AAAA-MM-DD` | ≤ 1.000/consulta → dividir por mês e **conferir teto** | por repo+mês |
| Rate limit | `GET /rate_limit` | **Não consome cota** | — |

## 8.6 O que precisa ser calculado na S01

As **funções** devem existir e estar testadas; a execução completa sobre o dataset de 100 é [RECOMENDAÇÃO] (valida o pipeline de ponta a ponta):
- Deployment frequency; lead time (a)/(b); CFR (a); recuperação por episódios; classificação DORA por métrica e geral. (CFR(b) e heurística entram na S02, mas **nada impede** deixar o esqueleto da função.)

## 8.7 O que precisa ser testado

Ver **§12 (Plano de testes)**. Mínimo obrigatório da S01: testes das funções de lead time, CFR, tempo de recuperação e classificação DORA, **com os 4 casos de borda do enunciado** (release sem commits novos; falha nunca recuperada; repo com 1 release; `cancelled` ignorado) e cobertura ≥ 80% do módulo de métricas.

## 8.8 O que precisa estar no GitHub

| Item | Detalhe |
|---|---|
| **Issues** | 1 por componente (sugestão do professor, E§10); cada uma com **Assignee**, descrição do artefato esperado e critério de aceite |
| **Assignees** | Os 3 integrantes; cada um com ≥ 1 Issue **de código** |
| **Commits** | Mensagem com `#N` (ex.: `feat(collect): paginação do compare (#7)`) |
| **Scripts/código** | `pipeline/`, `metricas/` |
| **Testes** | `tests/` (pytest + fixtures) |
| **GitHub Actions** | `.github/workflows/testes.yml` verde |
| **README** | Instalação, versão de Python, `GITHUB_TOKEN`, comando único, config, como retomar |
| **Dataset** | Cache de 100 repos (ou instruções para regenerar) + `funil.csv` |
| **Documentação** | `config.yaml` comentado |
| **Project (board)** | Colunas, WIP, Assignees, cartões movendo ao longo da semana |
| **Artigo** | `artigo/` com Introdução |

## 8.9 O que precisa entrar no artigo (S01)

- **Introdução** (contexto DORA, proxies, problema, objetivo — E§1/E§8).
- **Uma hipótese informal por RQ** (RQ01–RQ07; 💡 incluir RQ08 se optar pelo bônus): *o que esperamos e por quê*, **escrita antes de ver os dados** (E§8).
- 💡 **Prova da anterioridade:** fazer commit/tag (`hipoteses-v1`) da Introdução **antes** de rodar qualquer análise (⭐ D15 amplia).
- Usar A5-s104–113 (DORA como indicadores de processo; tese "velocidade e estabilidade não são opostas") como [RECOMENDAÇÃO] de embasamento conceitual.

## 8.10 Critérios de aceite da S01

- [ ] `python -m pipeline --config config.yaml` (ou equivalente) roda do início ao fim.
- [ ] **100 repositórios** processados (pós-filtro — 🔎 L17).
- [ ] Funil gerado automaticamente com motivos de descarte.
- [ ] Releases, commits entre releases e runs (default branch, push, janela) coletados.
- [ ] Teste de interrupção: matar (`Ctrl+C`) e reexecutar **não repete chamadas**.
- [ ] Rate limit: o script espera por `X-RateLimit-Reset` (demonstrado em teste ou log).
- [ ] 5xx com backoff 1 s, 2 s, 4 s, 8 s…
- [ ] `pytest` verde com fixtures baseadas nos exemplos da E§5.
- [ ] 4 casos de borda cobertos.
- [ ] Cobertura do módulo de métricas **≥ 80%**.
- [ ] CI roda e passa no GitHub Actions.
- [ ] Token **fora** do Git.
- [ ] Introdução com 1 hipótese por RQ.
- [ ] Cada integrante com Issue de código + commits `#N`.
- [ ] Board atualizado semanalmente.

## 8.11 Dependências

Ver §16. Resumo: `config`+`http_client`+`cache` → todos os coletores; `selection` → coletores; `collect_releases` → `collect_commits`; `collect_runs` independente de releases; funções de métrica independem de rede (usam fixtures).

## 8.12 Riscos

- Rate limit estourando na seleção de 100 repos (Search tem limite próprio — 💡 conferir na doc linkada).
- Janela ainda não informada (⚠️ L01) travando a coleta de runs/releases.
- Cache inconsistente após queda (arquivo meio escrito).
- Divisão sugerida deixa DF/classificação sem dono.
- Hipóteses escritas **depois** de ver dados.

## 8.13 Erros que NÃO podem acontecer (S01)

1. Commitar o token (ou deixá-lo em `config.yaml`).
2. Usar PyGithub/biblioteca de acesso à API.
3. Coletar runs de todos os branches/eventos.
4. Contar `cancelled`/`skipped` como falha.
5. Cortar releases **anteriores** à janela (quebra o lead time da 1ª release).
6. Esquecer paginação do `compare`.
7. Cobertura medida no módulo errado.
8. Funil montado à mão.
9. Commits sem `#Issue`.
10. Um integrante sem código na sprint (**zera a parcela individual dele**).

## 8.14 Checklist executável S01

### Preparação
- [ ] Obter com o professor as **datas da janela** (⚠️ L01) e registrar em `config.yaml`.
- [ ] Criar repositório do grupo; adicionar os 3 integrantes.
- [ ] Criar GitHub Project (colunas Backlog / In progress / Review / Done); definir **WIP** e escrevê-lo no README do board (⚠️ L14).
- [ ] Criar Issues por componente (§14.3) e atribuir Assignees.
- [ ] Criar estrutura: `pipeline/`, `metricas/`, `tests/`, `artigo/`, `data/`, `outputs/`, `.github/workflows/`.
- [ ] `.gitignore` para `cache/`, `.env`, `*.token`.
- [ ] Gerar token GitHub; exportar `GITHUB_TOKEN` localmente; **nunca** commitar.
- [ ] Fixar versão do Python (modelo do professor usa 3.12) e criar `requirements.txt`.
- [ ] Escrever esqueleto do README (comando único).

### Infraestrutura
- [ ] Implementar `http_client` (headers, auth, timeout).
- [ ] Implementar leitura de `X-RateLimit-Remaining`/`X-RateLimit-Reset` e espera automática.
- [ ] Implementar backoff exponencial para 5xx com limite de tentativas (⚠️ L21).
- [ ] Implementar helper de paginação por `Link rel="next"`.
- [ ] Implementar cache em disco (JSON por repo+endpoint ou SQLite) com escrita atômica.
- [ ] Implementar retomada (não repetir chamadas já cacheadas).
- [ ] Testar interrupção com `Ctrl+C` e reexecução.

### Seleção
- [ ] Implementar busca de candidatos com **fatiamento** (faixas de estrelas e/ou linguagem).
- [ ] Definir e documentar critério de "popular" (⚠️ L03).
- [ ] Implementar descarte `total_count=0`.
- [ ] Implementar filtro ≥ 5 releases e ≥ 50 runs válidos (documentando L04/L05).
- [ ] Registrar **motivo de descarte** por repo.
- [ ] Gerar **funil** automaticamente.
- [ ] Parar no 100º repo que passa nos filtros (ou documentar a regra).

### Coleta
- [ ] Coletar metadados (estrelas, linguagem, `created_at`, `default_branch`, contribuidores).
- [ ] Coletar releases (todas, inclusive pré-janela) e marcar `draft`/`prerelease`.
- [ ] Coletar tags e a data do commit apontado.
- [ ] Coletar commits entre releases (`compare`), paginando; tratar 404.
- [ ] Coletar runs por mês com `branch`+`event=push`+`created=`.
- [ ] Verificar teto de 1.000 por mês e subdividir se atingido.
- [ ] Confirmar que `GET /rate_limit` é usado sem consumir cota.

### Métricas (módulo `metricas`)
- [ ] `classify_conclusion` (9 valores).
- [ ] `deployment_frequency`.
- [ ] `lead_time_release` (a) e `lead_time_commit` (b).
- [ ] `cfr_ci` (a).
- [ ] `recovery_episodes` (+ censura).
- [ ] `classify_df`, `classify_lt`, `classify_cfr`, `classify_recovery`, `classify_overall`.
- [ ] Rodar o cálculo sobre os 100 repos (💡) e inspecionar valores absurdos.

### Testes e CI
- [ ] Escrever fixtures a partir dos exemplos da E§5 (v1.1 → 13 dias; CI 1h20; etc.).
- [ ] Escrever os 4 casos de borda obrigatórios.
- [ ] Rodar `pytest --cov=metricas --cov-report=term-missing`; chegar a ≥ 80%.
- [ ] Criar `.github/workflows/testes.yml` com `--cov-fail-under=80`.
- [ ] Verificar execução verde no GitHub Actions.

### GitHub
- [ ] Todo commit com `#N`.
- [ ] Cada integrante com ≥ 1 Issue de **código** (A: seleção/funil/metadados; B: releases/tags/commits + lead time; C: runs + cache/rate limit + CFR(a)/recuperação — 💡 sugestão do professor).
- [ ] Mover cartões ao longo da semana (evidência de evolução semanal).
- [ ] Fechar Issues somente com commit/PR referenciando.

### Artigo
- [ ] Criar projeto Overleaf com **template SBC**.
- [ ] Escrever Introdução (contexto, proxies, problema, objetivo).
- [ ] Escrever **1 hipótese informal por RQ** (o que esperamos e por quê) **antes** de analisar dados.
- [ ] Commitar `.tex` com tag `hipoteses-v1`.

### Fechamento
- [ ] Executar o §19.1 (Definition of Done).
- [ ] Teste do README em máquina limpa (💡 antecipar o §13).

---

# 9. SPRINT 02 (Lab03S02) — AMOSTRA COMPLETA, MÉTRICAS E VALIDAÇÃO MANUAL · 5 pontos

## 9.1 Objetivo da sprint

Passar de **100 para ≥ 300 repositórios**, **calcular todas as métricas em todas as variantes obrigatórias**, **entregar o dataset em CSV com dicionário** e **descobrir o quanto a heurística de release corretiva e os critérios podem ser confiados**, comparando-os com o julgamento de três pessoas (amostra-ouro de 60 repos). Escrever a **Metodologia**.

## 9.2 O que é obrigatório

1. [OBR] Amostra final **≥ 300 repositórios após os filtros** (E§10).
2. [OBR] Métricas calculadas em **todas as variantes obrigatórias** (DF, LT a/b, CFR a/b, recuperação, classificação).
3. [OBR] **Dataset `.csv` + dicionário de dados** (cada coluna: nome, tipo, unidade, fórmula/origem).
4. [OBR] **Validação manual:** 60 repos sorteados (semente fixa), **3 rotuladores independentes**, **kappa de Fleiss** nas **3 dimensões**, **consenso** com protocolo de desempate no repo, **P/R/F1** da heurística; se **F1 < 0,70 → refinar e reavaliar, documentando cada versão e seu F1**.
5. [OBR] **Artigo: Metodologia completa.**
6. [OBR] Individual: cada integrante com **sua Issue e seu arquivo de rótulos commitado** + o componente sugerido (A/B/C).
7. [OBR] `#N` nos commits; GitHub Projects bem usado.

## 9.3 O que precisa ser implementado

| # | Componente | Tag |
|---|---|---|
| 1 | Execução em escala (300+): robustez do cache/retomada, execução em segundo plano, logs | OBR (E§11) |
| 2 | `heuristica.py` — release corretiva (SemVer *patch* e/ou mensagens `revert`/`hotfix`/`fix`; regra do grupo) + `heuristic_version` | OBR |
| 3 | `cfr_release` — CFR(b) com janela de 7 dias e censura dos últimos 7 dias | OBR |
| 4 | Cálculo das variantes para RQ07 (release+pré-release; tag) | DER |
| 5 | `consolidate_dataset` — junta tudo nos CSVs finais | OBR |
| 6 | `DICIONARIO_DE_DADOS` + verificação de completude | OBR / ⭐ |
| 7 | `sample_gold.py` — sorteio com `random_state` fixo; geração de planilhas com **links** das releases (💡 dica); sorteio das **5 releases por repo** com semente | OBR / REC / DER |
| 8 | `agreement.py` — `aggregate_raters` + `fleiss_kappa` por dimensão | OBR |
| 9 | `consensus.py` + `PROTOCOLO_CONSENSO.md` | OBR |
| 10 | `evaluate_heuristic.py` — `precision_recall_fscore_support`; histórico de versões | OBR |
| 11 | Testes de heurística e de CFR(b) (adicionados à suíte; cobertura ≥ 80% mantida) | DER |

## 9.4 O que precisa ser coletado

- Coleta completa (metadados, releases, tags, `compare`, runs) para **todos** os repositórios da amostra final.
- **Rótulos humanos:** 3 arquivos independentes — (i) tipo do projeto (biblioteca/framework · aplicação/serviço · ferramenta CLI · outro); (ii) releases representam entregas reais ao usuário (sim/não/incerto); (iii) **5 releases sorteadas** por repo: corretiva (sim/não), lendo *release notes* e lista de commits.
- Volume mínimo de rotulagem: **60 repos × (1 + 1 + 5) = 420 julgamentos por integrante** (60 tipos + 60 "entrega real" + 300 releases). 🔎 Aritmética derivada do enunciado.

## 9.5 O que precisa ser calculado

| Cálculo | Detalhe |
|---|---|
| Métricas do §5 | DF; LT(a); LT(b); CFR(a); CFR(b); recuperação; classificação por métrica e geral |
| Contagens de censura/ignorados | Releases censuradas (últimos 7 dias); episódios censurados; releases com 404; releases sem commits novos |
| Kappa de Fleiss | **3 dimensões** (tipo, entrega real, corretiva); interpretar com Landis & Koch (< 0 pobre; 0–0,20 leve; 0,21–0,40 razoável; 0,41–0,60 moderada; 0,61–0,80 substancial; 0,81–1 quase perfeita) |
| P/R/F1 | Precisão = TP/(marcadas pela heurística); Recall = TP/(corretivas reais); F1 = 2PR/(P+R). Exemplo do professor: 40 marcadas, 30 confirmadas → P=75%; 50 reais → R=60%; F1 ≈ 0,67 |

## 9.6 O que precisa ser testado

- Heurística: casos SemVer (`2.3.0→2.3.1` corretiva; `2.3.0→2.4.0` não), mensagens com `fix/hotfix/revert`, falso positivo `prefix`, tags não-SemVer.
- CFR(b): os dois exemplos da E§5; fronteira de 7 dias; censura nos últimos 7 dias; 1 release.
- Dataset: sem duplicatas de `full_name`; nenhum repo abaixo de 5 releases/50 runs; todas as colunas no dicionário.
- Sorteio: mesma semente ⇒ mesmos 60 repos e mesmas 5 releases.
- Estatística de concordância: casos conhecidos (concordância perfeita ⇒ κ=1; exemplo P/R/F1 do professor ⇒ 0,75/0,60/≈0,67). 💡 [RECOMENDAÇÃO].

## 9.7 O que precisa estar no GitHub

| Item | Detalhe |
|---|---|
| **Issues** | 3 Issues de rotulagem (uma por pessoa) + A (concordância/consenso) + B (heurística) + C (coleta completa/dataset/dicionário) + escrita da Metodologia |
| **Assignees** | Cada integrante com sua Issue de rotulagem e arquivo de rótulos commitado |
| **Commits** | `#N` em todos; **rótulos de cada pessoa commitados por ela** (evidência individual) |
| **Scripts** | `sample_gold.py`, `agreement.py`, `evaluate_heuristic.py`, `heuristica.py`, `consolidate_dataset.py` |
| **Datasets** | `repos.csv` (≥ 300 linhas), `releases.csv`, rótulos A/B/C, `consenso.csv` |
| **Documentação** | `DICIONARIO_DE_DADOS`, `PROTOCOLO_CONSENSO.md`, README atualizado |
| **Testes/CI** | Suíte ampliada, CI verde |
| **Board** | Atualizado semanalmente |

## 9.8 O que precisa entrar no artigo (S02): **Metodologia**

Fonte de dados · **funil de seleção** (tabela gerada) · janela · **definições operacionais e suas variantes** · critérios mínimos · tratamento de censura · **protocolo de validação manual** (sorteio com semente, rotulagem independente, kappa de Fleiss, consenso/desempate, P/R/F1, **versões da heurística com F1**). Detalhe na §15.

## 9.9 Critérios de aceite da S02

- [ ] `len(repos_final) ≥ 300` e nenhum viola ≥ 5 releases/≥ 50 runs.
- [ ] Todas as colunas de métricas preenchidas (ou NaN justificado).
- [ ] Contagem de censurados e de 404 reportada.
- [ ] CSV + dicionário completos.
- [ ] Sorteio de 60 reproduzível (semente no código).
- [ ] 3 arquivos de rótulos **independentes** commitados (um por integrante).
- [ ] Kappa de Fleiss nas 3 dimensões, com interpretação.
- [ ] Protocolo de desempate versionado; `consenso.csv` gerado.
- [ ] F1 final ≥ 0,70 **ou** histórico de refinamentos com F1 de cada versão documentado.
- [ ] Metodologia completa no artigo.
- [ ] CI verde; cobertura ≥ 80%.
- [ ] Commits `#N`; cada integrante com código/artefato.

## 9.10 Dependências

Amostra final congelada → sorteio da amostra-ouro → rotulagem → kappa + consenso → avaliação da heurística → refinamento → CFR(b) final. Ver §16.

## 9.11 Riscos

- Rate limit estourando repetidamente (E§11 prevê).
- **Contaminação da rotulagem** (ver a saída da heurística ou combinar rótulos).
- Kappa baixo por critério ambíguo (é **achado**, deve ser discutido — E§6).
- F1 < 0,70 e pouco tempo para refinar.
- **Overfitting da heurística** à amostra-ouro (💡 declarar no artigo como ameaça).
- Reamostrar a amostra final **depois** do sorteio da amostra-ouro.

## 9.12 Erros que NÃO podem acontecer (S02)

1. Rotuladores **conversarem** antes de entregar rótulos, ou **verem a coluna da heurística**.
2. Rotuladores receberem **releases diferentes** (kappa fica inválido).
3. Sorteio sem semente documentada.
4. Descartar casos censurados.
5. Esquecer o dicionário de dados.
6. Usar a heurística no CFR(b) **sem validação**.
7. Reportar só "% de concordância" no lugar do kappa.
8. Apresentar F1 sem registrar as versões testadas.
9. Fundir os 3 arquivos de rótulos num só (perde-se a evidência individual).
10. Misturar CFR(a) e CFR(b) em uma coluna só.

## 9.13 Checklist executável S02

### Amostra e coleta
- [ ] Ajustar `config` para meta ≥ 300 (alargar faixas de estrelas/linguagens se necessário).
- [ ] Testar **sempre com poucos repos** antes de rodar o completo (E§11).
- [ ] Rodar coleta completa em segundo plano; monitorar logs e cota.
- [ ] Após interrupção, reexecutar o mesmo comando e confirmar retomada.
- [ ] Gerar **funil final** (números reais) e `repos_final.csv`.
- [ ] **Congelar** a lista (commit + hash citado) antes de sortear a amostra-ouro.

### Métricas
- [ ] Calcular DF, LT(a), LT(b), CFR(a), CFR(b), recuperação, classificação.
- [ ] Calcular colunas das combinações da RQ07 (release+pré-release, tag).
- [ ] Registrar censura (CFR(b) últimos 7 dias; episódios) e 404.

### Dataset
- [ ] Gerar CSVs finais.
- [ ] Escrever dicionário (nome, tipo, unidade, fórmula/origem) para **cada** coluna.
- [ ] Rodar verificação de completude coluna×dicionário.

### Validação manual
- [ ] `df.sample(n=60, random_state=<semente>)`; registrar semente no código **e** no artigo.
- [ ] Sortear **5 releases por repo** (mesmas para os 3).
- [ ] Gerar 3 planilhas **sem** a coluna da heurística, com **link** direto de cada release (💡).
- [ ] Cada integrante rotula (i) tipo, (ii) entrega real, (iii) corretiva — **sozinho**.
- [ ] Commitar os 3 arquivos (cada um por seu autor, com `#N`).
- [ ] Calcular **Fleiss** nas 3 dimensões (`aggregate_raters` → `fleiss_kappa`).
- [ ] Registrar protocolo de desempate em `PROTOCOLO_CONSENSO.md` e gerar `consenso.csv`.
- [ ] Rodar heurística v1 e calcular P/R/F1 (`precision_recall_fscore_support`).
- [ ] Se F1 < 0,70: refinar (v2, v3…) e reavaliar; **tabela versão → F1**.
- [ ] Congelar a versão final da heurística e recalcular CFR(b)/rework.

### GitHub
- [ ] Issues: 3 rotulagens, concordância/consenso (A), heurística (B), dataset/dicionário (C), Metodologia.
- [ ] Commits `#N`; cartões atualizados; evolução semanal.

### Artigo
- [ ] Escrever Metodologia (fonte, funil, janela, definições/variantes, protocolo de validação).
- [ ] Inserir tabela do funil e tabela de versões da heurística.
- [ ] Revisão cruzada entre os três.

### Fechamento
- [ ] Executar o §19.2 (Definition of Done).

---

# 10. SPRINT 03 (Lab03S03) — ANÁLISE ESTATÍSTICA RQ01–RQ07 · 5 pontos

## 10.1 Objetivo da sprint

Transformar o CSV final em **respostas**: estatística descritiva (mediana/IQR) e classificação DORA para RQ01–RQ04, correlação (RQ05), testes com tamanho de efeito e correção de múltiplas comparações (RQ06) e análise de sensibilidade (RQ07). Escrever **Resultados e Discussão** (hipóteses × resultados). O bônus RQ08 é opcional.

## 10.2 O que é obrigatório

1. [OBR] Análise completa **RQ01 a RQ07** (E§10).
2. [OBR] Estatística descritiva (**mediana e IQR**) + **classificação DORA** (E§10, E§5).
3. [OBR] **Correlações** (RQ05): ρ, p, n por variante (a)/(b) + dispersão.
4. [OBR] **Testes com tamanho de efeito e correção para comparações múltiplas** (RQ06): ≥ 3 fatores; KW/MW; Holm; ε²/Cliff.
5. [OBR] **Sensibilidade** (RQ07): ≥ 3 combinações; % mudança e kappa ponderado por par; discussão de robustez.
6. [OBR] **Cada análise = notebook ou script próprio, reexecutável a partir do CSV** (E§10).
7. [OBR] **Artigo: Resultados + Discussão** (E§8, E§10).
8. [OBR] Cada integrante com Issue de código; commits `#N`; Projects em dia.
9. [OPCIONAL → +1 ponto] RQ08 (uma das duas opções).

## 10.3 O que precisa ser implementado

| # | Artefato | Responsável sugerido (professor) |
|---|---|---|
| 1 | `analysis/rq01_rq04.(ipynb\|py)` — descritiva + classificação C1 | **A** |
| 2 | `analysis/dora_class_C1.(ipynb\|py)` + `dora_class.csv` | **A** |
| 3 | `analysis/rq05.(ipynb\|py)` — Spearman + dispersão | **B** |
| 4 | `analysis/rq06.(ipynb\|py)` — fatores, KW/MW, Holm, ε², Cliff | **B** |
| 5 | `analysis/rq07.(ipynb\|py)` — combinações, % mudança, κ ponderado | **C** |
| 6 | `analysis/rq08.(ipynb\|py)` — bônus | **C** (se optar) |
| 7 | `analysis/common.py` — leitura do CSV, helpers (IQR, quartis, Cliff, ε²) | 💡 compartilhado |
| 8 | Figuras/tabelas exportadas para `artigo/figs` | 💡 |

> Divisão A/B/C é **sugestão** do professor (E§10). O que é **obrigatório**: cada integrante com ≥ 1 Issue de código/análise commitada.

## 10.4 O que precisa ser coletado

Nada novo da API. **Exceção:** se faltarem dados para RQ07 (pré-release/tags) ou para um fator RQ06, voltar ao pipeline (DER) — por isso S02 deve entregar as colunas das combinações.

## 10.5 O que precisa ser calculado (por RQ)

| RQ | Cálculo mínimo | Saídas obrigatórias |
|---|---|---|
| RQ01 | Mediana/IQR de `df_per_week` | Tabela + classe DORA de DF |
| RQ02 | Mediana/IQR de LT(a) e LT(b) | Tabela + explicação da divergência |
| RQ03 | Mediana/IQR de CFR(a) e (b) | Tabela + discussão pipeline ≠ produção |
| RQ04 | Mediana/IQR de recuperação; **proporção de episódios censurados por repositório** | Tabela + proporção |
| RQ05 | `spearmanr(DF, CFR_a)` e `spearmanr(DF, CFR_b)` | ρ, p, n + dispersão |
| RQ06 | KW/MW por fator×métrica → Holm → ε²/δ | Tabela (estatística, p, p_holm, efeito) |
| RQ07 | Classificação em ≥ 3 combinações; % mudança e κ linear por par | Tabela por par + discussão |
| RQ08 | Rework rate **ou** Mann-Kendall trimestral | Resultado + discussão |

## 10.6 O que precisa ser testado

- 💡 [RECOMENDAÇÃO] Testes unitários das **funções estatísticas auxiliares** (Cliff, ε², Holm com valores conhecidos, codificação ordinal do kappa) — ver §12.4. O enunciado só **exige** testes das funções de métricas (E§7).
- **Reexecução limpa:** apagar saídas e rodar todos os notebooks/scripts a partir do CSV; resultados idênticos (**obrigatório**, E§10).

## 10.7 O que precisa estar no GitHub

| Item | Detalhe |
|---|---|
| Issues | Uma por análise (RQ01–04, RQ05, RQ06, RQ07, [RQ08]) + Resultados + Discussão |
| Assignees | A, B, C (cada um com análise commitada) |
| Notebooks/scripts | `analysis/` com instrução de execução no README |
| Dataset | O mesmo CSV da S02 (versionado) |
| CI | Verde (💡 smoke test dos scripts) |
| README | Seção "Como reproduzir as análises" |
| Board | Atualizado |

## 10.8 O que precisa entrar no artigo (S03): **Resultados + Discussão**

- **Resultados por RQ** com **mediana, IQR e classificação DORA**, em **tabelas e gráficos** (E§8).
- **Discussão:** hipóteses (da Introdução) **vs** resultados; **o que surpreendeu e por quê** (E§8).
- Pontos que o enunciado manda **explicitamente** discutir: divergência LT(a)×(b); CFR(a) ≠ falha em produção; RQ05 × tese DORA (sem causalidade); robustez (RQ07).

## 10.9 Critérios de aceite da S03

- [ ] RQ01–RQ07 com resultado, tabela e figura.
- [ ] **Nenhuma média/DP** como estatística principal.
- [ ] RQ04 com proporção de censura.
- [ ] RQ05: ρ, p, n **para (a) e (b)**; dispersão com escala adequada.
- [ ] RQ06: ≥ 3 fatores; ≥ 12 testes (3×4) com **Holm**; ε² (KW) ou δ (2 grupos) em cada linha.
- [ ] RQ07: ≥ 3 combinações; **3 pares** com % e κ ponderado linear.
- [ ] Notebooks/scripts reexecutáveis a partir do CSV.
- [ ] Resultados + Discussão revisadas.
- [ ] Commits `#N`; cada integrante com artefato.

## 10.10 Dependências

S02 completa (CSV, heurística validada, rótulo de tipo, colunas de combinações). Ver §16.

## 10.11 Riscos

- NaN em CFR(b) reduzindo `n` (e diferença de `n` entre (a) e (b)).
- Subgrupos minúsculos (linguagens raras; tipo do projeto com 60 repos).
- Confusão de sinais (Cliff's δ depende da ordem `x,y`).
- Esquecer Holm (ou aplicá-lo só a um subconjunto).
- Kappa com rótulos de texto (ordem alfabética).
- Discussão que "prova" causalidade.

## 10.12 Erros que NÃO podem acontecer (S03)

1. Reportar **média ± DP**.
2. Aplicar Kruskal-Wallis a 2 grupos (ou Mann-Whitney a ≥ 3).
3. Reportar só p-valor sem tamanho de efeito.
4. Não corrigir p-valores.
5. Rodar RQ05 só para uma variante.
6. Descartar episódios censurados na RQ04.
7. Notebooks que dependem de estado oculto/células fora de ordem.
8. Concluir causalidade em RQ05/RQ06.
9. Reclassificar com cortes diferentes dos da tabela da disciplina.
10. Integrante sem commits na sprint.

## 10.13 Checklist executável S03

### Preparação
- [ ] Congelar versão do CSV e do dicionário (tag Git).
- [ ] Criar `analysis/common.py` (leitura, IQR, quartis, Cliff, ε²).
- [ ] Criar Issues por análise e atribuir.

### RQ01–RQ04 + classificação (A)
- [ ] Mediana e IQR de DF, LT(a), LT(b), CFR(a), CFR(b), recuperação.
- [ ] Classificar C1 (DF, LT(a), CFR(a), recuperação) e a classe geral (mediana arredondada para baixo).
- [ ] Reportar proporção de episódios censurados (RQ04).
- [ ] Tabela e gráficos por RQ.
- [ ] Parágrafo: por que LT(a) e LT(b) divergem (commit "esquecido").
- [ ] Parágrafo: CFR(a) mede falha de pipeline, não de produção.

### RQ05 e RQ06 (B)
- [ ] `spearmanr(DF, CFR_a)` e `spearmanr(DF, CFR_b)`; registrar ρ, p, n.
- [ ] Dispersão (escala log se necessário).
- [ ] Discussão: tese DORA × dados; "correlação ≠ causalidade".
- [ ] Escolher ≥ 3 fatores; construir grupos (quartis para numéricos; "Outras" para linguagens raras).
- [ ] Para cada fator×métrica: KW (≥ 3 grupos) ou MW (2).
- [ ] Holm via `multipletests(method='holm')` sobre **todos** os testes.
- [ ] ε² = H/(n−1) e δ = 2·U₁/(n₁n₂) − 1; classificar |δ| (Romano).
- [ ] Tabela final com p, p_holm e efeito.

### RQ07 e bônus (C)
- [ ] Definir ≥ 3 combinações (💡 C1/C2/C3 do professor).
- [ ] Classificar cada repo em cada combinação (rótulos → inteiros 1–4).
- [ ] Para cada par: % que mudou e `cohen_kappa_score(..., weights='linear')`.
- [ ] 💡 Matriz de transição.
- [ ] Discussão: robustez das RQ01–06.
- [ ] (Opcional) RQ08: escolher **uma** opção e executar.

### GitHub
- [ ] Commits `#N`; cada integrante com análise commitada.
- [ ] Board atualizado semanalmente.

### Artigo
- [ ] Resultados por RQ (mediana, IQR, classificação).
- [ ] Discussão: hipótese × resultado × surpresa × motivo.

### Fechamento
- [ ] Reexecutar todos os notebooks do zero.
- [ ] Executar o §19.3 (Definition of Done).

---

# 11. ENTREGA FINAL — REPLICAÇÃO, ISSUES E ARTIGO COMPLETO · 5 pontos (2 + 1 + 2)

## 11.1 Objetivo

Provar que o estudo **é reprodutível por outras pessoas** e **fechar o artigo**. Cada grupo é, ao mesmo tempo, **replicador** (de outro grupo) e **autor** (replicado). O professor sorteia para cada grupo o pipeline de outro grupo (E§9).

## 11.2 O que é obrigatório

| Bloco | Entrega | Pontos | Origem |
|---|---|---|---|
| **Replicação cruzada** | Executar o pipeline do outro grupo **só com o README**, em **30 repos** do dataset original, **sem pedir ajuda**; comparar; abrir Issues; relatar | **2** | E§9, E§10 |
| **Resposta às Issues** | Responder **cada** Issue recebida até o prazo final: corrigir ou justificar; Issues no **próprio Projects** | **1** | E§9, E§10 |
| **Artigo completo e revisado** | Inclui **Ameaças à validade** e **relato da replicação**; ≤ 10 páginas; link preenchido | **2** | E§8, E§10 |

## 11.3 O que precisa ser implementado

| # | Item | Responsável sugerido | Tag |
|---|---|---|---|
| 1 | Execução do pipeline do outro grupo + **script/log de execução** (comandos, versões, saída) | **A** | OBR (+ DER p/ artefato de código) |
| 2 | `replicacao/compara.py`: diferença relativa por métrica + % de repos com mesma classificação DORA | **B** | OBR |
| 3 | Issues de divergência/falha/documentação no repo do outro grupo | **B** (execução: A) | OBR |
| 4 | Correções no **próprio** pipeline a partir das Issues recebidas | **C** | OBR |
| 5 | Opção de rodar com **lista de repositórios** (30 repos) no próprio pipeline | DER (feito antes, S03) | DER |
| 6 | Seções do artigo: **Ameaças à validade** e **Replicação cruzada**; revisão final | **Os três** | OBR |

## 11.4 O que precisa ser coletado

- Dados do **replicador:** saída da execução (logs), CSV regenerado para os 30 repos, versão de Python, SO, data da coleta.
- Dados do **autor:** Issues recebidas (texto, evidências, resolução).

## 11.5 O que precisa ser calculado

| Cálculo | Detalhe | Origem |
|---|---|---|
| **Diferença relativa por métrica** | `(valor_replicado − valor_original) / valor_original` por repo e métrica; resumo (💡 mediana da diferença relativa) | E§9 |
| **% de repos com a mesma classificação DORA** | Original × replicado, nos 30 | E§9 |
| Explicação das diferenças | Repos continuam recebendo commits; datas de coleta diferem | E§9 |

⚠️ Valor original zero ⇒ diferença relativa indefinida: 💡 tratar e documentar.

## 11.6 O que precisa ser testado

- Reprodutibilidade do **próprio** pipeline (§13) — **antes** de o outro grupo executá-lo.
- Após corrigir Issues recebidas: **rodar a suíte** (CI verde) e, quando for correção de resultado, reexecutar a subamostra.

## 11.7 O que precisa estar no GitHub

| Item | Detalhe |
|---|---|
| **Issues (como replicador)** | No repo do **autor**; uma por problema; com **comando executado, mensagem de erro, valores esperados e obtidos** |
| **Issues (como autor)** | Todas **respondidas** (corrigido via commit `#N` **ou** justificativa) e **adicionadas ao seu Project** |
| **Commits** | `#N` nas correções |
| **Artefatos do replicador** | `replicacao/` (log, script de comparação, tabela) |
| **README** | Corrigido conforme Issues |
| **Artigo** | PDF final + `.tex` |
| **Board** | Atualizado (inclui as Issues recebidas) |

## 11.8 O que precisa entrar no artigo (Final)

- **Ameaças à validade** (4 categorias) **apoiadas** em resultados da validação manual e da sensibilidade (§15.4).
- **Replicação cruzada:** o estudo foi reproduzível? O que impediu/dificultou? (E§8/E§9)
- **Link** do repositório/GitHub Projects (substituir `<preencher>`).
- **Revisão geral** (≤ 10 páginas; coerência entre seções; hipóteses × resultados).

## 11.9 Critérios de aceite da entrega final

- [ ] Replicação feita **só com o README** do outro grupo (sem contato).
- [ ] Subamostra de **30 repos** do dataset original.
- [ ] Se travou: travamento **registrado** como resultado.
- [ ] Tabela com **diferença relativa por métrica** e **% mesma classificação**.
- [ ] Explicação das diferenças.
- [ ] **Todas** as Issues abertas ao autor, com evidências completas.
- [ ] **Todas** as Issues recebidas respondidas e no Project.
- [ ] Seção "Replicação cruzada" escrita.
- [ ] Ameaças à validade nas **4 categorias**, com números.
- [ ] Artigo ≤ 10 páginas, template SBC, **7 itens**, link preenchido.
- [ ] Cada integrante com Issue de **código** + commits `#N`.
- [ ] Revisão final dos três.

## 11.10 Dependências

Pipeline e README do **grupo autor** disponíveis; sorteio do professor feito; (⚠️ L15) definição de quem escolhe os 30 repos e do prazo. Ver §16.

## 11.11 Riscos

- Dependência do **outro grupo** (README incompleto; repo privado; dados ausentes).
- Rate limit na execução do replicador (30 repos é pouco, mas exige token válido).
- Atrasos nas Issues do replicador deixando pouco tempo para o autor corrigir.
- Integrante A (replicação) sem artefato de código ⇒ zera sua parcela individual.

## 11.12 Erros que NÃO podem acontecer (Final)

1. Pedir ajuda ao grupo autor durante a execução.
2. Abrir Issue sem evidência (sem comando/erro/valores).
3. Ignorar Issues recebidas, ou responder sem corrigir/justificar.
4. Esquecer de adicionar Issues recebidas ao Project.
5. Omitir **ameaças de commit data (rebase/squash)** e as 4 categorias.
6. Ameaças à validade **sem números** da validação e da sensibilidade.
7. Passar de 10 páginas.
8. Link do repo ainda `<preencher>`.
9. Alterar o dataset original no meio da replicação sem registrar.
10. Integrante sem código na sprint.

## 11.13 Checklist executável Final

### Antes de abrir a janela de replicação
- [ ] README do grupo validado em máquina limpa (§13).
- [ ] CSV original + dicionário versionados no `main`.
- [ ] Pipeline roda com `--repos-file` (30 repos).
- [ ] Repositório **acessível** para o outro grupo (e para o professor).

### Como replicador
- [ ] Identificar o grupo sorteado.
- [ ] Clonar o repo do outro grupo; **seguir só o README**.
- [ ] Registrar: SO, versão do Python, comandos, saídas, tempo, erros.
- [ ] Executar sobre os **30 repos** da subamostra do dataset original.
- [ ] Se travar, registrar o ponto exato e a causa provável (resultado, não fracasso).
- [ ] Rodar `replicacao/compara.py`: diferença relativa por métrica e % mesma classificação.
- [ ] Explicar as diferenças esperadas (repos continuam recebendo commits; datas de coleta).
- [ ] Abrir **uma Issue por problema** no repo do autor (comando, erro, esperado × obtido).
- [ ] Escrever a seção "Replicação cruzada".

### Como autor
- [ ] Monitorar Issues recebidas.
- [ ] Adicionar **cada** Issue ao Project.
- [ ] Atribuir responsável e responder (corrigir com commit `#N` ou justificar).
- [ ] Atualizar README/pipeline; rerodar testes/CI.
- [ ] Fechar Issues com resposta.

### Artigo
- [ ] Escrever **Ameaças à validade** (4 categorias) com números (κ, F1, sensibilidade).
- [ ] Incluir a ameaça de **rebase/squash vs. `author.date`**.
- [ ] Escrever Replicação cruzada.
- [ ] Preencher link do repositório/Projects.
- [ ] Revisão final dos três; ≤ 10 páginas; referências.

### GitHub
- [ ] Cada integrante com Issue de código (A: log/script de replicação; B: compara + Issues de divergência; C: correções).
- [ ] Commits `#N`; board atualizado.

### Fechamento
- [ ] Executar o §19.4 (Definition of Done).

---

# 12. PLANO DE TESTES

## 12.1 Exigências (E§7)

- **pytest**, com **fixtures** (dados pequenos feitos à mão, cujo resultado o grupo já sabe calcular no papel; os exemplos numéricos da E§5 são o ponto de partida).
- Funções cobertas: **lead time, CFR, tempo de recuperação, classificação DORA**.
- **Casos de borda obrigatórios:** release sem commits novos · falha nunca recuperada (censurada) · repo com uma única release · execuções `cancelled` ignoradas.
- **Cobertura ≥ 80% do módulo de métricas** (`pytest --cov=metricas --cov-report=term-missing`); CI com `--cov-fail-under=80`.
- CI do grupo roda em **todo push** (GitHub Actions).

> 🔎 O nome `metricas` vem do comando de exemplo. **O módulo que contém as funções de métrica deve ter exatamente o nome passado a `--cov=`**, senão a cobertura mede outra coisa.

Legenda das linhas abaixo: **[OBR]** = caso exigido explicitamente · **[DER]** = consequência necessária de definição do enunciado · **[REC]** = caso adicional [RECOMENDAÇÃO].

## 12.2 Casos concretos por função

### `classify_conclusion(conclusion)`

| Caso normal | Caso limite | Caso inválido | Resultado esperado |
|---|---|---|---|
| `"success"` | — | — | SUCESSO [OBR] |
| `"failure"`, `"timed_out"`, `"startup_failure"` | — | — | FALHA [OBR] |
| `"cancelled"`, `"skipped"`, `"neutral"`, `"action_required"`, `"stale"` | — | — | IGNORAR [OBR] — **a variante `cancelled` é caso de borda explícito** |
| — | `None` / `""` (em andamento) | — | IGNORAR [OBR] |
| — | — | valor desconhecido (`"foo"`) | 💡 IGNORAR + log de aviso (⚠️ não definido) [REC] |

### `deployment_frequency(releases, window)`

| Caso normal | Caso limite | Caso inválido | Resultado esperado |
|---|---|---|---|
| 52 releases publicadas, janela de 365 dias | 0 releases | janela com `end ≤ start` | ≈ 0,997/sem [DER]; 0,0; erro explícito |
| Mix com `draft=true` e `prerelease=true` | release no 1º/último instante da janela | `published_at` ausente | draft/pré-release **não** contam [OBR]; fronteira documentada [REC]; item descartado |

### `lead_time_release` — variante (a)

| Caso normal | Caso limite | Caso inválido | Resultado esperado |
|---|---|---|---|
| **`v1.1` em 15/03, commits 02/03, 10/03, 14/03** | **Release sem commits novos** [OBR] | Commit com data posterior à release (⚠️ L07) | **13 dias** (312 h) [OBR] · release excluída do cálculo e contada [DER/REC] · sinalizado/erro [REC] |
| Mediana entre 3 releases (13 d, 4 d, 2 d) | **Repo com 1 única release** [OBR] | Data malformada | 4 d [DER] · lead time indefinido/`None` [OBR] · exceção clara [REC] |
| — | **1ª release da história (sem anterior)** [OBR, E§5] | — | Ignorada no cálculo |
| — | `compare` 404 (E§11) | — | Release ignorada **e contada** [OBR] |
| — | Primeira release da janela com anterior **fora** da janela | — | **Entra** no cálculo [OBR] |

### `lead_time_commit` — variante (b)

| Caso normal | Caso limite | Caso inválido | Resultado esperado |
|---|---|---|---|
| `v1.1`: valores {13, 5, 1} dias | Duas releases: R1={13,5,1}, R2={2,2} | commit duplicado em 2 releases | Mediana de **todos** {1,2,2,5,13} = **2 d** [DER] (**não** mediana das medianas) |
| **Divergência (a)×(b):** commits {100 d, 1 d, 1 d, 1 d, 1 d} | — | — | (a) = **100 d**; (b) = **1 d** [DER do E§5 "pista"] |
| — | Release sem commits novos / 1 release | — | Sem contribuição / indefinido [OBR] |
| — | Compare com > 250 commits (ex.: 600 em 3 páginas, mock) | — | Todos os 600 considerados [DER] |

### `cfr_ci(runs)` — variante (a)

| Caso normal | Caso limite | Caso inválido | Resultado esperado |
|---|---|---|---|
| 6 falhas (mix `failure`/`timed_out`/`startup_failure`) + 14 `success` + 5 `cancelled` + 3 `skipped` | **Somente `cancelled`/`skipped`** (denominador 0) | Run `event=schedule` com falha | **30%** (6/20) [DER]; `None`/NaN sem `ZeroDivisionError` [REC]; run **não** entra [OBR] |
| Vários workflows juntos (lint+test) | **`cancelled` ignorado** [OBR] | Run em outro branch | Agregado em conjunto [OBR]; fora [OBR] |
| — | `conclusion=None` (em andamento) | Run fora da janela | Ignorado [OBR] |

### `cfr_release(releases, window_end, is_corrective)` — variante (b)

| Caso normal | Caso limite | Caso inválido | Resultado esperado |
|---|---|---|---|
| **`v2.3.0` (10/05) → `v2.3.1` (12/05)**, só *patch*, commit `fix: crash ao abrir arquivo` | **Exatamente 7 d 0 h** depois | `v2.3.0 → v2.4.0` sem commit `fix` | `v2.3.0` **falhou** [OBR] · falhou (“em até 7 dias”) [DER] · não corretiva [DER] |
| **`v2.4.0` (01/06) → `v2.5.0` (20/06)** | **7 d 1 h** depois | — | `v2.4.0` **não falhou** [OBR] · não falhou [DER] |
| 10 releases, 2 falhas | **Release nos últimos 7 dias da janela** | — | CFR = 2/**avaliadas** (a release censurada fica **fora do denominador**) [OBR] |
| — | **Repo com 1 release** | — | Indefinido [OBR] |
| — | Tag fora de SemVer (`release-2020-01`), `v2.3.0`, `2.3.0-rc1` | Mensagem `prefix`/`fixture` | Heurística não quebra; `fix` como **palavra inteira** [REC] |

### `recovery_episodes(runs)` — tempo de recuperação

| Caso normal | Caso limite | Caso inválido | Resultado esperado |
|---|---|---|---|
| **09:00 success · 10:00 failure · 10:30 failure · 11:15 success (updated_at 11:20)** | **Falha nunca recuperada** [OBR] | `updated_at` do sucesso anterior ao `run_started_at` da falha | **1h20 = 1,333… h** [OBR] · episódio **censurado**; proporção reportada [OBR] · erro/aviso [REC] |
| 2 episódios (1h, 3h) → mediana | **`cancelled` entre as falhas** [OBR] | Runs fora de ordem | 2 h [DER] · ignorado: **não** quebra nem encerra o episódio [OBR] · função **ordena** antes [DER] |
| **2 workflows intercalados** (CI falha, Lint passa) | Sem falhas (0 episódios) | — | Sucesso do Lint **não** encerra a falha do CI [OBR E§11] · indefinido [REC] |
| — | Falha inicial **sem sucesso anterior** (⚠️ L09) | — | Comportamento **documentado** e testado |

### `classify_df / classify_lt / classify_cfr / classify_recovery`

| Caso normal | Caso limite (fronteiras exatas) | Caso inválido | Resultado esperado |
|---|---|---|---|
| DF=10 · LT=6 h · CFR=0,10 · REC=0,5 h | DF **7,0**→Elite; **6,99**→High; **1,0**→High; **0,230** (1/mês)→Medium (⚠️ L11) | DF negativo; NaN | Elite em todas [DER] |
| LT=3 d → High | LT **24 h**→High; **168 h**→Medium; **720 h**→Low; 23,99 h→Elite | LT negativo | conforme tabela [OBR] |
| CFR=0,20 → High | CFR **0,15**→Elite; **0,30**→High; **0,45**→Medium; 0,4501→Low | CFR > 1 ou < 0 | conforme tabela [OBR] |
| REC=3 h → High | REC **1 h**→High; **24 h**→Medium; **168 h**→Low | REC negativo | conforme tabela [OBR] |

### `classify_overall(scores)`

| Caso normal | Caso limite | Caso inválido | Resultado esperado |
|---|---|---|---|
| **(4,3,3,1)** | **(4,3,2,1)** → 2,5 | menos de 4 notas | **High** (mediana 3) [OBR] · **Medium** (floor 2,5) [DER] · erro/regra de L10 |
| (4,4,4,4) → Elite · (1,1,1,1) → Low | (4,4,3,1) → 3,5 · (4,4,1,1) → 2,5 | nota fora de 1–4 | Elite/Low [DER] · High / Medium [DER] · erro |

### Coletor/infra (testes de integração com mocks) — [REC] / [DER]

| Cenário | Esperado |
|---|---|
| Resposta com 3 páginas e `Link rel="next"` | Todas as páginas lidas [DER E§4] |
| `X-RateLimit-Remaining: 0` + `X-RateLimit-Reset` no futuro | Script **dorme** até o reset [OBR E§7] |
| Sequência 500, 500, 200 | Retentativas com 1 s, 2 s e sucesso [OBR E§7] |
| Interrupção a meio e reexecução | Chamadas já feitas **não** se repetem [OBR E§7] |
| Mês de runs com 1.000 resultados | Alerta/subdivisão [OBR E§4] |
| Token ausente | Erro claro; token não aparece em logs [DER E§7] |

## 12.3 Cobertura

- **Meta:** ≥ 80% **do módulo de métricas** (E§7). 💡 Mirar 90%+ nele (margem).
- **Prova:** relatório `--cov-report=term-missing` anexado/CI com `--cov-fail-under=80`.

## 12.4 Funções estatísticas (testes recomendados — [REC])

| Função | Caso | Esperado |
|---|---|---|
| `cliffs_delta(x, y)` | x todos > y | **+1** |
| `cliffs_delta(x, y)` | amostras idênticas | **0** |
| `cliffs_delta` com `U₁` | δ = 2·U₁/(n₁n₂) − 1 vs. cálculo manual | iguais |
| `epsilon_squared(H, n)` | H=10, n=101 | 0,1 |
| Holm | p=[0,01; 0,04; 0,03; 0,005] | ajustados = [0,03; 0,06; 0,06; 0,02] (cálculo à mão: ordem crescente × 4,3,2,1 + monotonicidade) |
| Kappa ponderado | classificações idênticas | κ = 1 |
| Kappa ponderado | rótulos como **texto** vs **inteiros** | resultados **diferentes** (prova da armadilha) |
| P/R/F1 | 40 marcadas, 30 corretas, 50 reais | P=0,75; R=0,60; F1≈0,667 |
| Fleiss | 3 avaliadores concordando em tudo, ≥ 2 categorias | κ = 1 |
| Fleiss | todas as avaliações numa única categoria | κ indefinido (NaN) — tratar |

---

# 13. PLANO DE REPRODUTIBILIDADE

> **Exigência:** outro grupo executará o pipeline **seguindo apenas o README**, sem ajuda do autor, em 30 repos do dataset original (E§7, E§9). Se travar, **é resultado a ser registrado**.

## 13.1 Teste mental obrigatório

> *"Se eu entregar apenas o repositório para outro grupo e não responder nenhuma pergunta, ele consegue executar?"*

**O que impediria (checar cada item):**

| Impedimento | Como evitar | Tag |
|---|---|---|
| Versão do Python não informada | README + `.python-version`/CI com versão fixa | DER |
| Dependências sem versão / `requirements.txt` ausente | `requirements.txt` com versões; instalar via `pip install -r` | DER (E§7 CI usa `requirements.txt`) |
| Token: não se sabe onde configurar | README: `export GITHUB_TOKEN=...`; escopos mínimos; **nunca** no repo | OBR |
| Janela de observação não declarada | Datas no `config.yaml` documentado | DER |
| Comando de execução ausente/ambíguo | **Um** comando (ex.: `python -m pipeline --config config.yaml`) | OBR |
| Como rodar nos **30 repos** | Parâmetro `--repos-file` e exemplo no README | DER |
| Cache: onde fica, como retomar/limpar | Seção "Cache e retomada" no README | OBR |
| Dataset original ausente | `data/` versionado + dicionário | DER |
| Como gerar métricas/análises | Comandos separados e documentados; notebooks reexecutáveis | OBR |
| Como rodar testes | `pytest --cov=metricas ...` documentado | OBR |
| Rate limit lento sem aviso | README estima tempo e explica esperas | REC |
| Caminhos absolutos, dependência do SO | Caminhos relativos; testar em Linux (CI) | REC |
| Dados em formatos sem explicação | Dicionário de dados | OBR |
| Parte dos passos "na cabeça do autor" | Revisão do README por quem **não escreveu** o código | REC |

## 13.2 Conteúdo mínimo do README (checklist)

- [ ] Objetivo e visão do pipeline (diagrama de etapas).
- [ ] **Requisitos:** versão do Python, SO testado, tempo estimado, espaço em disco.
- [ ] **Instalação:** `python -m venv`, `pip install -r requirements.txt`.
- [ ] **Token:** variável `GITHUB_TOKEN` e como obter.
- [ ] **Configuração:** `config.yaml` comentado (janela, limiares, sementes, caminhos).
- [ ] **Comando único** de execução.
- [ ] **Execução parcial/replicação:** como rodar com lista de repositórios (30).
- [ ] **Cache/retomada:** onde fica, como reiniciar, como limpar.
- [ ] **Saídas:** onde estão `funil.csv`, CSVs finais, dicionário.
- [ ] **Métricas:** como gerar; como cada coluna é calculada (link ao dicionário).
- [ ] **Análises:** como reexecutar notebooks/scripts a partir do CSV.
- [ ] **Testes e cobertura:** comando + meta de 80%.
- [ ] **CI:** badge/descrição.
- [ ] **Decisões do grupo** (L01–L22 resolvidas): critério de "popular", `válidos`, tratamento de censura etc.
- [ ] **Problemas conhecidos e solução de erros comuns.**
- [ ] **Link** do GitHub Projects.

## 13.3 Rotina de validação

1. Clonar em pasta vazia, **máquina/VM/Codespace limpos**.
2. Seguir **somente** o README (💡 cronometrar).
3. Rodar com **5–10 repos**, depois com **30**.
4. Comparar com o CSV oficial (diferença relativa, % mesma classificação).
5. Registrar falhas e **corrigir o README** (não só o código).
6. 💡 Repetir com um integrante que **não escreveu** o trecho.

---

# 14. GITHUB PROJECTS E CONTRIBUIÇÃO INDIVIDUAL

> **A correção parte do GitHub Projects** (E§10). Trate-o como parte da nota, não como burocracia.

## 14.1 Regras objetivas (E§10)

| Regra | Consequência |
|---|---|
| Cada integrante **Assignee** de ≥ 1 Issue **com artefato de código** (script, teste, notebook ou análise) **por sprint** (S01, S02, S03, Final) | Sem commits atribuíveis ⇒ **zera a parcela individual** do integrante naquela sprint |
| **Commit sem `#N` não é considerado** | Perde-se a evidência do trabalho |
| Desconto de **até 10% da nota da sprint** se: **WIP não respeitado**, **Issue sem Assignee**, **cartões desatualizados**, **ausência de evolução semanal** | Perda direta de nota |
| Issues recebidas do replicador devem estar **no próprio Project** | Faz parte da nota "Resposta às Issues" |

## 14.2 Estrutura do Project (💡 [RECOMENDAÇÃO])

- Colunas: **Backlog → To do (sprint) → In progress → In review → Done**.
- **WIP** (⚠️ L14: limite não definido): 💡 máx. 1–2 cartões `In progress` por pessoa; escrito no README do board.
- Campos: `Sprint` (S01/S02/S03/Final), `Assignee`, `Tipo` (código/escrita/dados/rotulagem), `Artefato`, `RQ`.
- Rótulos (labels): `sprint-s01`…, `codigo`, `artigo`, `rotulagem`, `bug`, `replicacao`.
- **Issues de replicação recebidas** com label `replicacao-recebida`.

## 14.3 Issues que devem existir, por sprint (uma Issue = um artefato verificável)

> A divisão A/B/C é **sugestão** do professor. O que importa é: cada pessoa com código por sprint.

### S01

| Issue | Assignee sug. | Artefato | Evidência | Commits |
|---|---|---|---|---|
| Estrutura do repo, `config`, README base, `.gitignore`, `requirements` | A (💡) | Esqueleto | `main` | `#n` |
| `http_client` + rate limit + backoff | C | `http_client.py` + testes | Teste de rate/backoff | `#n` |
| Cache + retomada | C | `cache.py` + teste de interrupção | Teste verde | `#n` |
| Seleção + filtros + funil | A | `selection.py`, `funil.csv` | Funil gerado | `#n` |
| Coleta de metadados | A | `collect_metadata` | Colunas no CSV | `#n` |
| Coleta de releases/tags | B | `collect_releases/tags` | JSON/CSV | `#n` |
| Coleta de commits entre releases (compare paginado, 404) | B | `collect_commits` | Teste com paginação/404 | `#n` |
| Coleta de runs (fatiada por mês) | C | `collect_runs` | Log mensal e teto | `#n` |
| Lead time (a)/(b) + testes | B | `metricas.lead_time` + testes | Cobertura | `#n` |
| CFR(a) + recuperação + testes | C | `metricas.cfr/recovery` + testes | Cobertura | `#n` |
| **DF + classificação DORA + testes** (⚠️ sem dono na sugestão) | A (💡) | `metricas.dora` + testes | Fronteiras testadas | `#n` |
| CI (`testes.yml`) | qualquer (💡 A) | Workflow | Actions verde | `#n` |
| Artigo: Introdução + hipóteses | os três | `artigo/` | `.tex` | `#n` |

### S02

| Issue | Assignee | Artefato | Evidência |
|---|---|---|---|
| Rotulagem independente — pessoa A | A | `labels_A.csv` | Commit do autor |
| Rotulagem independente — pessoa B | B | `labels_B.csv` | Commit do autor |
| Rotulagem independente — pessoa C | C | `labels_C.csv` | Commit do autor |
| Concordância (Fleiss) + consenso + protocolo | A | `agreement.py`, `consenso.csv`, `PROTOCOLO_CONSENSO.md` | κ por dimensão |
| Heurística corretiva + P/R/F1 + refinamento | B | `heuristica.py`, `evaluate_heuristic.py` | Tabela versão→F1 |
| Coleta completa + dataset + dicionário | C | `consolidate_dataset.py`, CSVs, dicionário | ≥ 300 repos |
| Sorteio da amostra-ouro + planilhas | 💡 A ou C | `sample_gold.py` | Reprodutível |
| Artigo: Metodologia | os três | `artigo/` | PDF |

### S03

| Issue | Assignee | Artefato |
|---|---|---|
| RQ01–RQ04 + classificação C1 | A | notebook/script |
| RQ05 | B | notebook/script |
| RQ06 | B | notebook/script |
| RQ07 | C | notebook/script |
| RQ08 (opcional) | C | notebook/script |
| Artigo: Resultados + Discussão | os três | `artigo/` |

### Final

| Issue | Assignee | Artefato |
|---|---|---|
| Executar pipeline do outro grupo + log/script | A | `replicacao/` |
| Comparação + Issues de divergência | B | `replicacao/compara.py`, Issues no repo do autor |
| Tratar Issues recebidas no próprio pipeline | C | commits `#n`, respostas |
| Artigo: Ameaças + Replicação + revisão | os três | `artigo/` |

## 14.4 Como vincular commit à Issue

- Mensagem: `tipo(escopo): descrição (#N)` — ex.: `feat(collect): paginação do compare (#12)`.
- Para fechar automaticamente: `closes #12` no PR/commit. Para apenas referenciar: `#12`.
- 💡 Hook/CI que **falha** se a mensagem do commit não tiver `#\d+` (⭐ D13).
- Commits "wip", "fix", "ajustes" **sem `#N` não contam** (E§10).

## 14.5 Como demonstrar contribuição individual

- Cada integrante **autor** (git author) dos commits da sua Issue (configurar `user.name/email` corretos).
- Arquivos de rótulos **por pessoa** (S02) commitados pelo próprio autor.
- Notebook/script próprio por análise (S03).
- Evitar "commits em nome de outro" e squash que apague a autoria 💡 (usar *rebase and merge* ou *merge commit* quando houver PR).
- 💡 `git shortlog -sn --all` por sprint para auditar (⭐ D13).

## 14.6 Evidência de "evolução semanal"

- Mover cartões **durante a semana**, não só no último dia.
- 💡 Registrar print/exportação semanal do board (ou usar *Insights/Burnup*).
- Issues com comentários de progresso e links de commits.

## 14.7 O que atualizar ao final de cada sprint

- [ ] Todas as Issues da sprint **fechadas ou justificadas**; sem Issue sem Assignee.
- [ ] Cartões em `Done` com link para artefato.
- [ ] Issues recebidas (Final) no Project.
- [ ] WIP respeitado.
- [ ] Nenhum cartão "esquecido" em `In progress`.

---

# 15. MAPA DO ARTIGO

> **Formato:** artigo científico, **template SBC (Overleaf)**, **≤ 10 páginas**, escrito aos poucos (E§8). É a base do artigo atualizado no Lab04. ⚠️ L19: idioma não definido.

## 15.1 Quando cada parte é entregue

| Sprint | Seção(ões) | Conteúdo obrigatório |
|---|---|---|
| **S01** | **Introdução + hipóteses** | Contexto DORA/proxies; problema; objetivo; **1 hipótese informal por RQ** (o que esperamos e por quê), **escrita antes de ver os dados** |
| **S02** | **Metodologia** | Fonte de dados; **funil de seleção**; janela; **definições operacionais e variantes**; **protocolo de validação manual** |
| **S03** | **Resultados** + **Discussão** | Por RQ: **mediana, IQR, classificação DORA**, tabelas/gráficos; **hipóteses vs. resultados; o que surpreendeu e por quê** |
| **Final** | **Ameaças à validade** + **Replicação cruzada** + **link** + revisão geral | Quatro categorias apoiadas em resultados; relato da replicação |

## 15.2 Estrutura obrigatória (E§8) e conteúdo de cada seção

| # | Seção | Conteúdo obrigatório | Evidências a inserir |
|---|---|---|---|
| 1 | **Introdução** | Hipótese informal **por RQ**, antes dos dados | Tabela RQ→hipótese→justificativa (💡) |
| 2 | **Metodologia** | Fonte de dados (API GitHub REST/GraphQL); **funil**; **janela (datas)**; definições operacionais (E§3) e **variantes** (LT a/b; CFR a/b; combinações C1–C3); critério mínimo; censura; **validação manual** (sorteio com semente, 3 rotuladores, Fleiss, consenso, P/R/F1, versões da heurística) | Tabela do funil; tabela de definições; tabela de versões da heurística |
| 3 | **Resultados por RQ** | **Mediana, IQR e classificação DORA**; RQ04 com censura; RQ05 ρ,p,n por variante; RQ06 (≥ 3 fatores, Holm, ε²/δ); RQ07 (% mudança, κ por par) | Tabelas e gráficos (dispersão obrigatória em RQ05) |
| 4 | **Discussão** | **Hipóteses × resultados; surpresas e porquês**; divergência LT(a)×(b); CFR(a) ≠ produção; tese DORA; robustez (RQ07) | — |
| 5 | **Ameaças à validade** | **Construto** (release ≠ deploy; CI ≠ produção), **Interna** (repos antigos têm mais releases; `author.date` vs rebase/squash), **Externa** (populares ≠ corporativos), **Conclusão** (muitas comparações; subgrupos pequenos) — cada uma **apoiada nos resultados da validação manual e da sensibilidade** | κ, F1, % mudança da RQ07 |
| 6 | **Replicação cruzada** | Foi reproduzível? O que impediu/dificultou? Diferenças e explicações | Tabela de diferença relativa e % classificação |
| 7 | **Link do repositório/GitHub Projects** | Preencher `<preencher>` | — |

## 15.3 Itens "escondidos" que o artigo precisa conter

- [ ] Ameaça: **rebase/squash distorcem `commit.author.date`** (E§3 manda registrar).
- [ ] **Quantos casos censurados** (CFR(b) últimos 7 dias; episódios RQ04).
- [ ] **Quantas releases ignoradas por 404** (E§11).
- [ ] **Por que as duas variantes de lead time divergem** (E§5).
- [ ] **Diferença entre CFR(a) e falha em produção** (E§5).
- [ ] **Kappa baixo = critério ambíguo = achado** a discutir (E§6).
- [ ] **Histórico de versões da heurística com F1** (se F1 < 0,70, E§6).
- [ ] Tabela de cortes **adaptada** (não oficial DORA) explicada (E§5).
- [ ] **Tipo do projeto só nos 60 rotulados** se usado na RQ06 (🔎 consequência).

## 15.4 Como apoiar cada ameaça em resultado (checklist)

| Categoria | Pergunta | Evidência que o grupo deve citar |
|---|---|---|
| Construto | Estamos medindo o que achamos? | Fleiss dimensão (ii) "releases = entregas reais"; F1 da heurística; CFR(a) vs (b); RQ07 |
| Interna | Fatores não controlados? | RQ06 (idade, popularidade, linguagem); rebase/squash; 404 |
| Externa | Vale além da amostra? | Funil (só populares com Actions e ≥ 5 releases); distribuição de linguagens/tipos |
| Conclusão | Estatística adequada? | Holm; nº de testes; `n` por subgrupo; ε²/δ; Spearman só monotônico; p vs efeito |

---

# 16. DEPENDÊNCIAS

## 16.1 Tabela geral

| Tarefa | Depende de | Não pode começar antes de |
|---|---|---|
| `config.yaml` (janela) | Datas do professor (⚠️ L01) | Coleta de runs/releases com filtro de janela |
| `http_client` (rate limit/backoff) | Token configurado | Qualquer coletor |
| `cache` + retomada | `http_client` | Coleta em escala; teste de interrupção |
| `selection` (busca + fatiamento) | `http_client`, `cache` | Funil, coleta |
| Filtro `total_count=0` | `selection` (candidatos) | Chamar releases/runs (E§4: antes de gastar chamadas) |
| Filtro ≥ 5 releases / ≥ 50 runs | `collect_releases`, `collect_runs` (ou contagem barata) | Amostra final |
| Funil | Todas as etapas de filtro | Seção Metodologia |
| `collect_metadata` | `selection` | RQ06 (fatores) |
| `collect_releases` (inclui pré-janela) | `cache`, `selection` | `collect_commits`, lead time, CFR(b), DF |
| `collect_tags` | `selection` | Variante tag da RQ07 |
| `collect_commits` (compare paginado) | `collect_releases` | Lead time (a)/(b), heurística (mensagens) |
| `collect_runs` (por mês) | `selection`, `default_branch` (metadados) | CFR(a), RQ04 |
| Funções de métrica | Definições da E§5 (não dependem de rede) | Cálculo em escala; testes |
| Testes + cobertura | Funções de métrica | CI com `--cov-fail-under=80` |
| CI | `requirements.txt`, testes | Fechamento da S01 |
| Hipóteses (Introdução) | Leitura do enunciado (nenhum dado) | **Antes** de qualquer análise (S03) |
| Amostra final ≥ 300 | Pipeline estável + cache | Sorteio da amostra-ouro |
| Sorteio de 60 repos | **Lista final congelada** | Rotulagem |
| Sorteio das 5 releases | Sorteio dos 60 | Planilhas de rotulagem |
| Rotulagem (3 pessoas) | Planilhas **sem** a saída da heurística | Kappa e consenso |
| Kappa de Fleiss | 3 arquivos de rótulos | Interpretação / Discussão |
| Consenso | Rótulos individuais prontos + protocolo | P/R/F1; tipo do projeto (RQ06) |
| P/R/F1 | Consenso + heurística v1 | Refinamento da heurística |
| **Heurística final validada** | P/R/F1 (F1 ≥ 0,70 ou versões documentadas) | **CFR(b) final**, RQ03(b), RQ05(b), RQ08 (rework) |
| Dataset CSV | Métricas calculadas | Dicionário completo; S03 |
| Dicionário de dados | Colunas do CSV finalizadas | Replicação (outro grupo) |
| RQ01–RQ04 | CSV final | Classificação C1; RQ05–RQ07 |
| Classificação C1 | RQ01–RQ04 (DF, LT(a), CFR(a), recuperação) | RQ07 |
| RQ05 | DF (RQ01), CFR (RQ03 a e b) | Discussão da tese DORA |
| RQ06 | RQ01–RQ04 + fatores (+ **tipo do projeto** do consenso, se usado) | Holm; tamanho de efeito |
| RQ07 | Colunas das ≥ 3 combinações (pré-release/tag) | Discussão de robustez |
| RQ08 (rework) | Heurística final | — |
| RQ08 (Mann-Kendall) | Métricas por trimestre | — |
| Resultados + Discussão | RQ01–RQ07 prontas | Ameaças à validade |
| Ameaças à validade | Resultados da validação manual (κ, F1) e da sensibilidade (RQ07) | Artigo final |
| Replicação (como replicador) | README/dataset do outro grupo; sorteio do professor; 30 repos definidos (⚠️ L15) | Comparação e Issues |
| Comparação | Execução do replicador | Issues de divergência |
| Resposta às Issues | Issues recebidas; pipeline do grupo | Fechamento da entrega final |
| Artigo final | Todas as seções + replicação | Entrega |

## 16.2 Fluxo crítico (caminho mais longo)

`janela (L01)` → `http_client/cache` → `seleção/funil` → `coleta completa (300+)` → **`congelar lista`** → `sorteio 60 + 5 releases` → `rotulagem independente` → `kappa/consenso` → `P/R/F1 + refinamento` → **`heurística final`** → `CFR(b)/RQ03b` → `RQ05(b)/RQ06/RQ07` → `Resultados/Discussão` → `Ameaças` → `replicação`.

Qualquer atraso na **janela**, na **coleta de 300+** (rate limit) ou na **rotulagem** empurra todo o resto. 💡 Rotulagem é trabalho humano pesado (**420 julgamentos por pessoa**): agendar cedo.

---

# 17. ARMADILHAS (O QUE PODE DAR ERRADO)

> Formato: **Problema → consequência → como detectar → como evitar.** Tags: DER/REC conforme a origem.

## 17.1 S01

| # | Problema | Consequência | Como detectar | Como evitar |
|---|---|---|---|---|
| 1 | Search limitado a 1.000 resultados | Menos candidatos que o necessário; vieses de ordenação | `total_count` > 1.000 mas só 1.000 retornados | Fatiar por faixas de estrelas/linguagem (E§4) |
| 2 | Rate limit estourado | Coleta cai com 403/429 | Logs; `X-RateLimit-Remaining=0` | Ler cabeçalhos e dormir até `Reset`; `GET /rate_limit` não gasta cota (E§4) |
| 3 | 5xx transitórios | Falha espúria derruba a coleta | Exceção em um repo | Backoff 1,2,4,8… com limite (E§7) |
| 4 | Paginação ignorada | Dados truncados (30 itens/pág., releases/commits perdidos) | Contagens "redondas" (30, 100) | Seguir `Link rel="next"` (E§4) |
| 5 | `compare` sem paginação | Máx. 250 commits ⇒ lead time errado | Releases com exatamente 250 commits | `per_page`/`page` (E§4) |
| 6 | Runs > 1.000 por consulta | Runs ausentes ⇒ CFR(a)/recuperação enviesados | Algum mês com exatamente 1.000 | Dividir por mês e **conferir teto**, subdividindo se atingir (E§4) |
| 7 | Cortar releases pré-janela | 1ª release da janela perde a "release anterior" | LT nulo para 1ª release | Coletar histórico de releases completo (DER) |
| 8 | Repos sem Actions entram na coleta | Desperdício de cota | `total_count=0` tarde demais | Filtro precoce (E§4) |
| 9 | Draft/pré-release contados como deploy | DF/CFR(b) inflados | Comparar com contagem do site | Filtrar `draft`/`prerelease` (E§3) |
| 10 | Runs de `schedule`/outros branches | Falhas espúrias | Conferir `event` e `head_branch` | `event=push`, `branch=<default>` (E§3) |
| 11 | `cancelled`/`skipped` tratados como falha | CFR(a) inflado | Teste parametrizado | Tabela de `conclusion` (E§3) |
| 12 | Token no Git | Vazamento de credencial | Varredura de histórico | Env var + `.gitignore` (E§7) |
| 13 | Cobertura medida no módulo errado | CI "verde" sem cumprir E§7 | `--cov=` ≠ nome do módulo | Alinhar nome do módulo |
| 14 | Hipóteses escritas depois | Introdução inválida (E§8) | Datas de commit | Commit/tag `hipoteses-v1` antes das análises |
| 15 | Commit sem `#N` | Trabalho não contabilizado | `git log` | Hook/padrão de mensagem |
| 16 | Um integrante sem código | **Zera parcela individual** | `git shortlog` por sprint | Issues de código para cada um |
| 17 | Cache corrompido por interrupção | Retomada quebra | JSON inválido | Escrita atômica (arquivo temporário + rename) |
| 18 | Datas em fusos diferentes | Janela/lead time deslocados (⚠️ L18) | Comparar com UI | Trabalhar em UTC |

## 17.2 S02

| # | Problema | Consequência | Como detectar | Como evitar |
|---|---|---|---|---|
| 1 | Amostra < 300 após filtros | Entrega incompleta (E§10) | `len(df)` | Alargar busca cedo; monitorar funil |
| 2 | Rate limit "várias vezes" (E§11) | Coleta de dias | Logs | Começar cedo; rodar em segundo plano; retomada |
| 3 | Descartar casos censurados | Repos parecem mais rápidos para se recuperar (E§3) | Contagem de censurados = 0 suspeito | Campo `censored` e contagem reportada |
| 4 | Heurística vê/influencia rotuladores | Validação circular | Planilha com coluna da heurística | Planilhas **sem** saída da heurística (E§6) |
| 5 | Rotuladores combinam rótulos | Kappa inflado | Rótulos idênticos demais | Rotular **sem consultar** os demais (E§6) |
| 6 | 5 releases diferentes por avaliador | Kappa inválido | IDs de release não coincidem | Sorteio único com semente |
| 7 | Amostra final muda depois do sorteio | Amostra-ouro não pertence à amostra final | Repos da gold fora do final | Congelar antes (DER) |
| 8 | Só "% concordância" | Ignora acaso (E§6) | — | Fleiss via `aggregate_raters` |
| 9 | Kappa NaN (todos numa categoria) | Valor indefinido | `nan` | Tratar caso degenerado; discutir |
| 10 | F1 < 0,70 e sem refinamento | Descumpre E§6 | F1 do relatório | Iterar e **documentar cada versão** |
| 11 | Overfitting da heurística | F1 otimista | Ajustes casuísticos | 💡 Declarar como ameaça; ⭐ D7 (análise de erros) |
| 12 | Sem dicionário de dados | Replicador não compara (E§7) | Coluna sem entrada | Verificação automática |
| 13 | Unidades confusas (h vs dia) | Classificação errada | Valores absurdos | Dicionário com unidade; testes de fronteira |
| 14 | CFR(b) sem excluir os últimos 7 dias | CFR subestimado/ruído | Releases tardias avaliadas | Excluir do denominador e **contar** (E§5) |
| 15 | `compare` 404 não tratado | Crash ou lead time errado | Exceção 404 | Registrar, ignorar e contar (E§11) |
| 16 | Dados de pré-release/tag não coletados | RQ07 trava | Colunas ausentes | Planejar colunas da RQ07 na S02 (DER) |
| 17 | Misturar workflows no tempo de recuperação | Recuperação artificialmente curta | Episódios mistos | Agrupar **por workflow** (E§11) |

## 17.3 S03

| # | Problema | Consequência | Como detectar | Como evitar |
|---|---|---|---|---|
| 1 | Média/DP | Distorção por outliers (E§5) | Tabelas | Mediana e IQR |
| 2 | Holm esquecido ou parcial | Falsos positivos (E§5) | Nº de p ajustados < nº de testes | Corrigir **todos** os testes |
| 3 | Só p-valor | Não se sabe o tamanho do efeito | Tabela sem ε²/δ | ε² (KW), δ (2 grupos) |
| 4 | Cliff's δ com sinal trocado | Interpretação invertida | Teste com x>y | Fixar ordem `(x, y)`; documentar |
| 5 | KW em 2 grupos / MW em ≥ 3 | Teste errado | — | Regra explícita (E§5) |
| 6 | Kappa ponderado com texto | Ordem alfabética distorce pesos | Resultado muda ao recodificar | Inteiros 1–4 |
| 7 | Tipo do projeto com n≈60 | Baixo poder; conclusões frágeis | `n` por grupo | Reportar `n`; evitar extrapolar |
| 8 | Subgrupos minúsculos | Testes instáveis | `n` < 5 | Agrupar "Outras" |
| 9 | Spearman só para (a) ou (b) | Incumpre E§5 | Falta variante | Rodar as duas |
| 10 | RQ05 com escala linear e dados assimétricos | Gráfico ilegível | Pontos colados nos eixos | Escala log (E§5) |
| 11 | "Correlação implica causalidade" | Conclusão inválida | Texto | Redação cuidadosa (E§5) |
| 12 | Descartar censura na RQ04 | Viés (E§3) | Proporção ausente | Reportar proporção |
| 13 | Notebook não reexecutável | Perde pontos (E§10) | Rodar do zero | Seeds fixas; ordem de células; caminhos relativos |
| 14 | Resultados sem comparar com hipóteses | Discussão incompleta (E§8) | — | Tabela hipótese×resultado |
| 15 | RQ07 com combinações idênticas | Sensibilidade nula/artificial | % mudança = 0 em tudo | Combinações **realmente distintas** (≥ 3) |
| 16 | NaN tratado como valor | Estatísticas erradas | `n` inesperado | Registrar `n` e política de NaN (⚠️ L10) |

## 17.4 Entrega final

| # | Problema | Consequência | Como detectar | Como evitar |
|---|---|---|---|---|
| 1 | README do autor insuficiente | Replicador trava | — | **Registrar** como resultado (E§9) |
| 2 | Pedir ajuda ao autor | Quebra o protocolo (E§9) | — | Só o README |
| 3 | Issue sem evidência | Perde pontos (E§9) | — | Comando + erro + esperado/obtido |
| 4 | Comparar com dataset errado/versão diferente | Divergência artificial | Hash do CSV | Usar o CSV do `main` do autor e citar commit |
| 5 | Diferenças "inexplicadas" | Replicação sem análise | — | Explicar: repos continuam recebendo commits; datas de coleta (E§9) |
| 6 | Ignorar Issues recebidas | Perde o ponto de resposta | — | Responder **todas**; no Project |
| 7 | Ameaças "genéricas" | Perde pontos (E§8) | Texto sem números | Citar κ, F1, % mudança |
| 8 | Estourar 10 páginas | Descumpre E§8 | Compilar | Cortar/condensar |
| 9 | Link `<preencher>` | Falta item obrigatório | Busca no `.tex` | Preencher |
| 10 | Integrante A sem código (só "executou") | Zera parcela individual | `git shortlog` | Artefato de replicação (log/script) |

---

# 18. CRITÉRIOS DE ACEITE DAS TAREFAS CRÍTICAS

> Para cada tarefa: 1) deve existir · 2) como saberemos que funciona · 3) como testar · 4) artefato · 5) resultado esperado · 6) evidência a guardar.

### T1 — Cache e retomada (S01-015/016)
- **Obrigatório?** Sim (E§7).
- **Deve existir:** persistência de **cada resposta da API** em disco (JSON por repo+endpoint ou SQLite).
- **Aceite:** 1ª execução consulta a API · 2ª execução **reutiliza** respostas · interromper (`Ctrl+C`, queda de rede, rate limit) **não perde o progresso** · reexecutar o comando **continua de onde parou**, **sem repetir** chamadas.
- **Como testar:** rodar em 5 repos; contar requisições; rodar de novo (esperado: 0 novas); matar no meio; reexecutar (só as faltantes).
- **Artefato:** `cache.py`, diretório/SQLite, teste.
- **Resultado esperado:** contador de requisições na 2ª execução ≈ 0 para o já coletado.
- **Evidência:** teste automatizado, log com "cache hit/miss", seção do README.

### T2 — Rate limit (S01-017)
- **Obrigatório?** Sim.
- **Aceite:** o script lê `X-RateLimit-Remaining`/`Reset`; quando `Remaining=0`, **espera automaticamente** até o `Reset` e continua.
- **Como testar:** mock com `Remaining=0` e `Reset=agora+2s`; verificar espera e continuidade.
- **Evidência:** teste + log "aguardando até <epoch>".

### T3 — Backoff exponencial (S01-018)
- **Aceite:** 5xx ⇒ esperas 1 s, 2 s, 4 s, 8 s… até limite (⚠️ L21); depois, erro claro.
- **Como testar:** mock 500,500,500,200; medir sequência de `sleep`.
- **Evidência:** teste com `sleep` mockado; configuração documentada.

### T4 — Funil de seleção (S01-007)
- **Aceite:** tabela **gerada pelo pipeline** com nº de repos por etapa **e motivo** de descarte; `soma(saídas) + restantes = entradas`.
- **Como testar:** executar em 100 repos; conferir consistência; reexecutar (mesmos números ou diferença justificada pela cache).
- **Artefato:** `outputs/funil.csv` (+ tabela no artigo).
- **Evidência:** arquivo + trecho do log.

### T5 — Coleta de workflow runs (S01-014)
- **Aceite:** só `event=push` + default branch; `created=` por mês; **nenhum mês** com 1.000 resultados sem subdivisão.
- **Como testar:** repo ativo; logar contagem/mês; forçar mock de 1.000 e verificar subdivisão.
- **Evidência:** log por mês; teste.

### T6 — Lead time (S01/S02, RQ02)
- **Aceite:** reproduz o exemplo `v1.1` (13 dias) em (a) e {13,5,1} em (b); 1ª release da história é ignorada; 404 ignorado e contado; compare paginado.
- **Como testar:** fixtures + mocks de compare com 600 commits.
- **Evidência:** testes verdes; coluna `n_releases_ignored_404`.

### T7 — Tempo de recuperação (S01/S02, RQ04)
- **Aceite:** exemplo (09:00…11:20) = 1h20; `cancelled` ignorado; 2 workflows independentes; falha sem recuperação ⇒ **censurada** e proporção reportada.
- **Evidência:** testes; coluna `prop_episodes_censored`.

### T8 — CFR (a) e (b) (S01/S02, RQ03)
- **Aceite (a):** `falhas/(falhas+sucessos)`, só `push`/default/janela, todos os workflows juntos. **(b):** exemplos `v2.3.0` falhou / `v2.4.0` não falhou; últimos 7 dias fora do denominador.
- **Evidência:** testes + contagem de censura.

### T9 — Classificação DORA (S01/S03)
- **Aceite:** todas as **fronteiras** da tabela; geral = mediana (4/3/2/1) **arredondada para baixo**; (4,3,3,1) → High.
- **Evidência:** testes parametrizados.

### T10 — Dataset + dicionário (S02-005)
- **Aceite:** **toda** coluna dos CSVs finais no dicionário com nome, tipo, unidade, fórmula/origem; `≥ 300` linhas; sem duplicatas.
- **Como testar:** script compara `df.columns` × dicionário.
- **Evidência:** CSV + dicionário + script de verificação.

### T11 — Validação manual (S02-007…012)
- **Aceite:** semente fixa no código; 3 arquivos de rótulos independentes; mesmas 5 releases/repo; κ Fleiss nas 3 dimensões; protocolo de desempate no repo; consenso.
- **Como testar:** reexecutar sorteio ⇒ mesma lista; hash dos 3 arquivos distintos; κ recalculável do zero.
- **Evidência:** `sample_gold.py`, `labels_{A,B,C}.csv`, `agreement.py`, `PROTOCOLO_CONSENSO.md`.

### T12 — Avaliação da heurística (S02-014/015)
- **Aceite:** P/R/F1 vs consenso; se F1 < 0,70, nova versão e novo F1; **todas as versões documentadas**.
- **Evidência:** tabela `versão | descrição | P | R | F1` no artigo + commits `#N`.

### T13 — RQ05 (S03-006)
- **Aceite:** `spearmanr` para (a) **e** (b); **ρ, p, n**; dispersão (log se necessário); texto sobre tese DORA e causalidade.
- **Evidência:** tabela, figura, notebook.

### T14 — RQ06 (S03-007…009)
- **Aceite:** ≥ 3 fatores × 4 métricas (≥ 12 testes); KW/MW correto; **Holm** sobre todos; ε²/δ por linha.
- **Evidência:** tabela completa; `multipletests(method='holm')` no código.

### T15 — RQ07 (S03-010/011)
- **Aceite:** ≥ 3 combinações; 3 pares; % mudança e κ linear (rótulos inteiros); discussão de robustez.
- **Evidência:** tabela + matriz de transição + parágrafo.

### T16 — Replicação cruzada (SF-001…006)
- **Aceite:** só README; 30 repos; comparação (diferença relativa, % classificação); Issues com evidências; seção no artigo.
- **Evidência:** `replicacao/`, links das Issues, tabela no artigo.

### T17 — Resposta às Issues recebidas (SF-007/008)
- **Aceite:** toda Issue com resposta (commit `#N` ou justificativa); todas no Project.
- **Evidência:** Issues fechadas/comentadas; board.

---

# 19. DEFINITION OF DONE POR SPRINT

## 19.1 S01 — Definition of Done
- [ ] Pipeline roda com **um comando** (README) para **100 repos**.
- [ ] Seleção + **funil automático** com motivos.
- [ ] Releases (incl. pré-janela), tags, commits entre releases (paginados) e runs (push/default/janela/mês) coletados.
- [ ] **Cache/retomada** demonstrados.
- [ ] **Rate limit** e **backoff** testados.
- [ ] Token em variável de ambiente; **não** está no Git.
- [ ] Funções DF, LT(a)(b), CFR(a), recuperação, classificação **implementadas**.
- [ ] **Testes com fixtures**, incluindo os **4 casos de borda**.
- [ ] **Cobertura ≥ 80%** do módulo de métricas.
- [ ] **CI verde** no GitHub Actions.
- [ ] Introdução + **1 hipótese por RQ** (antes dos dados).
- [ ] Issues com **Assignee**; **cada integrante** com Issue de código.
- [ ] Commits com **`#N`**.
- [ ] Board atualizado; WIP respeitado; evolução semanal.
- [ ] Evidências arquivadas (prints/logs).
- [ ] **Revisão** pelos três.

## 19.2 S02 — Definition of Done
- [ ] **≥ 300 repos** após filtros; funil final.
- [ ] Todas as métricas/variantes calculadas; **censura e 404 contados**.
- [ ] CSV + **dicionário completo** (verificação automática).
- [ ] **60 repos** sorteados com semente fixa; **mesmas 5 releases** para os 3.
- [ ] **3 arquivos de rótulos** independentes commitados por seus autores.
- [ ] **Fleiss** nas 3 dimensões; interpretação (Landis & Koch).
- [ ] **Consenso** + protocolo de desempate versionado.
- [ ] **P/R/F1** da heurística; se F1 < 0,70, **refinar** e documentar versões.
- [ ] **Metodologia** completa no artigo.
- [ ] Testes/CI verdes; cobertura ≥ 80%.
- [ ] Issues, `#N`, board, individual por integrante.
- [ ] Revisão pelos três.

## 19.3 S03 — Definition of Done
- [ ] RQ01–RQ07 com tabelas e gráficos (mediana/IQR/classificação).
- [ ] RQ04 com proporção de censura.
- [ ] RQ05: ρ, p, n (a) e (b) + dispersão.
- [ ] RQ06: ≥ 3 fatores; Holm; ε²/δ.
- [ ] RQ07: ≥ 3 combinações; % mudança + κ ponderado por par; robustez discutida.
- [ ] (Opcional) RQ08 pronto.
- [ ] Cada análise em **notebook/script reexecutável a partir do CSV** (testado do zero).
- [ ] Resultados + Discussão revisados (hipóteses × resultados).
- [ ] CI verde; Issues, `#N`, board; cada integrante com análise.
- [ ] Revisão pelos três.

## 19.4 Entrega final — Definition of Done
- [ ] Replicação executada **só com o README**, em **30 repos**.
- [ ] Comparação (diferença relativa; % mesma classificação) e explicação.
- [ ] **Issues abertas** ao autor com evidências completas.
- [ ] **Todas** as Issues recebidas respondidas e no Project.
- [ ] Seção **Replicação cruzada** escrita.
- [ ] **Ameaças à validade** (4 categorias, com números).
- [ ] Artigo SBC **≤ 10 páginas**, **7 itens**, link preenchido, revisado.
- [ ] CI verde; commits `#N`; cada integrante com código/artefato.
- [ ] Board atualizado.
- [ ] Revisão final pelos três.

---

# 20. DIFERENCIAIS POSSÍVEIS ⭐

> **Regra de prioridade:** (1) cumprir **100% do obrigatório**; (2) garantir **qualidade e reprodutibilidade**; (3) **só então** diferenciais. **Nada desta seção é exigido pelo professor.** Todos são [DIFERENCIAL].
> Critério de escolha: cada um **reforça um requisito que o enunciado já valoriza** (confiabilidade das métricas, validação, sensibilidade, reprodutibilidade).

## 20.1 Catálogo

### ⭐ D1 — Relatório automático de qualidade dos dados
- **O que fazer:** script que gera `data_quality.md/.csv` com: nulos por coluna, duplicatas, datas inconsistentes (commit **após** a release — ⚠️ L07), runs fora da janela, contagem de censurados e 404, repos com poucos runs/mês, distribuição por linguagem.
- **Por que:** a pergunta central do lab é "o quanto podemos confiar?" (E§1); isso audita a **entrada**.
- **Esforço:** baixo–médio · **Risco:** baixo · **Quando:** S02 (antes do CSV final) · **Dependência:** dataset consolidado.
- **Impacto:** transforma "tratamos nulos" em evidência; alimenta Ameaças à validade (interna/conclusão).

### ⭐ D2 — Sanity checks e invariantes automáticos
- **O que fazer:** asserts pós-cálculo (ex.: `0 ≤ CFR ≤ 1`; `lead_time ≥ 0`; `n_eval + n_censored = n_releases`; todas as colunas no dicionário; `soma do funil` fecha). Falha o pipeline com mensagem clara.
- **Por que:** pega bugs silenciosos que testes unitários não cobrem em dados reais.
- **Esforço:** baixo · **Risco:** baixo · **Quando:** S01–S02 · **Dependência:** métricas e dicionário.
- **Impacto:** reduz risco de resultados inconsistentes e de Issues na replicação.

### ⭐ D3 — Testes mais abrangentes (property-based + regressão)
- **O que fazer:** Hypothesis para propriedades (ex.: lead time (b) invariante a ordem dos commits; mediana com 1 elemento; `classify_overall` monotônica); *golden files* de saída para 3 repos; cobertura 90%+ do módulo de métricas.
- **Por que:** E§7 pede ≥ 80%; ir além mostra rigor.
- **Esforço:** médio · **Risco:** baixo · **Quando:** S01–S02 · **Dependência:** funções de métrica estáveis.
- **Impacto:** alta confiança nas definições; ótima história para o artigo.

### ⭐ D4 — Sensibilidade ampliada (além das 3 combinações mínimas)
- **O que fazer:** varrer parâmetros de forma controlada: janela do CFR(b) (3/7/14 dias), mínimo de releases (5 vs 10), tratamento de censura da RQ04 (excluir vs limite inferior com fim da janela), pontos de corte da tabela ±10%; reportar % de mudança e κ.
- **Por que:** E§5 RQ07 exige ≥ 3; este extra responde "robusto a quê, exatamente?".
- **Esforço:** médio · **Risco:** médio (explosão de combinações; cuidar da narrativa) · **Quando:** S03 · **Dependência:** RQ07 base.
- **Impacto:** forte diferencial científico; sustenta Ameaças de construto/conclusão.

### ⭐ D5 — Intervalos de confiança por *bootstrap*
- **O que fazer:** IC95% para medianas (RQ01–04), κ de Fleiss, F1 da heurística.
- **Por que:** mediana/IQR descrevem a amostra; IC mostra a **incerteza** da estimativa (amostra-ouro é só 60 repos).
- **Esforço:** baixo–médio · **Risco:** baixo · **Quando:** S02 (κ/F1) e S03 · **Dependência:** dados consolidados.
- **Impacto:** discussão mais honesta do poder da validação.

### ⭐ D6 — Análise de sobrevivência para a recuperação (censura)
- **O que fazer:** Kaplan-Meier por grupo para o tempo de recuperação, tratando episódios **censurados** como tal (em vez de apenas reportar a proporção).
- **Por que:** a censura é uma preocupação explícita do enunciado (E§3); KM é o instrumento estatístico adequado.
- **Esforço:** médio–alto · **Risco:** médio (biblioteca extra; interpretação) · **Quando:** S03 · **Dependência:** episódios com flag de censura.
- **Impacto:** alto, se bem explicado; pode ser a "assinatura" do grupo.

### ⭐ D7 — Análise de erros da heurística corretiva
- **O que fazer:** matriz de confusão, listar FP/FN, taxonomia de causas (ex.: patch bump sem bug; `fix` em docs; releases corretivas sem SemVer), comparar versões v1→vN.
- **Por que:** E§6 pede F1 e versões; aqui vira **explicação** do porquê.
- **Esforço:** médio · **Risco:** baixo · **Quando:** S02 · **Dependência:** consenso + P/R/F1.
- **Impacto:** reforça Ameaças de construto com evidência qualitativa.

### ⭐ D8 — Análise de casos anômalos/outliers
- **O que fazer:** investigar repos extremos (DF muito alto, LT ≈ 0, CFR ≈ 0/1): releases por bot, nightly, monorepos; decidir (com justificativa) se afetam conclusões; reportar sensibilidade à sua exclusão.
- **Por que:** distribuições assimétricas são a razão de usar mediana/IQR (E§5).
- **Esforço:** médio · **Risco:** médio (tentação de "limpar" dados) · **Quando:** S03 · **Dependência:** CSV final.
- **Impacto:** discussão rica e crível.

### ⭐ D9 — Pipeline de análise ponta a ponta e relatório automático
- **O que fazer:** `make all`/script único que roda coleta (a partir do cache) → métricas → análises → gera tabelas/figuras (inclusive `.tex`) para o artigo.
- **Por que:** E§10 pede análises reexecutáveis; isto leva ao extremo.
- **Esforço:** médio · **Risco:** baixo–médio · **Quando:** S03–Final · **Dependência:** notebooks/scripts de S03.
- **Impacto:** elimina divergência entre artigo e código.

### ⭐ D10 — Reprodutibilidade reforçada
- **O que fazer:** `Dockerfile`/devcontainer, dependências travadas (`pip freeze`/lock), **manifesto de execução** (versão do Python, data da coleta, hash do CSV, commit).
- **Por que:** E§9 manda outro grupo executar só com README; isto reduz atrito.
- **Esforço:** médio · **Risco:** baixo · **Quando:** S03 · **Dependência:** pipeline estável.
- **Impacto:** replicação suave; menos Issues recebidas.

### ⭐ D11 — Logs estruturados e telemetria da coleta
- **O que fazer:** logs JSON/`logging` com requisições, *cache hits*, tempo dormindo por rate limit, retentativas; resumo ao final.
- **Por que:** economia de cota é um objetivo do enunciado (E§7); mostra que o cache funciona.
- **Esforço:** baixo · **Risco:** baixo · **Quando:** S01 · **Dependência:** `http_client`.
- **Impacto:** evidência pronta para T1/T2 e para depuração da replicação.

### ⭐ D12 — Visualizações superiores
- **O que fazer:** violinos/ECDF para distribuições assimétricas; **heatmap/Sankey** de transição entre categorias DORA (RQ07); *forest plot* de tamanhos de efeito (RQ06); dispersão com escala log e *rug*.
- **Por que:** E§8 pede tabelas e gráficos; qualidade visual comunica robustez (apoio TF-s37–50).
- **Esforço:** médio · **Risco:** baixo · **Quando:** S03 · **Dependência:** resultados das RQs.
- **Impacto:** artigo mais claro dentro de 10 páginas.

### ⭐ D13 — Governança automática de contribuição
- **O que fazer:** hook/Action que **rejeita commit sem `#N`**; script de relatório por pessoa/sprint (`git shortlog`); templates de Issue/PR com critério de aceite.
- **Por que:** E§10 desconta nota por GitHub Projects ruim e ignora commits sem `#N`.
- **Esforço:** baixo · **Risco:** baixo · **Quando:** S01 · **Dependência:** repositório criado.
- **Impacto:** protege a nota individual de cada integrante.

### ⭐ D14 — Teste ponta a ponta offline no CI
- **O que fazer:** fixtures de respostas da API gravadas (2–3 repos mínimos) para rodar o pipeline completo no CI **sem rede nem token**.
- **Por que:** E§7 quer CI rodando testes; isso testa o **pipeline**, não só as funções.
- **Esforço:** médio · **Risco:** médio · **Quando:** S02 · **Dependência:** pipeline integrado.
- **Impacto:** detecta regressões de integração cedo.

### ⭐ D15 — Pré-registro das hipóteses
- **O que fazer:** tag Git `hipoteses-v1` com hash citado no artigo; tabela automática **hipótese × resultado**.
- **Por que:** E§8 exige hipóteses antes dos dados; isto cria **prova**.
- **Esforço:** baixo · **Risco:** baixo · **Quando:** S01 e S03 · **Dependência:** Introdução pronta.
- **Impacto:** reforça credibilidade científica.

### ⭐ D16 — Auto-replicação antes da entrega
- **O que fazer:** um integrante que **não escreveu** o pipeline o executa em máquina limpa (Codespace) em 30 repos; compara com o CSV; corrige README.
- **Por que:** E§9 avalia exatamente isso no **outro** grupo — se o seu falhar, você recebe Issues.
- **Esforço:** baixo–médio · **Risco:** baixo · **Quando:** S03/Final · **Dependência:** README e dataset prontos.
- **Impacto:** alto retorno: reduz Issues recebidas e melhora o artigo (Replicação).

## 20.2 Resumo de priorização

| Prioridade | Diferencial | Motivo |
|---|---|---|
| 1 (barato, alto retorno) | D2, D11, D13, D15, D16 | Reforçam obrigatórios (cache, GitHub, hipóteses, replicação) |
| 2 (valor científico) | D1, D4, D5, D7 | Reforçam validação e sensibilidade |
| 3 (se sobrar tempo) | D3, D8, D9, D10, D12, D14 | Qualidade e polimento |
| 4 (alto esforço/risco) | D6 | Só com folga e boa explicação |

## 20.3 Tabela "OBRIGATÓRIO + FAZER ALÉM"

| Item obrigatório | O que o professor exige | Como fazer bem | Diferencial possível |
|---|---|---|---|
| Pipeline com comando único | Um comando no README; token em env var | README testado em máquina limpa; mensagens de erro claras | D10, D16 |
| Cache e retomada | Resposta em disco; continuar de onde parou | Escrita atômica; chave determinística; teste de interrupção | D11 (telemetria), D14 |
| Rate limit e backoff | Esperar reset; 5xx com 1,2,4,8… | Funções isoladas e testadas com mocks | D11 |
| Funil de seleção | Tabela automática por etapa e motivo | Motivo único por descarte; checagem de soma | D1, D2 |
| Testes (pytest) | Fixtures; 4 casos de borda; ≥ 80% | Usar os exemplos da E§5; testar fronteiras | D3, D14 |
| CI | Testes a cada push | Modelo `testes.yml`; `--cov-fail-under=80` | D13, D14 |
| Hipóteses por RQ | Antes dos dados | Tabela RQ→hipótese→porquê; commit antes | D15 |
| Amostra ≥ 300 | Após filtros | Começar cedo; monitorar funil | D1 |
| Métricas (todas as variantes) | LT a/b; CFR a/b; recuperação; classificação | Conferir contra exemplos; invariantes | D2, D1 |
| Dataset + dicionário | Cada coluna documentada | Verificação automática | D2 |
| Validação manual | 60 repos; independência; Fleiss; consenso; P/R/F1 | Planilhas sem heurística; mesmas 5 releases | D5, D7 |
| Heurística F1 ≥ 0,70 | Refinar e documentar versões | Tabela versão→F1 | D7 |
| RQ01–RQ04 | Mediana/IQR + classificação | Gráficos em escala log; tabela única | D8, D12 |
| RQ05 | Spearman (a) e (b); dispersão | ρ,p,n; texto sobre causalidade | D5 |
| RQ06 | ≥ 3 fatores; Holm; ε²/δ | Tabela única com p_holm e efeito | D12 (forest plot) |
| RQ07 | ≥ 3 combinações; % mudança; κ ponderado | Matriz de transição; rótulos inteiros | D4, D12 |
| RQ08 (bônus) | Rework **ou** Mann-Kendall | Escolher a mais viável; discutir diferenças | — |
| Replicação | Só README; 30 repos; Issues | Log completo; comparação clara | D10, D16 |
| Resposta às Issues | Corrigir ou justificar; no Project | Responder rápido; fechar com `#N` | D13 |
| Artigo | SBC; ≤ 10 p.; 7 itens | Aos poucos; citar números nas Ameaças | D9, D12 |
| GitHub Projects | WIP; Assignees; atualização semanal | Mover cartões durante a semana | D13 |

---

# 21. ROADMAP EXECUTÁVEL

> ⚠️ L02: **datas das sprints não estão no material** — usar "Etapa N". Ajustar quando o professor divulgar o cronograma.

## 21.0 Antes da S01
- Ler E§1–E§12 completo (cada integrante) + as 2 leituras recomendadas (DORA four keys; Quick Check).
- Obter **datas da janela** (⚠️ L01) e decisões L03–L22 que dependem do professor (perguntar em bloco).
- Criar repo, Project, Issues; definir papéis A/B/C (sugestão) e donos de DF/classificação.
- Criar token; ambiente Python.

## 21.1 S01
- **Etapa 1:** infraestrutura (`config`, `http_client`, rate limit, backoff, cache); funções de métrica + testes (em paralelo, sem rede); esqueleto do artigo (Introdução).
- **Etapa 2:** seleção + funil; coleta de metadados/releases/tags; compare paginado; runs por mês; escrever **hipóteses** (antes de olhar dados).
- **Etapa 3 (integração):** pipeline único para 100 repos; testes de interrupção/retomada; CI verde; cobertura ≥ 80%.
- **Fechamento:** revisar DoD §19.1; atualizar board; README em máquina limpa; fechar Issues.

## 21.2 S02
- **Etapa 1:** escalar para 300+ (rodar em segundo plano); congelar lista; calcular métricas e variantes; começar dicionário.
- **Etapa 2:** sortear 60 repos e 5 releases; gerar planilhas **sem heurística**; rotulagem independente (3 pessoas); heurística v1 (B) **sem** compartilhar saída com os rotuladores.
- **Etapa 3:** Fleiss + consenso + protocolo; P/R/F1; refinar heurística até F1 ≥ 0,70 (ou documentar); recalcular CFR(b).
- **Fechamento:** CSV + dicionário finais; Metodologia; DoD §19.2.

## 21.3 S03
- **Etapa 1:** congelar CSV; `analysis/common.py`; RQ01–RQ04 + C1.
- **Etapa 2:** RQ05, RQ06, RQ07 em paralelo (B, B, C); (opcional) RQ08.
- **Etapa 3:** Resultados + Discussão; reexecução limpa dos notebooks.
- **Fechamento:** DoD §19.3; antecipar teste de reprodutibilidade (§13) e `--repos-file`.

## 21.4 Entrega final
- **Etapa 1:** confirmar sorteio do professor e definição dos 30 repos (⚠️ L15); executar pipeline do outro grupo (A).
- **Etapa 2:** comparar resultados (B); abrir Issues com evidências; tratar Issues recebidas (C).
- **Etapa 3:** escrever Ameaças + Replicação; revisão final dos três; ≤ 10 páginas; link.
- **Fechamento:** DoD §19.4; board com Issues recebidas; checar commits `#N`.

---

# 22. MATRIZ FINAL DE AUDITORIA

**Legenda das colunas de sprint:** `●` = entrega principal nesta sprint · `○` = precisa continuar válido/ser mantido · `—` = não se aplica.
**Status:** `NÃO INICIADO` · `EM ANDAMENTO` · `CONCLUÍDO` · `BLOQUEADO` · `PRECISA VALIDAR`. (Todos começam **NÃO INICIADO**; atualizar semanalmente.)

| Requisito | S01 | S02 | S03 | Final | Evidência | Status |
|---|---|---|---|---|---|---|
| Janela de 12 meses fixada (L01) | ● | ○ | ○ | ○ | `config.yaml` + Metodologia | NÃO INICIADO |
| Definições operacionais (TRV-002…009) | ● | ○ | ○ | ○ | Testes + README | NÃO INICIADO |
| Proibição de libs de acesso à API (TRV-011) | ● | ○ | ○ | ○ | `requirements.txt` | NÃO INICIADO |
| Comando único + token em env (S01-002/003) | ● | ○ | ○ | ○ | README; histórico sem token | NÃO INICIADO |
| Seleção + fatiamento (S01-004) | ● | ○ | — | — | Log de faixas | NÃO INICIADO |
| Funil automático (S01-007) | ● (100) | ● (final) | — | — | `funil.csv` | NÃO INICIADO |
| Coleta de releases/tags/commits/runs (S01-009…014) | ● | ○ | — | — | Cache + testes | NÃO INICIADO |
| Cache/retomada (S01-015/016) | ● | ○ | — | — | Teste de interrupção | NÃO INICIADO |
| Rate limit + backoff (S01-017/018) | ● | ○ | — | — | Testes com mocks | NÃO INICIADO |
| Pipeline para 100 repos (S01-019) | ● | — | — | — | Execução | NÃO INICIADO |
| Testes + 4 bordas (S01-020/021) | ● | ○ | ○ | ○ | `pytest` verde | NÃO INICIADO |
| Cobertura ≥ 80% módulo de métricas (S01-022) | ● | ○ | ○ | ○ | Relatório de cobertura | NÃO INICIADO |
| CI do grupo (S01-023) | ● | ○ | ○ | ○ | Actions verde | NÃO INICIADO |
| Artigo: Introdução + hipóteses (S01-026) | ● | — | — | ○ | `.tex`/PDF; commit anterior aos dados | NÃO INICIADO |
| Amostra ≥ 300 (S02-001) | — | ● | ○ | ○ | `repos_final.csv` | NÃO INICIADO |
| Métricas em todas as variantes (S02-003) | — | ● | ○ | ○ | `repos.csv` | NÃO INICIADO |
| Variantes da RQ07 (S02-004) | — | ● | ○ | — | Colunas C1…C3 | NÃO INICIADO |
| CSV + dicionário (S02-005) | — | ● | ○ | ○ | Dicionário completo | NÃO INICIADO |
| Censura e 404 contados (TRV-009, S01-013) | ○ | ● | ○ | ○ | Colunas/números no artigo | NÃO INICIADO |
| Sorteio 60 repos, semente (S02-007) | — | ● | — | — | `sample_gold.py` | NÃO INICIADO |
| Rotulagem independente (S02-008) | — | ● | — | — | 3 arquivos | NÃO INICIADO |
| Fleiss 3 dimensões (S02-011) | — | ● | — | ○ | κ no artigo | NÃO INICIADO |
| Consenso + protocolo (S02-012) | — | ● | ○ | — | `PROTOCOLO_CONSENSO.md` | NÃO INICIADO |
| Heurística + P/R/F1 + versões (S02-013…016) | — | ● | ○ | ○ | Tabela versão→F1 | NÃO INICIADO |
| Artigo: Metodologia (S02-017) | — | ● | — | ○ | PDF | NÃO INICIADO |
| RQ01–RQ04 + C1 (S03-001…005) | — | — | ● | ○ | Notebooks + tabelas | NÃO INICIADO |
| RQ05 (S03-006) | — | — | ● | ○ | ρ,p,n + dispersão | NÃO INICIADO |
| RQ06 (S03-007…009) | — | — | ● | ○ | Tabela com Holm e efeito | NÃO INICIADO |
| RQ07 (S03-010/011) | — | — | ● | ○ | % mudança + κ por par | NÃO INICIADO |
| RQ08 bônus (S03-012) | — | — | ● (opc.) | — | Resultado | NÃO INICIADO |
| Notebooks reexecutáveis (S03-013) | — | — | ● | ○ | Reexecução limpa | NÃO INICIADO |
| Artigo: Resultados + Discussão (S03-015) | — | — | ● | ○ | PDF | NÃO INICIADO |
| `--repos-file` e README validado (SF-014/015) | ○ | ○ | ● | ○ | Teste em máquina limpa | NÃO INICIADO |
| Replicação (SF-001…006) | — | — | — | ● | `replicacao/` + artigo | NÃO INICIADO |
| Issues recebidas respondidas e no Project (SF-007/008) | — | — | — | ● | Issues/board | NÃO INICIADO |
| Ameaças à validade (SF-009) | — | ○ | ○ | ● | Seção com números | NÃO INICIADO |
| Artigo completo ≤ 10 p., link (SF-010/011) | ○ | ○ | ○ | ● | PDF final | NÃO INICIADO |
| Issues com Assignee + código por integrante (S01-028 etc.) | ● | ● | ● | ● | Lista por sprint | NÃO INICIADO |
| Commits com `#N` (S01-029/AVL-004) | ● | ● | ● | ● | `git log` | NÃO INICIADO |
| GitHub Projects (WIP, atualização semanal) (S01-030) | ● | ● | ● | ● | Board | NÃO INICIADO |
| Lacunas L01–L22 resolvidas e documentadas | ● | ● | ○ | ○ | README "Decisões do grupo" | NÃO INICIADO |

---

# 23. PASSADA FINAL DO AVALIADOR (SEGUNDA ANÁLISE)

## 23.1 "Se eu fosse o professor, existe alguma exigência que não aparece claramente?"

Itens que **foram adicionados** a este documento após a segunda leitura do enunciado:

| # | Exigência | Onde estava | Onde está aqui |
|---|---|---|---|
| 1 | **Release anterior pode estar fora da janela**; sem anterior (1ª da história) ⇒ ignorar | E§5 RQ02 | §5.2, S01-010 |
| 2 | **Contar** releases ignoradas por 404 | E§11 | S01-013, §9.5 |
| 3 | CFR(a) agrega **todos os workflows**; recuperação é **por workflow**, depois mediana | E§11 | §5.3, §5.4 |
| 4 | Informar **quantos** casos censurados houve | E§3 | TRV-009, §6 |
| 5 | **Proporção de episódios censurados por repositório** (RQ04) | E§5 | S03-004 |
| 6 | Últimos 7 dias da janela **fora do denominador** do CFR(b) | E§5 | §5.3 |
| 7 | Heurística **validada** na amostra-ouro; **versões e F1 no artigo** | E§5/E§6 | S02-013…016 |
| 8 | Kappa em **três dimensões** | E§6 | S02-011 |
| 9 | Registrar o **protocolo de desempate no repositório** | E§6 | S02-012 |
| 10 | **Seed documentada no código** | E§6 | S02-007 |
| 11 | `cohen_kappa_score(weights='linear')` por **par** de combinações | E§5 | S03-010 |
| 12 | Tamanho de efeito: **ε²** (KW) e **Cliff's δ** com `U₁` | E§5 | S03-009 |
| 13 | **Holm** via `multipletests` | E§5 | S03-008 |
| 14 | Gráfico de **dispersão** na RQ05 (log se necessário) | E§5 | §7 |
| 15 | **Funil** automático e **dicionário** de dados | E§7 | S01-007, S02-005 |
| 16 | **Issues do replicador no Project do autor** | E§9 | SF-008 |
| 17 | **Cada integrante com Issue de código**, também no Final | E§10 | SF-013 |
| 18 | `compare` com **paginação** (≥ 250 commits) | E§4 | S01-012 |
| 19 | **Subdividir runs por mês** e conferir teto de 1.000 | E§4 | S01-014 |
| 20 | **Contribuidores via `per_page=1&anon=true`** + `Link` | E§4 | S01-008 |
| 21 | Outras linguagens permitidas com comando único + testes/cobertura equivalentes | E§11 | AVL-006 |
| 22 | **Rebase/squash** como ameaça (data de commit) | E§3 | TRV-005, §15.3 |

## 23.2 "Existe algo aqui que parece obrigatório mas **não** foi exigido?" (corrigido para REC/DIF)

| Item | Classificação correta |
|---|---|
| Stars > 1000, não-fork, não-arquivado | **Lacuna L03** — `stars:>1000` é só exemplo de endpoint |
| Python como linguagem | **Não obrigatório** (E§11 permite outras) — mas pytest/pytest-cov são os exemplos |
| Nome `metricas` / `pipeline` / `config.yaml` | **Exemplos** do enunciado; o requisito é o **comando único** e a **cobertura do módulo de métricas** |
| Combinações C1/C2/C3 | **Exemplo**; exige-se **≥ 3** |
| Escolha de gráficos (boxplot, violino…) | **Não exigido** (só dispersão na RQ05) — [RECOMENDAÇÃO] |
| Dockerfile, bootstrap, Kaplan-Meier, property-based tests | [DIFERENCIAL] |
| Uma Issue por componente | **Sugestão** (dentro da divisão sugerida) — mas Assignee e `#N` são obrigatórios |
| Divisão A/B/C | [RECOMENDAÇÃO] do professor |
| Planilha com links para releases | [RECOMENDAÇÃO] (é "dica") |
| Mediana de 4 valores para classe geral | **É obrigatório** (definição); `floor` incluído |
| Usar notebooks (vs. scripts) | **Livre** ("notebook ou script") |
| 420 julgamentos/pessoa | Aritmética **derivada** (60×(1+1+5)) |

## 23.3 "Que tarefas importantes estão implícitas e o grupo poderia esquecer?" ([DERIVADO])

1. Coletar **todas** as releases (incl. pré-janela).
2. `requirements.txt` e versão do Python (o CI do professor depende deles).
3. **Congelar** a lista final antes de sortear a amostra-ouro.
4. As **mesmas 5 releases** para os três avaliadores.
5. **Esconder a saída da heurística** das planilhas.
6. Colunas das **combinações da RQ07** (pré-release, tag) coletadas até a S02.
7. **Tipo do projeto** só existe para os 60 (impacta o *n* da RQ06).
8. Rótulos do kappa ponderado como **inteiros**.
9. Opção `--repos-file` para replicar com 30 repos.
10. **Dataset e dicionário no repositório** (para o replicador comparar).
11. **Preencher o link** (`<preencher>`).
12. Artefato de **código** do integrante que "só executa" a replicação.
13. Ordem de execução: README **testado** antes que outro grupo o use.
14. Cobrir `deployment_frequency` e `classify_*` com dono (a divisão sugerida não os cita).
15. Evidência de **anterioridade** das hipóteses.

## 23.4 Cinco a dez coisas que diferenciariam o trabalho (⭐)

1. **D4** — sensibilidade além das 3 combinações (parâmetros do CFR(b), censura, cortes).
2. **D7** — análise de erros da heurística (explica *por que* o F1 é o que é).
3. **D5** — IC por bootstrap para medianas, κ e F1.
4. **D6** — Kaplan-Meier para recuperação (censura tratada como censura).
5. **D1 + D2** — relatório de qualidade de dados e invariantes automáticos.
6. **D16** — auto-replicação antes da entrega.
7. **D9 + D10** — pipeline de análise ponta a ponta e ambiente reprodutível.
8. **D3 + D14** — testes além de 80% e CI ponta a ponta offline.
9. **D12** — visualizações (transição RQ07, *forest plot*).
10. **D15** — pré-registro das hipóteses com tag Git.

---

# 24. AUDITORIA DE COBERTURA (MATERIAL → REQUISITO → SPRINT → TAREFA → ARTEFATO → EVIDÊNCIA → ACEITE)

| Material | Requisito (ID) | Sprint | Tarefa | Artefato | Evidência | Aceite |
|---|---|---|---|---|---|---|
| E§1 Contexto/proxies | S01-026 (Intro) | S01 | Escrever Intro e hipóteses | `artigo/` | `.tex` | §8.10 |
| E§2 Visão geral | §3.1 | Todas | Mapa de entregas | Este documento | — | §19 |
| E§3 Janela | TRV-001/002 | S01 | `config.yaml` | Config | Teste de filtro | T5, §19.1 |
| E§3 Branch/deploy/data/runs | TRV-003…006 | S01 | Filtros + funções | `collect_*`, `metricas` | Testes | T5, T6 |
| E§3 `conclusion` | TRV-007 | S01 | `classify_conclusion` | Função | Teste parametrizado | §12.2 |
| E§3 Critério mínimo | TRV-008 | S01/S02 | Filtros + funil | `selection`, `funil.csv` | Funil | T4 |
| E§3 Censura | TRV-009 | S01–S03 | Flags e contagem | Colunas | Números no artigo | T7 |
| E§4 Endpoints/limites | TRV-012…014; S01-004…014 | S01 | Coletores | `collect_*` | Mocks/logs | T5 |
| E§4 Rate limit/paginação | S01-014/017 | S01 | `http_client` | Código | Testes | T2 |
| E§4 Dica contribuidores | S01-008 | S01 | `collect_metadata` | Coluna `contributors` | CSV | §6 |
| E§5 RQ01 | S03-001; S01-025 | S01/S03 | DF | Função + notebook | Tabela | §5.1 |
| E§5 RQ02 | S03-002; S01-010…013 | S01/S03 | Lead time (a)(b) | Função + notebook | Testes + tabela | T6 |
| E§5 RQ03 | S03-003; S02-013…016 | S02/S03 | CFR (a)(b) + heurística | Funções + notebook | Testes + F1 | T8, T12 |
| E§5 RQ04 | S03-004 | S01/S03 | Episódios | Função + notebook | Testes + proporção | T7 |
| E§5 RQ05 | S03-006 | S03 | Spearman | Notebook | ρ,p,n + dispersão | T13 |
| E§5 RQ06 | S03-007…009 | S03 | KW/MW + Holm + efeito | Notebook | Tabela | T14 |
| E§5 RQ07 + tabela DORA | S03-010/011; TRV-015 | S01/S03 | Classificação + sensibilidade | Funções + notebook | Testes + tabela | T9, T15 |
| E§5 RQ08 | S03-012 | S03 | Opção escolhida | Notebook | Resultado | §10.5 |
| E§6 Validação manual | S02-007…016 | S02 | Sorteio, rótulos, κ, consenso, P/R/F1 | Scripts + CSVs | Arquivos + κ + F1 | T11, T12 |
| E§7 Engenharia (comando, cache, rate limit) | S01-002/003/015…018 | S01 | Infra | Código | Testes | T1–T3 |
| E§7 Testes/cobertura/CI | S01-020…024 | S01 | pytest + CI | `tests/`, workflow | CI verde | §12 |
| E§7 Funil/Dicionário | S01-007; S02-005 | S01/S02 | Gerar e documentar | CSV + dicionário | Arquivos | T4, T10 |
| E§8 Artigo | S01-026; S02-017; S03-015; SF-009/010 | Todas | Seções por sprint | `artigo/` | PDF ≤ 10 p. | §15 |
| E§9 Replicação | SF-001…008 | Final | Executar, comparar, Issues, responder | `replicacao/`, Issues | Links | T16, T17 |
| E§10 Sprints e pontuação | AVL-001…006; S0x-028…030 | Todas | Issues, commits, Project | Board/commits | Histórico | §14 |
| E§11 FAQ | S01-013; TRV-008; §5.3/5.4 | S01/S02 | 404, tags sem release, workflows, rate limit | Código/README | Testes | §12 |
| E§12 Referências | §1 | — | Citar no artigo | `.bib` | PDF | §15 |
| A5-s104–113 | — | S01 | Embasar a Introdução | Texto | Referências | [REC] |
| TF-s15, 19–21, 37–50 | — | S03 | Boas práticas (efeito, mediana, gráficos) | Notebooks | Figuras | [REC] |

### Cadeias com ponto frágil (a decidir pelo grupo / professor)
1. **Janela de 12 meses (L01):** sem datas, TRV-001 não fecha → **bloqueia a coleta**.
2. **Datas das sprints (L02):** o Roadmap usa "Etapas".
3. **Critério "popular" (L03)** e **"runs válidos" (L04)**: afetam o funil e o *n* final.
4. **Censura na mediana de RQ04 (L09)** e **classificação com métrica indefinida (L10)**: afetam RQ04, RQ07 e a classe geral.
5. **Lead time com release sem commits / commits negativos (L07)**: E§7 exige testar a borda, mas **não fixa** o resultado.
6. **Quem escolhe os 30 repos da replicação (L15)**.
7. **WIP e peso individual (L14)**.

**Conclusão da auditoria:** todos os requisitos explícitos do enunciado percorrem a cadeia **requisito → sprint → tarefa → artefato → evidência → critério de aceite**, exceto os itens da lista acima, que estão **explicitamente marcados** como lacunas (§0.5) e precisam de decisão documentada.

---

*Fim da Fonte da Verdade. Mantenha este arquivo versionado no repositório do grupo; ao resolver uma lacuna `Lxx`, registre a decisão e a data na seção "Decisões do grupo" do README e atualize a §22.*