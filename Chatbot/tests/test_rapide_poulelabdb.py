#!/usr/bin/env python
"""
TEST RAPIDE POULELABDB — Vérification manuelle complète du chatbot
Base de données : PouleLabDB (localhost\\SQLEXPRESS)
Tous les comptes : Admin@1234

Commande :
    cd Chatbot
    python tests/test_rapide_poulelabdb.py
"""
import asyncio
import sys
import httpx

BASE    = "http://localhost:8000/api/v1"
TIMEOUT = 90

# ---------------------------------------------------------------------------
# Comptes de test (DataSeeder.cs — mot de passe universel Admin@1234)
# ---------------------------------------------------------------------------
PASSWORD = "Admin@1234"

ADMIN_EMAIL = "admin@poulelabapp.com"

USERS = {
    "Administrator": [
        {"email": "admin@poulelabapp.com",         "permissions": ["CHAT_READ", "CHAT_ML", "ADMIN_TRAIN", "DATA_READ"]},
    ],
    "Manager": [
        {"email": "manager1@poulelabapp.com",       "permissions": ["CHAT_READ", "CHAT_ML", "DATA_READ"]},
        {"email": "manager2@poulelabapp.com",       "permissions": ["CHAT_READ", "CHAT_ML", "DATA_READ"]},
    ],
    "Analyst": [
        {"email": "analyst@poulelabapp.com",        "permissions": ["CHAT_READ", "CHAT_ML", "DATA_READ"]},
        {"email": "analyst2@poulelabapp.com",       "permissions": ["CHAT_READ", "CHAT_ML", "DATA_READ"]},
    ],
    "LabChief": [
        {"email": "labchief1@poulelabapp.com",      "permissions": ["CHAT_READ", "DATA_READ"]},
        {"email": "labchief2@poulelabapp.com",      "permissions": ["CHAT_READ", "DATA_READ"]},
    ],
    "Receptionist": [
        {"email": "receptionist1@poulelabapp.com",  "permissions": ["CHAT_READ", "DATA_READ"]},
        {"email": "receptionist2@poulelabapp.com",  "permissions": ["CHAT_READ", "DATA_READ"]},
    ],
    "Client": [
        {"email": "client1@poulelabapp.com",        "permissions": ["CHAT_READ"]},
        {"email": "client2@poulelabapp.com",        "permissions": ["CHAT_READ"]},
        {"email": "client3@poulelabapp.com",        "permissions": ["CHAT_READ"]},
        {"email": "client4@poulelabapp.com",        "permissions": ["CHAT_READ"]},
    ],
}

SOUCHE_PAYLOAD = {
    "type_production":   "Poulet de chair",
    "biosecurite_score": 8.0,
    "taux_mortalite":    2.5,
    "temperature_moyenne": 28,
    "humidite":          55,
    "fertilite_visee":   90,
    "capacite":          10000,
    "surface_m2":        600,
    "experience_equipe": 6,
    "distance_labo":     15,
    "budget":            60000,
    "saison":            "Ete",
    "demande_marche":    "Eleve",
    "cout_aliment":      5.2,
}

# ---------------------------------------------------------------------------
# Affichage
# ---------------------------------------------------------------------------

def titre(t):    print(f"\n{'=' * 70}\n  {t}\n{'=' * 70}")
def ok(m):       print(f"  [OK]    {m}")
def echec(m):    print(f"  [ECHEC] {m}")
def info(m):     print(f"          {m}")
def tronq(v, n=120): s = str(v); return s[:n] + "..." if len(s) > n else s


# ---------------------------------------------------------------------------
# 1. Health
# ---------------------------------------------------------------------------
async def test_health(client):
    titre("1. HEALTH CHECK")
    r = await client.get(f"{BASE}/health")
    if r.status_code == 200:
        d = r.json()
        ok(f"status={d['status']}  llm_provider={d.get('llm_provider')}  embedding={d.get('embedding')}")
        return True
    echec(f"HTTP {r.status_code}")
    return False


