#!/usr/bin/env python
"""
TEST CONNEXION SQL SERVER - PouleLabDB
Diagnostic complet : drivers ODBC, variables .env, connexion, tables, donnees.
Usage : python tests/connexion_sqlServer.py
"""

import sys
import os

# =============================================================================
# 1. VERIFICATION DES DRIVERS ODBC
# =============================================================================

SEP  = "=" * 80
SEP2 = "-" * 80

print(f"\n{SEP}")
print("  TEST CONNEXION SQL SERVER — PouleLabDB")
print(SEP)

print("\n[1] DRIVERS ODBC DISPONIBLES")
print(SEP2)

try:
    import pyodbc
except ImportError:
    print("ERREUR : pyodbc non installe.")
    print("  Installer : pip install pyodbc")
    sys.exit(1)

drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]

if not drivers:
    print("ERREUR : Aucun driver SQL Server trouve.")
    print("  Installer : ODBC Driver 17 for SQL Server")
    print("  Telechargement : https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
    sys.exit(1)

for d in drivers:
    print(f"  - {d}")

# Choisir le driver le plus recent disponible
DRIVER = "ODBC Driver 17 for SQL Server"
if DRIVER not in drivers:
    DRIVER = drivers[-1]
    print(f"\nATTENTION : driver prefere absent, utilisation de : {DRIVER}")
else:
    print(f"\nDriver selectionne : {DRIVER}")

# =============================================================================
# 2. CHARGEMENT DES VARIABLES .ENV
# =============================================================================

print(f"\n[2] VARIABLES .ENV")
print(SEP2)

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERREUR : python-dotenv non installe.")
    print("  Installer : pip install python-dotenv")
    sys.exit(1)

load_dotenv()

SERVER   = os.getenv("SQLSERVER_SERVER", "").strip()
DATABASE = os.getenv("SQLSERVER_DATABASE", "").strip()
USER     = os.getenv("SQLSERVER_USER", "").strip()
PASSWORD = os.getenv("SQLSERVER_PASSWORD", "").strip()
TRUSTED  = os.getenv("SQLSERVER_TRUSTED", "yes").strip().lower()

print(f"  SQLSERVER_SERVER   : {SERVER   or '(non defini)'}")
print(f"  SQLSERVER_DATABASE : {DATABASE or '(non defini)'}")
print(f"  SQLSERVER_TRUSTED  : {TRUSTED}")
print(f"  SQLSERVER_USER     : {USER     or '(vide — Windows Auth)'}")

erreurs_env = []
if not SERVER:
    erreurs_env.append("SQLSERVER_SERVER manquant  -> exemple : VICTUSL\\SQLEXPRESS")
if not DATABASE:
    erreurs_env.append("SQLSERVER_DATABASE manquant -> valeur attendue : PouleLabDB")

if erreurs_env:
    print("\nERREUR .env :")
    for e in erreurs_env:
        print(f"  - {e}")
    sys.exit(1)

if DATABASE.upper() != "POULELABDB":
    print(f"\nATTENTION : la base configuree est '{DATABASE}'.")
    print("  La base attendue pour PouleLabApp est 'PouleLabDB'.")
    print("  Verifier SQLSERVER_DATABASE dans .env.")

# =============================================================================
# 3. CONSTRUCTION DE LA CHAINE DE CONNEXION
# =============================================================================

print(f"\n[3] CONNEXION A SQL SERVER")
print(SEP2)

if TRUSTED == "yes" or not USER:
    conn_str = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
    print("  Mode : Windows Authentication (Trusted_Connection)")
else:
    conn_str = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USER};"
        f"PWD={PASSWORD};"
        "TrustServerCertificate=yes;"
    )
    print(f"  Mode : SQL Authentication (user={USER})")

print(f"  Chaine : {conn_str}")

conn = None
try:
    conn = pyodbc.connect(conn_str, timeout=5)
    print("\n  CONNEXION OK")
except pyodbc.InterfaceError as e:
    print(f"\n  ERREUR InterfaceError : {e}")
    print("  Causes probables :")
    print("    - Nom de serveur incorrect (verifier SQLSERVER_SERVER dans .env)")
    print("    - Authentification Windows refusee")
    sys.exit(1)
except pyodbc.OperationalError as e:
    print(f"\n  ERREUR OperationalError : {e}")
    print("  Causes probables :")
    print("    - SQL Server non demarre  -> Get-Service MSSQL* dans PowerShell")
    print("    - Mauvaise instance       -> verifier le nom exact (ex: VICTUSL\\SQLEXPRESS)")
    print("    - TCP/IP desactive        -> SQL Server Configuration Manager > Protocols")
    print("    - Pare-feu bloquant       -> autoriser le port 1433")
    sys.exit(1)
except Exception as e:
    print(f"\n  ERREUR {type(e).__name__} : {e}")
    sys.exit(1)

cursor = conn.cursor()

# Nom du serveur reel
cursor.execute("SELECT @@SERVERNAME, @@VERSION")
row = cursor.fetchone()
print(f"  Serveur    : {row[0]}")
print(f"  SQL Server : {str(row[1]).splitlines()[0]}")

