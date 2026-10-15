# Validação independente da heurística v12 (CFR b): procedimento

> **Estado (15/10, após a coleta): pacote pronto, rotulagem humana pendente.** 40 repositórios disjuntos dos 60 do desenvolvimento, 200 releases congeladas (0 falhas, 245 chamadas à API), planilhas cegas em `data/validacao_independente/`. **Não existem** rótulos humanos nem F1 independente. A meta F1 ≥ 0,70 **não** foi verificada de forma independente.
>
> Registro da coleta: `data/validacao_independente/congelamento.json` (hashes, proveniência por repositório: 6 só de cache de leitura, 34 via API; 3 releases com `compare` sem commits novos; 0 `compare` 404; 0 truncados). Os caches de produção foram lidos em modo somente leitura; respostas novas foram para `cache/validacao_independente/` (ignorado pelo Git). `dados_congelados.json` contém notas e mensagens de commit (sem previsões) e **não deve ser distribuído aos avaliadores**; eles recebem apenas `labels_<nome>.csv` e o protocolo.

## 1. Situação encontrada (sem alterar nada)

| Pergunta | Resposta (evidência) |
|---|---|
| Como os 60 repositórios foram selecionados? | `random.Random(42).sample(sorted(resultados.csv), 60)` em `scripts/sample_gold.py`; `sorteio.json` guarda semente e sha256 da lista |
| Onde estão os repositórios/releases usados? | `data/amostra_ouro/amostra_ouro.csv` (300 releases = 60 × 5); rótulos em `labels_*.csv`; consenso em `consenso.csv` |
| Dados brutos | cache HTTP (SHA-256 de path+params) + JSON por repositório; **não versionado**. Local: `~/Developer/Lab03/cache` (100 repositórios da S01) e `.../implementar-validacao/cache` (60 da amostra-ouro) |
| Previsões | `heuristica_amostra.csv` (v1–v10) e `avaliacao_heuristica.csv`; v11/v12 estão descritas na seção "Versão avaliada: v12" abaixo |
| Executar a v12 | `metricas.heuristica.avaliar(base, tag, mensagens, "v12", notas=body)` |
| Evitar mistura dev/teste | não havia mecanismo; este fluxo o cria (seções 3–5) |

## 2. Amostra independente

Critérios (pré-registrados em `data/validacao_independente/sorteio_repos.json`):

1. Quadro: os 300 repositórios de `outputs/repos_final.csv`, sem duplicatas (sem diferenciar caixa).
2. Excluir os 60 de `amostra_ouro.csv` (desenvolvimento e análise de erros): 60 excluídos.
3. Excluir quem tem o **mesmo dono** de um repositório do desenvolvimento (convenção de notas e mantenedores compartilhados): 28 excluídos.
4. Quadro elegível: **212**. Sorteio simples de **40** com semente **7342** (`random.Random(7342).sample(sorted(...), 40)`).
5. Por repositório: 5 releases de deploy na janela, **com release anterior** (a 1ª da história nunca é corretiva e não tem `compare`), semente derivada de `7342/full_name`.

Verificações feitas: 0 sobreposição com os 60; 0 sobreposição de dono; lista de entrada e de usados com sha256 no manifesto. Os 6 repositórios da amostra com cache da S01 nunca foram rotulados nem usados no desenho da heurística.

**Limites da independência.** (a) Os 40 vêm do mesmo quadro de 300 (primeiros que passam em ordem alfabética), então a validade externa não melhora; (b) são independentes dos dados usados para **desenhar** v1–v12, não dos avaliadores nem da definição de "corretiva"; (c) a independência da rotulagem só existe se o protocolo for cumprido, e isso não é verificável pelo Git.

### Tamanho
Simulação por reamostragem dos 60 repositórios (v12 como população de referência, 5 releases por repositório):

| Repositórios | Releases | IC95% do F1 (±) | P(F1 observado ≥ 0,70) se o F1 verdadeiro for ≈ 0,72 | idem se for ≈ 0,65 |
|---:|---:|---:|---:|---:|
| 20 | 100 | 0,15 | 0,61 | 0,24 |
| 30 | 150 | 0,12 | 0,65 | 0,20 |
| **40** | **200** | **0,10** | 0,64 | 0,15 |
| 60 | 300 | 0,085 | 0,68 | 0,10 |

