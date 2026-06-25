"""Informações centralizadas de versão do Boxio.

A versão do aplicativo e a versão do schema do banco são separadas. Isso permite
atualizar a interface sem alterar o banco, ou aplicar migrações SQL quando a
estrutura de dados evoluir.
"""
from __future__ import annotations

APP_NAME = "Boxio"
PRODUCT_ID = "boxio"
APP_VERSION = "2.2.6"
DB_SCHEMA_VERSION = 21
UPDATE_CHANNEL = "stable"
GITHUB_OWNER = "sua-conta-ou-empresa"
GITHUB_REPO = "boxio-releases"

# Define se o atualizador deve consultar o GitHub Releases por padrão.
# Em ambiente de desenvolvimento, pode ser alterado para False para testar endpoint JSON direto.
USE_GITHUB_RELEASES = True
