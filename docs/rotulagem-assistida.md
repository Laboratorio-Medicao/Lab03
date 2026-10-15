# Rotulagem assistida e registrada (validação independente)

> **Aviso:** `sugestoes_ia.csv`, o adendo e a pasta `comparacao_ia/` foram removidos do repositório. Sem `sugestoes_ia.csv` a ferramenta funciona só no modo normal (fase 1, sem sugestões); o modo `--comparacao` fica inoperante. As seções sobre sugestões/comparação descrevem o que existiu.

## 1. Estado encontrado
- `data/validacao_independente/`: 200 releases de 40 repositórios, 3 planilhas em branco (`labels_<nome>.csv`, colunas `tipo_projeto`, `releases_sao_entregas_reais` na 1ª linha de cada repositório e `corretiva` por release), `dados_congelados.json` (5 MB; notas e mensagens, 1 release com 4.362 commits), `congelamento.json` (hashes, avaliadores).
- O consumo é por `scripts.validacao_independente avaliar`, que valida com `validar_rotulos` e usa `scripts.agreement`. Nada disso foi alterado.
- O protocolo diz que cada avaliador lê `release_url` e `compare_url` e rotula sem ver previsões. Preencher 280 itens por pessoa em CSV é o gargalo.

## 2. Alternativas

| | A. Lista única com todas as filas | B. Cada integrante roda a **própria instância** com `--usuario` e vê só a própria fila |
|---|---|---|
| Complexidade | Média: login, multiusuário, concorrência | Baixa: um processo local por pessoa, um arquivo de log por pessoa |
| Proteção contra sobrescrita | Depende de autenticação que não existe | Estrutural: a instância só escreve `rotulagem/<usuario>.jsonl` e `labels_<usuario>.csv` |
| Cegamento entre avaliadores | Exige impedir ver o trabalho dos outros | Natural (cada máquina, cada arquivo) |
| Compatibilidade | Precisa exportar 3 arquivos | Exporta exatamente `labels_<usuario>.csv` |
| Risco de "um clique = decisão" | Igual | Mitigado igual nas duas (confirmação explícita) |

**Recomendada: B.** É a mais simples e não depende de autenticação.

## 3. O que foi implementado
`scripts/rotulagem_assistida.py` (servidor local `127.0.0.1`, uma página, sem dependências novas) e `tests/test_rotulagem_assistida.py` (14 testes).

- **Exibe** links, notas (até 6.000 caracteres) e mensagens dos commits (até 40, 300 caracteres cada), exatamente o conteúdo que o protocolo manda ler. Nunca exibe previsão, versão, sinais; o módulo não importa `metricas`.
- **Duas fases:** decisão inicial (sem sugestão) → opcionalmente "Ver sugestão automática" → decisão final com confirmação do navegador e do servidor. "Adotar" não existe: a sugestão não vira decisão sem escolher o valor e confirmar.
- **Log só de acréscimo** por usuário: horário, item, valor, fase, `sugestao_vista_antes`, `valor_coincide_com_sugestao`, origem `humano_via_interface`. A decisão inicial é imutável depois de ver a sugestão.
- **Salvar e continuar:** o estado é recomputado do log; reabrir retoma.
- **Exportar** `labels_<usuario>.csv` (usa a decisão final, senão a inicial) e `rotulagem/<usuario>_resumo.json`. Recusa sobrescrever um arquivo com conteúdo que não veio da ferramenta (`--forcar-exportar` cria `.bak`).
- **Nenhum F1 é calculado ou exibido.** O `avaliar` continua recusando rodar com rótulos incompletos.
- **Sugestões:** `sugestoes_ia.csv` (200 linhas; 67 `sim`, 34 marcadas como dúvida), fonte e motivo por linha; ver `data/validacao_independente/ADENDO_PROTOCOLO_SUGESTOES.md`.

