"""
check_prerequisites.py
────────────────────────────────────────────────────────────────────────────
Script de diagnostic à lancer AVANT de démarrer le chatbot.
Vérifie les 4 prérequis critiques :
  1. ODBC Driver 17 installé
  2. Connexion à PouleLabDB réussie
  3. Tables ASP.NET Identity présentes
  4. Compte admin accessible et hash compatible
"""

import sys
import os

from dotenv import load_dotenv
load_dotenv()

OK    = "✅"
FAIL  = "❌"
WARN  = "⚠️ "

print("=" * 65)
print("  DIAGNOSTIC CHATBOT — PouleLabDB")
print("=" * 65)

errors = 0

# ──────────────────────────────────────────────────────────────────
# 1. ODBC Driver
# ──────────────────────────────────────────────────────────────────
print("\n[1] ODBC Driver")
try:
    import pyodbc
    drivers = pyodbc.drivers()
    sql_drivers = [d for d in drivers if "SQL Server" in d]

    if not sql_drivers:
        print(f"  {FAIL} Aucun driver SQL Server trouvé.")
        print("       → Télécharge : https://aka.ms/odbc17")
        errors += 1
    else:
        driver_17 = [d for d in sql_drivers if "17" in d]
        if driver_17:
            print(f"  {OK} {driver_17[0]}")
        else:
            print(f"  {WARN} Driver trouvé mais pas la v17 : {sql_drivers}")
            print("       → Installe 'ODBC Driver 17 for SQL Server'")
            errors += 1

except ImportError:
    print(f"  {FAIL} pyodbc non installé → pip install pyodbc")
    errors += 1
    sys.exit(1)

# ──────────────────────────────────────────────────────────────────
# 2. Connexion à PouleLabDB
# ──────────────────────────────────────────────────────────────────
print("\n[2] Connexion SQL Server → PouleLabDB")

server   = os.getenv("SQLSERVER_SERVER", r"localhost\SQLEXPRESS")
database = os.getenv("SQLSERVER_DATABASE", "PouleLabDB")
trusted  = os.getenv("SQLSERVER_TRUSTED", "yes").lower() == "yes"
user     = os.getenv("SQLSERVER_USER", "")
password = os.getenv("SQLSERVER_PASSWORD", "")

print(f"       Server   : {server}")
print(f"       Database : {database}")

if database.upper() != "POULELABDB":
    print(f"  {WARN} SQLSERVER_DATABASE={database} — attendu: PouleLabDB")
    print("       → Corrige ton .env")
    errors += 1

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};DATABASE={database};"
    "TrustServerCertificate=yes;"
)
if trusted or not user:
    conn_str += "Trusted_Connection=yes;"
else:
    conn_str += f"UID={user};PWD={password};"

try:
    conn = pyodbc.connect(conn_str, timeout=5)
    print(f"  {OK} Connexion réussie")
except pyodbc.Error as e:
    print(f"  {FAIL} Connexion échouée : {e}")
    print("       Vérifie : SQL Server démarré ? Base PouleLabDB créée ?")
    errors += 1
    conn = None

# ──────────────────────────────────────────────────────────────────
# 3. Tables ASP.NET Identity
# ──────────────────────────────────────────────────────────────────
print("\n[3] Tables ASP.NET Identity dans PouleLabDB")

REQUIRED_TABLES = ["AspNetUsers", "AspNetRoles", "AspNetUserRoles"]

if conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
    """)
    existing = {row[0] for row in cur.fetchall()}

    for table in REQUIRED_TABLES:
        if table in existing:
            print(f"  {OK} {table}")
        else:
            print(f"  {FAIL} {table} MANQUANTE")
            print(f"       → Lance : dotnet ef database update")
            errors += 1

    # Vérifier aussi l'absence de l'ancienne table POULINA
    if "utilisateur" in existing:
        print(f"  {WARN} Ancienne table 'utilisateur' encore présente (POULINA ?)")
else:
    print(f"  {WARN} Impossible de vérifier sans connexion")

# ──────────────────────────────────────────────────────────────────
# 4. Hash du compte admin
# ──────────────────────────────────────────────────────────────────
print("\n[4] Hash PBKDF2 ASP.NET Identity v3")

if conn:
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT TOP 1 Email, PasswordHash, IsActive
            FROM dbo.AspNetUsers
            WHERE NormalizedEmail = 'ADMIN@POULELABAPP.COM'
        """)
        row = cur.fetchone()

        if row is None:
            print(f"  {FAIL} Compte admin@poulelabapp.com introuvable")
            print("       → Lance le .NET API une fois pour que DataSeeder crée le compte")
            errors += 1
        else:
            email, ph, is_active = row
            print(f"  {OK} Compte trouvé : {email} (actif={is_active})")

            # Vérifier que c'est bien du Base64 ASP.NET v3
            import base64, struct
            try:
                raw = base64.b64decode(ph)
                version = struct.unpack(">B", raw[0:1])[0]
                if version == 1 and len(raw) >= 61:
                    print(f"  {OK} Format PBKDF2-v3 valide (longueur={len(raw)} octets)")
                else:
                    print(f"  {WARN} Format hash inattendu (version={version}, len={len(raw)})")
                    errors += 1
            except Exception as e:
                print(f"  {FAIL} Hash non décodable en Base64 : {e}")
                print("       → security.py incompatible avec ce hash")
                errors += 1

            # Test verify_password avec le mot de passe seedé
            try:
                sys.path.insert(0, ".")
                from app.core.security import verify_password
                if verify_password("Admin@1234", ph):
                    print(f"  {OK} verify_password('Admin@1234') → True ✓")
                else:
                    print(f"  {FAIL} verify_password('Admin@1234') → False")
                    print("       → security.py ne reproduit pas le bon format")
                    errors += 1
            except ImportError:
                print(f"  {WARN} Impossible d'importer security.py pour le test")

    except pyodbc.Error as e:
        print(f"  {FAIL} Erreur SQL : {e}")
        errors += 1

    conn.close()

# ──────────────────────────────────────────────────────────────────
# Résumé
# ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
if errors == 0:
    print(f"  {OK} TOUT EST OK — Tu peux démarrer le chatbot : python main.py")
else:
    print(f"  {FAIL} {errors} problème(s) à corriger avant de démarrer")
print("=" * 65)