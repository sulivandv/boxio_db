# Boxio v1.21 — Atualizações via GitHub Releases

## Objetivo

O Boxio já possui estrutura de atualização via GitHub Releases. Esta versão mantém e documenta o fluxo para uso comercial.

## Fluxo

1. Gere uma nova versão do aplicativo com PyInstaller.
2. Crie um instalador ou pacote `.zip`.
3. Gere SHA-256 do pacote.
4. Crie o arquivo `latest.json`.
5. Publique uma nova GitHub Release.
6. Anexe:
   - instalador ou pacote `.zip`;
   - `latest.json`.
7. O Boxio consulta a release mais recente.
8. Se a versão publicada for maior que a instalada:
   - exibe aviso;
   - mostra changelog;
   - baixa o pacote;
   - valida SHA-256;
   - cria backup dos dados persistentes;
   - prepara atualização manual/externa.

## Exemplo de latest.json

```json
{
  "product": "boxio",
  "channel": "stable",
  "latest_version": "1.22.0",
  "minimum_supported_version": "1.20.0",
  "download_url": "",
  "installer_url": "",
  "sha256": "HASH_SHA256_DO_ARQUIVO",
  "notes": [
    "Melhorias de desempenho.",
    "Correções no licenciamento.",
    "Novos relatórios."
  ]
}
```

Se `download_url` estiver vazio, o cliente tenta localizar automaticamente um asset `.zip` ou `.exe` na release.

## Configuração

Edite `src/core/version.py`:

```python
GITHUB_OWNER = "sua-conta-ou-empresa"
GITHUB_REPO = "boxio-releases"
UPDATE_CHANNEL = "stable"
USE_GITHUB_RELEASES = True
```

## Canais recomendados

- `stable`: produção;
- `beta`: clientes de teste;
- `internal`: uso interno.

## Compatibilidade com PyInstaller

O aplicativo principal não deve substituir a si mesmo enquanto está aberto. Em produção, use uma das opções:

1. atualização manual assistida;
2. instalador externo;
3. `updater.exe` separado que:
   - aguarda o Boxio fechar;
   - substitui arquivos;
   - preserva AppData;
   - reabre o sistema.

## Preservação dos dados

Os dados do usuário ficam em AppData e não devem ser apagados pelo instalador:

- banco local/cache;
- configurações;
- licença;
- logs;
- backups;
- dados persistentes do cliente.
