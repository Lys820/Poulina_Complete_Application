#!/usr/bin/env python
"""
TEST SQL SERVER – Connexion Windows Authentication
"""
import pyodbc
from dotenv import load_dotenv
import os

# Charger les variables .env
load_dotenv()

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║              SQL SERVER CONNECTION TEST - TRUSTED CONNECTION              ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

# Variables depuis .env
SERVER = os.getenv("SQLSERVER_SERVER", r"localhost\SQLEXPRESS")
DATABASE = os.getenv("SQLSERVER_DATABASE", "POULINA")

print(f"\n1️⃣  CONFIGURATION")
print("-" * 70)
print(f"Server   : {SERVER}")
print(f"Database : {DATABASE}")
print("Auth     : Windows Authentication (Trusted Connection)")

print(f"\n2️⃣  CONNEXION")
print("-" * 70)

try:
    # Connexion Windows Authentication
    connection_string = (
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server={SERVER};"
        f"Database={DATABASE};"
        f"Trusted_Connection=yes;"
    )

    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    print("✓ CONNEXION OK")

    # 3. Test query
    print(f"\n3️⃣  TEST QUERY")
    print("-" * 70)

    cursor.execute("SELECT COUNT(*) FROM centre_elevage")
    row = cursor.fetchone()
    print(f"✓ Centres   : {row[0]}")

    cursor.execute("SELECT COUNT(*) FROM laboratoire")
    row = cursor.fetchone()
    print(f"✓ Labos     : {row[0]}")

    cursor.execute("SELECT COUNT(*) FROM demande_analyse")
    row = cursor.fetchone()
    print(f"✓ Analyses  : {row[0]}")

    # 4. Liste des tables
    print(f"\n4️⃣  TABLES")
    print("-" * 70)

    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)

    tables = cursor.fetchall()

    print(f"✓ {len(tables)} tables trouvées :")

    for table in tables:
        print(f"  - {table[0]}")

    cursor.close()
    conn.close()

    print(f"\n{'=' * 70}")
    print("✅ SQL SERVER OK – Prêt pour l'application")
    print(f"{'=' * 70}")

except Exception as e:
    print(f"❌ ERREUR : {type(e).__name__}")
    print(f"Message   : {e}")

    print(f"\nDiagnostic :")
    print("  1. SQL Server est démarré ?")
    print("  2. ODBC Driver 17 installé ?")
    print("  3. Base POULINA créée ?")
    print("  4. Votre compte Windows a accès à SQL Server ?")