Escolhido: **40 × 5 = 200 releases** (≈ 40 + 40 + 200 julgamentos por avaliador). Mesmo assim o resultado é **incerto**: com F1 verdadeiro ≈ 0,72, a chance de o ponto sair ≥ 0,70 é só ~64%. Por isso a conclusão será sempre o ponto **com** o intervalo, nunca o ponto isolado.

## 3. Rotulagem cega

Protocolo: constante `PROTOCOLO` em `scripts/validacao_independente.py` (o arquivo gerado foi removido do repositório e é recriado por `pacote`). Resumo:

- Planilhas sem previsão, versão ou sinais; só links e identificadores (`release_id`).
- Definição operacional: corretiva = **objetivo principal** é corrigir um defeito; regras explícitas para releases mistas, backports, sem informação e dado inacessível.
- Rótulos individuais preservados; consenso por maioria (binário: sem 1-1-1); nenhum rótulo antigo é tocado.
- Quem implementou a heurística **declara** e o resultado sai também sem ele (sensibilidade).
- **Limitação:** κ foi 0,27 e as taxas de "sim" dos avaliadores foram 59%/16%/29%. O protocolo reduz, não elimina, a ambiguidade.

## 4. Fluxo reproduzível (`scripts/validacao_independente.py`)

```bash
python -m scripts.validacao_independente sortear      # feito: data/validacao_independente/sorteio_repos.json
python -m scripts.validacao_independente pacote       # offline por padrão; --permitir-api (GITHUB_TOKEN) para o que falta
#  → amostra_validacao.csv, labels_<nome>.csv (em branco), dados_congelados.json, congelamento.json
#  (3 avaliadores rotulam sozinhos e commitam, cada um o seu arquivo, com #N)
python -m scripts.validacao_independente avaliar      # uso único; P/R/F1 e IC95% por repositório
```

Salvaguardas implementadas e testadas (`tests/test_validacao_independente.py`):

| Risco | Salvaguarda |
|---|---|
| Vazar previsão aos avaliadores | `sortear`/`pacote` nunca executam a heurística; teste verifica ausência de campos de previsão e de versão |
| Alterar a heurística depois de ver o teste | `congelamento.json` guarda sha256 de `metricas/heuristica.py`; `avaliar` recusa se mudou |
| Alterar dados/amostra | sha256 de `dados_congelados.json` e `amostra_validacao.csv`; recusa se diferem |
| Escolher outra versão olhando o teste | só `v12`; sem parâmetro de versão; uso único (`--refazer` só reproduz) |
| F1 sem rótulos | recusa se faltar arquivo, célula, ou consenso pendente; nenhum número é calculado |
| Dependência entre releases do mesmo repositório | IC por *bootstrap* que reamostra **repositórios** (10.000 réplicas, semente 20261015) |
| Dado removido depois (`MaaNTE`) | `dados_congelados.json` guarda notas e mensagens no momento do pacote |

**Regra de decisão pré-registrada:** a meta é "atingida no teste independente" somente se o F1 pontual do consenso ≥ 0,70, reportado sempre com IC95% por repositório, P/R, matriz de confusão e a sensibilidade sem itens inacessíveis. Se não atingir, a v12 permanece não validada e **nenhuma v13 pode ser avaliada nesta amostra**: exigiria nova amostra disjunta.

## 5. Impacto de coletar os dados que faltam

Dos 40 sorteados, **6** têm cache local (testado em dados reais: 5 releases cada, com notas, sem rede). Faltam **34**:

| Item | Estimativa |
|---|---|
| Páginas de `/releases` (com `body`) | ≈ 46 (2.677 releases no total) |
| `compare` das 5 releases sorteadas | ≈ 170 (mais páginas se > 100 commits) |
| **Total** | **≈ 220–390 chamadas** (≪ 5.000/h; minutos) |
| Diferença para a coleta anterior | só `releases` e `compare` (sem `actions/runs`); `body` mantido; saída congelada, não escrita no cache de produção |

Não foi executada nenhuma chamada. Requer autorizar `--permitir-api` com um `GITHUB_TOKEN` válido (o token colado no chat deve ser revogado).

## 6. Proveniência de `1bananachicken/MaaNTE`

| Cache | Coletado | `compare` das 5 releases da amostra-ouro |
|---|---|---|
| `~/Developer/Lab03/cache` | 2026-10-08 (pré-remoção) | `ok`, 46–180 commits |
| `.../implementar-validacao/cache` | 2026-10-14 | `404` |

