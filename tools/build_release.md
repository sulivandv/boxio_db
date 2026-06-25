# Publicação gratuita de versões via GitHub Releases

## 1. Preparar versão

Atualize `src/core/version.py`:

```python
APP_VERSION = "1.18.0"
DB_SCHEMA_VERSION = 16
GITHUB_OWNER = "seu_usuario"
GITHUB_REPO = "boxio-releases"
```

## 2. Gerar build Windows

No PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File tools\release\create_windows_build.ps1
```

Isso cria:

```text
dist/boxio_1.18.0.zip
dist/latest.json
```

## 3. Criar release no GitHub

No GitHub:

1. Abra o repositório de releases.
2. Clique em Releases > Draft a new release.
3. Tag: `v1.18.0`.
4. Título: `Boxio v1.18.0`.
5. Anexe:
   - `boxio_1.18.0.zip`
   - `latest.json`
6. Publique a release.

## 4. Como o app detecta atualização

O app consulta:

```text
https://api.github.com/repos/SEU_USUARIO/boxio-releases/releases/latest
```

Depois baixa o asset `latest.json`, compara a versão e oferece atualização.

## 5. Segurança mínima

Sempre publique o SHA-256 correto no `latest.json`. O app bloqueia instalação caso o hash não confira.

## 6. Compatibilidade com dados existentes

Não salve banco do cliente na pasta do executável. Os dados devem ficar em AppData ou no PostgreSQL centralizado. Antes de migrações, crie backup.
