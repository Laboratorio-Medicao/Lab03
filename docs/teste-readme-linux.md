# Teste do README em ambiente Linux limpo

**Data:** 2026-10-22  
**Ambiente:** Docker `python:3.12-slim` (Debian 13 / arm64) — Linux limpo, sem cache, sem venv pré-existente  
**Commit testado:** `e5731b5` (branch `feat/s82-ensaio-replicacao`, pós-merge do #84)  
**Executado por:** Claude (não é o autor do #36)

---

## Passos executados (seguindo o README)

```bash
# Pré-requisitos
apt-get install -y git          # Git instalado com sucesso
# Python 3.12 já presente na imagem python:3.12-slim

# Clonar
git clone https://github.com/Laboratorio-Medicao/Lab03 /repo

# Criar venv e instalar dependências
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Resultados

| Etapa | Resultado |
|---|---|
| `git clone` | ✅ OK |
| `python -m venv .venv` | ✅ OK |
| `pip install -r requirements.txt` | ✅ OK (aviso de nova versão do pip, não é erro) |
| `pytest` (877 testes) | ✅ **877 passed, 1 warning** |
| `python -m pipeline` sem `GITHUB_TOKEN` | ✅ Mensagem de erro clara: `variável de ambiente GITHUB_TOKEN não definida. Defina com: export GITHUB_TOKEN="seu_token"` |
| `python -m scripts.sensitivity_analysis` | ✅ OK (requer `data/metrics.csv`) |
| `python -m scripts.sensitivity_ampliada` | ✅ OK (requer `data/metrics.csv`) |

## Observações

- `data/metrics.csv` precisa ser copiado/fornecido separadamente — está versionado no repo, então `git clone` o traz automaticamente. ✅
- O pipeline completo (`python -m pipeline`) exige `GITHUB_TOKEN` e o cache (~19 GB). A mensagem de erro é clara e orienta o usuário.
- Para rodar só as análises e o `compute_metrics.py` a partir do cache fornecido pelo grupo, basta seguir os comandos do README — nenhuma etapa falhou.
- Aviso de `UndefinedMetricWarning` no sklearn (kappa com uma única classe) é esperado e documentado nos testes.

## Conclusão

O README está funcional em Linux limpo. Um replicador consegue instalar as dependências, rodar os testes e executar as análises sem precisar de ajuda adicional.
