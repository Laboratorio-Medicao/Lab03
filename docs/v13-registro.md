# Registro da heurística v13 (experimental, não promovida)

> Documento de registro. A v13 **não** está em `metricas/heuristica.py`. A v12 continua sendo a versão oficial.
> Data: 2026-10-15.

## 1. O que é
A v13 é a v12 com **uma** mudança (hipótese H1): uma tag que termina em `-lts` ou `-stable` deixa de ser lida como
pré-release. Na v12, `v2.10.5-lts` ou `v4.7.4-stable` são tratadas como SemVer com pré-release, o que bloqueia a
regra de patch. O conjunto de releases do estudo só tem `prerelease=false`, então esses sufixos nomeiam um canal
de manutenção, não um candidato. `rc`, `alpha`, `beta` e `preview` continuam bloqueados.

Origem: nos 46 erros da v12 na avaliação (27 FN, 19 FP), 15 FN eram bloqueados pela trava de major/minor/pré-release,
8 deles por sufixo de canal (`-lts`, `-stable`, `-beta`). Das hipóteses testadas no desenvolvimento, só esta não piorou
(as demais — aceitar minor com notas de correção, remover a trava, limiar por nº de commits — reduziram o F1 de
desenvolvimento). A H1 não tem cobertura no desenvolvimento.

## 2. Onde está
| Item | Local |
|---|---|
| Implementação | `experimental/v13/heuristica_v13.py` (importa a v12, não a altera) |
| Testes (19) | `experimental/v13/tests/test_v13.py` |
| Comparação | `experimental/v13/comparar.py`, `relatorio_comparacao.py` |
| Resultados | `experimental/v13/resultados_exploratorios.md`, `relatorio_comparacao_v12_v13.md`, `diferencas_v12_v13.csv` |
| Origem da H1 | resumida na seção 1 e em `relatorio_comparacao_v12_v13.md` (a investigação detalhada foi removida) |
| v12 congelada (cópia, hash `727b6c2b…`) | `data/validacao_independente/heuristica_v12_congelada.py` |
| Rascunho do teste cego da H1 (não executado) | `experimental/v13/teste_cego_h1.py` |

## 3. Resultados
| Amostra | v12 F1 | v13 F1 | Releases que mudam | ΔF1 IC95% (por repositório) |
|---|---:|---:|---:|---|
| Desenvolvimento (300) | 0,7219 | 0,7219 | 0 | [0,000; 0,000] |
| Avaliação (200) — **pós-hoc** | 0,6892 | 0,7067 | 2 (MaxKB v2.10.5-lts e v2.10.6-lts, ambas positivas) | [+0,000; +0,056] |

A avaliação independente oficial da v12 (F1 = 0,689; IC95% 0,563–0,790) está em
`data/validacao_independente/resultado_validacao.json` e **não foi alterada**.

## 4. O que se pode e o que não se pode afirmar
| Nível | Situação |
|---|---|
| Melhora observada | Sim: +0,018 de F1 na avaliação (2 releases, 1 repositório) |
| Evidência estatística | **Não**: o intervalo inclui zero |
| Validação independente | **Não**: a H1 foi formulada vendo os erros desta mesma amostra; o desenvolvimento não tem tags `-lts`/`-stable` |

O 0,707 é um sinal exploratório. **Não** deve ser citado como "meta atingida" nem como validação da v13.

## 5. Decisões e pendências
- **Decisão atual:** manter a v13 experimental; v12 oficial e reproduzível.
- **Teste cego da H1 (pendente):** rotular só as releases `-lts`/`-stable` ainda não rotuladas. Localmente, em 133 dos
  300 repositórios, há ~23 releases assim (MaxKB 11, go-algorand 10, 1Panel 2; várias já rotuladas). Os 167
  repositórios restantes exigiriam chamadas à API apenas para listar releases. Regras: seleção só pelo sufixo, sem
  olhar previsões, material sem hipótese nem previsões, três avaliadores independentes.
- **Para promover:** só após o teste cego (ou amostra independente); então adicionar a v13 a `VERSOES` como versão
  nova (v12 intacta) e atualizar o hash de congelamento.
- **Para descartar:** `rm -rf experimental/v13` (e apagar este registro, se quiser).

## 6. Riscos de ler isto errado
- Comparar 0,707 com 0,689 sem o contexto sugere uma melhora que o desenho não permite afirmar.
- Dois dos três repositórios com tags desse tipo já foram examinados; qualquer teste futuro deve priorizar
  releases ainda não rotuladas e declarar essa limitação.
- O token do GitHub colado na conversa foi usado em chamadas anteriores; convém **revogá-lo**.
