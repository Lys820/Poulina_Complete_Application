#!/usr/bin/env python
"""
TEST QUICK POULINA - Verifier API marche
Commande: python test_quick_cro.py
"""
import asyncio
import httpx
import json

BASE = "http://localhost:8000/api/v1"
TIMEOUT = 60

# Fonctions aide ---------------------------------------------------------------

def titre(texte: str):
    print(f"\n{'='*70}")
    print(f"  {texte}")
    print('='*70)

def ok(msg):  
    print(f"  [OK] {msg}")

def erreur(msg): 
    print(f"  [ERREUR] {msg}")

def montrer(donnees, cles):
    for cle in cles:
        valeur = donnees.get(cle, "N/A")
        if isinstance(valeur, float): 
            valeur = round(valeur, 3)
        print(f"     {cle}: {valeur}")


# Tests -----------------------------------------------------------------------

async def test_health(client):
    titre("1. VERIFIER SERVEUR")
    r = await client.get(f"{BASE}/health")
    d = r.json()
    if r.status_code == 200:
        ok(f"statut={d['status']}  fournisseur={d.get('llm_provider')}  embedding={d.get('embedding')}")
    else:
        erreur(f"HTTP {r.status_code}")
    return r.status_code == 200


async def test_train_sqlserver(client):
    titre("2. ENTRAINER DEPUIS SQL SERVER")
    print("  (peut prendre quelques secondes...)")
    try:
        r = await client.post(f"{BASE}/analyses/train-from-sqlserver")

        print("STATUS =", r.status_code)
        print("TEXT =")
        print(r.text)

        try:
            d = r.json()
            print(d)

        except Exception as e:
            print("JSON ERROR =", e)
        #d = r.json()
        if r.status_code == 200:
            ok(f"statut={d['status']}")
            ok(f"analyses indexees : {d['analyses']['docs']} docs  [{d['analyses']['embedder']}]")
            ok(f"labos indexes     : {d['labos']['docs']} docs")
            ok(f"modele souche     : {d['model_status']['souche'].get('model')}  acc={d['model_status']['souche'].get('accuracy', 0):.3f}")
            ok(f"modele labo       : {d['model_status']['labo'].get('model')}  acc={d['model_status']['labo'].get('accuracy', 0):.3f}")
            ok(f"entraine a        : {d.get('trained_at')}")
            return True
        else:
            erreur(f"HTTP {r.status_code}")
            if isinstance(d, dict):
                erreur(f"Detail: {d.get('detail', d)}")
            return False
    except Exception as e:
        erreur(f"Exception: {e}")
        return False


async def test_status(client):
    titre("3. STATUT DETAILLE")
    r = await client.get(f"{BASE}/status")
    d = r.json()
    if r.status_code == 200:
        ok(f"rag_ready={d['rag_ready']}  ml_ready={d['ml_ready']}")
        ok(f"modele souche : {d['ml_models']['souche']['model']}  acc={d['ml_models']['souche'].get('accuracy',0):.3f}")
        ok(f"modele labo   : {d['ml_models']['labo']['model']}  acc={d['ml_models']['labo'].get('accuracy',0):.3f}")
    else:
        erreur(f"HTTP {r.status_code}")


async def test_chat_simple(client):
    titre("4. CHAT - Souche par ville")
    r = await client.post(f"{BASE}/chat", json={
        "question": "Quelle est la meilleure souche pour un elevage poulet chair a Bizerte ?"
    })
    d = r.json()
    if r.status_code == 200:
        ok(f"modele : {d['model_used']}")
        ok(f"temps : {d['execution_time_ms']} ms")
        ok(f"analyses recuperees : {len(d['retrieved_analyses'])}")
        print(f"\n  REPONSE :\n  {d['answer'][:400]}...")
    else:
        erreur(f"HTTP {r.status_code} - {d}")


async def test_chat_maladie(client):
    titre("5. CHAT - Alerte maladie critique")
    r = await client.post(f"{BASE}/chat", json={
        "question": "Y a-t-il des centres atteints de Salmonelle ou Newcastle ? Quels centres sont a risque ?"
    })
    d = r.json()
    if r.status_code == 200:
        ok(f"modele : {d['model_used']}")
        print(f"\n  REPONSE :\n  {d['answer'][:400]}...")
    else:
        erreur(f"HTTP {r.status_code}")


async def test_chat_labo(client):
    titre("6. CHAT - Recommandation laboratoire urgent")
    r = await client.post(f"{BASE}/chat", json={
        "question": "Quel est le meilleur laboratoire disponible en urgence pour une analyse Salmonelle a Sfax ?"
    })
    d = r.json()
    if r.status_code == 200:
        ok(f"labos recuperes : {len(d['retrieved_labos'])}")
        ok(f"modele : {d['model_used']}")
        print(f"\n  REPONSE :\n  {d['answer'][:400]}...")
    else:
        erreur(f"HTTP {r.status_code}")


