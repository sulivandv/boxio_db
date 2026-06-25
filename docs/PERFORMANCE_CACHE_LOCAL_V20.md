# Boxio v1.20.0 — Arquitetura de performance cache-first

## Objetivo

A interface desktop não deve depender da latência do banco online para abrir páginas, trocar telas, digitar em formulários ou renderizar tabelas. O PostgreSQL/Neon permanece como fonte oficial, mas o cliente desktop usa um cache local SQLite para leitura rápida.

## Camadas

```text
PySide UI
  ↓ leitura instantânea
StockServicePostgres
  ↓ cache-first
SQLite local: AppData/Local/Boxio/Cache/boxio_local_cache.sqlite
  ↓ sincronização em background
PostgreSQL/Neon
```

## O que foi implementado

- `src/services/local_cache.py`: cache local SQLite de coleções.
- `StockServicePostgres.products()`: lê produtos do SQLite local antes de consultar Neon.
- `StockServicePostgres.purchase_requests()`: lê solicitações do cache local e filtra em memória.
- `StockServicePostgres.recent_movements()`: lê movimentações recentes do cache local.
- `StockServicePostgres.sync_remote_cache_async()`: sincroniza Neon em thread de fundo.
- `MainWindow.start_background_sync()`: inicia sincronização após abertura da UI.
- `refresh_all()` passou a atualizar apenas a página atual, evitando recarregar telas invisíveis.
- Inventário renderiza no máximo 500 linhas por vez para evitar travamento em grandes bases.

## Próximas evoluções recomendadas

1. Criar uma API intermediária para WebSocket/SSE em vez de conectar cada desktop diretamente no banco.
2. Implementar sincronização incremental real por `updated_at` e tombstones para exclusões.
3. Trocar `QTableWidget` por `QTableView + QAbstractTableModel` para virtualização completa.
4. Adicionar fila local de operações pendentes para modo offline.
5. Criar um botão de sincronização manual e indicador visual de status da conexão.

## Boas práticas

- Operações de gravação continuam indo diretamente ao PostgreSQL/Neon.
- A UI lê cache local para permanecer responsiva.
- Após gravações, os caches relacionados são invalidados para evitar dados obsoletos.
- A sincronização remota ocorre em background e não bloqueia a thread principal do Qt.
