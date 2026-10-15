# Análise de erros da heurística — versão v9

Gerado por `python -m scripts.analise_erros_heuristica` (Issue #30) a partir da rodada da #28.

## Matriz de confusão

| | Consenso: corretiva | Consenso: não |
|---|---:|---:|
| **Heurística: corretiva** | 47 (TP) | 28 (FP) |
| **Heurística: não** | 35 (FN) | 185 (TN) |

## Causas (triagem automática)

| Tipo | Causa | Releases |
|---|---|---:|
| FP | `conteudo_corretivo_sem_consenso` | 28 |
| FN | `conteudo_sem_sinal_corretivo` | 35 |

## Comparação entre versões (frente à v9)

No subconjunto comum (releases avaliáveis por todas as versões, o mesmo da escolha da #28). "Corrige": releases que a versão acerta e a analisada erra; "piora": o contrário.

| Versão | Regra | n comum | Precisão | Recall | F1 | Corrige | Piora |
|---|---|---:|---:|---:|---:|---:|---:|
| v1 | só patch E palavra estrita | 295 | 0.42 | 0.77 | 0.55 | 40 | 82 |
| v2 | só patch OU palavra estrita | 295 | 0.32 | 0.99 | 0.48 | 37 | 146 |
| v3 | só palavra estrita (ignora SemVer) | 295 | 0.31 | 0.87 | 0.46 | 32 | 136 |
| v4 | só patch (não comparável: palavra estrita) | 295 | 0.42 | 0.89 | 0.57 | 45 | 92 |
| v5 | só patch E palavra ampla | 295 | 0.43 | 0.82 | 0.57 | 41 | 81 |
| v6 | só patch OU palavra ampla | 295 | 0.32 | 0.99 | 0.48 | 36 | 146 |
| v7 | só palavra ampla (ignora SemVer) | 295 | 0.32 | 0.91 | 0.47 | 32 | 135 |
| v8 | commit de correção e nenhum de feature | 295 | 0.62 | 0.43 | 0.51 | 7 | 12 |
| v9 | v8 OU release notes com correção e sem novidade | 295 | 0.63 | 0.57 | 0.60 | 0 | 0 |

## Falsos positivos e falsos negativos

| Tipo | Release | Base | Causa automática | Causa manual |
|---|---|---|---|---|
| FP | [0x676e67/wreq v6.0.0-rc.23](https://github.com/0x676e67/wreq/releases/tag/v6.0.0-rc.23) | v6.0.0-rc.22 | `conteudo_corretivo_sem_consenso` |  |
| FP | [0x676e67/wreq v0.16.0](https://github.com/0x676e67/wreq/releases/tag/v0.16.0) | v6.0.0-rc.31 | `conteudo_corretivo_sem_consenso` |  |
| FN | [0xSteph/pentest-ai v0.16.2](https://github.com/0xSteph/pentest-ai/releases/tag/v0.16.2) | v0.16.1 | `conteudo_sem_sinal_corretivo` |  |
| FN | [10up/ElasticPress 5.3.2](https://github.com/10up/ElasticPress/releases/tag/5.3.2) | 5.3.1 | `conteudo_sem_sinal_corretivo` |  |
| FN | [10up/ElasticPress 5.3.5](https://github.com/10up/ElasticPress/releases/tag/5.3.5) | 5.3.4 | `conteudo_sem_sinal_corretivo` |  |
| FN | [4ian/GDevelop v5.5.247](https://github.com/4ian/GDevelop/releases/tag/v5.5.247) | v5.5.246 | `conteudo_sem_sinal_corretivo` |  |
| FN | [4thfever/cultivation-world-simulator v1.2.2](https://github.com/4thfever/cultivation-world-simulator/releases/tag/v1.2.2) | v1.2.1 | `conteudo_sem_sinal_corretivo` |  |
| FN | [4thfever/cultivation-world-simulator v1.5.2](https://github.com/4thfever/cultivation-world-simulator/releases/tag/v1.5.2) | v1.5.1 | `conteudo_sem_sinal_corretivo` |  |
| FP | [4thfever/cultivation-world-simulator v1.6.0](https://github.com/4thfever/cultivation-world-simulator/releases/tag/v1.6.0) | v1.5.4 | `conteudo_corretivo_sem_consenso` |  |
| FN | [7ritn/VaulTLS v1.0.1](https://github.com/7ritn/VaulTLS/releases/tag/v1.0.1) | v0.11.1 | `conteudo_sem_sinal_corretivo` |  |
| FP | [7ritn/VaulTLS v1.3.0](https://github.com/7ritn/VaulTLS/releases/tag/v1.3.0) | v1.2.0 | `conteudo_corretivo_sem_consenso` |  |
| FN | [99designs/gqlgen v0.17.90](https://github.com/99designs/gqlgen/releases/tag/v0.17.90) | v0.17.89 | `conteudo_sem_sinal_corretivo` |  |
| FN | [A-EDev/Flow v1.8.1](https://github.com/A-EDev/Flow/releases/tag/v1.8.1) | v1.8.0 | `conteudo_sem_sinal_corretivo` |  |
| FN | [ACINQ/eclair v0.14.1](https://github.com/ACINQ/eclair/releases/tag/v0.14.1) | v0.14.0 | `conteudo_sem_sinal_corretivo` |  |
| FP | [AChep/keyguard-app r20260911](https://github.com/AChep/keyguard-app/releases/tag/r20260911) | r20260905.2 | `conteudo_corretivo_sem_consenso` |  |
| FP | [AccessKit/accesskit accesskit_consumer-v0.34.0](https://github.com/AccessKit/accesskit/releases/tag/accesskit_consumer-v0.34.0) | accesskit-v0.24.0 | `conteudo_corretivo_sem_consenso` |  |
| FP | [Aethersailor/SubConverter-Extended v1.9.6](https://github.com/Aethersailor/SubConverter-Extended/releases/tag/v1.9.6) | v1.9.5 | `conteudo_corretivo_sem_consenso` |  |
| FP | [Ajaxy/telegram-tt air_v2.8.14](https://github.com/Ajaxy/telegram-tt/releases/tag/air_v2.8.14) | air_v2.8.13 | `conteudo_corretivo_sem_consenso` |  |
| FP | [Ajaxy/telegram-tt air_v2.9.3](https://github.com/Ajaxy/telegram-tt/releases/tag/air_v2.9.3) | air_v2.9.1 | `conteudo_corretivo_sem_consenso` |  |
| FN | [Aleksoid1978/VideoRenderer 0.10.3](https://github.com/Aleksoid1978/VideoRenderer/releases/tag/0.10.3) | 0.10.1 | `conteudo_sem_sinal_corretivo` |  |
| FN | [Aleksoid1978/VideoRenderer 0.10.5](https://github.com/Aleksoid1978/VideoRenderer/releases/tag/0.10.5) | 0.10.3 | `conteudo_sem_sinal_corretivo` |  |
| FN | [Altinity/clickhouse-backup v2.6.40](https://github.com/Altinity/clickhouse-backup/releases/tag/v2.6.40) | v2.6.39 | `conteudo_sem_sinal_corretivo` |  |
| FN | [Altinity/clickhouse-backup v2.6.43](https://github.com/Altinity/clickhouse-backup/releases/tag/v2.6.43) | v2.6.42 | `conteudo_sem_sinal_corretivo` |  |
| FN | [Altinity/clickhouse-backup v2.7.2](https://github.com/Altinity/clickhouse-backup/releases/tag/v2.7.2) | v2.7.1 | `conteudo_sem_sinal_corretivo` |  |
| FP | [a-ghorbani/pocketpal-ai v1.11.7](https://github.com/a-ghorbani/pocketpal-ai/releases/tag/v1.11.7) | v1.11.6 | `conteudo_corretivo_sem_consenso` |  |
| FP | [a-ghorbani/pocketpal-ai v1.17.2](https://github.com/a-ghorbani/pocketpal-ai/releases/tag/v1.17.2) | v1.17.1 | `conteudo_corretivo_sem_consenso` |  |
| FP | [aardappel/lobster v2026.3](https://github.com/aardappel/lobster/releases/tag/v2026.3) | v2026.2 | `conteudo_corretivo_sem_consenso` |  |
| FP | [abenz1267/walker v2.5.6](https://github.com/abenz1267/walker/releases/tag/v2.5.6) | v2.5.5 | `conteudo_corretivo_sem_consenso` |  |
| FP | [abetlen/llama-cpp-python v0.3.26-cu124](https://github.com/abetlen/llama-cpp-python/releases/tag/v0.3.26-cu124) | v0.3.26-cu118 | `conteudo_corretivo_sem_consenso` |  |
| FN | [abhigyanpatwari/GitNexus v1.6.10](https://github.com/abhigyanpatwari/GitNexus/releases/tag/v1.6.10) | v1.6.9 | `conteudo_sem_sinal_corretivo` |  |
| FN | [abhixdd/ghgrab v1.0.5](https://github.com/abhixdd/ghgrab/releases/tag/v1.0.5) | v1.0.4 | `conteudo_sem_sinal_corretivo` |  |
| FP | [abhixdd/ghgrab v1.2.0](https://github.com/abhixdd/ghgrab/releases/tag/v1.2.0) | v1.1.0 | `conteudo_corretivo_sem_consenso` |  |
| FP | [abraham/twitteroauth 7.1.0](https://github.com/abraham/twitteroauth/releases/tag/7.1.0) | 7.0.0 | `conteudo_corretivo_sem_consenso` |  |
| FN | [abraham/twitteroauth 8.1.1](https://github.com/abraham/twitteroauth/releases/tag/8.1.1) | 8.1.0 | `conteudo_sem_sinal_corretivo` |  |
| FP | [absmach/magistrala v0.40.0](https://github.com/absmach/magistrala/releases/tag/v0.40.0) | v0.30.0 | `conteudo_corretivo_sem_consenso` |  |
| FN | [ace-step/ACE-Step-1.5 v0.1.5](https://github.com/ace-step/ACE-Step-1.5/releases/tag/v0.1.5) | v0.1.4 | `conteudo_sem_sinal_corretivo` |  |
| FP | [actions/setup-dotnet v5.1.0](https://github.com/actions/setup-dotnet/releases/tag/v5.1.0) | v5.0.1 | `conteudo_corretivo_sem_consenso` |  |
| FP | [actions/setup-java v4.8.0](https://github.com/actions/setup-java/releases/tag/v4.8.0) | v5.1.0 | `conteudo_corretivo_sem_consenso` |  |
| FN | [actualbudget/actual v26.5.2](https://github.com/actualbudget/actual/releases/tag/v26.5.2) | v26.5.1 | `conteudo_sem_sinal_corretivo` |  |
| FP | [actualbudget/actual v26.10.0](https://github.com/actualbudget/actual/releases/tag/v26.10.0) | v26.9.0 | `conteudo_corretivo_sem_consenso` |  |
| FN | [ag-grid/ag-grid release-34.3.1](https://github.com/ag-grid/ag-grid/releases/tag/release-34.3.1) | release-34.3.0 | `conteudo_sem_sinal_corretivo` |  |
| FN | [ag2ai/ag2 v0.11.2](https://github.com/ag2ai/ag2/releases/tag/v0.11.2) | v0.11.1 | `conteudo_sem_sinal_corretivo` |  |
| FN | [ag2ai/ag2 v1.1.1](https://github.com/ag2ai/ag2/releases/tag/v1.1.1) | v1.1.0 | `conteudo_sem_sinal_corretivo` |  |
| FP | [agentrhq/webcmd webcmd-v0.2.5](https://github.com/agentrhq/webcmd/releases/tag/webcmd-v0.2.5) | webcmd-v0.2.4 | `conteudo_corretivo_sem_consenso` |  |
| FN | [agentscope-ai/AgentTeams v0.9.2](https://github.com/agentscope-ai/AgentTeams/releases/tag/v0.9.2) | v0.9.1 | `conteudo_sem_sinal_corretivo` |  |
| FP | [ajayyy/DeArrow 2.3.6](https://github.com/ajayyy/DeArrow/releases/tag/2.3.6) | 2.3.5 | `conteudo_corretivo_sem_consenso` |  |
| FP | [ajayyy/DeArrow 2.3.8](https://github.com/ajayyy/DeArrow/releases/tag/2.3.8) | 2.3.7 | `conteudo_corretivo_sem_consenso` |  |
| FN | [akash-network/node v2.1.1](https://github.com/akash-network/node/releases/tag/v2.1.1) | v2.1.0 | `conteudo_sem_sinal_corretivo` |  |
| FN | [akto-api-security/akto v1.89.6](https://github.com/akto-api-security/akto/releases/tag/v1.89.6) | v1.89.5 | `conteudo_sem_sinal_corretivo` |  |
| FN | [akvorado/akvorado v2.0.1](https://github.com/akvorado/akvorado/releases/tag/v2.0.1) | v2.0.0 | `conteudo_sem_sinal_corretivo` |  |
| FN | [akvorado/akvorado v2.4.1](https://github.com/akvorado/akvorado/releases/tag/v2.4.1) | v2.4.0 | `conteudo_sem_sinal_corretivo` |  |
| FN | [alam00000/bentopdf v2.8.2](https://github.com/alam00000/bentopdf/releases/tag/v2.8.2) | v2.8.1 | `conteudo_sem_sinal_corretivo` |  |
| FN | [alibaba/nacos 3.2.1](https://github.com/alibaba/nacos/releases/tag/3.2.1) | 3.2.0 | `conteudo_sem_sinal_corretivo` |  |
| FN | [alibaba/nacos 3.2.3](https://github.com/alibaba/nacos/releases/tag/3.2.3) | 2.5.3 | `conteudo_sem_sinal_corretivo` |  |
| FP | [allenpeng0705/EnvoyMesh EnvoyMesh-0-4-0](https://github.com/allenpeng0705/EnvoyMesh/releases/tag/EnvoyMesh-0-4-0) | EnvoyMesh_0_3_0-release | `conteudo_corretivo_sem_consenso` |  |
| FP | [alookai/alook cli/v0.0.7](https://github.com/alookai/alook/releases/tag/cli/v0.0.7) | cli/v0.0.6 | `conteudo_corretivo_sem_consenso` |  |
| FN | [alookai/alook app/v0.0.100](https://github.com/alookai/alook/releases/tag/app/v0.0.100) | cli/v0.0.100 | `conteudo_sem_sinal_corretivo` |  |
| FN | [alookai/alook v0.1.21](https://github.com/alookai/alook/releases/tag/v0.1.21) | v0.1.20 | `conteudo_sem_sinal_corretivo` |  |
| FN | [alphaXiv/OpenResearch v0.1.34](https://github.com/alphaXiv/OpenResearch/releases/tag/v0.1.34) | v0.1.33 | `conteudo_sem_sinal_corretivo` |  |
| FP | [alphaXiv/OpenResearch v0.1.109](https://github.com/alphaXiv/OpenResearch/releases/tag/v0.1.109) | v0.1.108 | `conteudo_corretivo_sem_consenso` |  |
| FN | [alphaXiv/OpenResearch v0.2.4](https://github.com/alphaXiv/OpenResearch/releases/tag/v0.2.4) | v0.2.3 | `conteudo_sem_sinal_corretivo` |  |
| FP | [alshedivat/al-folio v0.16.2](https://github.com/alshedivat/al-folio/releases/tag/v0.16.2) | v0.16.1 | `conteudo_corretivo_sem_consenso` |  |
| FP | [alvinunreal/tmuxai v2.2.0](https://github.com/alvinunreal/tmuxai/releases/tag/v2.2.0) | v2.2.1 | `conteudo_corretivo_sem_consenso` |  |

## Resumo para Ameaças à validade (construto)

Na versão v9, 28 das 75 releases marcadas como corretivas são falsos positivos (37%) e 35 das 82 corretivas do consenso não foram encontradas (43%). Causa mais frequente de FP: `conteudo_corretivo_sem_consenso` (28); de FN: `conteudo_sem_sinal_corretivo` (35). 0 FN se devem a commits indisponíveis (`compare` 404 ou truncado). O CFR (b) herda esses erros: FP inflam e FN reduzem a taxa.
