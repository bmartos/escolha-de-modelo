# Escolha de modelo

Seletor de modelo e esforço para a IDE que já está aberta. Antigravity fica no Google, Grok fica no Grok, Codex fica no GPT e Claude Code fica no Claude. A régua é o volume de tokens da cota da mensalidade. O preço de API por milhão de tokens não escolhe o par.

O catálogo está em `references/plataformas.md`. O hook está em `scripts/aplicar-plataforma.py`.

## O que o hook faz

1. Lê o pedido e escolhe o par da família da IDE.
2. Se o seletor aberto já é esse par, o turno segue.
3. Se o seletor lido é outro, o hook segura o turno e mostra o comando daquela IDE.
4. A pessoa troca o seletor e reenvia o pedido.

A palavra isolada `bypass` no pedido atual mantém o modelo e o esforço já configurados.

## Instalação

Coloque esta pasta em `~/.agents/skills/escolha-de-modelo/` e aponte o hook de cada IDE para:

```text
python -X utf8 -B <pasta>/scripts/aplicar-plataforma.py --plataforma <grok|codex|antigravity|claude>
```

O registro da resposta no Antigravity usa o mesmo script com `--fase resposta`.

O log local fica em `~/.escolha-de-modelo/rotas.md`. Esse histórico não entra neste repositório.

## Verificação

```text
python -m unittest scripts/test_bypass.py
```
