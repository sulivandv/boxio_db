# Boxio v1.21.1 — Correção app_logger

## Problema corrigido

A versão v1.21.0 importava `app_logger` em `src/licensing/license_manager.py`, mas `src/core/logger.py` ainda não possuía essa função.

Erro apresentado:

```text
ImportError: cannot import name 'app_logger' from 'src.core.logger'
```

## Correção

Foi adicionada a função `app_logger()` em `src/core/logger.py`, mantendo compatibilidade com o novo módulo de licenciamento.

## Versão

Boxio v1.21.1
