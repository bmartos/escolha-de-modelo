---
name: escolha-de-modelo
description: Choose and apply the model and effort that finish a request while spending the least of the open IDE's subscription token quota. Antigravity stays on Google, Grok stays on Grok, Codex stays on GPT, and Claude Code stays on Claude. Use when a task's model or effort changes quota use or quality. API price per million tokens is not the route. A later phase may add a free-model platform.
metadata:
  short-description: Gasta menos da cota da mensalidade
---
# Escolha de modelo

A regra global já roda a checagem em toda mensagem. A IDE aberta só aplica um modelo da própria família. O catálogo e o aplicador estão em [references/plataformas.md](references/plataformas.md). A cota da mensalidade e a origem estão em [references/guia-unificado.md](references/guia-unificado.md). A tabela longa em [references/aplicacao-modelos-esforco.md](references/aplicacao-modelos-esforco.md) compara famílias. Ela não autoriza trocar de plataforma. O preço de API por milhão de tokens não escolhe o par.

Antes da resposta, o entendimento usa o esforço mais baixo da plataforma que ainda classifica. O par da resposta é o que termina o pedido gastando menos tokens da cota da mensalidade. O aplicador compara esse par com o seletor aberto. A primeira linha visível é `Rota: <situação> · <modelo> · esforço <nível> · aplicado` quando o seletor já está nesse par, ou `· pedido` quando não está. Se o seletor lido diverge do par, o hook segura o turno antes do modelo responder e mostra o comando daquela IDE: Grok `/model` e `/effort`, Codex `/model <slug> --reasoning=<esforço>`, Antigravity `/model <nome> (<Esforço>)`, Claude `/model`. Sem seletor legível, o turno segue e o log fica `pedido`.

## Checagem de toda mensagem

0. Se o usuário incluir a palavra isolada `bypass` no pedido atual (sem distinguir maiúsculas), ignore a recomendação e mantenha o modelo e o esforço já configurados na IDE. Não classifique, não chame outro modelo, não grave um par novo e não bloqueie por divergência ou falta de cota. Vale apenas para esse pedido; o próximo sem `bypass` volta ao roteamento normal. A linha visível usa `Rota: bypass · <modelo atual> · esforço <nível atual> · aplicado` quando o seletor for legível; se não for, informe que o seletor não foi lido, sem inventar modelo nem exigir troca. O hook tenta registrar o bypass, mas falha de leitura ou log não impede o turno.
1. Identifique a plataforma aberta.
2. Classifique o pedido com o entendimento dessa plataforma. No Grok, as regras do catálogo são o padrão: um `grok -p` separado gasta de novo a cota.
3. Escolha o modelo e o esforço dessa plataforma que terminam o pedido com o menor gasto de tokens da cota. Conte o retrabalho. Suba um nível de esforço só quando o de baixo não fecha.
4. Aplique esse par antes da resposta.
5. Adapte o pedido ao jeito dessa família.

## Rota padrão

O par aplicado está em [references/plataformas.md](references/plataformas.md). Dentro da plataforma, suba o esforço um nível antes de subir de modelo, e só porque o esforço de baixo não fechou. Modelos gratuitos ficam para a fase seguinte.

## Como pedir na família atual

- **Claude:** separe instrução, contexto e exemplo com tags XML. Diga o que fazer e por quê. No código, exija o teste e a leitura do resultado.
- **GPT / Codex:** dê objetivo, material e o que conta como pronto. Não peça o raciocínio interno. Instrução estável no começo.
- **Gemini:** documentos primeiro, pergunta e regras de saída no fim. Se o material não disser, a resposta é que não está dito.
- **Grok:** fato posterior a maio de 2026 passa por busca web ou busca no X. Esforço `high` em código; `xhigh` só se `high` não fechou.
- **Muse:** entregue um objetivo e o critério de conclusão. E-mail, compra e browser pedem aprovação.
- **Volume:** uma amostra conferida antes do lote.

## Pronto

O pedido original está feito. A linha `Rota:` é a primeira linha visível e nomeia um modelo da plataforma aberta. `aplicado` significa que o seletor aberto já está nesse par. `pedido` significa que o hook não trocou o seletor.

Cada classificação das quatro IDEs entra na mesma tabela em `~/.escolha-de-modelo/rotas.md` (JSONL em `rotas.jsonl`): plataforma, pedido, o que foi analisado, o par sugerido e o par que o seletor usava. O Grok também espelha esses dois arquivos em `~/.grok/escolha-de-modelo/`.