async def test_chat_ml(client):
    titre("7. CHAT - Avec prediction ML souche")
    r = await client.post(f"{BASE}/chat", json={
        "question": "Quelle souche recommandes-tu pour ce profil ?",
        "predict_souche": {
            "type_production": "Poulet de chair",
            "biosecurite_score": 9.0,
            "taux_mortalite": 2.0,
            "temperature_moyenne": 28,
            "humidite": 55,
            "fertilite_visee": 94,
            "capacite": 15000,
            "surface_m2": 800,
            "experience_equipe": 8,
            "distance_labo": 10,
            "budget": 80000,
            "saison": "Ete",
            "demande_marche": "Eleve",
            "cout_aliment": 5.2
        }
    })
    d = r.json()
    if r.status_code == 200:
        pred = d.get("souche_prediction")
        if pred:
            ok(f"Prediction ML : {pred['souche']}  ({pred['confiance_pct']}%)")
            ok(f"Alternatives  : {pred.get('alternatives', [])}")
            ok(f"Modele        : {pred['model']}")
        else:
            print("  [ATTENTION] Pas de prediction ML (modele non entraine ?)")
        print(f"\n  REPONSE :\n  {d['answer'][:300]}...")
    else:
        erreur(f"HTTP {r.status_code}")


async def test_chat_hors_sujet(client):
    titre("8. CHAT - Hors sujet (doit refuser)")
    r = await client.post(f"{BASE}/chat", json={
        "question": "Quelle est la capitale de la France ?"
    })
    d = r.json()
    if r.status_code == 200:
        answer = d["answer"]
        if "hors" in answer.lower() or "domaine" in answer.lower():
            ok(f"Refus correct : {answer[:120]}")
        else:
            print(f"  [ATTENTION] Reponse inattendue : {answer[:120]}")
    else:
        erreur(f"HTTP {r.status_code}")


async def test_souche_predict(client):
    titre("9. SOUCHE PREDICT - Direct (sans chat)")
    cas = [
        ("Poulet de chair", 9.0, 2.0, 28, 55, 80000, "Ete"),
        ("Oeuf",            8.0, 1.5, 26, 60, 50000, "Hiver"),
        ("Dinde",           7.0, 4.0, 25, 58, 35000, "Automne"),
    ]
    for prod, bio, mort, temp, hum, budget, saison in cas:
        r = await client.post(f"{BASE}/souches/predict", json={
            "type_production": prod,
            "biosecurite_score": bio,
            "taux_mortalite": mort,
            "temperature_moyenne": temp,
            "humidite": hum,
            "fertilite_visee": 92,
            "capacite": 12000,
            "surface_m2": 600,
            "experience_equipe": 5,
            "distance_labo": 15,
            "budget": budget,
            "saison": saison,
            "demande_marche": "Eleve",
            "cout_aliment": 5.2
        })
        d = r.json()
        if r.status_code == 200 and "souche" in d:
            ok(f"{prod:<20} -> {d['souche']:<18} ({d['confiance_pct']}%)  [{d['model']}]")
        else:
            erreur(f"{prod} -> {d.get('error', d)}")


async def test_labos(client):
    titre("10. LABOS RECOMMEND")
    cas = [
        ("Tous",          {}),
        ("Urgence",       {"urgence": "true"}),
        ("Tunis urgence", {"urgence": "true", "ville": "Tunis"}),
        ("Sfax",          {"ville": "Sfax"}),
    ]
    for label, params in cas:
        r = await client.get(f"{BASE}/labos/recommend", params=params)
        d = r.json()
        if r.status_code == 200:
            labos = d.get("labos", [])
            if labos:
                top = labos[0]
                ok(f"{label:<18} -> {top.get('nom_laboratoire','?')} | score={top.get('score_global','?')} | tier={top.get('tier_labo','?')}")
            else:
                print(f"  [ATTENTION] {label}: aucun labo retourne")
        else:
            erreur(f"{label} -> HTTP {r.status_code}")


# Main -----------------------------------------------------------------------

async def main():
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║              POULINA - TEST QUICK (API complete)                           ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:

        # Verifie que le serveur tourne
        try:
            await client.get(f"{BASE}/health")
        except Exception:
            print("ERREUR : Serveur inaccessible. Lance d'abord : python main.py")
            return

        ok_train = await test_health(client)
        ok_train = await test_train_sqlserver(client)

        if not ok_train:
            print("\nATTENTION : Entrainement SQL Server echoue - tests chat/ML seront limites.")

        await test_status(client)
        await test_chat_simple(client)
        await test_chat_maladie(client)
        await test_chat_labo(client)
        await test_chat_ml(client)
        await test_chat_hors_sujet(client)
        await test_souche_predict(client)
        await test_labos(client)

    print(f"\n{'='*70}")
    print("  Tests termines")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())