# ---------------------------------------------------------------------------
# 2. Entraînement
# ---------------------------------------------------------------------------
async def test_entrainement(client):
    titre("2. ENTRAINEMENT DEPUIS POULELABDB")
    info("(peut prendre 10-30 secondes...)")
    try:
        r = await client.post(f"{BASE}/analyses/train-from-sqlserver", timeout=90)
        if r.status_code == 200:
            d = r.json()
            ok(f"statut={d['status']}")
            ok(f"analyses : {d['analyses']['docs']} docs  [{d['analyses']['embedder']}]")
            ok(f"labos    : {d['labos']['docs']} docs")
            souche = d.get("model_status", {}).get("souche", {})
            ok(f"modele souche : {souche.get('model')}  acc={souche.get('accuracy', 0):.3f}")
            ok(f"entraine a    : {d.get('trained_at')}")
            return True
        echec(f"HTTP {r.status_code} — {tronq(r.text)}")
        return False
    except Exception as e:
        echec(f"Exception : {e}")
        return False


# ---------------------------------------------------------------------------
# 3. Status
# ---------------------------------------------------------------------------
async def test_status(client):
    titre("3. STATUT DETAILLE")
    r = await client.get(f"{BASE}/status")
    if r.status_code == 200:
        d = r.json()
        ok(f"rag_ready={d['rag_ready']}  ml_ready={d['ml_ready']}")
        souche = d["ml_models"]["souche"]
        labo   = d["ml_models"]["labo"]
        ok(f"modele souche : {souche['model']}  acc={souche.get('accuracy', 0):.3f}")
        ok(f"modele labo   : {labo['model']}  acc={labo.get('accuracy', 0):.3f}")
    else:
        echec(f"HTTP {r.status_code}")


# ---------------------------------------------------------------------------
# 4. Authentification — tous les utilisateurs
# ---------------------------------------------------------------------------
async def test_auth_tous_les_users(client):
    titre("4. AUTHENTIFICATION — TOUS LES COMPTES (mot de passe : Admin@1234)")
    erreurs = []
    for role, users in USERS.items():
        for u in users:
            r = await client.post(f"{BASE}/auth/login",
                json={"email": u["email"], "password": PASSWORD})
            if r.status_code == 200:
                d = r.json()
                perms = d.get("permissions", [])
                manquantes = [p for p in u["permissions"] if p not in perms]
                if manquantes:
                    echec(f"{u['email']:<40} role={d['role']:<14} permissions manquantes : {manquantes}")
                    erreurs.append(u["email"])
                else:
                    ok(f"{u['email']:<40} role={d['role']:<14} permissions OK")
            else:
                echec(f"{u['email']:<40} HTTP {r.status_code} — {tronq(r.text, 80)}")
                erreurs.append(u["email"])
    if erreurs:
        info(f"{len(erreurs)} compte(s) en erreur. Relancez dotnet run pour recréer les comptes.")
    return erreurs


async def test_auth_mauvais_mdp(client):
    titre("4b. MAUVAIS MOT DE PASSE (doit retourner 401)")
    r = await client.post(f"{BASE}/auth/login",
        json={"email": ADMIN_EMAIL, "password": "Mauvais!"})
    if r.status_code == 401:
        ok("401 recu comme attendu")
    else:
        echec(f"Attendu 401, recu {r.status_code}")


async def test_login_admin(client):
    titre("4c. LOGIN ADMIN (compte principal)")
    r = await client.post(f"{BASE}/auth/login",
        json={"email": ADMIN_EMAIL, "password": PASSWORD})
    if r.status_code == 200:
        d = r.json()
        ok(f"role={d['role']}  permissions={d['permissions']}")
        ok(f"token : {d['access_token'][:40]}...")
        return d["access_token"]
    echec(f"HTTP {r.status_code} — {tronq(r.text)}")
    return None


