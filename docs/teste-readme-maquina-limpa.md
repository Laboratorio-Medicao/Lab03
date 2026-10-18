# Teste do README em ambiente limpo (Issue #36)

**Data:** 2026-10-18 · **Quem:** Marcos (com Claude Code) · **Commit base:** `a16ebf4` + a mudança `--repos-file`

## O que foi feito (e o que não foi)

Cópia limpa do repositório (sem `cache/`, `.venv/` e sem os arquivos de `outputs/`), Python 3.12 do Homebrew em macOS, `venv` novo, seguindo só os passos do README: `pip install -r requirements.txt` → `pytest --cov=metricas --cov-fail-under=80` → `python -m pipeline --config config.yaml --repos-file ...`.

**Limite:** isto **não** foi um Codespace nem uma VM Linux, como pede a Issue. Em máquina nova de verdade ainda faltam: Python 3.12 ausente, `git config core.hooksPath`, e o Linux do CI. **Pendente:** repetir os mesmos passos num Codespace antes da replicação (SF-015).

## Resultado

| Passo | Resultado |
|---|---|
| `pip install -r requirements.txt` | OK, sem erro |
| `pytest --cov=metricas --cov-fail-under=80` | 765 testes; 764 passaram; cobertura de `metricas` 99,09% (o 1 que falhou: ver abaixo) |
| `--repos-file` com `.txt` (1 repo privado + 1 inexistente) | Ambos descartados com `repo_not_found`, código 0, funil gravado |
| `--repos-file` com `.csv` (`aidenybai/bippy`, `affaan-m/agentshield`, dataset original) | 2 concluídos, 0 erros, 47 s, 60 chamadas à API |

**Comparação com `data/metrics.csv`** (mesma janela 2025-10-02 a 2026-10-02): `deployment_frequency`, `lt_release_median_h`, `cfr_a`, `n_runs_coletados` e `dora_geral` **idênticos** nos 2 repositórios (diferença relativa 0%; mesma classe DORA). Amostra pequena: não prova a replicação dos 30.

## O que travou ou incomodou

1. **Falha de teste na cópia limpa** (`test_estrutura_minima_existe[outputs]`): foi por eu ter excluído `outputs/` da cópia, não do README. Não é defeito do projeto.
2. **`--repos-file` sobrescreve `outputs/funil.*` e `resultados.csv`** da pasta de saídas. Corrigido na documentação: o README manda usar `caminhos.saidas` separado.
3. **Cabeçalho do README dizia "Estado atual (Sprint S01)"**, desatualizado. Corrigido para S03.
