# Plataformas

## Exceção explícita: bypass

Quando o pedido atual contiver a palavra isolada `bypass` (inclusive `BYPASS` ou `/bypass`), o seletor configurado prevalece sobre qualquer tabela abaixo. Preserve modelo e esforço, sem classificação, alteração de configuração ou bloqueio por divergência. A exceção vale nas quatro plataformas apenas para esse pedido; o próximo pedido sem a palavra volta à rota normal. É útil quando o modelo recomendado está sem cota. Se o seletor não puder ser lido, deixe a IDE continuar com sua configuração e não invente um par.

Cada IDE só aplica um modelo da própria família. Antigravity fica no Google. Grok fica no Grok. Codex fica no GPT. Claude Code fica no Claude. O catálogo abaixo reflete as versões e caches disponíveis no ambiente em 13 de novembro de 2026. A segunda fase, uma plataforma ligada para modelos gratuitos, não entra aqui.

A régua é o volume de tokens da cota que a mensalidade já inclui. O preço de API por milhão de tokens não escolhe o par. O entendimento do pedido usa o catálogo desta plataforma. Em 10 de novembro de 2026, um `grok -p` com `grok-4.7` esforço `low` e prompt de sistema curto ainda carregou o prompt inteiro do Grok Build: cerca de 26 mil tokens de entrada, e devolveu o mesmo par que as regras. Por isso o hook usa as regras no dia a dia. `ESCOLHA_DE_MODELO_LLM=1` liga aquela chamada. A resposta usa o par escolhido, antes de seguir, só se o seletor aberto já está nele.

## Grok

Catálogo inspecionado em `~/.grok/models_cache.json` e `grok models`.
Modelos suportados: `grok-4.7`, `grok-4.7-build-fast`, `grok-4.6`, `grok-4.5`.

| Id | Quando | Esforço |
| --- | --- | --- |
| `grok-4.7` | Entendimento do pedido | `low` |
| `grok-4.7` | Formato, lista, renome, typo | `low` |
| `grok-4.7` | Explicação ou edição simples | `medium` |
| `grok-4.7` | Código, bug, desenho, regra | `high` |
| `grok-4.7` | O `high` desta sessão não fechou | `xhigh` |
| `grok-4.7-build-fast` | O pedido pede explicitamente latência/velocidade | o mesmo esforço da tarefa (`low`, `medium`, `high`, `xhigh`) |

`grok-4.6` e `grok-4.5` aparecem no seletor. Esta rota não os escolhe por padrão: ainda não há medida de que fechem a mesma tarefa com menos tokens da cota. Se a sessão já estiver num desses ids, o aplicador mantém o id e só ajusta o esforço listado por ele. O Fast entra só quando o pedido pede latência/urgência explícita (a folha de API cobra cerca do dobro por ele; na cota, o débito é o que `/usage` mostrar).

Aplicação: `session/set_config_option` é o controle ao vivo. O processo do TUI não abre esse canal para um hook, e reescreve `summary.json` a partir da memória. O hook não grava esse arquivo. Ele lê `current_model_id` e `reasoning_effort`. `aplicado` só quando os dois já são o par escolhido. Se divergem, a saída do hook é `decision: block` com `/model` e `/effort`, e a decisão fica em `~/.escolha-de-modelo/ultima-rota.json` (espelho em `~/.grok/escolha-de-modelo/`). Cada pedido das quatro IDEs entra em `~/.escolha-de-modelo/rotas.jsonl` e na tabela `rotas.md`: plataforma, pedido, análise, par sugerido e par utilizado. As regras são o entendimento padrão. `ESCOLHA_DE_MODELO_LLM=1` chama `grok -p` em `grok-4.7` esforço `low` e volta às regras se a chamada falhar. Hooks novos entram na próxima sessão ou em `/hooks` e depois `r`.

## Codex