# ---------------------------------------------------------------------------
# 5. Chat
# ---------------------------------------------------------------------------
async def test_chat_question_simple(client, headers):
    titre("5. CHAT — Question domaine avicole")
    r = await client.post(f"{BASE}/chat", headers=headers, json={
        "question": "Quelle est la meilleure souche pour un élevage de poulet de chair en Tunisie ?",
    })
    if r.status_code == 200:
        d = r.json()
        ok(f"session={d['session_id'][:12]}...  modele={d['model_used']}")
        info(f"Réponse : {tronq(d['answer'])}")
    else:
        echec(f"HTTP {r.status_code} — {tronq(r.text)}")


async def test_chat_avec_contexte_ml(client, headers):
    titre("6. CHAT — Avec contexte ML (predict_souche)")
    r = await client.post(f"{BASE}/chat", headers=headers, json={
        "question": "Quelle souche recommandez-vous pour mon élevage ?",
        "predict_souche": SOUCHE_PAYLOAD,
    })
    if r.status_code == 200:
        d = r.json()
        ok(f"session={d['session_id'][:12]}...")
        info(f"Réponse : {tronq(d['answer'])}")
    else:
        echec(f"HTTP {r.status_code} — {tronq(r.text)}")


async def test_chat_maladie(client, headers):
    titre("7. CHAT — Alerte maladie avicole")
    r = await client.post(f"{BASE}/chat", headers=headers, json={
        "question": "Y a-t-il des cas de Salmonelle ou de Newcastle signalés récemment ?",
    })
    if r.status_code == 200:
        info(f"Réponse : {tronq(r.json()['answer'])}")
        ok("réponse obtenue")
    else:
        echec(f"HTTP {r.status_code}")


async def test_chat_recommandation_labo(client, headers):
    titre("8. CHAT — Recommandation de laboratoire")
    r = await client.post(f"{BASE}/chat", headers=headers, json={
        "question": "Quel laboratoire recommandez-vous pour une analyse urgente de sang de poulet ?",
    })
    if r.status_code == 200:
        info(f"Réponse : {tronq(r.json()['answer'])}")
        ok("réponse obtenue")
    else:
        echec(f"HTTP {r.status_code}")


async def test_chat_hors_sujet(client, headers):
    titre("9. CHAT — Hors sujet (doit refuser)")
    r = await client.post(f"{BASE}/chat", headers=headers, json={
        "question": "Quel est le score du match de football de ce soir ?",
    })
    if r.status_code == 200:
        answer = r.json()["answer"].lower()
        mots_refus = ("hors", "domaine", "ne peux pas", "spécialisé", "avicole")
        if any(m in answer for m in mots_refus):
            ok("refus hors-sujet correct")
        else:
            echec(f"Le chatbot aurait dû refuser. Réponse : {tronq(answer)}")
    else:
        echec(f"HTTP {r.status_code}")


async def test_chat_sans_token(client):
    titre("9b. CHAT — Sans token (doit retourner 401/403)")
    r = await client.post(f"{BASE}/chat", json={"question": "Test sans token."})
    if r.status_code in (401, 403):
        ok(f"HTTP {r.status_code} comme attendu")
    else:
        echec(f"Attendu 401 ou 403, recu {r.status_code}")


async def test_chat_client(client):
    titre("9c. CHAT — Accès avec compte Client (CHAT_READ)")
    u = USERS["Client"][0]
    r_login = await client.post(f"{BASE}/auth/login",
        json={"email": u["email"], "password": PASSWORD})
    if r_login.status_code != 200:
        echec(f"Login {u['email']} échoué : {r_login.text[:100]}")
        return
    token = r_login.json()["access_token"]
    r = await client.post(f"{BASE}/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Bonjour, pouvez-vous m'aider ?"},
    )
    if r.status_code == 200:
        ok(f"Client {u['email']} a accès au chat")
        info(f"Réponse : {tronq(r.json()['answer'])}")
    else:
        echec(f"HTTP {r.status_code} — {tronq(r.text)}")


