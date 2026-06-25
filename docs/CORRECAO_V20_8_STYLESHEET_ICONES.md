# Boxio v1.20.8 — Correção do stylesheet dos ícones

## Correção aplicada

A versão anterior utilizava `f-string` diretamente no stylesheet Qt. Como CSS usa chaves `{}` em todos os seletores, o Python tentou interpretar trechos como `background` como variáveis, causando:

`NameError: name 'background' is not defined`

## Solução

O stylesheet voltou a ser uma string normal e os caminhos dos ícones foram aplicados por placeholders:

- `__COMBO_ARROW_ICON__`
- `__PLUS_ICON__`
- `__MINUS_ICON__`

Isso mantém os ícones visuais nos controles sem quebrar a leitura do CSS pelo Python.
