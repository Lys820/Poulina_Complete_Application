#!/usr/bin/env python
"""
TEST CONNEXION SQL SERVER - Diagnostic complet
Verifie la connexion a SQL Server et charge les donnees
"""

import sys
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

log = logging.getLogger(__name__)

print("""
================================================================================
                    TEST CONNEXION SQL SERVER POULINA
================================================================================
""")

# =============================================================================
# 1. VERIFICATION DRIVERS
# =============================================================================

print("\n1. VERIFICATION DES DRIVERS ODBC")
print("-" * 80)

try:
    import pyodbc

    drivers = pyodbc.drivers()

    print("Drivers ODBC disponibles :")

    sql_drivers = []

    for driver in drivers:
        if "SQL Server" in driver:
            sql_drivers.append(driver)
            print(f"  - {driver}")

    if not sql_drivers:
        print("\nERROR: Aucun driver SQL Server trouve")
        sys.exit(1)

except ImportError:
    print("ERROR: pyodbc non installe")
    print("Installation : pip install pyodbc")
    sys.exit(1)

# =============================================================================
# 2. CHARGEMENT .ENV
# =============================================================================

print("\n2. CHARGEMENT .env")
print("-" * 80)

from dotenv import load_dotenv

load_dotenv()

SQLSERVER_SERVER = os.getenv("SQLSERVER_SERVER", "").strip()
SQLSERVER_DATABASE = os.getenv("SQLSERVER_DATABASE", "").strip()

print(f"SQLSERVER_SERVER  : {SQLSERVER_SERVER}")
print(f"SQLSERVER_DATABASE: {SQLSERVER_DATABASE}")
print("AUTHENTIFICATION  : Windows Authentication")

if not SQLSERVER_SERVER or not SQLSERVER_DATABASE:
    print("\nERROR: Variables SQL Server manquantes dans .env")
    sys.exit(1)

# =============================================================================
# 3. TEST CONNEXION
# =============================================================================

print("\n3. TEST DE CONNEXION")
print("-" * 80)

conn = None

try:

    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={SQLSERVER_SERVER};"
        f"DATABASE={SQLSERVER_DATABASE};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

    print("Connection string:")
    print(connection_string)

    conn = pyodbc.connect(connection_string, timeout=5)

    print("\nSUCCESS: Connexion SQL Server reussie !")

    cursor = conn.cursor()

    cursor.execute("SELECT @@SERVERNAME")
    server_name = cursor.fetchone()[0]

    print(f"Serveur connecte : {server_name}")

    # Test table
    cursor.execute("SELECT COUNT(*) FROM dbo.centre_elevage")
    count = cursor.fetchone()[0]

    print(f"Centres trouves : {count}")

    cursor.close()

except pyodbc.InterfaceError as e:

    print(f"\nERROR InterfaceError : {e}")

    print("\nDiagnostic possible :")
    print("  - Probleme d'authentification Windows")
    print("  - SQL Server inaccessible")
    print("  - Mauvais nom de serveur")

    sys.exit(1)

except pyodbc.OperationalError as e:

    print(f"\nERROR OperationalError : {e}")

    print("\nDiagnostic possible :")
    print("  - SQL Server n'est pas lance")
    print("  - Mauvaise instance SQLExpress")
    print("  - Firewall Windows")
    print("  - TCP/IP desactive")

    sys.exit(1)

except Exception as e:

    print(f"\nERROR {type(e).__name__}: {e}")

    sys.exit(1)

# =============================================================================
# 4. TEST CHARGEMENT DONNEES
# =============================================================================

print("\n4. CHARGEMENT DES DONNEES")
print("-" * 80)

try:

    import pandas as pd

    # -------------------------------------------------------------------------
    # ANALYSES
    # -------------------------------------------------------------------------

    query_a = """
    SELECT TOP 5 *
    FROM dbo.demande_analyse
    ORDER BY id_demande DESC
    """

    df_a = pd.read_sql(query_a, conn)

    print(f"Analyses chargees : {len(df_a)} lignes")

    if not df_a.empty:
        print("Colonnes :")
        for col in df_a.columns:
            print(f"  - {col}")

    # -------------------------------------------------------------------------
    # LABOS
    # -------------------------------------------------------------------------

    query_l = """
    SELECT TOP 5 *
    FROM dbo.laboratoire
    WHERE actif = 1
    """

    df_l = pd.read_sql(query_l, conn)

    print(f"\nLabos charges : {len(df_l)} lignes")

    # -------------------------------------------------------------------------
    # SOUCHES
    # -------------------------------------------------------------------------

    query_s = """
    SELECT COUNT(*) AS total
    FROM dbo.souche
    """

    df_s = pd.read_sql(query_s, conn)

    print(f"\nSouches totales : {df_s.iloc[0]['total']}")

except Exception as e:

    print(f"\nERROR chargement donnees : {e}")

    sys.exit(1)

finally:

    if conn:
        conn.close()
        print("\nConnexion fermee")

# =============================================================================
# SUCCESS
# =============================================================================

print("\n" + "=" * 80)
print("SUCCESS: SQL SERVER OK ET DONNEES ACCESSIBLES")
print("=" * 80)

print("\nProchaines etapes :")
print("  1. Copier database_sqlserver.py dans app/data/")
print("  2. Copier config_sqlserver.py dans app/core/")
print("  3. Mettre a jour main.py")
print("  4. Lancer : python main.py")
print("  5. Tester l'endpoint FastAPI")