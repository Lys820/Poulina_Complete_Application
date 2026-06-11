#!/usr/bin/env python
"""
TEST RAPIDE POULELABDB — Vérification manuelle complète du chatbot
Compte seeder : admin@poulelabapp.com / Admin@1234
Base de données : PouleLabDB (VICTUSL\SQLEXPRESS)

Commande :
    python test_rapide_poulelabdb.py

Le serveur FastAPI doit tourner sur http://localhost:8000.
"""
import asyncio
import json
import sys

import httpx

BASE = "http://localhost:8000/api/v1"
TIMEOUT = 90

ADMIN_EMAIL = "admin@poulelabapp.com"
ADMIN_PASSWORD = "Admin@1234"

# ---------------------------------------------------------------------------
# Helpers d'affichage
# ---------------------------------------------------------------------------

def titre(texte: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {texte}")
    print("=" * 70)


def ok(msg: str) -> None:
    print(f"  [OK]     {msg}")


def echec(msg: str) -> None:
    print(f"  [ECHEC]  {msg}")


def info(msg: str) -> None:
    print(f"           {msg}")


def tronquer(valeur: object, n: int = 120) -> str:
    s = str(valeur)
    return s[:n] + "..." if len(s) > n else s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_health(client: httpx.AsyncClient) -> bool:
    titre("1. HEALTH CHECK")
    r = await client.get(f"{BASE}/health")
    if r.status_code == 200:
        d = r.json()
        ok(f"statut={d['status']}  provider={d.get('llm_provider')}  embedding={d.get('embedding')}")
        if d.get("llm_provider") != "genai":
            echec("LLM_PROVIDER devrait etre 'genai' — verifier .env")
        return True
    echec(f"HTTP {r.status_code}")
    return False


async def test_entrainement(client: httpx.AsyncClient) -> bool:
    titre("2. ENTRAINEMENT DEPUIS POULELABDB")
    print("  (peut prendre 10-30 secondes selon le volume de donnees...)")
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
        echec(f"HTTP {r.status_code} — {tronquer(r.text)}")
        return False
    except Exception as e:
        echec(f"Exception : {e}")
        return False


async def test_status(client: httpx.AsyncClient) -> None:
    titre("3. STATUT DETAILLE")
    r = await client.get(f"{BASE}/status")
    if r.status_code == 200:
        d = r.json()
        ok(f"rag_ready={d['rag_ready']}  ml_ready={d['ml_ready']}")
        souche = d["ml_models"]["souche"]
        labo = d["ml_models"]["labo"]
        ok(f"modele souche : {souche['model']}  acc={souche.get('accuracy', 0):.3f}")
        ok(f"modele labo   : {labo['model']}  acc={labo.get('accuracy', 0):.3f}")
    else:
        echec(f"HTTP {r.status_code}")


async def test_login(client: httpx.AsyncClient) -> str | None:
    titre("4. AUTHENTIFICATION (compte DataSeeder)")
    r = await client.post(f"{BASE}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    if r.status_code == 200:
        d = r.json()
        token = d["access_token"]
        ok(f"role={d['role']}  permissions={d['permissions']}")
        ok(f"token (debut) : {token[:40]}...")
        return token
    echec(f"HTTP {r.status_code} — {tronquer(r.text)}")
    return None


async def test_login_mauvais_mdp(client: httpx.AsyncClient) -> None:
    titre("4b. AUTHENTIFICATION — Mauvais mot de passe (doit retourner 401)")
    r = await client.post(f"{BASE}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": "MauvaisMotDePasse!",
    })
    if r.status_code == 401:
        ok("401 recu comme attendu")
    else:
        echec(f"Attendu 401, recu {r.status_code}")


async def test_chat_question_simple(client: httpx.AsyncClient, headers: dict) -> None:
    titre("5. CHAT — Question domaine avicole")
    r = await client.post(f"{BASE}/chat", headers=headers, json={
        "question": "Quelle est la meilleure souche pour un elevage de poulet de chair en Tunisie ?",
    })
    if r.status_code == 200:
        d = r.json()
        ok(f"session={d['session_id'][:12]}...  modele={d['model_used']}")
        info(f"Reponse : {tronquer(d['answer'])}")
    else:
        echec(f"HTTP {r.status_code} — {tronquer(r.text)}")


async def test_chat_avec_contexte_ml(client: httpx.AsyncClient, headers: dict) -> None:
    titre("6. CHAT — Avec contexte ML (predict_souche)")
    r = await client.post(f"{BASE}/chat", headers=headers, json={
        "question": "Quelle souche recommandez-vous pour mon elevage ?",
        "predict_souche": {
            "type_production": "Poulet de chair",
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
            "demande_marche": "Eleve",
            "cout_aliment": 5.2,
        },
    })
    if r.status_code == 200:
        d = r.json()
        ok(f"session={d['session_id'][:12]}...")
        info(f"Reponse : {tronquer(d['answer'])}")
    else:
        echec(f"HTTP {r.status_code} — {tronquer(r.text)}")


async def test_chat_maladie(client: httpx.AsyncClient, headers: dict) -> None:
    titre("7. CHAT — Alerte maladie avicole")
    r = await client.post(f"{BASE}/chat", headers=headers, json={
        "question": "Y a-t-il des cas de Salmonelle ou de Newcastle signales recemment ?",
    })
    if r.status_code == 200:
        info(f"Reponse : {tronquer(r.json()['answer'])}")
        ok("reponse obtenue")
    else:
        echec(f"HTTP {r.status_code}")


async def test_chat_recommandation_labo(client: httpx.AsyncClient, headers: dict) -> None:
    titre("8. CHAT — Recommandation de laboratoire")
    r = await client.post(f"{BASE}/chat", headers=headers, json={
        "question": "Quel laboratoire recommandez-vous pour une analyse urgente de sang de poulet ?",
    })
    if r.status_code == 200:
        info(f"Reponse : {tronquer(r.json()['answer'])}")
        ok("reponse obtenue")
    else:
        echec(f"HTTP {r.status_code}")


async def test_chat_hors_sujet(client: httpx.AsyncClient, headers: dict) -> None:
    titre("9. CHAT — Hors sujet (doit refuser)")
    r = await client.post(f"{BASE}/chat", headers=headers, json={
        "question": "Quel est le score du match de football de ce soir ?",
    })
    if r.status_code == 200:
        answer = r.json()["answer"].lower()
        mots_refus = ("hors", "domaine", "ne peux pas", "specialise", "avicole")
        if any(m in answer for m in mots_refus):
            ok("refus hors-sujet correct")
        else:
            echec(f"Le chatbot aurait du refuser, reponse : {tronquer(answer)}")
    else:
        echec(f"HTTP {r.status_code}")


async def test_souche_predict(client: httpx.AsyncClient, headers: dict) -> None:
    titre("10. SOUCHE PREDICT — Endpoint direct (3 types de production)")
    payload_base = {
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
        "demande_marche": "Eleve",
        "cout_aliment": 5.2,
    }
    for prod in ["Poulet de chair", "Oeuf", "Dinde"]:
        r = await client.post(
            f"{BASE}/souches/predict",
            headers=headers,
            json={**payload_base, "type_production": prod},
        )
        if r.status_code == 200:
            d = r.json()
            ok(f"{prod:<22} => {d['souche']:<20} ({d.get('confiance_pct', '?')}%)  [{d['model']}]")
        else:
            echec(f"{prod:<22} => HTTP {r.status_code}")


async def test_labos_recommend(client: httpx.AsyncClient, headers: dict) -> None:
    titre("11. LABOS RECOMMEND — Filtres varies (labos PouleLabDB : DICK, SNA, GIPA, MEDOIL)")
    cas = [
        ("Tous",             {}),
        ("Urgence",          {"urgence": True}),
        ("Tunis (DICK)",     {"ville": "Tunis"}),
        ("Sfax (SNA)",       {"ville": "Sfax"}),
        ("Urgence + Tunis",  {"urgence": True, "ville": "Tunis"}),
    ]
    for label, params in cas:
        r = await client.get(f"{BASE}/labos/recommend", headers=headers, params=params)
        if r.status_code == 200:
            labos = r.json().get("labos", [])
            if labos:
                top = labos[0]
                ok(f"{label:<22} => {top.get('nom_laboratoire', '?')}  score={top.get('score_global', '?')}")
            else:
                info(f"{label:<22} => aucun labo retourne")
        else:
            echec(f"{label:<22} => HTTP {r.status_code}")


async def test_data_endpoints(client: httpx.AsyncClient, headers: dict) -> None:
    titre("12. DATA — Lectures directes PouleLabDB")
    endpoints = [
        ("/data/count",   "Compteurs globaux"),
        ("/data/labos",   "Laboratoires"),
        ("/data/souches", "Souches"),
        ("/data/centres", "Centres d'elevage"),
    ]
    for path, label in endpoints:
        r = await client.get(f"{BASE}{path}", headers=headers)
        if r.status_code == 200:
            ok(f"{label:<22} => HTTP 200")
        else:
            echec(f"{label:<22} => HTTP {r.status_code}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║         TEST RAPIDE — CHATBOT POULELABAPP (PouleLabDB)                    ║
║         Compte : admin@poulelabapp.com / Admin@1234                       ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:

        # Vérifier que le serveur est démarré
        try:
            await client.get(f"{BASE}/health", timeout=5)
        except Exception:
            print("ERREUR : Le serveur FastAPI est inaccessible.")
            print("         Demarrez-le d'abord avec : python main.py")
            sys.exit(1)

        health_ok = await test_health(client)
        train_ok = await test_entrainement(client)

        if not train_ok:
            print("\nATTENTION : L'entrainement a echoue.")
            print("  Verifiez que PouleLabDB contient des donnees (AnalysisRequests, Samples).")
            print("  Les tests de chat et ML seront probablement limites.\n")

        await test_status(client)
        await test_login_mauvais_mdp(client)

        token = await test_login(client)
        if token is None:
            print("\nARRET : Impossible de se connecter avec le compte DataSeeder.")
            print("  1. L'API .NET est-elle demarree (dotnet run) ?")
            print("  2. La migration a-t-elle ete appliquee (dotnet ef database update) ?")
            print("  3. Le DataSeeder a-t-il cree admin@poulelabapp.com / Admin@1234 ?")
            sys.exit(1)

        headers = {"Authorization": f"Bearer {token}"}

        await test_chat_question_simple(client, headers)
        await test_chat_avec_contexte_ml(client, headers)
        await test_chat_maladie(client, headers)
        await test_chat_recommandation_labo(client, headers)
        await test_chat_hors_sujet(client, headers)
        await test_souche_predict(client, headers)
        await test_labos_recommend(client, headers)
        await test_data_endpoints(client, headers)

    print(f"\n{'=' * 70}")
    print("  Tests termines.")
    print("  Pour une suite exhaustive avec assertions : pytest test_integration_poulelabdb.py -v")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())
