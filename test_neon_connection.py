"""Teste rápido de conexão do Boxio com Neon/PostgreSQL.

Uso:
1. Crie o arquivo .env na raiz do projeto.
2. Configure BOXIO_DATABASE_URL.
3. Rode: python test_neon_connection.py
"""
from src.database.postgres.connection import check_database_connection, get_schema_version

if __name__ == "__main__":
    database, user, schema = check_database_connection()
    print("Conexão realizada com sucesso!")
    print("Banco:", database)
    print("Usuário:", user)
    print("Schema atual:", schema)
    print("Versão do schema Boxio:", get_schema_version())