## 4. Uso (cada integrante, na própria máquina)
```bash
git pull
python -m scripts.rotulagem_assistida --usuario marcosffp      # ou GuilhermeVieira05 / ALuiz19
# decida cada item na página; "Exportar" grava data/validacao_independente/labels_<usuario>.csv
python -m scripts.validar_rotulos data/validacao_independente/labels_<usuario>.csv \
       --amostra data/validacao_independente/amostra_validacao.csv
git add data/validacao_independente/labels_<usuario>.csv data/validacao_independente/rotulagem/<usuario>*
git commit -m "#N - rótulos da validação independente (<usuario>)"      # só o seu arquivo
```
Depois que os três commitaram: `python -m scripts.validacao_independente avaliar` (uso único).

Para **não** usar sugestões: remova ou renomeie `sugestoes_ia.csv` antes de abrir a ferramenta.

## 5. Limitações metodológicas que permanecem
1. **Sem autenticação:** o nome é informado, não comprovado. Uma pessoa pode preencher os três arquivos; isso invalida a independência e deve ser declarado.
2. **Sugestões únicas, de IA, iguais para todos:** risco de ancoragem e circularidade (ver adendo). Não foram variadas artificialmente. A fase 1 cega e o log permitem medir o efeito, mas não eliminá-lo.
3. **Mudança de protocolo:** usar sugestões é um adendo, não o protocolo original; precisa de aceite.
4. **Quem implementou a heurística** (e conhece suas regras) segue sendo avaliador; declarar em `observacoes` e reportar sensibilidade.
5. **κ baixo e limiares diferentes entre avaliadores** (59%/16%/29% de "sim" no desenvolvimento) continuam; a definição do protocolo reduz, não elimina.
6. Os arquivos `sugestoes_ia.csv` e `dados_congelados.json` ficam legíveis no repositório: a ferramenta controla a ordem de exibição, não impede quem abrir os arquivos.

## 6. Modo de comparação com as sugestões da IA (`--comparacao`)

Para comparar a resposta de alguém (p. ex., anotada no papel) com as sugestões automáticas **sem** fazer rotulagem cega.

```bash
.venv/bin/python -m scripts.rotulagem_assistida --usuario GuilhermeVieira05 --comparacao   # porta 8766
# na página: Confirmar / Alterar / Rejeitar cada sugestão (com confirmação) e, no fim, "Concluir"
# ou, sem abrir a página: ... --usuario GuilhermeVieira05 --comparacao --exportar
```

- Mostra as 200 releases com a sugestão de `data/validacao_independente/sugestoes_ia.csv`, rotulada em destaque como **AUTOMÁTICA (IA), não decisão humana**. Nenhum valor é pré-aceito: cada item começa `pendente`.
- **Confirmar** registra a sugestão como resposta do avaliador; **Alterar** registra o valor oposto; **Rejeitar** registra "sem resposta". Todas pedem confirmação, e a decisão é sempre **vendo** a sugestão (marcada `decisao_vendo_sugestao`).
- **Saída separada** em `data/validacao_independente/comparacao_ia/`: `<usuario>.jsonl` (log), `<usuario>_comparacao.csv` e `<usuario>_comparacao_resumo.json`. O CSV é **regenerável** a partir do log (`--comparacao --exportar`), então pode ser apagado; o log `.jsonl` e o resumo são a evidência. **Não** escreve `labels_*.csv`, nem `rotulagem/`; o `avaliar` não lê essa pasta (teste garante).
- O CSV tem, por release: `sugestao_ia`, `origem_da_sugestao`, `fonte_da_sugestao`, `acao_do_avaliador`, `resposta_humana`, `alterou_a_sugestao`, `registrado_em`, `usuario_informado`.
- **Isto não é a validação independente da v12.** As respostas aqui foram dadas com a sugestão à vista; para que a pessoa tenha rótulos válidos na validação, ela precisa usar o modo normal (fase 1 cega). A ferramenta não converte uma comparação em `labels_*.csv`.
- Só `corretiva` é comparada: não há sugestões para tipo do projeto nem para "entregas reais".
- Não foram gerados rótulos "no estilo" de nenhuma pessoa nem erros artificiais; as sugestões são as mesmas, únicas, de `sugestoes_ia.csv`.
