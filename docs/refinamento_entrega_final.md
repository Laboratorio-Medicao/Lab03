# Refinamento da Entrega Final (Issue #45)

Refinamento feito em 2026-10-20 sobre `main` em `0bb6690`. Cada card da milestone "Entrega Final" tem
abaixo: dono, critério de aceite verificável, dependências e o estado conferido no repositório e no board
nessa data. Dois cards novos (N1 e N2) são propostos; o número deles sai quando forem criados.

## Decisões registradas depois do refinamento (2026-10-20)

Lacunas que o enunciado não resolve e que foram decididas pelo grupo:

| Lacuna | O que o enunciado diz | Decisão |
|---|---|---|
| L02 prazo | "conforme cronograma da disciplina" (E§10) | **Prazo final: quinta, 2026-10-22.** Vale para a replicação, as respostas às Issues e o artigo |
| L15 30 repositórios | "subamostra de 30 repositórios do dataset original" (E§9), sem dizer quem escolhe | **O replicador sorteia** 30 linhas do CSV final do autor com semente fixa (`df.sample(n=30, random_state=42)`, como na amostra-ouro) e salva a lista em `replicacao/repos_30.txt` com o sha256 do CSV de origem |
| L19 idioma | não diz | **Português (PT-BR)** |
| L19 referências | "no máximo 10 páginas" (E§8) | **As referências contam nas 10 páginas** (leitura conservadora; se não contarem, sobra espaço) |