# ---------------------------------------------------------------------------
# 10. Souche predict
# ---------------------------------------------------------------------------
async def test_souche_predict(client, headers):
    titre("10. SOUCHE PREDICT — 3 types de production")
    for prod in ["Poulet de chair", "Oeuf", "Dinde"]:
        r = await client.post(f"{BASE}/souches/predict", headers=headers,
            json={**SOUCHE_PAYLOAD, "type_production": prod})
        if r.status_code == 200:
            d = r.json()
            ok(f"{prod:<22} => {d['souche']:<20} ({d.get('confiance_pct', '?')}%)  [{d['model']}]")
        else:
            echec(f"{prod:<22} => HTTP {r.status_code}")


# ---------------------------------------------------------------------------
# 11. Labos recommend
# ---------------------------------------------------------------------------
async def test_labos_recommend(client, headers):
    titre("11. LABOS RECOMMEND — Filtres variés")
    cas = [
        ("Tous",            {}),
        ("Urgence",         {"urgence": True}),
        ("Tunis",           {"ville": "Tunis"}),
        ("Sfax",            {"ville": "Sfax"}),
        ("Urgence + Tunis", {"urgence": True, "ville": "Tunis"}),
    ]
    for label, params in cas:
        r = await client.get(f"{BASE}/labos/recommend", headers=headers, params=params)
        if r.status_code == 200:
            labos = r.json().get("labos", [])
            if labos:
                top = labos[0]
                ok(f"{label:<22} => {top.get('nom_laboratoire', '?')}  score={top.get('score_global', '?')}")
            else:
                info(f"{label:<22} => aucun labo retourné")
        else:
            echec(f"{label:<22} => HTTP {r.status_code}")


# ---------------------------------------------------------------------------
# 12. Data endpoints (Breeds + FarmCenters)
# ---------------------------------------------------------------------------
async def test_data_endpoints(client, headers):
    titre("12. DATA — Breeds (souches) et FarmCenters (centres)")
    endpoints = [
        ("/data/count",   "Compteurs globaux"),
        ("/data/labos",   "Laboratoires"),
        ("/data/souches", "Breeds (souches)"),
        ("/data/centres", "FarmCenters (centres)"),
    ]
    for path, label in endpoints:
        r = await client.get(f"{BASE}{path}", headers=headers)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                ok(f"{label:<25} => HTTP 200  ({len(data)} entrées)")
            else:
                ok(f"{label:<25} => HTTP 200  {tronq(data, 60)}")
        else:
            echec(f"{label:<25} => HTTP {r.status_code} — {tronq(r.text, 80)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║     TEST RAPIDE — CHATBOT POULELABAPP (PouleLabDB)                  ║
║     Mot de passe universel : Admin@1234                             ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            await client.get(f"{BASE}/health", timeout=5)
        except Exception:
            print("ERREUR : Serveur FastAPI inaccessible. Lancez : python main.py")
            sys.exit(1)

        await test_health(client)
        await test_entrainement(client)
        await test_status(client)
        await test_auth_mauvais_mdp(client)
        await test_auth_tous_les_users(client)

        token = await test_login_admin(client)
        if token is None:
            print("\nARRET : Login admin échoué.")
            print("  Relancez dotnet run pour que DataSeeder crée admin@poulelabapp.com / Admin@1234")
            sys.exit(1)

        headers = {"Authorization": f"Bearer {token}"}

        await test_chat_question_simple(client, headers)
        await test_chat_avec_contexte_ml(client, headers)
        await test_chat_maladie(client, headers)
        await test_chat_recommandation_labo(client, headers)
        await test_chat_hors_sujet(client, headers)
        await test_chat_sans_token(client)
        await test_chat_client(client)
        await test_souche_predict(client, headers)
        await test_labos_recommend(client, headers)
        await test_data_endpoints(client, headers)

    print(f"\n{'=' * 70}")
    print("  Tests terminés.")
    print("  Suite complète : pytest tests/test_integration_poulelabdb.py -v")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())