Slugs oficiais de `~/.codex/models_cache.json`.
Modelos ativos na família GPT-6 e suporte:
- `gpt-6.1-sol` (prioridade 1): linha de frente para tarefas cotidianas e código profundo. Suporta esforços `low`, `medium`, `high`, `xhigh`, `max`, `ultra`. Default: `low`.
- `gpt-6-astra` (prioridade 2): modelo topo para raciocínio exaustivo e os problemas mais difíceis onde o Sol não fecha. Suporta `low` a `ultra`. Default: `low`.
- `gpt-6.1-terra` (prioridade 3): otimizado para visão computacional, inspeção de UI, telas e computer-use. Suporta `low` a `ultra`. Default: `low`.
- `gpt-6-sol` (prioridade 4): geração estável anterior de código. Suporta `low` a `ultra`. Default: `medium`.
- `gpt-reserve` (prioridade 5): failover de alta capacidade da OpenAI. Suporta `low` a `max`. Default: `medium`.
- `gpt-6-luna` (prioridade 6): ultrarrápido e econômico para extração, classificação e formatos estruturados. Suporta `low` a `max`. Default: `medium`.
- Modelos legados mantidos no cache: `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `codex-auto-review`.

Quando o hook roda dentro do Codex, ele grava `model` e `model_reasoning_effort` em `~/.codex/config.toml`. `aplicado` só se essas duas linhas já eram o par. Uma gravação nova fica `pedido`: a sessão aberta não relê o arquivo. Nesse caso o `UserPromptSubmit` devolve `decision: block` e pede `/model <slug> --reasoning=<esforço>`. O hook em `~/.codex/hooks.json` fica inativo até o `/hooks` confiar nele.

| Slug | Quando | Esforço |
| --- | --- | --- |
| `gpt-6-luna` | Entendimento do pedido | `low` |
| `gpt-6-luna` | Formato, lista, extração, renome | `low` |
| `gpt-6.1-terra` | Tela, screenshot, inspeção de UI, visão | `low` (sobe para `medium`/`high` se exigir julgamento complexo) |
| `gpt-6.1-sol` | Código, bugs, refatoração e engenharia do dia a dia | `low`, depois `medium`, depois `high`, depois `xhigh` |
| `gpt-6-astra` | O `gpt-6.1-sol` não fechou ou tarefa de máxima complexidade | `low`, depois `medium`, depois `high` |

## Antigravity (Gemini)

No ecossistema Google Antigravity, a CLI e o ambiente expõem os modelos Gemini com níveis de raciocínio integrados (Low, Medium, High, XHigh).
Configuração em `~/.gemini/antigravity-cli/settings.json` e catálogo nativo de execução:
- `Gemini 3.8 Flash` (`Low`, `Medium`, `High`): linha ultrarrápida, de baixo consumo de cota, recomendada para entendimento, classificação, tarefas de texto, edições cirúrgicas e scripts simples.
- `Gemini 4 Argon` (`Low`, `Medium`, `High`): modelo equilibrado para engenharia de software cotidiana, contexto amplo e análise de documentos complexos.
- `Gemini 4 Hydrogen` (`Low`, `Medium`, `High`, `XHigh`): modelo de raciocínio profundo de fronteira, reservado para arquitetura complexa, depuração profunda e casos onde o Argon não fecha.
- `Orchestrator (Argon)` (`gemini-pro-orchestrator-g1-pro`): modelo de orquestração de subagentes/enxame.

| Modelo / Identificador | Quando | Esforço |
| --- | --- | --- |
| `Gemini 3.8 Flash` | Entendimento do pedido, formatação, extração, edição simples | `Low` |
| `Gemini 3.8 Flash` | Explicação, rascunho ou scripts rápidos | `Medium` |
| `Gemini 4 Argon` | Código, refatoração, engenharia de software, maço de arquivos | `Low`, depois `Medium`, depois `High` |
| `Gemini 4 Hydrogen` | Bug difícil, arquitetura crítica, raciocínio exaustivo quando Argon não fecha | `Medium`, depois `High`, depois `XHigh` |

Aplicação: Na CLI do Antigravity, o seletor ativo é refletido na chave `"model"` do arquivo de configurações (ex.: `"Gemini 3.8 Flash (Low)"` ou `"Gemini 4 Argon (Medium)"`). O hook `PreInvocation` em `~/.gemini/config/hooks.json` lê `modelName` do payload, ou essa chave, e grava a tabela com origem `pedido`. `PostInvocation` e `Stop` leem a linha `Rota:` escrita na resposta, depois do último pedido, e gravam a segunda linha com origem `resposta`. A linha é `aplicado` quando o seletor coincide com o par escolhido; caso contrário, é `pedido`. Na primeira invocação do turno (`invocationNum` 0), `pedido` com seletor legível encerra a chamada com `terminationBehavior: terminate` e o comando `/model`.

## Claude Code

A família é Claude. O `UserPromptSubmit` em `~/.claude/settings.json` não troca o seletor. Ele lê o modelo do payload ou de `settings.json`. Com seletor legível e par divergente, devolve `decision: block` e pede `/model`. Sem seletor legível, grava `pedido` e deixa o turno seguir. Os degraus continuam os do guia:
- `Claude Haiku 5.5` em `low`/`medium`: lote, classificação, extração rápida.
- `Claude Sonnet 5.5` em `high`: linha padrão para código, edição cirúrgica e regras rígidas.
- `Claude Opus 5.5` em `medium`: quando Sonnet não fecha ou para síntese conceitual.
- `Claude Fable 5.1` em `high`: em sessões de muitas horas ou tarefas de altíssima exigência.
