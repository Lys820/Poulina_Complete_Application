"""
Test complet API Poulina - avec authentification JWT
"""
import requests
import json

BASE = "http://localhost:8000/api/v1"

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
    "email": "admin@poulina.tn",
    "password": "Admin123!"
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
    ok("réponse", True, f"session={d['session_id'][:8]}... model={d['model_used']}")
    ok("answer", len(d['answer']) > 10, d['answer'][:120])
else:
    ok("réponse", False, f"HTTP {r.status_code} - {r.text[:200]}")

section("5. CHAT - Alerte maladie critique")
r = requests.post(f"{BASE}/chat", headers=HEADERS, json={
    "question": "Y a-t-il des cas de Salmonelle critiques non résolus ?"
})
if r.status_code == 200:
    d = r.json()
    ok("réponse", True, d['answer'][:120])
else:
    ok("réponse", False, f"HTTP {r.status_code} - {r.text[:200]}")

section("6. CHAT - Recommandation laboratoire urgent")
r = requests.post(f"{BASE}/chat", headers=HEADERS, json={
    "question": "Quel laboratoire recommandes-tu en urgence à Sfax ?"
})
if r.status_code == 200:
    d = r.json()
    ok("réponse", True, d['answer'][:120])
else:
    ok("réponse", False, f"HTTP {r.status_code} - {r.text[:200]}")

section("7. CHAT - Avec prédiction ML souche")
r = requests.post(f"{BASE}/chat", headers=HEADERS, json={
    "question": "Quelle souche pour ce profil ?",
    "predict_souche": {
        "type_production": "Poulet de chair",
        "biosecurite_score": 8.5,
        "taux_mortalite": 2.0,
        "temperature_moyenne": 28,
        "humidite": 55,
        "fertilite_visee": 92,
        "capacite": 12000,
        "surface_m2": 800,
        "experience_equipe": 7,
        "distance_labo": 10,
        "budget": 75000,
        "saison": "Ete",
        "demande_marche": "Élevé",
        "cout_aliment": 5.2
    }
})
if r.status_code == 200:
    d = r.json()
    pred = d.get("souche_prediction")
    ok("réponse + ML", True, f"souche={pred['souche'] if pred else 'N/A'} conf={pred['confiance_pct'] if pred else 0}%")
    ok("answer", len(d['answer']) > 10, d['answer'][:120])
else:
    ok("réponse", False, f"HTTP {r.status_code} - {r.text[:200]}")

section("8. CHAT - Hors sujet (doit refuser)")
r = requests.post(f"{BASE}/chat", headers=HEADERS, json={
    "question": "Quel est le score du match de foot ?"
})
if r.status_code == 200:
    d = r.json()
    refus = "hors de mon domaine" in d['answer'].lower() or "ne peux pas" in d['answer'].lower()
    ok("refus hors-sujet", refus, d['answer'][:120])
else:
    ok("réponse", False, f"HTTP {r.status_code} - {r.text[:200]}")

# ══════════════════════════════════════════════════════
# 9. Souche predict direct
# ══════════════════════════════════════════════════════
section("9. SOUCHE PREDICT - Direct")
for prod in ["Poulet de chair", "Oeuf", "Dinde"]:
    r = requests.post(f"{BASE}/souches/predict", json={
        "type_production": prod,
        "biosecurite_score": 8.0,
        "taux_mortalite": 2.5,
        "temperature_moyenne": 28,
        "humidite": 55,
        "fertilite_visee": 90,
        "capacite": 10000,
        "surface_m2": 600,
        "experience_equipe": 6,
        "distance_labo": 15,
        "budget": 60000,
        "saison": "Ete",
        "demande_marche": "Élevé",
        "cout_aliment": 5.2
    })
    if r.status_code == 200:
        d = r.json()
        ok(f"{prod:<20}", True, f"{d['souche']:<20} ({d['confiance_pct']}%)  [{d['model']}]")
    else:
        ok(f"{prod:<20}", False, f"HTTP {r.status_code}")

# ══════════════════════════════════════════════════════
# 10. Labos recommend
# ══════════════════════════════════════════════════════
section("10. LABOS RECOMMEND")
for label, params in [
    ("Tous",           {}),
    ("Urgence",        {"urgence": True}),
    ("Tunis urgence",  {"urgence": True, "ville": "Tunis"}),
    ("Sfax",           {"ville": "Sfax"}),
]:
    r = requests.get(f"{BASE}/labos/recommend", params=params)
    if r.status_code == 200:
        d = r.json()
        labos = d.get("labos", [])
        if labos:
            l = labos[0]
            ok(f"{label:<15}", True, f"{l.get('nom_laboratoire','?')} | score={l.get('score_global','?')} | tier={l.get('tier_labo','?')}")
        else:
            ok(f"{label:<15}", False, "0 labos retournés")
    else:
        ok(f"{label:<15}", False, f"HTTP {r.status_code}")

# ══════════════════════════════════════════════════════
# 11. Data endpoints
# ══════════════════════════════════════════════════════
section("11. DATA - Centres / Labos / Souches")
for path, label in [
    ("/data/count",       "Count global"),
    ("/data/centres",     "Centres"),
    ("/data/labos",       "Labos"),
    ("/data/souches",     "Souches"),
]:
    r = requests.get(f"{BASE}{path}")
    ok(label, r.status_code == 200, f"HTTP {r.status_code}")

print(f"\n{'='*70}")
print("  Tests terminés")
print('='*70 + "\n")