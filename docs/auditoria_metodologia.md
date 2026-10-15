# Auditoria da metodologia (Sprint 2)

> **Nota (15/10):** esta auditoria foi feita na rodada anterior, com versões dos arquivos de rótulos que não
> são as commitadas. Os números de kappa, consenso e F1 citados aqui são dessa rodada. Os números oficiais
> (rótulos das Issues #23–#25) estão em `data/amostra_ouro/concordancia.csv`, `avaliacao_heuristica.csv` e
> `docs/refino_heuristica.md`.

Escopo: `artigo/metodologia.tex` e `docs/metodologia_evidencias.md` contra o enunciado, a Fonte da Verdade
(`enunciado/fonte_vdd.md`), os dados e os scripts. Hierarquia documental do próprio projeto: o enunciado
prevalece sobre a Fonte da Verdade (cabeçalho de `fonte_vdd.md`); decisões do grupo valem onde o enunciado
é omisso (lacunas L01–L22).

Legenda: **[V]** fato verificado/reproduzido; **[D]** afirmação documental não reproduzida;
**[I]** inferência; **[P]** decisão pendente.

Nenhum artefato do repositório foi alterado; reproduções gravaram só em
`/private/tmp/claude-501/-Users-marcos-orca-workspaces-Lab03-implementar-validacao/0899af48-eb87-43f7-a2e1-98e63fe43588/scratchpad/`
(`dq/`, `ag/`). Sem rede nem API.

## 1. Resultado por item da auditoria

| # | Item | Resultado |
|---|---|---|
| 1 | Afirmações com evidência rastreável | Maioria **[V]**; exceções em §3 (itens D) |
| 2 | Janela marcada como provisória | **[V]** no `.tex` (`\pend`) e em `config.yaml`; sem confirmação oficial no repo |
| 3 | Funil reproduzível | **[V]** parcial: `funil.csv` (2677 linhas; 300 selecionados; descartes 1219/1038/120) bate com `funil.md`, com `repos_final.csv` e `resultados.csv` (conjuntos idênticos). Os 60.143/60.142 resultados brutos e os 57.465 não avaliados são **[D]** (só em `funil.md`; exigem a Search API) |
| 4 | Kappa reproduzível | **[V]** `scripts.agreement` rodado em diretório temporário: κ 0,8140 / 0,8342 / 0,4277 e concordância simples 80,0 / 96,7 / 60,3 %; `concordancia.csv` e `consenso.csv` idênticos (diff vazio) |
| 5 | Rotulagem assistida sem afirmar independência | **Parcial**: o `.tex` declara a assistência, mas **subestima** o problema (ver §2.1) |
| 6 | Tabela v1–v9 | **[V]** TP/FP/FN/TN recalculados de `heuristica_amostra.csv` × `consenso.csv`; P/R/F1 batem com `avaliacao_heuristica.csv` nas 9 versões. Cronologia: v1 em `fd2b384`; v2–v7 em `360adc7` (2026-10-14 01:54); análise de erros em `8fc43b4` (02:02) **[V]**. v8/v9 só na árvore de trabalho, sem commit; "depois da análise de erros" é **[D]** (`docs/refino_heuristica.md`) |
| 7 | Divergência sobre a versão principal | **Confirmada** (§2.3) |
| 8 | F1 ≥ 0,70 e "não validada" | **[V]** no `.tex` e no `refino_heuristica.md`; melhor F1 0,680 na rodada anterior, 0,599 (v9) na oficial |
| 9 | Censura, 404, sem recuperação | **[V]** `data_quality` (scratch) e contagem direta: 176 de 9062 episódios censurados (105 repositórios); 6 releases 404 (5 repositórios); 23 repositórios sem `rec_median_h` (17 sem episódios + 6 só com episódios censurados **[I]**) |
| 10 | Relatório de qualidade × 300 | **Confirmado desatualizado**: `outputs/data_quality.md` é de 100 repositórios; a regeneração em scratch usa 300 e traz 1 FALHA (§2.4) |
| 11 | Confusão com resultados da S03 | Não encontrei resultado estatístico apresentado como obtido; o `.tex` diz que RQ01–RQ07 não foram executadas **[V]** |
| 12 | Referências, compilação, macros | Problemas (§2.6) |

## 2. Inconsistências confirmadas

### 2.1 Independência da rotulagem (mais grave) — **[V]**

> **Atualização (15/10, rodada oficial):** a tabela abaixo foi calculada sobre versões dos arquivos de
> rótulos que **não** são as commitadas. Nos arquivos commitados (Issues #23, #24, #25), a concordância em
> `corretiva` é 82,0% (ALuiz19 × marcosffp), 63,3% (ALuiz19 × GuilhermeVieira05) e 56,0%
> (GuilhermeVieira05 × marcosffp), e o kappa de `corretiva` é 0,27. A aderência dos arquivos commitados à
> sugestão não pode ser recalculada (`rascunho/` fora do Git). A ressalva de rotulagem assistida continua.

Calculado sobre `labels_*.csv` e `rascunho/` (rodada anterior):

| Par / fonte | Concordância em `corretiva` (300 itens) |
|---|---|
| marcosffp × ALuiz19 | **97,7 %** (293/300) |
| marcosffp × GuilhermeVieira05 | 61,3 % |
| ALuiz19 × GuilhermeVieira05 | 61,7 % |
| marcosffp e ALuiz19 × sugestão (292 itens com sugestão) | **100 %** (292/292) cada |
| GuilhermeVieira05 × sugestão | 62,0 % (181/292) |

Os arquivos `revisao_*.csv` mostram 0 alterações de sugestão para os dois avaliadores. Portanto o κ = 0,43
mede essencialmente a divergência entre um avaliador (Guilherme) e dois que seguiram a mesma sugestão; não
é concordância entre três julgamentos independentes. O `.tex` e `metodologia_evidencias.md` dizem que a
rotulagem foi "parcialmente assistida" e citam os 0 alterados, mas não destacam os 97,7 % nem que 2/3 do
consenso coincide com a sugestão. A origem da sugestão (`rascunho/sugestoes.csv`) é regra automática
(coluna `motivo`); se for derivada de sinais que a heurística também usa, o F1 é contaminado **[I]**,
não verificado. `rascunho/` está fora do Git **[V]**; terceiros não reproduzem isso.

### 2.2 O `.tex` omite ou imprecisa pontos — **[V]**
- Afirma "lista congelada ... `sha256`": `sorteio.json` fixa `resultados.csv` (sha confere **[V]**), não
  `repos_final.csv`. Os dois têm os mesmos 300 repositórios, mas a redação deveria nomear o arquivo.
- Não menciona 381 commits excluídos por data posterior à release (32 repositórios) nem 1685 releases sem
  commits novos (51 repositórios), ambos em `data_quality`.
- "Cinco releases com mensagens incompletas" **[V]** (coluna `mensagens_incompletas` = sim: 5).

### 2.3 Versão principal da heurística — **[V]**
- `docs/refino_heuristica.md`: v8 principal exploratória, v4 sensibilidade, v9 fora do dataset.
- `data/amostra_ouro/avaliacao_heuristica.md` (gerado): "Versão escolhida: v9" e "atualize `HEURISTIC_VERSION`".
- `README.md` (edição desta sessão): sem versão padrão; `escolhida` é só regra interna.
- `metricas/heuristica.py`: `HEURISTIC_VERSION = "v1"` ainda existe como constante.
O artigo segue o primeiro, que é decisão provisória do grupo **[P]**, não requisito do professor.

### 2.4 Qualidade dos dados — **[V]**
Regeneração em scratch (`python -m scripts.data_quality --dicionario DICIONARIO_DE_DADOS.csv --saida <scratch>`):
7 OK, **1 FALHA**, 2 N/A. A falha: `agentclientprotocol/agent-client-protocol`, "releases avaliadas + ignoradas
= releases da janela (lead time)": 73 ≠ 74 (linha de `resultados.csv`: 61 avaliadas, 0 ignoradas por 404,
0 sem anterior, 12 sem commits novos, 2 commits negativos). Causa **não investigada**; é defeito de dados
ou de contagem **[I]**, fora do escopo desta auditoria. `metodologia_evidencias.md` não menciona a falha.
`cfr_b` não existe em `resultados.csv` **[V]**.

### 2.5 Funil: fatia saturada possível — **[V]**
`funil.md` linha `stars:1282..1312`: `total_count = 1000`, coletados 1000, "não saturada". 1000 é o teto da
Search API; se o limite foi atingido, houve truncamento **[I]**. Não verificável offline.

### 2.6 Compilação, referências e macros — **[V]**
- `artigo/` tem só `introducao.tex` e `metodologia.tex`: sem arquivo principal, classe SBC, `.bib` nem comando
  de compilação no README. `introducao.tex` cita `forsgren2018accelerate`, sem `.bib` no repositório.
  Não compilei (sem `pdflatex`).
- `metodologia.tex` define `\pend` e `\prov` no próprio arquivo: ok, mas se o template redefinir ou o
  arquivo for incluído antes de `\begin{document}` pode falhar **[I]**.
- Na tabela das versões, `\\` antes de `{\footnotesize ...}` após `\end{tabular}` tende a gerar erro
  ("There's no line here to end") **[I]**; usar `\par` ou `\caption` com nota.
- `\label{sec:heuristica}` está depois de `\subsection`: ok.
- Nenhuma referência bibliográfica nova foi adicionada (Landis & Koch, Wohlin etc. aparecem só por nome).

## 3. Afirmações documentais não reproduzidas **[D]**

| Afirmação | Fonte | Por que não reproduzi |
|---|---|---|
| v1 "definida antes de ver os dados" | `refino_heuristica.md`, README | Só documental; o histórico mostra v1 depois do primeiro `labels_*` commitado (10-13), embora a heurística não rodasse na amostra |
| v8/v9 desenhadas depois da análise de erros | `refino_heuristica.md` | Código não commitado |
| F1 da v9 ≈ 0,59–0,74 por metades | `refino_heuristica.md` | Nenhum script a gera (não usada no artigo) |
| Kappa calculado antes do consenso | `PROTOCOLO_CONSENSO.md` | `scripts.agreement` calcula ambos na mesma execução; a ordem real não é verificável |
| Execuções coletadas por mês; compare divergente | README | Código não executado offline |
| 12.191 acertos / 72.975 falhas de cache | `outputs/execucao.log` | Lido, não reexecutado (log com 3 execuções; é a última) |
| Totais da Search API (60.143; 57.465 não avaliados) | `funil.md` | Exigem API |
| Revisões dos avaliadores (0 alteradas) | `rascunho/revisao_*.csv` | Fora do Git |

## 4. Reprodução offline: comandos

| Indicador | Comando | Situação |
|---|---|---|
| κ e consenso | `python -m scripts.agreement labels_marcosffp.csv labels_ALuiz19.csv labels_GuilhermeVieira05.csv --saida <dir>` | **Reproduzido** (em scratch) |
| Qualidade dos dados | `python -m scripts.data_quality --dicionario DICIONARIO_DE_DADOS.csv --saida <dir>` | **Reproduzido** (scratch) |
| P/R/F1 por versão | `python -m scripts.evaluate_heuristic` | **Não rodei**: precisa de rede/cache de commits e sobrescreve `avaliacao_heuristica.*`. Recalculei a tabela de `heuristica_amostra.csv` e `consenso.csv` por script avulso |
| Erros v9 | `python -m scripts.analise_erros_heuristica --amostra-dir <cópia>` | Não rodei; sobrescreve `erros_heuristica.*` |
| Funil | pipeline completo | Não reproduzível offline (Search API); conferi só a consistência interna |
| Suíte de testes | `pytest` | 661 passed (execução anterior nesta sessão) |

## 5. Decisões pendentes

| Questão | Evidências | Conflito entre documentos | Decisão necessária | Consequência das alternativas |
|---|---|---|---|---|
| Janela oficial | `config.yaml` (L01 provisória); `sorteio.json` usa as mesmas datas | — | Professor | Datas diferentes invalidam seleção, coleta e sorteio; manter exige aceite explícito |
| Nenhuma versão com F1 ≥ 0,70 | Rodada anterior: melhor F1 0,680 (v9), 0,595 (v8). Oficial: 0,599 (v9), 0,580 (v4), 0,497 (v8) | `avaliacao_heuristica.md` × `refino_heuristica.md` | Professor/grupo | Aceitar "refinamentos documentados" (aceite S02 da Fonte da Verdade) vs. nova amostra rotulada; afeta RQ03(b), RQ05(b), RQ07, RQ08 |
| CFR(b) só exploratório | `refino_heuristica.md` (decisão provisória do grupo); Fonte da Verdade S02-016 exige heurística validada | Enunciado exige validação "precisa" | Professor | Reportar com ressalva vs. omitir CFR(b); muda RQ03(b), RQ05 variante b e C2 da RQ07 |
| Escolha v8 × v9 × v4 | Tabela de F1; v9 depende de `body` não coletado | `avaliacao_heuristica.md` diz v9 | Grupo (com ciência do professor) | v9 exige recoleta com `body`; v8 subestima (18,7 %), v4 superestima (59,0 %) |
| Independência da rotulagem | §2.1 | LEIAME admite ancoragem | Professor/grupo | Aceitar e declarar; ou rerrotular independentemente (muda κ, consenso, F1) |
| Corte de 300 e "popular" | `config.yaml` (L03, L17); primeiros 300 por `full_name` | — | Professor | Corte não aleatório afeta validade externa; outro corte exige refazer coleta e amostra-ouro |
| Idioma e páginas | Enunciado: SBC, ≤ 10 páginas (L19) | — | Professor | Define o espaço para tabelas (funil, versões) |
| IC / outros testes | Enunciado pede kappa, P/R/F1; nenhum IC | — | Professor | Sem IC, F1 pontual com n = 300; com IC é preciso escolher o método |
| Falha da invariante de lead time | §2.4 | — | Grupo | Explicar ou corrigir e recalcular antes de citar `data_quality` |

## 6. Correções simples propostas (não aplicadas)

1. `metodologia.tex`: trocar "lista congelada" por "`resultados.csv` (sha256 em `sorteio.json`)".
2. `metodologia.tex`: acrescentar a concordância de 97,7 % entre os dois avaliadores assistidos e que eles
   coincidem 100 % com a sugestão.
3. `metodologia.tex`: citar 381 commits excluídos e 1685 releases sem commits novos.
4. `metodologia.tex`: substituir `\\` antes da nota da tabela por `\par`.
5. `metodologia_evidencias.md`: acrescentar a FALHA da invariante (§2.4) e a possível saturação (já presente).
6. Regenerar `outputs/data_quality.md` com `scripts.data_quality` (só após decidir sobre a FALHA).
7. Regenerar ou anotar `avaliacao_heuristica.md` para remover "escolhida v9"/"atualize HEURISTIC_VERSION".
8. README: registrar o comando de compilação do artigo e adicionar `.bib`/classe SBC quando existirem.

---

# Parte 2 — Correções aplicadas e investigação (etapa seguinte)

## 7. Falha de qualidade: `agentclientprotocol/agent-client-protocol` (73 ≠ 74)

Investigação somente leitura. Nenhum registro foi corrigido, nenhuma release descartada e
`outputs/data_quality.md` não foi sobrescrito (a regeneração foi para diretório temporário).

**Fatos verificados [V]**
- A invariante (`scripts/data_quality.py::inv_particao_lead_time`) soma `n_releases_avaliadas +
  n_sem_anterior + n_releases_ignored_404 + n_sem_commits_novos` e compara com `n_releases_window` do
  `funil.csv` (74 para este repositório).
- Linha de `resultados.csv`: avaliadas 61, 404 = 0, sem anterior = 0, sem commits novos = 12 (soma 73),
  `n_commits_negativos` = 2.
- `outputs/execucao.log` (2026-10-11 04:44): "74 releases, 1892 commits, 0 ignoradas por 404, 0 sem
  anterior". Logo, as 74 releases entraram no cálculo e uma não caiu em nenhuma das quatro categorias.
- `metricas/lead_time.py::resumo_lead_time` conta como "avaliada" a release com ao menos um lead time
  não negativo; "sem commits novos" é só `status == ok` com lista de commits **vazia**. Uma release `ok`
  com commits, todos com `author_date` posterior à publicação, **não entra em nenhuma categoria** (exemplo
  sintético executado offline: 1 avaliada, 0 em `n_sem_commits_novos`, `n_commits_negativos = 2`).
- Os dois commits negativos do repositório correspondem exatamente a esse caso se estiverem na mesma
  release.

**Causa mais provável [I]:** lacuna entre a definição da invariante e as categorias de
`resumo_lead_time`: release cujos commits são todos posteriores à publicação (L07) fica fora das quatro
categorias. É um problema de contagem/definição, não de dados corrompidos nem de duplicidade.

**Não verificado:** qual release é. O cache local deste repositório (`cache/commits/agentclientprotocol__agent-client-protocol.json`)
hoje tem só 5 comparações (atualizado em 2026-10-14T23:08Z) e as 13 respostas HTTP em cache também são
posteriores à coleta; as 74 comparações da coleta de 2026-10-11 não estão mais disponíveis offline.
Também o log não registra o aviso de commits negativos (0 ocorrências de "posterior" em `execucao.log`).
Duplicidade e erro aritmético não foram observados, mas não podem ser excluídos sem os 74 `compare`.

**Pendência:** o grupo decide se a invariante deve incluir a categoria "todos os commits negativos" ou se
o cálculo deve registrá-la; qualquer das duas altera código ou relatório, e não foi feita aqui.

## 8. Classificação das oito correções propostas (§6)

| # | Correção | Classe | Ação |
|---|---|---|---|
| 1 | "lista congelada" → `resultados.csv` (sha em `sorteio.json`) | Segura (sha confere) | **Aplicada** em `metodologia.tex` |
| 2 | Acrescentar 97,7 % e 292/292 | Segura (fatos verificados) | **Aplicada**, com a limitação explicada (item 2 abaixo) |
| 3 | Citar 381 commits e 1685 releases | Segura (`scripts.data_quality`, reprodução temporária) | **Aplicada** |
| 4 | `\\` → `\par` antes da nota da tabela | Segura | **Aplicada** (não compilado) |
| 5 | Registrar a FALHA em `metodologia_evidencias.md` | Segura | **Aplicada** (item 2b) |
| 6 | Regenerar `outputs/data_quality.md` | Dependente de decisão | Adiada: sobrescreve artefato experimental e a FALHA está sem decisão |
| 7 | Remover "escolhida v9" de `avaliacao_heuristica.md` | Dependente / não fundamentada | Adiada: arquivo gerado com resultados; só regenerar com `evaluate_heuristic` (exige rede/cache) |
| 8 | Comando de compilação no README | Não fundamentada | Adiada: não há arquivo principal, classe nem `.bib` no repositório |

## 9. Rotulagem assistida: o que mudou no `.tex`
Foi reescrita a subseção para: declarar o uso de sugestões; listar os fatos (292 sugestões, 292/292
coincidências nos dois avaliadores com revisão, 97,7 % entre os dois, 62,0 % do terceiro, consenso = sugestão
nos 292); dizer que a origem das sugestões não está registrada; **não** afirmar independência nem que os
rótulos estejam errados; explicar o impacto sobre o kappa (reflete a divergência do terceiro avaliador
contra um par quase idêntico) e sobre o F1 (a referência pode herdar o viés da sugestão; magnitude não
medida). A adequação do procedimento ficou como `\pend` (decisão do professor). Rótulos, consenso,
arquivos de revisão e kappas não foram tocados.

## 10. Contradição v8/v9
Declarações conflitantes: `data/amostra_ouro/avaliacao_heuristica.md` ("Versão escolhida: v9" e
"atualize `HEURISTIC_VERSION`") × `docs/refino_heuristica.md`/README/dicionário (`escolhida` é regra interna;
v8 principal exploratória, v4 sensibilidade, v9 fora do dataset; não validada). Nos documentos editáveis
(`README.md`, `DICIONARIO_DE_DADOS.md`, `docs/`, `.tex`) **nenhuma afirmação contradiz** o estado
documental: todas dizem F1 máximo 0,680, critério 0,70 não atingido e heurística não validada. A
afirmação conflitante está só no arquivo gerado, que não foi editado. A escolha oficial entre v8, v9 e v4
continua **pendente de decisão**; `HEURISTIC_VERSION` permanece `"v1"` e o CFR(b) não foi integrado.

## 11. Estrutura do artigo para compilar

| Item | Estado |
|---|---|
| Arquivo principal | Ausente (`artigo/` tem `introducao.tex` e `metodologia.tex`, sem `\documentclass`) |
| Classe/estilo | O enunciado (§8) manda usar o template SBC do Overleaf, ≤ 10 páginas; os arquivos do template (`.sty`, `.bst`) não estão no repositório. **Pendência**, nada escolhido |
| Bibliografia | Sem `.bib`; `introducao.tex` cita `forsgren2018accelerate`. Referências do enunciado (Forsgren et al.; DORA; Wohlin; Romano; Landis & Koch) ainda não têm entrada |
| `\pend`/`\prov` | Definidos no início de `metodologia.tex` com `\newcommand`; devem ficar após `\begin{document}` ou no preâmbulo do arquivo principal e ser removidos antes da entrega |
| Comandos potencialmente inválidos | `\\` antes da nota da tabela: corrigido. Não verificado por compilação (sem `pdflatex`; não instalei) |
| Idioma | O enunciado não define (L19); o texto está em português |

## 12. Arquivos alterados nesta etapa
- `artigo/metodologia.tex`: subseções de rotulagem e concordância; `\par`; contagens de data_quality.
- `docs/metodologia_evidencias.md`: item 2b.
- `docs/auditoria_metodologia.md`: esta Parte 2.

Nenhum arquivo de rótulos, consenso, dataset, resultado, código ou `HEURISTIC_VERSION` foi alterado.

## 13. Comandos executados (resultado)
- Leitura de `scripts/data_quality.py`, `metricas/lead_time.py`, `pipeline/collect_commits.py`,
  `outputs/execucao.log`, `outputs/funil.csv`, `outputs/resultados.csv`, caches em `cache/` (somente leitura).
- Script Python avulso com `resumo_lead_time` sobre dados sintéticos: confirmou a lacuna de categorias.
- Scripts avulsos de contagem sobre `rascunho/sugestoes.csv`, `consenso.csv` e `labels_*.csv`.
- Nenhuma chamada de rede/API, nenhuma coleta, nenhum commit/push. A verificação do diff está na §14.

## 14. Verificação do diff (executada)
`git status` mostra o mesmo conjunto de arquivos rastreados modificados de antes desta etapa. Os arquivos
que **esta etapa** gravou são só `artigo/metodologia.tex`, `docs/metodologia_evidencias.md` e
`docs/auditoria_metodologia.md`. Rótulos, consenso, `outputs/` e `data/` não foram alterados por mim.

Ressalva: `find -mmin -90` também lista arquivos que **não** foram gravados pelos comandos desta
etapa (`README.md`, `DICIONARIO_DE_DADOS.*`, `.gitignore`, `scripts/*`, `metricas/*` e vários JSON em
`cache/`). Isso indica atividade concorrente no worktree (outro processo ou sessão), inclusive escrita no
cache HTTP, o que também explica o cache de `agent-client-protocol` ter sido reescrito em
2026-10-14. Não pude atribuir autoria a essas modificações; convém conferir antes de qualquer commit.

Observação adicional: arquivos de `data/amostra_ouro/` (`labels_marcosffp.csv`, `labels_ALuiz19.csv`,
`consenso.csv`, `concordancia.csv`, `avaliacao_heuristica.*`, `heuristica_amostra.csv`, `erros_heuristica.*`,
`LEIAME.md`) também têm data de modificação dentro dos últimos 90 minutos. **Nenhum comando desta etapa os
escreveu** (as reproduções de kappa e qualidade foram para diretório temporário). Os valores conferidos
nas duas etapas (κ, P/R/F1, contagens do consenso) coincidiram com esses arquivos no momento da leitura, mas
a origem da modificação recente não foi determinada. Recomenda-se `git diff` desses arquivos por quem os
alterou antes de qualquer commit.
