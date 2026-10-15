# v12 × v13-experimental (H1) — resultados exploratórios

> v13 = v12 + sufixo `-lts`/`-stable` não é pré-release. **Não validada.** Formulada depois de ver os erros da
> amostra de avaliação; os números dessa amostra são pós-hoc e **não** são evidência de que a meta foi atingida.

## DESENVOLVIMENTO (n=300)

| versão | TP | FP | FN | TN | Precisão | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| v12 | 61 | 23 | 24 | 192 | 0.726 | 0.718 | 0.7219 |
| v13-experimental | 61 | 23 | 24 | 192 | 0.726 | 0.718 | 0.7219 |

- Releases cuja previsão muda: **0** (0 positivas no consenso, 0 negativas).
- ΔF1 (v13 − v12) = +0.0000; IC95% por repositório [+0.000; +0.000].

## AVALIAÇÃO (n=200) — PÓS-HOC / EXPLORATÓRIO

| versão | TP | FP | FN | TN | Precisão | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| v12 | 51 | 19 | 27 | 103 | 0.729 | 0.654 | 0.6892 |
| v13-experimental | 53 | 19 | 25 | 103 | 0.736 | 0.679 | 0.7067 |

- Releases cuja previsão muda: **2** (2 positivas no consenso, 0 negativas).
- ΔF1 (v13 − v12) = +0.0175; IC95% por repositório [+0.000; +0.057].

## Ressalvas

- O desenvolvimento não tem tags `-lts`/`-stable`: efeito nulo ali é **falta de cobertura**, não evidência a favor.
- Na avaliação, o ganho vem de poucos itens de poucos repositórios; está dentro do intervalo de confiança.
- Para validar a v13 é preciso uma amostra nova, independente e rotulada antes de rodar a heurística.
