"""
Diagnostic ciblé — simule exactement l'appel fait par auth.py côté serveur.
Lance : python tests/diagnostic_auth_server.py

Utilise get_settings() et get_db(settings) comme le fait le vrai endpoint,
pour révéler si le serveur se connecte à un serveur SQL différent ou
obtient un hash différent.
"""
import os
import sys
import base64
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

ADMIN_EMAIL    = "admin@poulelabapp.com"
ADMIN_PASSWORD = "Admin@1234"
SEP = "-" * 70

def titre(s):
    print(f"\n{SEP}\n  {s}\n{SEP}")

# ===========================================================================
# Reproduire exactement ce que fait auth.py
# ===========================================================================
titre("SETTINGS CHARGES PAR LE SERVEUR")

try:
    from app.core.config import get_settings
    settings = get_settings()
    print(f"SQLSERVER_SERVER   : {getattr(settings, 'SQLSERVER_SERVER', 'NON DEFINI')}")
    print(f"SQLSERVER_DATABASE : {getattr(settings, 'SQLSERVER_DATABASE', 'NON DEFINI')}")
    print(f"SQLSERVER_DRIVER   : {getattr(settings, 'SQLSERVER_DRIVER', 'NON DEFINI')}")
    print(f"JWT_SECRET_KEY     : {str(getattr(settings, 'JWT_SECRET_KEY', ''))[:20]}...")
except Exception as e:
    print(f"Erreur import settings : {e}")
    sys.exit(1)

titre("CONNEXION VIA get_db(settings) — comme auth.py")

try:
    from app.data.database_sqlserver import get_db
    db = get_db(settings)
    ok = db.connect()
    print(f"Serveur cible : {db._server}")
    print(f"Base cible    : {db._database}")
    print(f"connect()     : {ok}")
    if not ok:
        print("ECHEC connexion via get_db(settings)")
        sys.exit(1)
except Exception as e:
    print(f"Erreur get_db : {e}")
    sys.exit(1)

titre("HASH RECUPERE VIA get_db(settings)")

user = db.get_utilisateur_par_email(ADMIN_EMAIL)
if user is None:
    print(f"Aucun utilisateur trouvé pour {ADMIN_EMAIL} via get_db(settings)")
    sys.exit(1)

hash_stored = user["password_hash"]
print(f"id_utilisateur : {user['id_utilisateur']}")
print(f"actif          : {user['actif']}")
print(f"nom_role       : {user['nom_role']}")
print(f"hash (60 chars): {hash_stored[:60] if hash_stored else 'NULL'}...")
print(f"hash longueur  : {len(hash_stored) if hash_stored else 0}")

if hash_stored:
    try:
        raw = base64.b64decode(hash_stored)
        prf, iterations, salt_len = struct.unpack_from(">III", raw, 1)
        algo = {1: "HMACSHA256", 2: "HMACSHA512"}.get(prf, f"inconnu({prf})")
        print(f"Format         : ASP.NET Identity v3 — {algo}, {iterations} iterations")
    except Exception:
        print(f"Format         : non-Base64 (longueur {len(hash_stored)})")

titre("VERIFY_PASSWORD VIA LE MODULE DU SERVEUR")

try:
    from app.core.security import verify_password
    import inspect
    src_file = inspect.getfile(verify_password)
    print(f"security.py chargé depuis : {src_file}")
    result = verify_password(ADMIN_PASSWORD, hash_stored)
    print(f"verify_password('{ADMIN_PASSWORD}', hash) = {result}")
    if result:
        print("OK — le serveur devrait accepter ce login.")
    else:
        print("ECHEC — même module, même hash, verify_password retourne False.")
        print("Cause probable : le hash en base ne correspond pas à Admin@1234.")
except Exception as e:
    print(f"Erreur : {e}")

print(f"\n{SEP}\n  Fin diagnostic\n{SEP}")