# =============================================================================
# 4. VERIFICATION DES TABLES POULELABDB
# =============================================================================

print(f"\n[4] TABLES DANS {DATABASE}")
print(SEP2)

cursor.execute("""
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_NAME
""")
tables = [r[0] for r in cursor.fetchall()]

if not tables:
    print("  ATTENTION : aucune table trouvee.")
    print("  La base existe mais les migrations EF Core n'ont pas ete appliquees.")
    print("  Executer depuis PouleLabApp.API :")
    print("    dotnet ef database update")
    conn.close()
    sys.exit(1)

print(f"  {len(tables)} tables trouvees :")
for t in tables:
    print(f"    - {t}")

# Tables attendues par PouleLabApp
tables_attendues = [
    "AspNetUsers", "AspNetRoles", "AspNetUserRoles",
    "Laboratories", "AnalysisRequests", "AnalysisResults",
    "Samples", "AnalysisTypes", "AuditLogs", "Notifications", "Deadlines",
]
manquantes = [t for t in tables_attendues if t not in tables]
if manquantes:
    print(f"\n  ATTENTION : {len(manquantes)} table(s) attendue(s) absente(s) :")
    for t in manquantes:
        print(f"    - {t}")
    print("  Executer : dotnet ef database update")
else:
    print("\n  Toutes les tables attendues sont presentes.")

# =============================================================================
# 5. COMPTAGE DES DONNEES
# =============================================================================

print(f"\n[5] DONNEES DANS POULELABDB")
print(SEP2)

comptes = {
    "AspNetUsers"      : "SELECT COUNT(*) FROM AspNetUsers",
    "AspNetRoles"      : "SELECT COUNT(*) FROM AspNetRoles",
    "AspNetUserRoles"  : "SELECT COUNT(*) FROM AspNetUserRoles",
    "Laboratories"     : "SELECT COUNT(*) FROM Laboratories",
    "AnalysisRequests" : "SELECT COUNT(*) FROM AnalysisRequests",
    "AnalysisResults"  : "SELECT COUNT(*) FROM AnalysisResults",
}

for nom_table, query in comptes.items():
    if nom_table not in tables:
        print(f"  {nom_table:<25} : (absente)")
        continue
    try:
        cursor.execute(query)
        count = cursor.fetchone()[0]
        avertissement = ""
        if nom_table == "AspNetUsers" and count == 0:
            avertissement = "  <- ATTENTION : aucun utilisateur, DataSeeder n'a pas tourne ?"
        if nom_table == "AspNetRoles" and count == 0:
            avertissement = "  <- ATTENTION : aucun role, DataSeeder n'a pas tourne ?"
        print(f"  {nom_table:<25} : {count} ligne(s){avertissement}")
    except Exception as e:
        print(f"  {nom_table:<25} : ERREUR ({e})")

# =============================================================================
# 6. VERIFICATION DU COMPTE ADMIN (DataSeeder)
# =============================================================================

print(f"\n[6] COMPTE ADMIN (DataSeeder)")
print(SEP2)

ADMIN_EMAIL = "admin@poulelabapp.com"

if "AspNetUsers" in tables:
    try:
        cursor.execute(
            "SELECT Id, UserName, Email, EmailConfirmed FROM AspNetUsers WHERE Email = ?",
            ADMIN_EMAIL
        )
        admin = cursor.fetchone()
        if admin:
            print(f"  Compte trouve    : {admin[2]}")
            print(f"  Id               : {admin[0]}")
            print(f"  EmailConfirmed   : {admin[3]}")

            # Verifier le role
            cursor.execute("""
                SELECT r.Name
                FROM AspNetUserRoles ur
                JOIN AspNetRoles r ON ur.RoleId = r.Id
                JOIN AspNetUsers u ON ur.UserId = u.Id
                WHERE u.Email = ?
            """, ADMIN_EMAIL)
            roles_admin = [r[0] for r in cursor.fetchall()]
            if roles_admin:
                print(f"  Roles            : {', '.join(roles_admin)}")
            else:
                print("  Roles            : (aucun — DataSeeder incomplet ?)")
        else:
            print(f"  ATTENTION : compte '{ADMIN_EMAIL}' introuvable.")
            print("  Le DataSeeder n'a pas ete execute ou l'API .NET n'a pas demarre.")
            print("  Demarrer l'API .NET une fois : dotnet run (depuis PouleLabApp.API)")
    except Exception as e:
        print(f"  ERREUR lors de la verification admin : {e}")
else:
    print("  Table AspNetUsers absente, verification impossible.")

# =============================================================================
# FERMETURE ET BILAN
# =============================================================================

cursor.close()
conn.close()

print(f"\n{SEP}")
print("  BILAN")
print(SEP)

if manquantes:
    print("  STATUT : CONNEXION OK — migrations incompletes")
    print(f"  Tables manquantes : {', '.join(manquantes)}")
    print("  Action requise    : dotnet ef database update (depuis PouleLabApp.API)")
else:
    print("  STATUT : OK — PouleLabDB accessible et complete")
    print("  Le chatbot peut demarrer : python main.py")

print(SEP + "\n")