A rodada de `4c4d583` (14/10) usou o 404 (5 linhas `404`); a regeneração de `b7ab06f` (15/10) usou dados `ok`: os dois caches coexistem e a mudança de F1 da v1–v9 entre rodadas veio dessas 5 linhas. Dois avaliadores rotularam essas releases **sem acesso** (`observacoes`), logo o consenso delas não se baseia no conteúdo que a heurística viu em `b7ab06f`.

Medidas tomadas: nenhum cache foi mesclado ou regenerado; `heuristica_amostra.csv`, `avaliacao_heuristica.*` e `metrics.csv` não foram tocados. v12 sobre a amostra-ouro: F1 0,7219 (300 releases, MaaNTE em 404) e **0,7349 sem os 5 itens de MaaNTE** (295). Recomendação: reportar a amostra-ouro **sem** MaaNTE e registrar a divergência; preservar ambos os caches (hash) antes de qualquer regeneração.

## 7. O que falta, em ordem

1. Autorizar a coleta dos 34 repositórios (seção 5) e rodar `pacote`.
2. Três avaliadores rotulam cegamente e commitam (Issues próprias).
3. Rodar `avaliar` **uma vez**.
4. Só então decidir sobre `metrics.csv`, README, dicionário e artigo.


## Versão avaliada: v12 (histórico v10 → v12)

Registro mantido aqui porque o enunciado (E§6) exige documentar cada versão testada e o F1 obtido.
Os F1 abaixo são **de desenvolvimento** (300 releases / 60 repositórios, em amostra) e **otimistas**: v8–v12 foram
desenhadas depois de ver os erros da v1–v7 nessa mesma amostra.

| Versão | Regra | F1 (desenvolvimento) |
|---|---|---:|
| v10 | rejeita major/minor; patch aceita nota corretiva ampla (≥ 4 fixes); não-SemVer como v9 | 0,646 |
| v11 | v10 **ou** (só patch **e** a nota se declara release de correção/segurança: `security fix/release`, `patch release`, `hotfix`, `this is a patch`, `fixes a crash/regression`) | 0,671 |
| **v12** | v11, com "patch" também pelo número da própria tag (`X.Y.Z`, Z > 0, sem pré-release); cobre backports (`5.0.1` publicada após `4.4.3`) | **0,722** |

- **v11** corrige 3 FN de patch cujas notas se declaram release de correção; **v12** corrige 8 FN de backport.
- Os ganhos de v11→v12 vêm de poucos repositórios (`ransack` ×4, `nacos` ×3); IC95% do F1 da v12 no desenvolvimento: 0,628–0,798.
- **Resultado independente da v12** (40 repositórios, 200 releases): F1 = 0,689 (IC95% 0,563–0,790). Ver
  `data/validacao_independente/resultado_validacao.json`.
- O arquivo `metricas/heuristica.py` com a v12 tem hash `727b6c2b…` (cópia em
  `data/validacao_independente/heuristica_v12_congelada.py`).


## Limitações declaradas (a citar na Metodologia)

Os arquivos de sugestões da IA, de comparação e de material de rotulagem foram **removidos do repositório** a pedido do
grupo. Os fatos abaixo continuam valendo e devem ser declarados no texto:

1. **Sugestões de IA.** Existiu uma lista de sugestões de `corretiva` (200 itens) gerada por IA (Claude Sonnet 5.5) a
   partir de notas e títulos de commits, sem executar a heurística. O Guilherme a viu no modo de comparação
   (42 itens confirmados manualmente; 158 preenchidos em lote, rotulados como não humanos). Essas sugestões **não**
   alimentaram `labels_*.csv`.
2. **Gabaritos descartados.** Um primeiro gabarito do Guilherme coincidia 200/200 com a lista da IA e foi descartado;
   um documento inicial do Marcos se intitulava "avaliação por IA" e foi descartado. Valem os gabaritos refeitos.
3. **Transcrição.** Os `labels_*.csv` foram transcritos de documentos colados pelo usuário, com autoria atestada
   presencialmente; não há autenticação. Origem de cada decisão em `rotulagem/<usuario>.jsonl`.
4. **Tipo de projeto.** Mapeado de texto livre para as 4 categorias do protocolo; o do ALuiz19 foi revisado depois de
   apontados os casos sem tipo reconhecível.
5. **Conhecimento da heurística.** Os três avaliadores alteraram a heurística em algum momento (histórico do Git).
6. **Independência.** O κ de Fleiss de `corretiva` (0,87) é muito maior que o do desenvolvimento (0,27); as respostas
   foram dadas na mesma sala. A independência entre avaliadores não é demonstrável por artefatos.
