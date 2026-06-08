"""
Script d'initialisation complet :
1. Crée les tables auth (role, permission, utilisateur, session_chat, message_chat)
2. Insère les données de référence (rôles, permissions)
3. Crée les utilisateurs avec vrais hash PBKDF2
"""
import hashlib
import os
import pyodbc

# ══════════════════════════════════════════════════════
# CONFIG — adapter selon ton .env
# ══════════════════════════════════════════════════════
SERVER   = r"localhost\SQLEXPRESS"
DATABASE = "POULINA"
DRIVER   = "ODBC Driver 17 for SQL Server"
AUTH_MODE    = "windows"       # "sql" ou "windows"
SQL_USER     = "sa"
SQL_PASSWORD = "VotreMotDePasse"

# Utilisateurs à créer
USERS = [
    ("Administrateur", "Poulina",  "admin@poulina.tn",       "Admin123!",        "ADMIN"),
    ("Ben Salem",      "Karim",    "k.bensalem@poulina.tn",  "Gestionnaire123!", "GESTIONNAIRE"),
    ("Labidi",         "Sonia",    "s.labidi@poulina.tn",    "Laborantin123!",   "LABORANTIN"),
    ("Trabelsi",       "Mohamed",  "m.trabelsi@poulina.tn",  "Viewer123!",       "VIEWER"),
]

# ══════════════════════════════════════════════════════
def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return (salt + key).hex()

def get_connection():
    if AUTH_MODE == "windows":
        cs = f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;TrustServerCertificate=yes;"
    else:
        cs = f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};UID={SQL_USER};PWD={SQL_PASSWORD};TrustServerCertificate=yes;"
    return pyodbc.connect(cs, autocommit=False)

# ══════════════════════════════════════════════════════
# Vérifier si la table filiale existe (FK optionnelle)
# ══════════════════════════════════════════════════════
def filiale_exists(cursor):
    cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='filiale'")
    return cursor.fetchone()[0] > 0

# ══════════════════════════════════════════════════════
# Étape 1 : Créer les tables
# ══════════════════════════════════════════════════════
def create_tables(cursor, has_filiale):
    print("\n--- Étape 1 : Création des tables ---")

    # Drop dans l'ordre inverse des FK
    for tbl in ["dbo.message_chat", "dbo.session_chat", "dbo.role_permission",
                "dbo.utilisateur", "dbo.permission", "dbo.role"]:
        cursor.execute(f"IF OBJECT_ID('{tbl}','U') IS NOT NULL DROP TABLE {tbl}")
    print("  [OK] Tables existantes supprimées")

    cursor.execute("""
        CREATE TABLE dbo.role (
            id_role     INT IDENTITY(1,1) PRIMARY KEY,
            nom_role    NVARCHAR(50)  UNIQUE NOT NULL,
            description NVARCHAR(200)
        )
    """)

    cursor.execute("""
        CREATE TABLE dbo.permission (
            id_permission INT IDENTITY(1,1) PRIMARY KEY,
            code          NVARCHAR(100) UNIQUE NOT NULL,
            description   NVARCHAR(200)
        )
    """)

    cursor.execute("""
        CREATE TABLE dbo.role_permission (
            id_role       INT NOT NULL,
            id_permission INT NOT NULL,
            PRIMARY KEY (id_role, id_permission),
            CONSTRAINT fk_rp_role FOREIGN KEY (id_role)       REFERENCES dbo.role(id_role),
            CONSTRAINT fk_rp_perm FOREIGN KEY (id_permission) REFERENCES dbo.permission(id_permission)
        )
    """)

    # Utilisateur : FK filiale optionnelle selon si la table existe
    if has_filiale:
        fk_filiale = "CONSTRAINT fk_user_filiale FOREIGN KEY (id_filiale) REFERENCES dbo.filiale(id_filiale),"
    else:
        fk_filiale = ""

    cursor.execute(f"""
        CREATE TABLE dbo.utilisateur (
            id_utilisateur INT IDENTITY(1,1) PRIMARY KEY,
            nom            NVARCHAR(100) NOT NULL,
            prenom         NVARCHAR(100) NOT NULL,
            email          NVARCHAR(150) UNIQUE NOT NULL,
            password_hash  NVARCHAR(500) NOT NULL,
            id_role        INT NOT NULL,
            id_filiale     INT,
            actif          BIT DEFAULT 1,
            date_creation  DATETIME2 DEFAULT GETDATE(),
            {fk_filiale}
            CONSTRAINT fk_user_role FOREIGN KEY (id_role) REFERENCES dbo.role(id_role)
        )
    """)

    cursor.execute("""
        CREATE TABLE dbo.session_chat (
            id_session             NVARCHAR(64) PRIMARY KEY,
            id_utilisateur         INT NOT NULL,
            date_debut             DATETIME2 DEFAULT GETDATE(),
            date_derniere_activite DATETIME2 DEFAULT GETDATE(),
            actif                  BIT DEFAULT 1,
            contexte_json          NVARCHAR(MAX) DEFAULT '{}',
            CONSTRAINT fk_session_user FOREIGN KEY (id_utilisateur)
                REFERENCES dbo.utilisateur(id_utilisateur)
        )
    """)

    cursor.execute("""
        CREATE TABLE dbo.message_chat (
            id_message   INT IDENTITY(1,1) PRIMARY KEY,
            id_session   NVARCHAR(64) NOT NULL,
            role         NVARCHAR(20) NOT NULL CHECK (role IN ('user','assistant')),
            contenu      NVARCHAR(MAX) NOT NULL,
            date_message DATETIME2 DEFAULT GETDATE(),
            CONSTRAINT fk_msg_session FOREIGN KEY (id_session)
                REFERENCES dbo.session_chat(id_session)
        )
    """)

    # Index
    cursor.execute("CREATE INDEX idx_session_user    ON dbo.session_chat(id_utilisateur)")
    cursor.execute("CREATE INDEX idx_session_actif   ON dbo.session_chat(actif)")
    cursor.execute("CREATE INDEX idx_message_session ON dbo.message_chat(id_session, date_message)")
    cursor.execute("CREATE INDEX idx_user_email      ON dbo.utilisateur(email)")

    print("  [OK] Tables créées (role, permission, role_permission, utilisateur, session_chat, message_chat)")