Continua pendente: o **sorteio dos grupos** pelo professor (E§9: "o professor sorteia para cada grupo o pipeline
de outro grupo"). Até 2026-10-20 nada foi divulgado no grupo da disciplina. Sem ele, #46 e #47 não começam.
Com o prazo em 2026-10-22, a ordem de prioridade passa a ser: confirmar o sorteio com o professor → N2 (nosso
pipeline pronto para ser replicado) → #42 e #49 (artigo) → #46 e #47 assim que o grupo for conhecido → #48 até o
prazo → #50 no fim.

Aplicado no GitHub em 2026-10-20:

- **N2 criada como #82** (Guilherme), já incluindo a regeneração do `data/metrics.csv` (divergência 13).
- **N1 não foi criada:** o `replicacao/compara.py` foi feito dentro da #47 (branch `feat/s47-compara`), e o corpo
  da #47 passou a depender só da #46.
- Corpos atualizados: #46 (commit fixo, `replicacao/autor/`, `repos_30.txt` com semente 42, LOG), #47, #49
  (SBC, PT-BR, 10 páginas com referências; depende de #42, #46 e #47) e #44 (fecha com #45–#50 e #82).
- Milestone "Entrega Final" com data 2026-10-22. PR #71 fechado.
- Pendente: pôr a #82 no Project (o token usado não tem o escopo `project`), confirmar o sorteio dos grupos com o
  professor e os itens 6, 8, 10, 11 e 12 da lista abaixo.

## Objetivo e entregáveis (E§9, E§10, #44)

Na Entrega Final o grupo tem dois papéis. Como **replicador**, executa o pipeline de outro grupo. Como
**autor**, tem o próprio pipeline executado por outro grupo. Os dois grupos podem ser diferentes, porque o
sorteio do professor não é necessariamente mútuo.

| Bloco | Entregável | Pontos | Cards |
|---|---|---|---|
| Replicação cruzada | Pipeline do outro grupo executado **só com o README**, em **30 repositórios** do dataset original, sem pedir ajuda. Comparação com o CSV original: diferença relativa por métrica e % de repositórios com a mesma classificação DORA, com as diferenças explicadas. Uma Issue por problema no repositório do autor, com evidências. Se a execução travar, o travamento é registrado como resultado | 2 | #46, N1, #47 |
| Issues recebidas | **Cada** Issue recebida respondida até o prazo, com correção (commit `#N`) ou justificativa, e adicionada ao nosso Project | 1 | N2, #48 |
| Artigo completo | Template SBC, **≤ 10 páginas**, com os 7 itens de E§8. Inclui **Ameaças à validade** (4 categorias, com números da validação manual e da sensibilidade), **Replicação cruzada** e link do repositório/Project. Revisão final pelos três | 2 | #49 (depende de #42 da S03) |
| Processo | Cada integrante com Issue de código e commits `#N`. WIP respeitado. Board atualizado, com evolução semanal | desconto de até 10% | #45, #50 |

## Cards: critérios de aceite e estado

| # | Card | Dono | Tipo | Critério de aceite (como provar) | Depende de | Estado em 2026-10-20 | Ação |
|---|---|---|---|---|---|---|---|
| 44 | Pai da Entrega Final | todos | — | Fecha quando #45–#50, N1 e N2 estiverem Done e a DoD da fonte da verdade (§19.4) estiver conferida item a item | — | Ready | Não vai para In progress (regra de WIP) |
| 45 | Refinamento | Arthur | processo | Este documento mergeado. Cada mudança proposta no board aplicada ou recusada pelo usuário | — | Ready, mas em execução | Mover para In progress (divergência 1) |
| N1 | `compara.py` e testes (novo) | Arthur | código | `replicacao/compara.py`, genérico e reexecutável: lê o CSV original e o replicado, mapeia colunas por um dicionário de nomes (o do autor) e junta por repositório. Calcula `(replicado − original) / original` por repositório e métrica e a mediana por métrica. Calcula o % de repositórios com a mesma classe DORA, por métrica e na classe geral. Informa `n comparados / 30` e o motivo de cada ausente (repositório removido, privado ou descartado por filtro). Original igual a zero ou ausente gera diferença indefinida, contada e documentada. Gera `comparacao.csv` e `comparacao.md`. Testes com *fixtures* cobrem: zero, ausente, classe igual/diferente, repositório faltando | #45 | Não existe (`replicacao/` não existe) | Criar o card. É prioridade do Arthur porque desbloqueia N2 e #47. Antes do sorteio, só com *fixtures* e o nosso `data/metrics.csv` |
| N2 | Pré-replicação: README pronto para o grupo replicador (novo) | Guilherme | código/doc | **(i) Começa já, sem esperar código:** ensaio do README num Codespace ou VM Linux limpos, por quem não escreveu o #36 (FV §13.3-6), registrado em `docs/`. README com link do GitHub Project, seção "Problemas conhecidos", tempo estimado, seção da RQ07 (`scripts.sensitivity_analysis` e `scripts.sensitivity_ampliada`) e o comando do snapshot do Kanban. sha256 de `data/metrics.csv` e de `DICIONARIO_DE_DADOS.csv` publicados no README e tag git (proposta: `dataset-final`) no commit de `main` que fecha o card. **(ii) Código:** `scripts/ensaio_replicacao.py` e testes. O script sorteia 30 repositórios de `data/metrics.csv` com semente fixa, gera o `--repos-file`, roda o pipeline com `caminhos.saidas` separado, registra SO, Python e tempo, e compara com `data/metrics.csv` usando `replicacao/compara.py` (N1). Commits citando o número da N2, com autoria do Guilherme | #45; N1 só no passo de comparação de (ii) | Não existe. O teste do #36 foi em macOS (`docs/teste-readme-maquina-limpa.md`). O README não tem link do Project, RQ07 nem snapshot | Criar o card. É o **item mais urgente**: precisa terminar antes de o outro grupo começar, e o prazo é desconhecido (L02, L15) |
| 46 | Executar o pipeline do outro grupo | Marcos | código/dados | Script commitado em `replicacao/` (ex.: `executar.sh` ou `executar.py`) que clona o repositório sorteado num **commit fixo**, cria o venv e roda os comandos do README sobre os 30 repositórios. `replicacao/LOG.md` com SO, Python, commit do autor, cada comando, saída, tempo, erros e ponto exato de travamento. `replicacao/repos_30.txt` com a regra de escolha dos 30 (semente fixa se a escolha couber a nós, L15). CSV regenerado e sha256 e commit do CSV original. Clone, venv, cache e token do outro grupo ficam no `.gitignore`. Nenhum contato com o autor. A execução registrada é a do commit fixo: respostas e correções do autor não entram nela, e uma nova rodada, se houver, é registrada à parte. Commits `#46` com autoria do Marcos | #45 (*); externa: sorteio do professor, repositório e README do autor, definição dos 30 e prazos (L15) | Não iniciado | Perguntar ao professor sobre L15 já. Pode montar o script com um repositório qualquer antes do sorteio |
| 47 | Comparação real e Issues no repositório do autor | Arthur | código | `compara.py` (N1) rodado sobre o CSV regenerado da #46 contra o CSV original do `main` do autor (commit citado). `replicacao/comparacao.md` com a tabela e a explicação das diferenças (os repositórios continuam recebendo commits; as datas de coleta diferem). Uma Issue por problema (falha de execução, documentação faltante, divergência) com comando, erro e esperado × obtido. Links em `replicacao/ISSUES.md`. As Issues de execução e documentação podem ser abertas assim que aparecem no log da #46, para dar prazo ao autor. Commits `#47` | #45, #46, N1 | Não iniciado | Depois do sorteio e do log da #46 |
| 48 | Tratar as Issues recebidas | Guilherme | código | Cada Issue recebida: adicionada ao Project com labels `lab03`, `entrega-final` e `replicacao-recebida` (nova) e com assignee. Respondida com correção (commit `#N #48`, teste de regressão quando for defeito) ou justificativa, até o prazo. README e pipeline atualizados e CI verde. Correção que muda resultado não sobrescreve `data/metrics.csv` sem registro: nova versão, nota, novo sha256 e nova execução da subamostra (FV §11.6). Guilherme é assignee e autor git de ao menos uma recebida que gere código. Se nenhuma Issue chegar ou nenhuma exigir código, isso é registrado na #48, e o código do Guilherme vem da N2 | #45; externa: Issues do grupo replicador; N2 (recomendado antes) | Nenhuma Issue recebida | Monitorar as Issues do repositório a partir do sorteio |
| 49 | Artigo: Ameaças, Replicação e revisão final | todos | escrita | `artigo/main.tex` no template SBC reunindo os 7 itens de E§8. **Ameaças** (`ameacas.tex`), nas 4 categorias de Wohlin e com números: construto (release ≠ deploy; κ 0,352 em "entrega real"; F1 0,689 com IC95% 0,563–0,790; CFR (a) × (b); RQ07 com 22–40% de repositórios mudando de classe; rebase/squash × `author.date`), interna (404, censura, RQ06 idade e popularidade, F1 otimista na escolha entre versões), externa (funil; ordem alfabética; piso de 1000 estrelas; linguagens e tipos) e conclusão (Holm e nº de testes, n por subgrupo, ε² e δ, Spearman só monotônico, κ 0,273 em "corretiva"). Essa seção substitui o resumo de `metodologia.tex` (l. 245). **Replicação** (`replicacao.tex`): o estudo foi reproduzível? O que impediu ou dificultou? Tabela da #47. Link do repositório e do Project preenchidos. PDF ≤ 10 páginas versionado. Revisão final com pelo menos 1 commit `#49` de cada um dos três | #45, #42, #46, #47 (**) | `artigo/` só tem `introducao.tex` e `metodologia.tex`. Não há `main.tex`, template, Resultados, Discussão nem PDF | Ameaças pode começar já. A Replicação espera a #47. O fechamento espera a #42 |
| 50 | Snapshot do Kanban | Arthur | dados | Snapshot final em `data/kanban-snapshots/` gerado com `python -m kanban.snapshot`, incluindo as Issues recebidas (que precisam da label `lab03`, porque o snapshot filtra por ela). Pelo menos 1 snapshot por semana da Entrega Final (evolução semanal). WIP, assignees e cartões conferidos, sem cartão esquecido em In progress | #46–#49, N1, N2 | Último snapshot: 2026-10-15 (S02) | Último card. Os snapshots semanais começam já |

(*) **#46 antes do sorteio.** O script de execução e o formato do log podem ser montados já. O que exige o sorteio
é a execução sobre os 30 repositórios do outro grupo. Regra: a execução registrada é a do commit fixo do autor,
seguindo só o README, sem contato com o grupo autor (E§9, FV §11.12-1).

(**) **"#49 depende de #48", reinterpretado.** O artigo não precisa relatar as Issues recebidas (FV §11.8), e
elas podem chegar até o prazo final. Por isso a #49 não espera a #48, a menos que uma correção da #48 mude
números do artigo: nesse caso a revisão é reaberta. A #42 (Resultados e Discussão, S03) entra como dependência
porque a FV §16.1 põe "Resultados + Discussão → Ameaças" e a revisão final precisa do artigo inteiro.

## Dependências e caminho crítico

São dois ramos independentes. O grupo que replicamos pode não ser o que nos replica.

```text
Replicador:  sorteio + L15 ──► #46 execução ──► #47 comparação + Issues ──► #49 (Replicação)
                                                   ▲
             #45 ──► N1 compara.py ────────────────┘
                       │
Autor:       #45 ──► N2 pré-replicação (README/Codespace/hash já; ensaio usa N1) ──► janela do outro grupo
                                                                                       ──► #48 recebidas
Artigo:      #42 (S03) ──► #49 Ameaças + revisão final ◄── #47
Fechamento:  #46, #47, #48, #49, N1, N2 ──► #50 snapshot final ──► #44
```

O grafo não tem ciclos. O caminho crítico do lado autor é N2: se o outro grupo começar antes de o README ser
validado em Linux, os problemas viram Issues contra nós. No lado replicador, o caminho crítico é sorteio → #46 →
#47 → seção de Replicação → revisão final, e depende de terceiros (L15).

## Código por integrante (E§10)

Sem commit de código atribuível a um integrante, a parcela individual dele na Entrega Final é zerada.

| Integrante | Cards de código | Situação |
|---|---|---|
| marcosffp | #46 (script de execução em `replicacao/`) | Planejado. Risco (FV §17.4-10): "só executou" não conta, então o script precisa ser commitado |
| ALuiz19 | N1 (`compara.py` + testes), #47 | Planejado. N1 não depende de terceiros e garante o código |
| GuilhermeVieira05 | N2 (`scripts/ensaio_replicacao.py` + testes), #48 (correções) | Planejado. A #48 depende de Issues que podem não exigir código. N2 garante o código mesmo assim |

## WIP e ordem de puxada

Limite: **3 cartões In progress por pessoa**. Regras: cards pai (#33, #44) não vão para In progress; cards
compartilhados (#42, #49) contam para os três; cada Issue recebida em In progress conta para o assignee. Hoje:
Arthur 1 (#39), Guilherme 0, Marcos 0. Com a #45 movida, Arthur fica com 2.

| Integrante | Ordem sugerida | Pico |
|---|---|---|
| Arthur | #39 + #45 → N1 (3) → ao mergear a #45, #42 (3) → ao fechar N1, #47 quando a #46 entregar (se a #39 ainda estiver aberta, ela sai de In progress antes) → #49 → #50 | 3 |
| Guilherme | N2 já (1) → #42 (2) → ao fechar a N2, #48 com no máximo 1 recebida em In progress por vez (3) → #49 depois da #42 | 3 |
| Marcos | #42 (1) → #46 assim que houver sorteio (2) → #43 no fim da S03 (3) → #49 depois da #43 | 3 |

## Divergências encontradas e ação

1. **#45 em Ready com o trabalho em andamento.** → Mover para In progress (Arthur). Superado: a #45 foi entregue
   e fechada pelo PR #80.
2. **#36 fechada sem o teste em Codespace/VM.** O corpo da #36 pede "máquina limpa (Codespace/VM)". O registro
   (`docs/teste-readme-maquina-limpa.md`) foi feito em macOS e deixa o Linux pendente (SF-015). → Comentar na #36
   que a pendência passa para a N2, sem reabrir a #36.
3. **Dependências desatualizadas nas Issues.** A #49 não lista a #42 e lista a #48. A #46 e a #48 não citam as
   dependências externas. A #47 não cita a N1. A #50 não cita N1 e N2. → Ajustar o "Depende de" conforme a tabela.
4. **Issues recebidas sumiriam do snapshot.** `kanban.snapshot` filtra pela label `lab03`, e quem abre a Issue
   no nosso repositório é o outro grupo. → Ao adicionar cada recebida ao Project, aplicar `lab03`,
   `entrega-final` e `replicacao-recebida` (criar esta label).
5. **Regra de WIP não escrita.** O README do Project está vazio (L14). → Escrever: máximo de 3 In progress por
   pessoa, pais fora de In progress, compartilhados contam para os três.
6. **Prazos desconhecidos.** A milestone "Entrega Final" não tem data (L02), e não se sabe quem escolhe os 30
   repositórios nem o prazo das Issues (L15). → Resolvido em 2026-10-20 (seção "Decisões registradas"): prazo
   2026-10-22 e sorteio dos 30 pelo replicador. Falta registrar a data na milestone e confirmar o sorteio dos
   grupos com o professor.
7. **Artigo sem esqueleto.** `artigo/` não tem `main.tex`, template SBC, Resultados, Discussão nem PDF. O resumo
   de ameaças em `metodologia.tex` (l. 245) duplicaria a seção final e gastaria página. → A #49 cria o
   `main.tex` e troca o resumo por uma remissão. A #42 entrega Resultados e Discussão.
8. **README incompleto para o replicador.** Faltam a seção da RQ07, o comando do snapshot, o link do Project,
   "Problemas conhecidos" e o tempo estimado de uma rodada de 30 repositórios. → N2.
9. **Dataset não congelado.** Não há tag nem hash publicado. O `data/metrics.csv` atual vem do commit `675d925`
   (#21, v12) e tem sha256 `07bba6286225973c0a97f55e8794dd4d9f755af1a67003488a51a750bf01b37c`.
   `DICIONARIO_DE_DADOS.csv` tem sha256 `cf7f6b915583aff7380e842ecf2e62de94d018f21661ca17db2bceedbb13b048`.
   Os dois foram calculados sobre o conteúdo versionado (`git show HEAD:<arquivo> | sha256sum`); no Windows, o
   `core.autocrlf` muda o hash do arquivo em disco. → N2 publica os hashes e põe a tag no `main` do fechamento.
10. **S03 ainda aberta.** Estão abertas a #33 (pai), a #39 (RQ08, In progress), a #42 (Ready, sem `.tex`) e a
    #43 (Ready). A #42 bloqueia o fechamento da #49. → Fechar a S03 antes de puxar a revisão final.
11. **PR #71 aberto e obsoleto.** Foi substituído pelo #72, já mergeado. → Fechar com comentário apontando o #72.
12. **Sem evolução semanal registrada desde 2026-10-15.** → Snapshot semanal com `python -m kanban.snapshot`
    (critério da #50) e comentário de progresso nos cards em In progress.
13. **`data/metrics.csv` defasado em relação ao código.** Conferido em 2026-10-20 com
    `analysis.common.classificar_c1`: (i) `df_class` dá `Low` em 11 repositórios com exatamente 12 releases na
    janela, e o código atual dá `Medium` (corte de 1 release/mês = 12 ÷ semanas da janela de 366 dias);
    (ii) `dora_geral` está vazio nos 23 repositórios sem `rec_median_h`, ao contrário da regra parcial descrita
    no dicionário (L10); (iii) `dora_c1` está vazio em `akto-api-security/akto`, com as 4 classes preenchidas.
    Quem regenerar o CSV com o nosso README vai encontrar essas diferenças. → N2 regenera o CSV, confere que só
    as colunas de classe mudam, refaz as saídas que usam classe (RQ01–RQ04 e sensibilidade da RQ07) e só então
    congela com hash e tag.

### Mudanças propostas no board (para o usuário aplicar)

1. ~~Mover a #45 para In progress~~: superado, a #45 foi fechada pelo PR #80.
2. Criar a **N1**: "[S2a] Entrega Final — `replicacao/compara.py` e testes". Assignee ALuiz19, milestone Entrega
   Final, labels `tarefa`, `entrega-final` e `lab03`. Corpo com o critério da tabela. Depende de #45.
3. Criar a **N2**: "[S6] Entrega Final — Pré-replicação: README validado em Linux, ensaio de autorreplicação e
   dataset congelado". Assignee GuilhermeVieira05, mesma milestone e labels. Depende de #45 (e de N1 só no passo
   de comparação).
4. Reescrever o corpo da #47 como "comparação real + Issues" e mudar o "Depende de" para #45, #46 e N1.
5. #46: acrescentar ao corpo o commit fixo, a regra da rodada à parte, `repos_30.txt`, sha256 do original e o
   `.gitignore`. Acrescentar a dependência externa (sorteio, L15).
6. #48: acrescentar as labels das recebidas, a regra de WIP, os commits `#N #48`, a regra de não sobrescrever
   `data/metrics.csv` sem registro e o caso "nenhuma Issue recebida". Acrescentar a dependência externa.
7. #49: mudar o "Depende de" para #45, #42, #46 e #47. Acrescentar ao corpo `main.tex` SBC, as evidências por
   categoria, a remissão no lugar do resumo da metodologia e 1 commit `#49` de cada integrante.
8. #50: mudar o "Depende de" para #46–#49, N1 e N2. Acrescentar os snapshots semanais e a label `lab03` nas
   recebidas.
9. #44: incluir no corpo o fechamento por #45–#50, N1, N2 e a DoD §19.4.
10. Criar a label `replicacao-recebida`.
11. Escrever a regra de WIP no README do Project.
12. Comentar na #36 que o teste em Linux passa para a N2.
13. Fechar o PR #71.
14. ~~Perguntar ao professor sobre L15 e L19~~: decidido pelo grupo (seção "Decisões registradas"). Resta
    confirmar com o professor o sorteio dos grupos e registrar a data 2026-10-22 na milestone.

## Riscos da Entrega Final

- **Dependência de terceiros:** README do outro grupo incompleto, repositório privado ou dados ausentes. Quando
  isso acontece, é resultado a registrar, não motivo para pedir ajuda.
- **Prazo curto (2026-10-22) e sorteio dos grupos não divulgado:** se o outro grupo começar antes da N2, os
  problemas do nosso README viram Issues contra nós; se o sorteio demorar, sobra pouco tempo para #46 e #47.
- **Issues recebidas tarde:** sobra pouco tempo para corrigir. Responder com justificativa também conta, desde
  que seja dentro do prazo.
- **Guilherme sem código** se a N2 não for feita e a #48 só tiver justificativas.
- **S03 atrasada:** sem a #42, a #49 não fecha.
- **Rate limit e token** na execução dos 30 repositórios.
- **10 páginas:** Resultados (RQ01–RQ08), Ameaças e Replicação competem por espaço. Compilar cedo.
- **Toolchain LaTeX:** o template SBC precisa estar no repositório. Precisa haver um caminho combinado (Overleaf
  ou TeX local) para gerar o PDF versionado.
- **Autoria apagada:** merge por squash pode apagar o autor dos commits (FV §14.5). Usar merge commit ou rebase
  nos PRs da Entrega Final.
- **Código de terceiros no repositório:** o clone, o venv e o cache do outro grupo não podem ser versionados.
  `.gitignore` em `replicacao/`.
