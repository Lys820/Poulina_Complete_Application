"""
Diagnostic login — à exécuter depuis le dossier chatbot/
Lance : python tests/diagnostic_login.py

Vérifie chaque étape du processus d'authentification :
  1. Connexion à PouleLabDB
  2. Récupération de l'utilisateur admin@poulelabapp.com
  3. Format du hash stocké en base
  4. Vérification du mot de passe Admin@1234
  5. Appel HTTP direct au endpoint /auth/login
"""
import os
import sys
import base64
import hashlib
import struct

# Ajouter la racine du chatbot au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

ADMIN_EMAIL    = "admin@poulelabapp.com"
ADMIN_PASSWORD = "Admin@1234"
BASE_URL       = "http://localhost:8000/api/v1"

SEP = "-" * 70


def titre(s):
    print(f"\n{SEP}\n  {s}\n{SEP}")


# ===========================================================================
# 1. Connexion directe à PouleLabDB
# ===========================================================================
titre("1. CONNEXION POULELABDB")

try:
    from app.data.database_sqlserver import SqlServerDatabase
    db = SqlServerDatabase()
    ok = db.connect()
    print(f"connect() = {ok}")
    if not ok:
        print("ECHEC : impossible de se connecter à PouleLabDB.")
        print("Vérifiez SQLSERVER_SERVER et SQLSERVER_DATABASE dans .env")
        sys.exit(1)
    print("Connexion OK")
except Exception as e:
    print(f"Import ou connexion échouée : {e}")
    sys.exit(1)


# ===========================================================================
# 2. Récupération de l'utilisateur
# ===========================================================================
titre("2. RECUPERATION UTILISATEUR")

user = db.get_utilisateur_par_email(ADMIN_EMAIL)
if user is None:
    print(f"ECHEC : aucun utilisateur trouvé pour {ADMIN_EMAIL}")
    print("Vérifiez que dotnet run a exécuté le DataSeeder.")
    sys.exit(1)

print(f"id_utilisateur : {user['id_utilisateur']}")
print(f"nom            : {user['prenom']} {user['nom']}")
print(f"actif          : {user['actif']}")
print(f"nom_role       : {user['nom_role']}")
print(f"permissions    : {user['permissions']}")
hash_stored = user["password_hash"]
print(f"password_hash  : {hash_stored[:60]}..." if hash_stored else "password_hash  : NULL")


# ===========================================================================
# 3. Analyse du format du hash
# ===========================================================================
titre("3. FORMAT DU HASH")

if not hash_stored:
    print("ECHEC : PasswordHash est NULL en base.")
    print("Le DataSeeder n'a pas défini de mot de passe pour cet utilisateur.")
    sys.exit(1)

print(f"Longueur       : {len(hash_stored)} caractères")

# Détection format
if len(hash_stored) == 128:
    try:
        int(hash_stored, 16)
        print("Format détecté : Python natif (hex 128 chars)")
        print("                 Ce format est produit par hash_password() du chatbot.")
        print("                 Il N'EST PAS compatible avec UserManager .NET.")
        detected = "python_hex"
    except ValueError:
        print("Format détecté : inconnu (128 chars, non hexadécimal)")
        detected = "unknown"
else:
    # Tenter Base64
    try:
        raw = base64.b64decode(hash_stored)
        version = raw[0] if raw else -1
        print(f"Format détecté : Base64 ({len(raw)} octets décodés)")
        print(f"  Octet version  : 0x{version:02X} (attendu 0x01 pour ASP.NET Identity v3)")
        if len(raw) >= 13 and version == 0x01:
            prf, iterations, salt_len = struct.unpack_from(">III", raw, 1)
            hash_algo = {1: "HMACSHA256", 2: "HMACSHA512"}.get(prf, f"inconnu ({prf})")
            print(f"  PRF            : {prf} ({hash_algo})")
            print(f"  Iterations     : {iterations}")
            print(f"  Salt length    : {salt_len}")
            detected = "aspnet_v3"
        else:
            print("  Format Base64 mais pas ASP.NET Identity v3")
            detected = "base64_unknown"
    except Exception:
        print(f"Format détecté : inconnu (ni hex 128 chars ni Base64 valide)")
        detected = "unknown"


# ===========================================================================
# 4. Vérification du mot de passe
# ===========================================================================
titre("4. VERIFICATION MOT DE PASSE")

try:
    from app.core.security import verify_password, hash_password
    print(f"verify_password importé depuis app.core.security")
except Exception as e:
    print(f"ECHEC import security : {e}")
    sys.exit(1)

result = verify_password(ADMIN_PASSWORD, hash_stored)
print(f"verify_password('{ADMIN_PASSWORD}', hash_stored) = {result}")

if not result:
    print("\nDIAGNOSTIC ECHEC :")
    if detected == "python_hex":
        print("  Le hash en base est au format Python hex (produit par hash_password()).")
        print("  UserManager .NET n'a PAS été utilisé pour créer ce compte.")
        print("  Soit le DataSeeder n'a pas fonctionné, soit le hash a été écrasé.")
        print("  Solution : relancer dotnet run pour recréer le compte via DataSeeder.")
    elif detected == "aspnet_v3":
        print("  Le hash est au format ASP.NET Identity v3 mais verify_password retourne False.")
        print("  Causes possibles :")
        print("    a) Le mot de passe Admin@1234 ne correspond pas au hash stocké.")
        print("       Vérifiez DataSeeder.cs — le mot de passe seeder est-il bien Admin@1234 ?")
        print("    b) security.py n'a pas été correctement remplacé.")
        print("       Vérifiez que la version avec _verify_aspnet_v3 est bien en place.")
        # Test manuel PBKDF2
        print("\n  Test manuel PBKDF2 (pour vérifier le code) :")
        try:
            raw_b = base64.b64decode(hash_stored)
            prf, iterations, salt_len = struct.unpack_from(">III", raw_b, 1)
            salt   = raw_b[13 : 13 + salt_len]
            subkey = raw_b[13 + salt_len :]
            algo   = "sha512" if prf == 2 else "sha256"
            candidate = hashlib.pbkdf2_hmac(
                algo, ADMIN_PASSWORD.encode("utf-8"), salt, iterations, len(subkey)
            )
            match = candidate == subkey
            print(f"    PBKDF2-{algo.upper()} avec {iterations} itérations : {'MATCH' if match else 'NO MATCH'}")
            if not match:
                print("    Le mot de passe Admin@1234 ne correspond PAS au hash en base.")
                print("    Le compte a peut-être été créé avec un autre mot de passe.")
        except Exception as ex:
            print(f"    Erreur test manuel : {ex}")
    else:
        print(f"  Format hash inconnu ({detected}).")
else:
    print("Vérification OK — le mot de passe correspond au hash.")


# ===========================================================================
# 5. Appel HTTP au endpoint /auth/login
# ===========================================================================
titre("5. APPEL HTTP /auth/login")

try:
    import requests
    r = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    print(f"HTTP {r.status_code}")
    print(f"Réponse : {r.text[:300]}")
    if r.status_code == 200:
        data = r.json()
        print(f"\nLogin OK !")
        print(f"  role        : {data.get('role')}")
        print(f"  permissions : {data.get('permissions')}")
        print(f"  token       : {data.get('access_token', '')[:40]}...")
    else:
        print("\nLogin échoué côté serveur.")
        print("Vérifiez les logs uvicorn dans le terminal du chatbot.")
except Exception as e:
    print(f"Erreur HTTP : {e}")
    print("Le chatbot Python est-il démarré ? (python main.py)")

print(f"\n{SEP}")
print("  Diagnostic terminé")
print(SEP)