"""
sync_jwt_secret.py
────────────────────────────────────────────────────────────────────────────
Lit le JWT:Secret depuis les User Secrets .NET et le synchronise dans le .env
du chatbot Python, pour garantir que les deux services utilisent la même clé.

Usage :
  cd Chatbot
  python tests/sync_jwt_secret.py

Prérequis :
  - dotnet CLI installé
  - Être dans un shell où les User Secrets du projet .NET sont accessibles
  - Le projet .NET doit se trouver dans ../AnalyseApp/PouleLabApp.API
    (relatif au dossier Chatbot). Adapte API_PROJECT_PATH si besoin.
"""

import subprocess
import os
import re
import sys

# ── Chemins ───────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CHATBOT_ROOT = os.path.dirname(SCRIPT_DIR)            # …/Chatbot/
API_PROJECT  = os.path.join(
    CHATBOT_ROOT, "..", "AnalyseApp", "PouleLabApp.API"
)
ENV_FILE     = os.path.join(CHATBOT_ROOT, ".env")

print("=" * 60)
print("  Synchronisation JWT Secret .NET → Python")
print("=" * 60)

# ── 1. Lire les User Secrets .NET ─────────────────────────────────────────────
api_path = os.path.normpath(API_PROJECT)
print(f"\n[1] Lecture des User Secrets .NET")
print(f"    Projet : {api_path}")

try:
    result = subprocess.run(
        ["dotnet", "user-secrets", "list"],
        cwd=api_path,
        capture_output=True,
        text=True,
        timeout=15,
    )
except FileNotFoundError:
    print("  ❌ dotnet CLI introuvable. Installe le SDK .NET.")
    sys.exit(1)
except subprocess.TimeoutExpired:
    print("  ❌ Timeout — dotnet user-secrets list trop long.")
    sys.exit(1)

if result.returncode != 0:
    print(f"  ❌ Erreur : {result.stderr.strip()}")
    print("     → As-tu lancé 'dotnet user-secrets set Jwt:Secret ...' ?")
    sys.exit(1)

output = result.stdout
print(f"    Secrets trouvés :\n{output}")

# ── 2. Extraire Jwt:Secret ────────────────────────────────────────────────────
print(f"[2] Extraction de Jwt:Secret")

match = re.search(r"Jwt:Secret\s*=\s*(.+)", output)
if not match:
    print("  ❌ Jwt:Secret introuvable dans les User Secrets.")
    print("     → Lance d'abord :")
    print("       cd AnalyseApp/PouleLabApp.API")
    print('       dotnet user-secrets set "Jwt:Secret" "ta_cle_secrete"')
    sys.exit(1)

jwt_secret = match.group(1).strip()
# Masquer pour l'affichage
masked = jwt_secret[:4] + "*" * max(0, len(jwt_secret) - 8) + jwt_secret[-4:]
print(f"    Jwt:Secret trouvé : {masked}")

# ── 3. Mettre à jour le .env Python ───────────────────────────────────────────
print(f"\n[3] Mise à jour de {ENV_FILE}")

if not os.path.exists(ENV_FILE):
    print(f"  ❌ .env introuvable : {ENV_FILE}")
    sys.exit(1)

with open(ENV_FILE, "r", encoding="utf-8") as f:
    content = f.read()

# Remplacer la ligne JWT_SECRET_KEY existante
new_line = f"JWT_SECRET_KEY={jwt_secret}"

if re.search(r"^JWT_SECRET_KEY=.*", content, re.MULTILINE):
    content = re.sub(r"^JWT_SECRET_KEY=.*", new_line, content, flags=re.MULTILINE)
    action = "remplacé"
else:
    content += f"\n{new_line}\n"
    action = "ajouté"

with open(ENV_FILE, "w", encoding="utf-8") as f:
    f.write(content)

print(f"  ✅ JWT_SECRET_KEY {action} dans .env")

# ── 4. Vérification finale ────────────────────────────────────────────────────
print(f"\n[4] Vérification")
with open(ENV_FILE, "r", encoding="utf-8") as f:
    lines = [l for l in f.readlines() if l.startswith("JWT_SECRET_KEY")]

if lines:
    val = lines[0].split("=", 1)[1].strip()
    if val == jwt_secret:
        print(f"  ✅ .env synchronisé correctement")
    else:
        print(f"  ❌ Valeur dans .env ne correspond pas")
        sys.exit(1)

print("\n" + "=" * 60)
print("  ✅ JWT synchronisé — .NET et Python utilisent la même clé")
print("=" * 60)
print("\nProchaine étape :")
print("  python tests/check_prerequisites.py")