# ══════════════════════════════════════════════════════
# Étape 2 : Données de référence
# ══════════════════════════════════════════════════════
def insert_referential(cursor):
    print("\n--- Étape 2 : Données de référence ---")

    roles = [
        ("ADMIN",        "Administrateur : accès complet"),
        ("GESTIONNAIRE", "Gestionnaire analyses et élevages"),
        ("LABORANTIN",   "Personnel laboratoire"),
        ("VIEWER",       "Consultation uniquement"),
    ]
    for nom, desc in roles:
        cursor.execute("INSERT INTO dbo.role (nom_role, description) VALUES (?, ?)", (nom, desc))
    print(f"  [OK] {len(roles)} rôles insérés")

    permissions = [
        ("CHAT_READ",      "Poser des questions au chatbot"),
        ("CHAT_ML",        "Déclencher des prédictions ML"),
        ("ANALYSE_CREATE", "Créer une demande d'analyse"),
        ("ANALYSE_READ",   "Consulter les analyses"),
        ("LABO_READ",      "Consulter les laboratoires"),
        ("SOUCHE_READ",    "Consulter les souches"),
        ("ADMIN_TRAIN",    "Ré-entraîner les modèles"),
        ("ADMIN_USERS",    "Gérer les utilisateurs"),
    ]
    for code, desc in permissions:
        cursor.execute("INSERT INTO dbo.permission (code, description) VALUES (?, ?)", (code, desc))
    print(f"  [OK] {len(permissions)} permissions insérées")

    # Permissions par rôle
    role_perms = {
        "ADMIN":        ["CHAT_READ","CHAT_ML","ANALYSE_CREATE","ANALYSE_READ",
                         "LABO_READ","SOUCHE_READ","ADMIN_TRAIN","ADMIN_USERS"],
        "GESTIONNAIRE": ["CHAT_READ","CHAT_ML","ANALYSE_CREATE","ANALYSE_READ",
                         "LABO_READ","SOUCHE_READ"],
        "LABORANTIN":   ["CHAT_READ","ANALYSE_CREATE","ANALYSE_READ",
                         "LABO_READ","SOUCHE_READ"],
        "VIEWER":       ["CHAT_READ","ANALYSE_READ","LABO_READ","SOUCHE_READ"],
    }
    for role_name, perms in role_perms.items():
        for perm_code in perms:
            cursor.execute("""
                INSERT INTO dbo.role_permission (id_role, id_permission)
                SELECT r.id_role, p.id_permission
                FROM dbo.role r, dbo.permission p
                WHERE r.nom_role = ? AND p.code = ?
            """, (role_name, perm_code))
    print("  [OK] Permissions assignées aux rôles")

# ══════════════════════════════════════════════════════
# Étape 3 : Utilisateurs
# ══════════════════════════════════════════════════════
def create_users(cursor, has_filiale):
    print("\n--- Étape 3 : Création des utilisateurs ---")

    # Récupérer id_filiale si la table existe
    id_filiale = None
    if has_filiale:
        cursor.execute("SELECT TOP 1 id_filiale FROM dbo.filiale")
        row = cursor.fetchone()
        id_filiale = row[0] if row else None

    for nom, prenom, email, password, role_name in USERS:
        cursor.execute("SELECT id_role FROM dbo.role WHERE nom_role = ?", (role_name,))
        id_role = cursor.fetchone()[0]
        h = hash_password(password)

        if id_filiale:
            cursor.execute("""
                INSERT INTO dbo.utilisateur (nom, prenom, email, password_hash, id_role, id_filiale, actif)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (nom, prenom, email, h, id_role, id_filiale))
        else:
            cursor.execute("""
                INSERT INTO dbo.utilisateur (nom, prenom, email, password_hash, id_role, actif)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (nom, prenom, email, h, id_role))

        print(f"  [OK] {email:<35} role={role_name}")

# ══════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════
def main():
    print("Initialisation base Poulina (auth + mémoire)...")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        has_filiale = filiale_exists(cursor)
        if not has_filiale:
            print("  [INFO] Table 'filiale' absente — FK ignorée")

        create_tables(cursor, has_filiale)
        insert_referential(cursor)
        create_users(cursor, has_filiale)

        conn.commit()
        print("\n  [SUCCÈS] Base initialisée.")

        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║  CREDENTIALS DE CONNEXION                                   ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        for _, _, email, pwd, role in USERS:
            print(f"║  {role:<15} {email:<30} {pwd}") 
        print("╚══════════════════════════════════════════════════════════════╝")

    except Exception as e:
        conn.rollback()
        print(f"\n  [ERREUR] {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()