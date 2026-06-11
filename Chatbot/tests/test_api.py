"""
Test complet API Poulina - avec authentification JWT
Credentials mis à jour : admin@poulelabapp.com / Admin@1234 (DataSeeder.cs)
"""
import requests
import json

BASE = "http://localhost:8000/api/v1"

# ✅ Credentials du compte seedé par DataSeeder.cs
ADMIN_EMAIL    = "admin@poulelabapp.com"
ADMIN_PASSWORD = "Admin@1234"

# ══════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════
def ok(label, cond, detail=""):
    icon = "[OK]" if cond else "[ERREUR]"
    print(f"  {icon} {label}" + (f" - {detail}" if detail else ""))

def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)

# ══════════════════════════════════════════════════════
# 1. Health
# ══════════════════════════════════════════════════════
section("1. HEALTH CHECK")
r = requests.get(f"{BASE}/health")
d = r.json()
ok("statut", d.get("status") == "ok", f"fournisseur={d.get('llm_provider')} embedding={d.get('embedding')}")

# ══════════════════════════════════════════════════════
# 2. Train depuis SQL Server
# ══════════════════════════════════════════════════════
section("2. ENTRAINER DEPUIS SQL SERVER")
r = requests.post(f"{BASE}/analyses/train-from-sqlserver")
d = r.json()
ok("status", d.get("status") == "trained_from_sqlserver")
ok("analyses", True, f"{d.get('analyses', {}).get('docs')} docs [{d.get('analyses', {}).get('embedder')}]")
ok("modele souche", True, f"{d.get('model_status', {}).get('souche', {}).get('model')} acc={d.get('model_status', {}).get('souche', {}).get('accuracy', 0):.3f}")

# ══════════════════════════════════════════════════════
# 3. LOGIN
# ══════════════════════════════════════════════════════
section("3. LOGIN")
r = requests.post(f"{BASE}/auth/login", json={
    "email":    ADMIN_EMAIL,
    "password": ADMIN_PASSWORD,
})
if r.status_code == 200:
    login_data = r.json()
    TOKEN = login_data["access_token"]
    ok("login", True, f"role={login_data['role']} permissions={login_data['permissions']}")
    HEADERS = {"Authorization": f"Bearer {TOKEN}"}
else:
    ok("login", False, f"HTTP {r.status_code} - {r.text}")
    print("  [ARRET] Impossible de continuer sans token")
    exit(1)

# ══════════════════════════════════════════════════════
# 4. CHAT - Tests
# ══════════════════════════════════════════════════════
section("4. CHAT - Souche par ville")
r = requests.post(f"{BASE}/chat", headers=HEADERS, json={
    "question": "Quelle est la meilleure souche à Tunis ?"
})
if r.status_code == 200:
    d = r.json()
    ok("reponse", True, f"model={d.get('model_used')}")
    ok("answer", len(d.get('answer', '')) > 10, d.get('answer', '')[:120])
else:
    ok("reponse", False, f"HTTP {r.status_code} - {r.text[:200]}")

section("5. CHAT - Alerte maladie critique")
r = requests.post(f"{BASE}/chat", headers=HEADERS, json={
    "question": "Y a-t-il des cas de Salmonelle critiques non resolus ?"
})
if r.status_code == 200:
    d = r.json()
    ok("reponse", True, d.get('answer', '')[:120])
else:
    ok("reponse", False, f"HTTP {r.status_code} - {r.text[:200]}")

section("6. CHAT - Recommandation labo")
r = requests.post(f"{BASE}/chat", headers=HEADERS, json={
    "question": "Quel laboratoire recommandes-tu a Sfax ?"
})
if r.status_code == 200:
    d = r.json()
    ok("reponse", True, d.get('answer', '')[:120])
else:
    ok("reponse", False, f"HTTP {r.status_code} - {r.text[:200]}")