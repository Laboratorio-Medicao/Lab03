# v13 experimental (candidata, NÃO validada)

Pasta isolada: **para descartar tudo, apague `experimental/v13/`** (e `experimental/` se ficar vazia).
Nada fora daqui foi alterado; a v12 (`metricas/heuristica.py`) segue como referência.

| Arquivo | Para quê |
|---|---|
| `heuristica_v13.py` | v12 + H1 (sufixo `-lts`/`-stable` não é pré-release); API: `corretiva(base, tag, mensagens, notas)` |
| `tests/test_v13.py` | 19 testes (H1 aplica; `rc/alpha/beta/preview` continuam bloqueados; sem sufixo = idêntica à v12; v12 não é afetada) |
| `comparar.py` | compara v12 × v13 nos dados existentes, sem rede |
| `resultados_exploratorios.md`, `diferencas_v12_v13.csv` | saída da comparação |

## Como usar
```bash
.venv/bin/python -m pytest experimental/v13/tests         # testes (não entram na suíte principal)
.venv/bin/python -m experimental.v13.comparar             # recalcula a comparação
```

## Status e o que NÃO se pode afirmar
- A H1 foi formulada **depois** de ver os erros da amostra de avaliação (200 releases). O F1 de 0,707 ali é
  **exploratório e pós-hoc**: não valida a v13 nem comprova que a meta de 0,70 foi atingida.
- No desenvolvimento a v13 não muda nenhuma previsão (não há tags `-lts`/`-stable`): não é teste, é falta de cobertura.
- A mudança afeta 2 releases (MaxKB v2.10.5-lts e v2.10.6-lts), dentro do intervalo de confiança.
- Validar exige amostra nova e independente, rotulada antes de executar a heurística (fluxo em
  `scripts/validacao_independente.py` e `docs/validacao-independente.md`). Se a v13 for validada, só então promova
  para `metricas/heuristica.py`; se não, apague a pasta.
